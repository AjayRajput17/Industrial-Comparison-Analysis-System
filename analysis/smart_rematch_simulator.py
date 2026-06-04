"""
Smart Re-Match Simulator — Phase 1 Analysis Only.

Investigates whether positional matching inside duplicate identity groups
causes incorrect Modified classifications.

STRICTLY ANALYTICAL:
  - Runs AFTER comparison completes
  - Does NOT affect comparison output, counts, or production runtime
  - Produces diagnostic reports only
  - Completely removable via feature flag or file deletion

When SMART_REMATCH_ANALYSIS_ENABLED = False:
  - Returns immediately
  - Zero overhead

Usage:
  from analysis.smart_rematch_simulator import run_smart_rematch_analysis
  report = run_smart_rematch_analysis(old_keyed, new_keyed, old_groups, new_groups, compare_cols)
"""

import pandas as pd
import numpy as np
import io
from config.smart_rematch_config import (
    SMART_REMATCH_ANALYSIS_ENABLED,
    SIMILARITY_WEIGHTS,
)

_NULL_ALIASES = frozenset({"", "NAN", "NONE", "NAT", "<NA>", "NULL", "_"})


def _safe_str(val):
    """Convert a value to a comparable string, treating NaN as empty."""
    if val is None:
        return ""
    if isinstance(val, float) and np.isnan(val):
        return ""
    return str(val).strip()


def _values_equal(old_val, new_val):
    """Check if two values are equal (string match or numeric equivalence)."""
    o = _safe_str(old_val)
    n = _safe_str(new_val)
    if o == n:
        return True
    try:
        if float(o) == float(n):
            return True
    except (ValueError, TypeError):
        pass
    return False


def _compute_similarity_score(old_dict, new_dict):
    """
    Compute a weighted similarity score between two row dicts.
    Uses SIMILARITY_WEIGHTS from config.
    """
    score = 0
    for field, weight in SIMILARITY_WEIGHTS.items():
        if _values_equal(old_dict.get(field, ""), new_dict.get(field, "")):
            score += weight
    return score


def _count_field_changes(old_dict, new_dict, compare_cols, skip_set):
    """Count how many comparable fields differ between two row dicts."""
    changes = 0
    for col in compare_cols:
        if col.upper() in skip_set:
            continue
        if not _values_equal(old_dict.get(col, ""), new_dict.get(col, "")):
            changes += 1
    return changes


def _detect_changes(old_dict, new_dict, compare_cols, skip_set):
    """Detect field-level changes, returns dict of {field: 'old → new'}."""
    changes = {}
    for col in compare_cols:
        if col.upper() in skip_set:
            continue
        o = _safe_str(old_dict.get(col, ""))
        n = _safe_str(new_dict.get(col, ""))
        if o != n:
            try:
                if float(o) == float(n):
                    continue
            except (ValueError, TypeError):
                pass
            changes[col] = f"{o} \u2192 {n}"
    return changes


# Skip set for change detection (same as main engine)
_SKIP_COMPARE = frozenset({
    "ROW ID", "ROW_ID", "ROWID", "ROW NO", "ROW_NO",
    "SR NO", "SR_NO", "SERIAL NO", "SERIAL_NO", "S NO", "S.NO",
    "INDEX", "__KEY__",
    "COMMENT", "COMMENTS",
    "DECISIONED CN #",
    "DECISION DATE",
    "END ITEM PART",
})


