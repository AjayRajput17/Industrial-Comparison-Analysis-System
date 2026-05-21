"""
Rescue Pass — Post-processing reclassification of false Added/Deleted pairs.

Runs AFTER the main comparison engine completes.
Does NOT modify the main comparison architecture.

Strategy:
  PHASE A — ENGINE-same rescue:
    Build 6-column rescue anchor (includes ENGINE).
    If Added and Deleted share the same anchor → directly rescue as Modified.

  PHASE B — ENGINE-different rescue:
    Build 5-column core anchor (excludes ENGINE).
    If Added and Deleted share the core anchor but ENGINE differs,
    validate that all important business fields are identical.
    If valid → rescue as Modified.  If not → keep as true Added/Deleted.

Pairing rules:
  - Strict 1-to-1 (each row used at most once)
  - Multiple candidates → pick highest matching field count
  - Tie at top → do NOT rescue (conservative)
"""

import pandas as pd
import numpy as np

# ── 6-column rescue anchor (includes ENGINE) ──────────────────────────────────
RESCUE_ANCHOR_COLUMNS = [
    "MODEL YEAR",
    "PART NO",
    "VEH FAM",
    "PART USAGE DESC",
    "PHYSCL DESC",
    "ENGINE",
]

# ── 5-column core identity (never rescue if ANY of these differ) ──────────────
CORE_IDENTITY_COLUMNS = [
    "MODEL YEAR",
    "PART NO",
    "VEH FAM",
    "PART USAGE DESC",
    "PHYSCL DESC",
]

# ── Important business fields for ENGINE-difference validation ────────────────
IMPORTANT_BUSINESS_FIELDS = [
    "MIN",
    "MAX",
    "TRGT",
    "TORQUE STRATEGY",
    "TIGHTENING CLASS",
    "MODEL YEAR",
    "PART NO",
    "VEH FAM",
    "PART USAGE DESC",
    "PHYSCL DESC",
    "VSC NAME",
]

# ── Fields to exclude from change comments (same exclusions as main engine) ───
# ── To re-enable any field for comparison, remove it from this set ────────────
_SKIP_COMMENT = frozenset({
    "ROW ID", "ROW_ID", "ROWID", "ROW NO", "ROW_NO",
    "SR NO", "SR_NO", "SERIAL NO", "SERIAL_NO", "S NO", "S.NO",
    "INDEX", "__KEY__",
    "COMMENT", "COMMENTS",
    # "DECISIONED CN #",   # excluded — re-add to compare by removing this line
    # "DECISION DATE",     # excluded — re-add to compare by removing this line
    # "END ITEM PART",     # excluded — re-add to compare by removing this line
})


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _safe_str(val):
    """Convert a value to a comparable string, treating NaN as empty."""
    if val is None:
        return ""
    if isinstance(val, float) and np.isnan(val):
        return ""
    return str(val).strip()


def build_rescue_anchor(row_dict, columns):
    """Build a pipe-separated rescue anchor key from specified columns."""
    parts = []
    for col in columns:
        val = _safe_str(row_dict.get(col, "")).upper()
        # Strip trailing .0 from float representations
        if val.endswith(".0"):
            val = val[:-2]
        parts.append(val)
    return "|".join(parts)


def _count_matching_fields(added_dict, deleted_dict, compare_cols):
    """Count how many data fields match between two row dicts."""
    matches = 0
    for col in compare_cols:
        a_val = _safe_str(added_dict.get(col, ""))
        d_val = _safe_str(deleted_dict.get(col, ""))
        if a_val == d_val:
            matches += 1
        else:
            try:
                if float(a_val) == float(d_val):
                    matches += 1
            except (ValueError, TypeError):
                pass
    return matches


def _detect_changes(old_dict, new_dict, compare_cols):
    """
    Detect field-level changes between two row dicts.
    Returns dict of {column: "old_val → new_val"}.
    Uses same logic as main comparator's _detect_changes_dict.
    """
    changes = {}
    for col in compare_cols:
        if col.upper() in _SKIP_COMMENT:
            continue
        old_val = _safe_str(old_dict.get(col, ""))
        new_val = _safe_str(new_dict.get(col, ""))
        if old_val != new_val:
            try:
                if float(old_val) == float(new_val):
                    continue
            except (ValueError, TypeError):
                pass
            changes[col] = f"{old_val} \u2192 {new_val}"
    return changes


