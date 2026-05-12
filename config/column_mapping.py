"""
Configuration for Multi-Level Hierarchical Column Mapping
Used to correctly map columns from a multi-indexed raw file (e.g. Torque report)
to the target flattened comparison schema.
"""

COLUMN_MAPPING = {
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
    "TRGT2": (
        "ANGLE CONTROL - TORQUE MONITOR(NM)",
        "ANGLE   SPECS",  # matching exact multi-level representation output
        "TRGT"
    )
}