def run_smart_rematch_analysis(old_groups, new_groups, compare_cols):
    """
    Run the Smart Re-Match analysis on duplicate identity groups.

    Parameters
    ----------
    old_groups : dict  — {identity_key: [list of row dicts]} from OLD dataset
    new_groups : dict  — {identity_key: [list of row dicts]} from NEW dataset
    compare_cols : list — columns used for change detection

    Returns
    -------
    dict with keys:
        'diagnostics' : summary metrics dict
        'excel_bytes'  : bytes of SMART_REMATCH_ANALYSIS.xlsx (or None)
    """
    if not SMART_REMATCH_ANALYSIS_ENABLED:
        return {"diagnostics": {"status": "DISABLED"}, "excel_bytes": None}

    # ── Find duplicate identity groups ────────────────────────────────────────
    # Only groups where OLD or NEW has >1 row under the same identity key
    common_keys = set(old_groups.keys()) & set(new_groups.keys())

    dup_keys = []
    for key in common_keys:
        old_count = len(old_groups[key])
        new_count = len(new_groups[key])
        if old_count > 1 or new_count > 1:
            dup_keys.append(key)

    diagnostics = {
        "status": "COMPLETED",
        "total_common_keys": len(common_keys),
        "duplicate_groups": len(dup_keys),
    }

    if not dup_keys:
        diagnostics["rows_analysed"] = 0
        diagnostics["no_impact"] = 0
        diagnostics["potential_better_match"] = 0
        diagnostics["modified_to_nochange"] = 0
        diagnostics["modified_to_different_modified"] = 0
        return {"diagnostics": diagnostics, "excel_bytes": None}

    # ── Analyse each duplicate group ──────────────────────────────────────────
    potential_better_matches = []    # Category 2
    modified_to_nochange = []       # Category 3
    modified_to_diff_modified = []  # Category 4
    group_details = []              # Full dump
    no_impact_count = 0
    total_rows_analysed = 0

    for key in dup_keys:
        old_rows = old_groups[key]
        new_rows = new_groups[key]
        min_len = min(len(old_rows), len(new_rows))
        total_rows_analysed += min_len

        for pos_idx in range(min_len):
            old_dict = old_rows[pos_idx]
            new_dict = new_rows[pos_idx]

            # ── Current positional match result ───────────────────────────────
            current_score = _compute_similarity_score(old_dict, new_dict)
            current_changes = _detect_changes(old_dict, new_dict, compare_cols, _SKIP_COMPARE)
            current_change_count = len(current_changes)
            current_classification = "No Change" if current_change_count == 0 else "Modified"

            # ── Find best match for this OLD row across ALL NEW rows ──────────
            best_new_idx = pos_idx
            best_score = current_score
            best_change_count = current_change_count

            for candidate_idx in range(len(new_rows)):
                if candidate_idx == pos_idx:
                    continue
                candidate_score = _compute_similarity_score(old_dict, new_rows[candidate_idx])
                candidate_changes = _count_field_changes(
                    old_dict, new_rows[candidate_idx], compare_cols, _SKIP_COMPARE
                )

                # Better = higher similarity score, or same score but fewer changes
                if (candidate_score > best_score or
                        (candidate_score == best_score and candidate_changes < best_change_count)):
                    best_score = candidate_score
                    best_new_idx = candidate_idx
                    best_change_count = candidate_changes

            best_changes = _detect_changes(
                old_dict, new_rows[best_new_idx], compare_cols, _SKIP_COMPARE
            )
            best_classification = "No Change" if len(best_changes) == 0 else "Modified"

            # ── Check if Duplicate Group Rescue already handled this ──────────
            import config.duplicate_group_rescue_config as dgr_config
            if dgr_config.ENABLE_DUPLICATE_GROUP_RESCUE and best_score >= dgr_config.DUPLICATE_GROUP_RESCUE_MIN_SCORE:
                # The DGR layer successfully rescued this!
                # So the 'current' applied match in the pipeline is actually the best match.
                actual_applied_idx = best_new_idx
            else:
                # DGR is off, or score too low. Pipeline fell back to positional.
                actual_applied_idx = pos_idx

            # Re-evaluate current metrics based on what was ACTUALLY applied
            if actual_applied_idx != pos_idx:
                current_score = best_score
                current_changes = best_changes
                current_change_count = best_change_count
                current_classification = best_classification

            # ── Build row info for reports ────────────────────────────────────
            old_row_id = _safe_str(old_dict.get("ROW ID", ""))
            current_new_row_id = _safe_str(new_rows[actual_applied_idx].get("ROW ID", ""))
            best_new_row_id = _safe_str(new_rows[best_new_idx].get("ROW ID", ""))
            part_no = _safe_str(old_dict.get("PART NO", ""))

            # Group details entry
            group_details.append({
                "IDENTITY KEY": key,
                "PART NO": part_no,
                "OLD ROW POS": pos_idx,
                "OLD ROW ID": old_row_id,
                "OLD ROWS IN GROUP": len(old_rows),
                "NEW ROWS IN GROUP": len(new_rows),
                "CURRENT NEW POS": actual_applied_idx,
                "CURRENT NEW ROW ID": current_new_row_id,
                "CURRENT SCORE": current_score,
                "CURRENT CHANGES": current_change_count,
                "CURRENT CLASSIFICATION": current_classification,
                "BEST NEW POS": best_new_idx,
                "BEST NEW ROW ID": best_new_row_id,
                "BEST SCORE": best_score,
                "BEST CHANGES": best_change_count,
                "BEST CLASSIFICATION": best_classification,
            })

            # ── Categorize ────────────────────────────────────────────────────
            if best_new_idx == actual_applied_idx:
                # Category 1: No impact — actual applied match IS the best
                no_impact_count += 1
                continue

            if current_classification == "Modified" and best_classification == "No Change":
                # Category 3: Modified → No Change
                changes_str = "; ".join(f"{k}: {v}" for k, v in current_changes.items())
                modified_to_nochange.append({
                    "IDENTITY KEY": key,
                    "PART NO": part_no,
                    "CURRENT MODIFIED ROW ID": current_new_row_id,
                    "CURRENT CHANGES": changes_str,
                    "SUGGESTED MATCH ROW ID": best_new_row_id,
                    "CURRENT SCORE": current_score,
                    "BEST SCORE": best_score,
                    "REASON": "Historical continuation — exact match exists at different position",
                })
            elif current_classification == "Modified" and best_classification == "Modified":
                # Category 4: Modified → Different Modified
                current_str = "; ".join(f"{k}: {v}" for k, v in current_changes.items())
                best_str = "; ".join(f"{k}: {v}" for k, v in best_changes.items())
                modified_to_diff_modified.append({
                    "IDENTITY KEY": key,
                    "PART NO": part_no,
                    "CURRENT NEW ROW ID": current_new_row_id,
                    "CURRENT CHANGES": current_str,
                    "CURRENT CHANGE COUNT": current_change_count,
                    "BEST MATCH ROW ID": best_new_row_id,
                    "BEST CHANGES": best_str,
                    "BEST CHANGE COUNT": best_change_count,
                    "CURRENT SCORE": current_score,
                    "BEST SCORE": best_score,
                    "REASON": "Better engineering match reduces change noise",
                })

            # Category 2: Any case where best differs from current
            potential_better_matches.append({
                "IDENTITY KEY": key,
                "PART NO": part_no,
                "CURRENT MATCH ROW ID": current_new_row_id,
                "BEST MATCH ROW ID": best_new_row_id,
                "CURRENT SCORE": current_score,
                "BEST SCORE": best_score,
                "CURRENT CLASSIFICATION": current_classification,
                "BEST CLASSIFICATION": best_classification,
                "REASON": f"{current_classification} \u2192 {best_classification}" if current_classification != best_classification else "Better match (same classification)",
            })

    # ── Build diagnostics ─────────────────────────────────────────────────────
    diagnostics["rows_analysed"] = total_rows_analysed
    diagnostics["no_impact"] = no_impact_count
    diagnostics["potential_better_match"] = len(potential_better_matches)
    diagnostics["modified_to_nochange"] = len(modified_to_nochange)
    diagnostics["modified_to_different_modified"] = len(modified_to_diff_modified)

    # ── Build Excel report ────────────────────────────────────────────────────
    excel_bytes = _build_report(
        diagnostics,
        potential_better_matches,
        modified_to_nochange,
        modified_to_diff_modified,
        group_details,
    )

    return {"diagnostics": diagnostics, "excel_bytes": excel_bytes}


