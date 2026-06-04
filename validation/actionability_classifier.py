"""
Actionability Classifier — Post-comparison classification for ACTION REQUIRED
and REVIEW CATEGORY columns.

Runs AFTER comparison is complete. Does NOT modify comparison logic, counts,
or matching. Reads the existing CHANGES dict on Modified rows to determine
classification.

All business rules are loaded from config/actionability_rules.py.
"""

import pandas as pd
import numpy as np
from config.actionability_rules import (
    ENABLE_ACTIONABILITY_CLASSIFIER,
    ENABLE_LOW_TORQUE_AUTO_IGNORE,
    ENABLE_LOW_TORQUE_ADDED_AUTO_IGNORE,
    LOW_TORQUE_THRESHOLD,
    LOW_TORQUE_EVALUATION_FIELDS,
    ACTIONABLE_FIELDS,
    ADMINISTRATIVE_FIELDS,
    REVIEW_CATEGORIES,
    CATEGORY_PRIORITY,
    FIELD_CATEGORY_MAP,
)


def _safe_float(val):
    """Parse a numeric value from a string, returning None on failure."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        if isinstance(val, float) and np.isnan(val):
            return None
        return float(val)
    s = str(val).strip()
    if not s:
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _parse_change_values(change_str):
    """
    Parse 'old_val → new_val' from the CHANGES dict value.
    Returns (old_str, new_str) or (None, None) on failure.
    """
    if not isinstance(change_str, str):
        return None, None
    # Handle the → separator used by the comparison engine
    if " \u2192 " in change_str:
        parts = change_str.split(" \u2192 ", 1)
        return parts[0].strip(), parts[1].strip()
    # Fallback: arrow variants
    for sep in [" -> ", " --> "]:
        if sep in change_str:
            parts = change_str.split(sep, 1)
            return parts[0].strip(), parts[1].strip()
    return None, None


def is_low_torque_change(changes_dict):
    """
    Check if ALL low-torque evaluation fields have BOTH old and new values
    below the threshold. Returns True if this is a low-torque-only change.

    Only evaluates fields listed in LOW_TORQUE_EVALUATION_FIELDS that
    actually appear in the changes dict.
    """
    if not ENABLE_LOW_TORQUE_AUTO_IGNORE:
        return False

    # Find which evaluation fields actually changed
    eval_fields_changed = [
        f for f in LOW_TORQUE_EVALUATION_FIELDS if f in changes_dict
    ]

    if not eval_fields_changed:
        return False

    for field in eval_fields_changed:
        old_str, new_str = _parse_change_values(changes_dict[field])
        old_val = _safe_float(old_str)
        new_val = _safe_float(new_str)

        if old_val is None or new_val is None:
            return False

        # 0 or 0.0 is actionable — not a low-torque change
        if old_val == 0 or new_val == 0:
            return False

        # If EITHER value crosses the threshold, NOT a low-torque change
        if old_val >= LOW_TORQUE_THRESHOLD or new_val >= LOW_TORQUE_THRESHOLD:
            return False

    return True


def _is_threshold_crossing(changes_dict):
    """
    Check if any LOW_TORQUE_EVALUATION_FIELD crosses the threshold
    (one side < threshold, other side >= threshold).
    """
    for field in LOW_TORQUE_EVALUATION_FIELDS:
        if field not in changes_dict:
            continue
        old_str, new_str = _parse_change_values(changes_dict[field])
        old_val = _safe_float(old_str)
        new_val = _safe_float(new_str)
        if old_val is None or new_val is None:
            continue
        if (old_val < LOW_TORQUE_THRESHOLD) != (new_val < LOW_TORQUE_THRESHOLD):
            return True
    return False


def determine_review_category(changes_dict):
    """
    Determine the REVIEW CATEGORY for a Modified row based on which fields
    changed. Follows the priority order defined in CATEGORY_PRIORITY.

    Returns (category_label, category_id).
    """
    changed_fields = set(changes_dict.keys())

    # Collect all category IDs that apply
    matched_categories = set()
    for field in changed_fields:
        if field in FIELD_CATEGORY_MAP:
            matched_categories.add(FIELD_CATEGORY_MAP[field])

    # Pick highest-priority match
    for cat_id in CATEGORY_PRIORITY:
        if cat_id in matched_categories:
            # Special case: TORQUE category with low-torque override
            if cat_id == "TORQUE" and is_low_torque_change(changes_dict):
                return REVIEW_CATEGORIES.get("LOW_TORQUE", "Low Torque Change"), "LOW_TORQUE"
            return REVIEW_CATEGORIES.get(cat_id, cat_id), cat_id

    # No actionable fields matched — check if admin-only
    admin_set = set(ADMINISTRATIVE_FIELDS)
    if changed_fields and changed_fields.issubset(admin_set):
        return REVIEW_CATEGORIES.get("ADMIN", "Administrative Change"), "ADMIN"

    # Fallback: fields changed but none matched any category
    return REVIEW_CATEGORIES.get("ADMIN", "Administrative Change"), "ADMIN"


def classify_modified_actionability(modified_df):
    """
    Classify each Modified row for ACTION REQUIRED and REVIEW CATEGORY.

    Reads the CHANGES column (dict) already produced by the comparison engine.
    Appends two new columns: ACTION REQUIRED, REVIEW CATEGORY.

    Returns modified_df with new columns + diagnostics dict.
    """
    diagnostics = {"modified_input": len(modified_df)}

    if modified_df.empty or "CHANGES" not in modified_df.columns:
        modified_df["ACTION REQUIRED"] = pd.Series(dtype="str")
        modified_df["REVIEW CATEGORY"] = pd.Series(dtype="str")
        diagnostics["action_yes"] = 0
        diagnostics["action_no"] = 0
        return modified_df, diagnostics

    actions = []
    categories = []
    admin_set = set(ADMINISTRATIVE_FIELDS)
    actionable_set = set(ACTIONABLE_FIELDS)

    cat_counts = {}
    low_torque_count = 0
    threshold_crossing_count = 0
    admin_count = 0

    for _, row in modified_df.iterrows():
        changes = row.get("CHANGES", {})
        if not isinstance(changes, dict):
            changes = {}

        changed_fields = set(changes.keys())

        # Determine category
        cat_label, cat_id = determine_review_category(changes)
        categories.append(cat_label)
        cat_counts[cat_label] = cat_counts.get(cat_label, 0) + 1

        # Determine action required
        if cat_id == "LOW_TORQUE":
            actions.append("NO")
            low_torque_count += 1
        elif not changed_fields.isdisjoint(actionable_set):
            # At least one ACTIONABLE_FIELD changed
            actions.append("YES")
            if _is_threshold_crossing(changes):
                threshold_crossing_count += 1
        else:
            # NO actionable fields changed -> NO Action Required
            actions.append("NO")
            if changed_fields and changed_fields.issubset(admin_set):
                admin_count += 1

    modified_df = modified_df.copy()
    modified_df["ACTION REQUIRED"] = actions
    modified_df["REVIEW CATEGORY"] = categories

    diagnostics["action_yes"] = actions.count("YES")
    diagnostics["action_no"] = actions.count("NO")
    diagnostics["category_breakdown"] = cat_counts
    diagnostics["low_torque_changes"] = low_torque_count
    diagnostics["threshold_crossings"] = threshold_crossing_count
    diagnostics["admin_changes"] = admin_count

    return modified_df, diagnostics


def classify_added_actionability(added_df):
    """
    Classify each Added row.

    If ENABLE_LOW_TORQUE_ADDED_AUTO_IGNORE is True, Added rows where ALL
    LOW_TORQUE_EVALUATION_FIELDS are below LOW_TORQUE_THRESHOLD are
    classified as non-actionable "New Low Torque Record".

    All other Added rows remain ACTION REQUIRED = YES.

    Returns added_df with new columns + diagnostics dict.
    """
    diagnostics = {"added_input": len(added_df)}

    if added_df.empty:
        added_df["ACTION REQUIRED"] = pd.Series(dtype="str")
        added_df["REVIEW CATEGORY"] = pd.Series(dtype="str")
        diagnostics["added_action_yes"] = 0
        diagnostics["added_action_no"] = 0
        return added_df, diagnostics

    new_label = REVIEW_CATEGORIES.get("NEW", "New Engineering Record")
    low_torque_label = REVIEW_CATEGORIES.get("NEW_LOW_TORQUE", "New Low Torque Record")

    added_df = added_df.copy()

    if ENABLE_LOW_TORQUE_ADDED_AUTO_IGNORE and LOW_TORQUE_EVALUATION_FIELDS:
        actions = []
        categories = []
        cat_counts = {}

        for _, row in added_df.iterrows():
            is_low = True
            for field in LOW_TORQUE_EVALUATION_FIELDS:
                val = _safe_float(row.get(field, None))
                # 0 or 0.0 is actionable — only 0 < val < threshold is low-torque
                if val is None or val == 0 or val >= LOW_TORQUE_THRESHOLD:
                    is_low = False
                    break

            if is_low:
                actions.append("NO")
                categories.append(low_torque_label)
                cat_counts[low_torque_label] = cat_counts.get(low_torque_label, 0) + 1
            else:
                actions.append("YES")
                categories.append(new_label)
                cat_counts[new_label] = cat_counts.get(new_label, 0) + 1

        added_df["ACTION REQUIRED"] = actions
        added_df["REVIEW CATEGORY"] = categories

        diagnostics["added_action_yes"] = actions.count("YES")
        diagnostics["added_action_no"] = actions.count("NO")
        diagnostics["category_breakdown"] = cat_counts
    else:
        added_df["ACTION REQUIRED"] = "YES"
        added_df["REVIEW CATEGORY"] = new_label
        diagnostics["added_action_yes"] = len(added_df)
        diagnostics["added_action_no"] = 0
        diagnostics["category_breakdown"] = {new_label: len(added_df)}

    return added_df, diagnostics


def apply_actionability_labels(modified_df, added_df):
    """
    Main entry point. Applies actionability classification to Modified
    and Added DataFrames.

    Returns (modified_df, added_df, combined_diagnostics).

    Does NOT modify comparison counts or other DataFrames.
    """
    if not ENABLE_ACTIONABILITY_CLASSIFIER:
        return modified_df, added_df, {"status": "DISABLED via ENABLE_ACTIONABILITY_CLASSIFIER=False"}

    modified_df, mod_diags = classify_modified_actionability(modified_df)
    added_df, add_diags = classify_added_actionability(added_df)

    combined = {
        "status": "Actionability classification applied",
        "modified": mod_diags,
        "added": add_diags,
    }

    return modified_df, added_df, combined