def validate_engine_difference(added_dict, deleted_dict):
    """
    Validate whether an ENGINE-different pair should be rescued.
    Returns True only if ALL important business fields are identical.
    If any important field differs → return False (do not rescue).
    """
    for col in IMPORTANT_BUSINESS_FIELDS:
        a_val = _safe_str(added_dict.get(col, ""))
        d_val = _safe_str(deleted_dict.get(col, ""))
        if a_val == d_val:
            continue
        # Numeric equivalence fallback
        try:
            if float(a_val) == float(d_val):
                continue
        except (ValueError, TypeError):
            pass
        return False
    return True


def _greedy_pair(a_indices, d_indices, added_rows, deleted_rows,
                 compare_cols, consumed_added, consumed_deleted,
                 require_engine_validation=False):
    """
    Greedy 1-to-1 pairing within a rescue anchor group.

    For each added row, scores all available deleted candidates by
    matching field count.  Picks the unique best; skips ties.

    Parameters
    ----------
    require_engine_validation : bool
        If True, candidates must pass validate_engine_difference().

    Returns
    -------
    List of (added_idx, deleted_idx) pairs.
    """
    pairs = []

    for a_idx in a_indices:
        if a_idx in consumed_added:
            continue

        candidates = []
        for d_idx in d_indices:
            if d_idx in consumed_deleted:
                continue

            # ENGINE-different validation gate
            if require_engine_validation:
                if not validate_engine_difference(
                    added_rows[a_idx], deleted_rows[d_idx]
                ):
                    continue

            score = _count_matching_fields(
                added_rows[a_idx], deleted_rows[d_idx], compare_cols
            )
            candidates.append((d_idx, score))

        if not candidates:
            continue

        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)

        # Tie at top → don't rescue
        if len(candidates) >= 2 and candidates[0][1] == candidates[1][1]:
            continue

        best_d_idx = candidates[0][0]
        pairs.append((a_idx, best_d_idx))
        consumed_added.add(a_idx)
        consumed_deleted.add(best_d_idx)

    return pairs


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN RESCUE FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def rescue_false_added_deleted(added_df, deleted_df):
    """
    Post-process Added and Deleted DataFrames to reclassify false pairs
    as Modified.

    Parameters
    ----------
    added_df  : pd.DataFrame — rows classified as "Added" by main engine.
    deleted_df: pd.DataFrame — rows classified as "Deleted" by main engine.

    Returns
    -------
    rescued_modified_df : pd.DataFrame — rescued rows (now Modified).
    remaining_added_df  : pd.DataFrame — true Added rows.
    remaining_deleted_df: pd.DataFrame — true Deleted rows.
    rescue_diagnostics  : dict
    """
    diagnostics = {
        "added_input": len(added_df),
        "deleted_input": len(deleted_df),
    }

    # Early exit if nothing to rescue
    if added_df.empty or deleted_df.empty:
        diagnostics["rescued_count"] = 0
        diagnostics["phase_a_rescued"] = 0
        diagnostics["phase_b_rescued"] = 0
        diagnostics["status"] = "Nothing to rescue (empty input)"
        return pd.DataFrame(), added_df, deleted_df, diagnostics

    # Convert to list of dicts for fast hash-map processing
    added_rows = added_df.to_dict("records")
    deleted_rows = deleted_df.to_dict("records")

    # Determine comparable columns (intersection minus skip set)
    common_cols = set(added_df.columns) & set(deleted_df.columns)
    compare_cols = sorted([c for c in common_cols if c.upper() not in _SKIP_COMMENT])

    consumed_added = set()
    consumed_deleted = set()
    rescued_pairs = []   # list of (added_idx, deleted_idx)

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE A — ENGINE-same rescue (6-column anchor match → direct rescue)
    # ══════════════════════════════════════════════════════════════════════════
    added_6col = {}
    for i, row in enumerate(added_rows):
        key = build_rescue_anchor(row, RESCUE_ANCHOR_COLUMNS)
        added_6col.setdefault(key, []).append(i)

    deleted_6col = {}
    for i, row in enumerate(deleted_rows):
        key = build_rescue_anchor(row, RESCUE_ANCHOR_COLUMNS)
        deleted_6col.setdefault(key, []).append(i)

    common_6col = set(added_6col.keys()) & set(deleted_6col.keys())

    for anchor in common_6col:
        pairs = _greedy_pair(
            added_6col[anchor], deleted_6col[anchor],
            added_rows, deleted_rows, compare_cols,
            consumed_added, consumed_deleted,
            require_engine_validation=False,
        )
        rescued_pairs.extend(pairs)

    phase_a_count = len(rescued_pairs)

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE B — ENGINE-different rescue (5-column core anchor + validation)
    # ══════════════════════════════════════════════════════════════════════════
    remaining_a_indices = [i for i in range(len(added_rows)) if i not in consumed_added]
    remaining_d_indices = [i for i in range(len(deleted_rows)) if i not in consumed_deleted]

    added_5col = {}
    for i in remaining_a_indices:
        key = build_rescue_anchor(added_rows[i], CORE_IDENTITY_COLUMNS)
        added_5col.setdefault(key, []).append(i)

    deleted_5col = {}
    for i in remaining_d_indices:
        key = build_rescue_anchor(deleted_rows[i], CORE_IDENTITY_COLUMNS)
        deleted_5col.setdefault(key, []).append(i)

    common_5col = set(added_5col.keys()) & set(deleted_5col.keys())

    for anchor in common_5col:
        pairs = _greedy_pair(
            added_5col[anchor], deleted_5col[anchor],
            added_rows, deleted_rows, compare_cols,
            consumed_added, consumed_deleted,
            require_engine_validation=True,   # ENGINE validation required
        )
        rescued_pairs.extend(pairs)

    phase_b_count = len(rescued_pairs) - phase_a_count

    # ══════════════════════════════════════════════════════════════════════════
    # GENERATE RESCUED MODIFIED ROWS (with change comments)
    # ══════════════════════════════════════════════════════════════════════════
    rescued_modified_rows = []
    for a_idx, d_idx in rescued_pairs:
        added_dict = added_rows[a_idx]
        deleted_dict = deleted_rows[d_idx]

        # Generate change comments: deleted = OLD side, added = NEW side
        changes = _detect_changes(deleted_dict, added_dict, compare_cols)

        # Output row is the NEW (added) side
        row_data = dict(added_dict)
        if changes:
            row_data["CHANGES"] = changes
        rescued_modified_rows.append(row_data)

    # ══════════════════════════════════════════════════════════════════════════
    # BUILD REMAINING TRUE ADDED / TRUE DELETED
    # ══════════════════════════════════════════════════════════════════════════
    remaining_added = [added_rows[i] for i in range(len(added_rows))
                       if i not in consumed_added]
    remaining_deleted = [deleted_rows[i] for i in range(len(deleted_rows))
                         if i not in consumed_deleted]

    rescued_df = pd.DataFrame(rescued_modified_rows) if rescued_modified_rows else pd.DataFrame()
    remaining_added_df = pd.DataFrame(remaining_added) if remaining_added else pd.DataFrame()
    remaining_deleted_df = pd.DataFrame(remaining_deleted) if remaining_deleted else pd.DataFrame()

    diagnostics["phase_a_rescued"] = phase_a_count
    diagnostics["phase_b_rescued"] = phase_b_count
    diagnostics["rescued_count"] = len(rescued_pairs)
    diagnostics["remaining_added"] = len(remaining_added)
    diagnostics["remaining_deleted"] = len(remaining_deleted)
    diagnostics["status"] = "Rescue pass completed"

    return rescued_df, remaining_added_df, remaining_deleted_df, diagnostics
