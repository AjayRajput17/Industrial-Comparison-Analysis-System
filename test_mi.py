import pandas as pd
df = pd.read_excel('TORQUE_CURRENT_REPORT.xlsx', header=[0,1,2], nrows=5)
for c in df.columns:
    if 'TRGT' in str(c).upper() or 'PART' in str(c).upper():
        print(c)
