"""
Centralized Deduplication Configuration.
Manager-confirmed: Use BUSINESS FIELD SUBSET matching, NOT full-row equality.
"""

DEDUP_COLUMNS = [
    "MODEL YEAR",
    "VEH FAM",
    "PART NO",
    "PART USAGE DESC",
    "PHYSCL DESC",
    "TORQUE STRATEGY",
    "MIN",
    "TRGT",
    "MAX",
]
