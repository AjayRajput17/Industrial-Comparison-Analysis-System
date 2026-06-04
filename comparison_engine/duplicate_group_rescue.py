"""
Duplicate Group Rescue — High-confidence historical re-match for duplicate
identity groups.

Runs AFTER the main comparison positional matching but BEFORE the existing
rescue pass (rescue_pass.py). Operates on the raw row-dict lists produced
during the matching loop, NOT on DataFrames.

Purpose:
  When positional matching (OLD[0]↔NEW[0]) inside duplicate identity groups
  produces false Modifieds, this layer re-evaluates matching using weighted
  similarity scoring and replaces the pairing when a high-confidence
  historical continuation is found.

Does NOT modify:
  - Identity key logic
  - Change detection logic
  - Existing rescue pass
  - Actionability classification

All rules are config-driven via config/duplicate_group_rescue_config.py.
"""

import numpy as np
import config.duplicate_group_rescue_config as config

# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_str(val):
    """Convert a value to a comparable string, treating NaN as empty."""
    if val is None:
        return ""
    if isinstance(val, float) and np.isnan(val):
        return ""
    return str(val).strip()


def _values_equal(a, b):
    """String match with numeric equivalence fallback."""
    sa, sb = _safe_str(a), _safe_str(b)
    if sa == sb:
        return True
    try:
        if float(sa) == float(sb):
            return True
    except (ValueError, TypeError):
        pass
    return False


def _compute_score(old_dict, new_dict):
    """Weighted similarity score between two row dicts."""
    score = 0
    for field, weight in config.RESCUE_SIMILARITY_WEIGHTS.items():
        if _values_equal(old_dict.get(field, ""), new_dict.get(field, "")):
            score += weight
    return score


def _detect_changes(old_dict, new_dict, compare_cols, skip_set):
    """Detect field-level changes between two row dicts."""
    changes = {}
    for col in compare_cols:
        if col.upper() in skip_set:
            continue
        ov = _safe_str(old_dict.get(col, ""))
        nv = _safe_str(new_dict.get(col, ""))
        if ov != nv:
            try:
                if float(ov) == float(nv):
                    continue
            except (ValueError, TypeError):
                pass
            changes[col] = f"{ov} \u2192 {nv}"
    return changes


# Skip set (same as main engine)
_SKIP = frozenset({
    "ROW ID", "ROW_ID", "ROWID", "ROW NO", "ROW_NO",
    "SR NO", "SR_NO", "SERIAL NO", "SERIAL_NO", "S NO", "S.NO",
    "INDEX", "__KEY__",
    "COMMENT", "COMMENTS",
    "DECISIONED CN #", "DECISION DATE", "END ITEM PART",
})


# ── Main entry point ─────────────────────────────────────────────────────────

