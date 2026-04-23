
import pandas as pd


def _resolve_part_key(columns):
    normalized = {str(col).strip().lower(): col for col in columns}
    
    # 1. Exact matches
    for candidate in ('part no', 'part number', 'part_no', 'partno'):
        if candidate in normalized:
            return normalized[candidate]
            
    # 2. Partial matches (e.g., 'old data(07-07-2025).part no')
    for col_lower, col_orig in normalized.items():
        if any(x in col_lower for x in ('part no', 'part number', 'part_no', 'partno')):
            return col_orig

    raise ValueError("PART NO column not found in input data.")


def match_parts(added, deleted):
    key_added = _resolve_part_key(added.columns)
    key_deleted = _resolve_part_key(deleted.columns)

    added = added.copy()
    deleted = deleted.copy()

    added['__match_key__'] = added[key_added].astype(str).str.strip().str.upper()
    deleted['__match_key__'] = deleted[key_deleted].astype(str).str.strip().str.upper()

    null_aliases = {'', 'NAN', 'NONE', 'NAT', '<NA>', 'NULL'}

    # Fallback to fill blank keys from any other column that looks like a part number
    for df_split in (added, deleted):
        part_cols = [c for c in df_split.columns if any(x in str(c).lower() for x in ('part no', 'part number', 'part_no', 'partno'))]
        for col in part_cols:
            mask = df_split['__match_key__'].isna() | df_split['__match_key__'].isin(null_aliases)
            if mask.any():
                df_split.loc[mask, '__match_key__'] = df_split.loc[mask, col].astype(str).str.strip().str.upper()

    added = added[~added['__match_key__'].isin(null_aliases)].drop_duplicates(subset=['__match_key__'])
    deleted = deleted[~deleted['__match_key__'].isin(null_aliases)].drop_duplicates(subset=['__match_key__'])

    added_keys = set(added['__match_key__'])
    deleted_keys = set(deleted['__match_key__'])

    modified_keys = added_keys & deleted_keys
    new_keys = added_keys - deleted_keys
    removed_keys = deleted_keys - added_keys

    modified_rows = []

    for k in modified_keys:
        new_row = added[added['__match_key__'] == k].iloc[0]
        old_row = deleted[deleted['__match_key__'] == k].iloc[0]

        changes = {}
        for col in added.columns:
            if col in deleted.columns and col != '__match_key__':
                if str(new_row[col]) != str(old_row[col]):
                    changes[col] = f"{old_row[col]} → {new_row[col]}"

        combined = new_row.to_dict()
        combined.pop('__match_key__', None)
        combined["CHANGES"] = changes
        modified_rows.append(combined)

    new_rows = added[added['__match_key__'].isin(new_keys)].drop(columns=['__match_key__'])
    removed_rows = deleted[deleted['__match_key__'].isin(removed_keys)].drop(columns=['__match_key__'])

    return pd.DataFrame(modified_rows), new_rows, removed_rows
