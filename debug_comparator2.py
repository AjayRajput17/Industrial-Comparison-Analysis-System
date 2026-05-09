import pandas as pd
from modules.comparator import compare_datasets, build_composite_key
from modules.analysis import normalize_columns
old_df = pd.read_excel('OLD REPORT 27 April.xlsx', nrows=5)
new_df = pd.read_excel('New report 5 May 2025.xlsx', nrows=5)
old_norm, _ = normalize_columns(old_df)
new_norm, _ = normalize_columns(new_df)
print('Old norm cols:', list(old_norm.columns)[:10])
print('New norm cols:', list(new_norm.columns)[:10])
print('Old keys:', build_composite_key(old_norm)['__KEY__'].tolist())
print('New keys:', build_composite_key(new_norm)['__KEY__'].tolist())