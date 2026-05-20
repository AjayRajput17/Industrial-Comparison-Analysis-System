"""
Comparison Identity Configuration.
Defines the 9-column business identity used by the Comparison Engine.

These fields together form a UNIQUE business row identity.

EXCLUDED from identity (treated as data fields — changes trigger MODIFIED):
  - ENGINE:       Engine code updates (e.g. ERC → ERC ERT) are common and should
                  be flagged as modifications, not New+Deleted pairs.
  - TRANSMISSION: Same rationale as ENGINE — configuration updates are modifications.
  - TRGT, MIN, MAX: Torque values are data, not identity.

REASONING (2026-05-15 → 2026-05-20):
  ENGINE and TRANSMISSION were previously removed after 112 False Additions/Deletions
  were identified from engine code updates (e.g. ERC → ERC ERT).
  Re-added on 2026-05-20 per user decision to test with full 9-column identity.
  If false New/Deleted pairs re-appear, comment them out again in this file.
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
    "ENGINE":          ["ENGINE", "ENGINE CODE", "ENGINE_CODE"],
    "TRANSMISSION":    ["TRANSMISSION", "TRANS", "TRANSMISSION CODE"],
}