def rescue_duplicate_groups(old_groups, new_groups, compare_cols):
    """
    Re-evaluate positional matching within duplicate identity groups.

    This function operates on the raw group-dict structures (same ones used
    by the main comparison loop). It returns replacement row lists that the
    comparator splices into its results.

    Parameters
    ----------
    old_groups : dict  {identity_key: [list of row dicts]}
    new_groups : dict  {identity_key: [list of row dicts]}
    compare_cols : list  columns used for change detection

    Returns
    -------
    dict with keys:
        'rescued_modified'   : list of row dicts (new Modified results)
        'rescued_nochange'   : list of row dicts (new NoChange results)
        'rescued_extra_new'  : list of row dicts (leftover new rows)
        'rescued_extra_del'  : list of row dicts (leftover old rows)
        'replaced_keys'      : set of identity keys that were re-matched
        'diagnostics'        : summary metrics dict
    """
    empty = {
        "rescued_modified": [],
        "rescued_nochange": [],
        "rescued_extra_new": [],
        "rescued_extra_del": [],
        "replaced_keys": set(),
        "diagnostics": {"status": "DISABLED"},
    }

    if not config.ENABLE_DUPLICATE_GROUP_RESCUE:
        return empty

    # ── 1. Find duplicate identity groups ─────────────────────────────────────
    common_keys = set(old_groups.keys()) & set(new_groups.keys())
    dup_keys = [
        k for k in common_keys
        if len(old_groups[k]) > 1 or len(new_groups[k]) > 1
    ]

    diags = {
        "status": "COMPLETED",
        "duplicate_groups_found": len(dup_keys),
        "groups_rescued": 0,
        "rows_analysed": 0,
        "modified_to_nochange": 0,
        "modified_to_diff_modified": 0,
        "no_impact": 0,
        "below_threshold": 0,
        "detail_rows": [],
    }

    if not dup_keys:
        empty["diagnostics"] = diags
        return empty

    replaced_keys = set()
    all_rescued_modified = []
    all_rescued_nochange = []
    all_rescued_extra_new = []
    all_rescued_extra_del = []

    for key in dup_keys:
        old_rows = old_groups[key]
        new_rows = new_groups[key]
        n_old = len(old_rows)
        n_new = len(new_rows)
        min_len = min(n_old, n_new)
        diags["rows_analysed"] += min_len

        # ── 2. Build score matrix ────────────────────────────────────────────
        score_matrix = {}
        for oi in range(n_old):
            for ni in range(n_new):
                score_matrix[(oi, ni)] = _compute_score(old_rows[oi], new_rows[ni])

        # ── 3. Greedy optimal assignment ─────────────────────────────────────
        sorted_pairs = sorted(score_matrix.items(), key=lambda x: -x[1])
        used_old = set()
        used_new = set()
        greedy_map = {}  # oi -> (ni, score)

        for (oi, ni), score in sorted_pairs:
            if oi in used_old or ni in used_new:
                continue
            greedy_map[oi] = (ni, score)
            used_old.add(oi)
            used_new.add(ni)

        # ── 4. Compare greedy vs positional ──────────────────────────────────
        # Build positional scores for comparison
        positional_map = {}
        for i in range(min_len):
            positional_map[i] = (i, score_matrix.get((i, i), 0))

        # Check if ANY assignment differs AND meets threshold
        any_rescue = False
        for oi in range(min_len):
            pos_ni, pos_score = positional_map.get(oi, (oi, 0))
            grdy_ni, grdy_score = greedy_map.get(oi, (oi, 0))

            if grdy_ni != pos_ni and grdy_score >= config.DUPLICATE_GROUP_RESCUE_MIN_SCORE:
                any_rescue = True
                break

        if not any_rescue:
            diags["no_impact"] += min_len
            continue

        # ── 5. Apply rescue: re-classify entire group with greedy assignment ─
        replaced_keys.add(key)
        diags["groups_rescued"] += 1

        group_modified = []
        group_nochange = []

        for oi in sorted(greedy_map.keys()):
            ni, score = greedy_map[oi]
            old_dict = old_rows[oi]
            new_dict = new_rows[ni]

            changes = _detect_changes(old_dict, new_dict, compare_cols, _SKIP)
            row_data = {k: v for k, v in new_dict.items() if k != "__KEY__"}

            # Was this pair positionally matched?
            was_positional = (oi < min_len and ni == oi)
            pos_ni_orig = oi if oi < min_len else None

            if changes:
                row_data["CHANGES"] = changes
                group_modified.append(row_data)

                # Track if this is a different Modified (was modified positionally too)
                if not was_positional and pos_ni_orig is not None:
                    pos_changes = _detect_changes(
                        old_rows[oi], new_rows[oi], compare_cols, _SKIP
                    ) if oi < n_new else {}
                    if pos_changes:
                        diags["modified_to_diff_modified"] += 1
            else:
                group_nochange.append(row_data)

                # Track Modified → NoChange
                if not was_positional and pos_ni_orig is not None:
                    pos_changes = _detect_changes(
                        old_rows[oi], new_rows[oi], compare_cols, _SKIP
                    ) if oi < n_new else {}
                    if pos_changes:
                        diags["modified_to_nochange"] += 1

            # Diagnostic detail row
            if config.DUPLICATE_GROUP_RESCUE_DIAGNOSTICS and not was_positional:
                detail = {
                    "IDENTITY KEY": key,
                    "OLD POS": oi,
                    "CURRENT NEW POS": oi if oi < min_len else "N/A",
                    "BEST NEW POS": ni,
                    "CURRENT SCORE": score_matrix.get((oi, oi), 0) if oi < n_new else 0,
                    "BEST SCORE": score,
                    "RESCUED": "YES" if score >= config.DUPLICATE_GROUP_RESCUE_MIN_SCORE else "NO",
                    "OLD CLASSIFICATION": "Modified" if (oi < min_len and oi < n_new and
                        _detect_changes(old_rows[oi], new_rows[oi], compare_cols, _SKIP)) else "NoChange",
                    "NEW CLASSIFICATION": "Modified" if changes else "NoChange",
                    "REASON": "Historical continuation" if not changes else "Better match",
                }
                diags["detail_rows"].append(detail)

        # Extra new rows (unmatched new rows)
        matched_new = {ni for ni, _ in greedy_map.values()}
        for ni in range(n_new):
            if ni not in matched_new:
                row_data = {k: v for k, v in new_rows[ni].items() if k != "__KEY__"}
                all_rescued_extra_new.append(row_data)

        # Extra deleted rows (unmatched old rows)
        for oi in range(n_old):
            if oi not in greedy_map:
                row_data = {k: v for k, v in old_rows[oi].items() if k != "__KEY__"}
                all_rescued_extra_del.append(row_data)

        all_rescued_modified.extend(group_modified)
        all_rescued_nochange.extend(group_nochange)

    return {
        "rescued_modified": all_rescued_modified,
        "rescued_nochange": all_rescued_nochange,
        "rescued_extra_new": all_rescued_extra_new,
        "rescued_extra_del": all_rescued_extra_del,
        "replaced_keys": replaced_keys,
        "diagnostics": diags,
    }
