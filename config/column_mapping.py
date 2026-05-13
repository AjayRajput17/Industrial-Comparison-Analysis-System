"""
Configuration for Multi-Level Hierarchical Column Mapping.

BUSINESS RULE (Manager Confirmed):
  - MIN / TRGT / MAX must ALWAYS come from RESIDUAL torque values.
  - TRGT2 must ALWAYS come from ANGLE CONTROL → ANGLE SPECS → TRGT.

Used to correctly map columns from a multi-indexed raw file (e.g. Torque report)
to the target flattened comparison schema.
"""

COLUMN_MAPPING = {
    # RESIDUAL torque values (NOT Dynamic)
    "MIN": (
        "TORQUE CONTROLLED (NM)",
        "RESIDUAL",
        "MIN"
    ),
    "TRGT": (
        "TORQUE CONTROLLED (NM)",
        "RESIDUAL",
        "TRGT"
    ),
    "MAX": (
        "TORQUE CONTROLLED (NM)",
        "RESIDUAL",
        "MAX"
    ),
    # TRGT2 from ANGLE CONTROL hierarchy
    "TRGT2": (
        "ANGLE CONTROL - TORQUE MONITOR(NM)",
        "ANGLE   SPECS",  # matching exact multi-level representation output
        "TRGT"
    )
}
