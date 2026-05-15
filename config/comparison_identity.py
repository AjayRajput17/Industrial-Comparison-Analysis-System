"""
Comparison Identity Configuration.
Defines the 7-column business identity used by the Comparison Engine.

These fields together form a UNIQUE business row identity.

EXCLUDED from identity (treated as data fields — changes trigger MODIFIED):
  - ENGINE:       Engine code updates (e.g. ERC → ERC ERT) are common and should
                  be flagged as modifications, not New+Deleted pairs.
  - TRANSMISSION: Same rationale as ENGINE — configuration updates are modifications.
  - TRGT, MIN, MAX: Torque values are data, not identity.

REASONING (2026-05-15):
  Analysis of production data found 112 False Additions/Deletions caused by
  ENGINE and TRANSMISSION being in the identity key. When these fields change
  for an otherwise-identical part, the system was producing a paired
  "Deleted (old ENGINE)" + "New (new ENGINE)" instead of a single "Modified".
  Removing them from identity fixes this and aligns with business intent:
  ENGINE/TRANSMISSION updates are parameter modifications, not part replacements.
"""

# ── 7-COLUMN BUSINESS IDENTITY KEY ───────────────────────────────────────────
IDENTITY_COLUMNS = [
    "MODEL YEAR",        # Part vintage
    "PART NO",           # Hardware identifier
    "VEH FAM",           # Vehicle family/platform
    "VEH LINE",          # Platform/geographical line
    "DEPT_REL",          # Assembly department/workstation
    "PART USAGE DESC",   # Where/how the part is used
    "PHYSCL DESC",       # Thread/size specification
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
}
