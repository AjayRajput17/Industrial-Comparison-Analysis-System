"""
Comparison Identity Configuration.
Defines the 9-column business identity used by the Comparison Engine.

These fields together form a UNIQUE business row identity.
Torque values (TRGT, MIN, MAX) are intentionally EXCLUDED because
changes in those fields should result in a "Modified" classification,
NOT a "New + Deleted" pair.
"""

# ── 9-COLUMN BUSINESS IDENTITY KEY ───────────────────────────────────────────
IDENTITY_COLUMNS = [
    "MODEL YEAR",        # Part vintage
    "PART NO",           # Hardware identifier
    "VEH FAM",           # Vehicle family/platform
    "VEH LINE",          # Platform/geographical line
    "DEPT_REL",          # Assembly department/workstation
    "PART USAGE DESC",   # Where/how the part is used
    "PHYSCL DESC",       # Thread/size specification
    "ENGINE",            # Engine configuration
    "TRANSMISSION",      # Transmission configuration
]

# ── FLEXIBLE COLUMN RESOLUTION CANDIDATES ─────────────────────────────────────
# Each identity field may appear under different column name variations.
IDENTITY_CANDIDATES = {
    "MODEL YEAR":      ["MODEL YEAR", "MODEL_YEAR", "MODELYEAR", "MY"],
    "PART NO":         ["PART NO", "PART_NO", "PARTNO", "PART NUMBER", "PART_NUMBER"],
    "VEH FAM":         ["VEH FAM", "VEH_FAM", "VEHFAM", "VEHICLE FAMILY", "VEHICLE_FAMILY"],
    "VEH LINE":        ["VEH LINE", "VEH_LINE", "VEHLINE", "VEHICLE LINE"],
    "DEPT_REL":        ["DEPT_REL", "DEPT REL", "DEPARTMENT", "DEPT"],
    "PART USAGE DESC": ["PART USAGE DESC", "PART_USAGE_DESC", "USAGE DESC"],
    "PHYSCL DESC":     ["PHYSCL DESC", "PHYSCL_DESC", "PHYSICAL DESC", "PHYSICAL_DESC"],
    "ENGINE":          ["ENGINE", "ENGINE CODE"],
    "TRANSMISSION":    ["TRANSMISSION", "TRANS"],
}
