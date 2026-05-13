"""
Authoritative Output Report Schema.
Extracted from the macro-generated reference: new_data.xlsx
This file is the code-level authority. Users do NOT need to upload a template.
"""

# ── COLUMN ORDER (exactly matches macro output) ──────────────────────────────
REPORT_COLUMNS = [
    "MODEL YEAR",
    "PART NO",
    "VEH FAM",
    "VEH LINE",
    "BODY STYLE",
    "PART USAGE DESC",
    "PHYSCL DESC",
    "QUANTITY",
    "DEPT_REL",
    "TORQUE SAFETY",
    "TIGHTENING CLASS",
    "TORQUE STRATEGY",
    "MIN",
    "TRGT",
    "MAX",
    "TORQUE SNUG TARGET",
    "TRGT2",
    "DECISIONED CN #",
    "DECISION DATE",
    "VSC",
    "VSC NAME",
    "END ITEM PART",
    "ENGINE",
    "TRANSMISSION",
    "CONDITION DESC",
    "NOUN NAME",
    "NOUN DESC",
    "COMMENTS",
    "ROW ID",
]

# ── COLUMN TYPING ─────────────────────────────────────────────────────────────
NUMERIC_COLUMNS = ["MIN", "TRGT", "MAX", "TORQUE SNUG TARGET"]
INTEGER_COLUMNS = ["TRGT2", "QUANTITY"]
DATE_COLUMNS = ["DECISION DATE"]
MULTILINE_COLUMNS = ["COMMENTS", "CHANGES", "PART USAGE DESC", "PHYSCL DESC", "VSC NAME"]
