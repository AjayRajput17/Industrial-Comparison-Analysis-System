"""
Report Structure Configuration.
Known EBOM/Torque report structure for fast-path loading.
"""

# ── KNOWN SHEET STRUCTURE ────────────────────────────────────────────────────
DEFAULT_SHEET_NAME = "Torque Report"

# MultiIndex header rows: [group_headers, subgroup_headers, business_headers]
DEFAULT_HEADER_ROWS = [0, 1, 2]

# ── VALIDATION COLUMNS ──────────────────────────────────────────────────────
# After loading, these columns MUST exist (at any level) to confirm structure.
REQUIRED_VALIDATION_COLUMNS = [
    "MODEL YEAR",
    "PART NO",
    "VEH FAM",
    "PART USAGE DESC",
    "PHYSCL DESC",
]