def _build_report(diagnostics, better_matches, mod_to_nc, mod_to_diff, group_details):
    """Build the SMART_REMATCH_ANALYSIS.xlsx workbook."""
    output = io.BytesIO()

    # ── Summary sheet data ────────────────────────────────────────────────────
    summary_data = [
        {"Metric": "Duplicate Groups Analysed", "Value": diagnostics["duplicate_groups"]},
        {"Metric": "Rows Analysed", "Value": diagnostics["rows_analysed"]},
        {"Metric": "No Impact (Current = Best)", "Value": diagnostics["no_impact"]},
        {"Metric": "Potential Better Match", "Value": diagnostics["potential_better_match"]},
        {"Metric": "Modified \u2192 No Change", "Value": diagnostics["modified_to_nochange"]},
        {"Metric": "Modified \u2192 Different Modified", "Value": diagnostics["modified_to_different_modified"]},
    ]
    summary_df = pd.DataFrame(summary_data)

    better_df = pd.DataFrame(better_matches) if better_matches else pd.DataFrame(
        columns=["IDENTITY KEY", "PART NO", "CURRENT MATCH ROW ID", "BEST MATCH ROW ID",
                 "CURRENT SCORE", "BEST SCORE", "CURRENT CLASSIFICATION",
                 "BEST CLASSIFICATION", "REASON"]
    )
    nc_df = pd.DataFrame(mod_to_nc) if mod_to_nc else pd.DataFrame(
        columns=["IDENTITY KEY", "PART NO", "CURRENT MODIFIED ROW ID", "CURRENT CHANGES",
                 "SUGGESTED MATCH ROW ID", "CURRENT SCORE", "BEST SCORE", "REASON"]
    )
    diff_df = pd.DataFrame(mod_to_diff) if mod_to_diff else pd.DataFrame(
        columns=["IDENTITY KEY", "PART NO", "CURRENT NEW ROW ID", "CURRENT CHANGES",
                 "CURRENT CHANGE COUNT", "BEST MATCH ROW ID", "BEST CHANGES",
                 "BEST CHANGE COUNT", "CURRENT SCORE", "BEST SCORE", "REASON"]
    )
    details_df = pd.DataFrame(group_details) if group_details else pd.DataFrame()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_df.to_excel(writer, index=False, sheet_name="Summary")
        better_df.to_excel(writer, index=False, sheet_name="Potential_Better_Matches")
        nc_df.to_excel(writer, index=False, sheet_name="Modified_To_NoChange")
        diff_df.to_excel(writer, index=False, sheet_name="Modified_To_Diff_Modified")
        if not details_df.empty:
            details_df.to_excel(writer, index=False, sheet_name="Duplicate_Group_Details")

        # Tab colors
        wb = writer.book
        wb["Summary"].sheet_properties.tabColor = "4472C4"
        wb["Potential_Better_Matches"].sheet_properties.tabColor = "FFC000"
        wb["Modified_To_NoChange"].sheet_properties.tabColor = "70AD47"
        wb["Modified_To_Diff_Modified"].sheet_properties.tabColor = "ED7D31"
        if "Duplicate_Group_Details" in wb.sheetnames:
            wb["Duplicate_Group_Details"].sheet_properties.tabColor = "A5A5A5"

    return output.getvalue()
