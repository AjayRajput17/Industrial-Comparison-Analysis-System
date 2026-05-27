"""
Centralized Business Rules Configuration.
Manager-confirmed authoritative rules for the report generation pipeline.
"""

# ── TORQUE FILTER RULES ──────────────────────────────────────────────────────
TORQUE_FILTER_FIELD = "TRGT"
TORQUE_THRESHOLD = 5
KEEP_ZERO_TORQUE = True
# Rule: Keep TRGT == 0 OR TRGT >= 5. Remove 0 < TRGT < 5.

# TRGT filter toggle — set to True to re-enable the 0 < TRGT < 5 removal.
# Disabled (2026-05-28): Rows with legitimate low torque values were being
# removed before comparison, causing missing Modified rows and false
# Deleted/Added classifications. Filter retained for future business review.
ENABLE_TRGT_FILTER = False

# ── PART STATUS FILTER ────────────────────────────────────────────────────────
VALID_PART_STATUS = ["R"]

# ── TORQUE SAFETY FILTER ─────────────────────────────────────────────────────
VALID_TORQUE_SAFETY = ["Y", "N"]
# Remove blank and '?'

# ── RAW MBOM HEADER PATHS ────────────────────────────────────────────────────
# These are the multi-index column paths in the raw TORQUE_CURRENT_REPORT.XLSX
# Used during business filtering BEFORE field mapping flattens the headers.
RAW_PART_STATUS_PATH = ("UNNAMED: 1_LEVEL_0", "UNNAMED: 1_LEVEL_1", "PART STATUS")
RAW_TORQUE_SAFETY_PATH = ("TORQUE REPORT", "UNNAMED: 18_LEVEL_1", "TORQUE SAFETY")
RAW_TRGT_RESIDUAL_PATH = ("TORQUE CONTROLLED (NM)", "RESIDUAL", "TRGT")
