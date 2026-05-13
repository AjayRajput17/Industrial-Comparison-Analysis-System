import pandas as pd
from exports.excel_exporter import export_excel

nc = pd.DataFrame({"MODEL YEAR": [2024], "CHANGES": [""]})
mod = pd.DataFrame({"MODEL YEAR": [2024], "CHANGES": [{"MIN": "1 -> 2"}]})
nw = pd.DataFrame({"MODEL YEAR": [2024], "CHANGES": [""]})
rm = pd.DataFrame({"MODEL YEAR": [2024], "CHANGES": [""]})

print("Testing export...")
try:
    export_excel(nc, mod, nw, rm)
    print("Done!")
except Exception as e:
    import traceback
    traceback.print_exc()
