"""
Actionability Classification Configuration.

All business rules for ACTION REQUIRED / REVIEW CATEGORY classification.
Designed for future UI-driven rule management — all rules are config-driven,
no hardcoded field names in the classifier logic.

To modify classification behavior, edit only this file.
"""

# ── MASTER TOGGLE ─────────────────────────────────────────────────────────────
ENABLE_ACTIONABILITY_CLASSIFIER = True

# ── LOW TORQUE AUTO-IGNORE ────────────────────────────────────────────────────
# When True, modifications where BOTH old and new torque values are below the
# threshold are classified as non-actionable "Low Torque Change".
ENABLE_LOW_TORQUE_AUTO_IGNORE = True

# When True, Added rows with ALL evaluation fields below the threshold are
# classified as non-actionable "New Low Torque Record".
ENABLE_LOW_TORQUE_ADDED_AUTO_IGNORE = True

LOW_TORQUE_THRESHOLD = 5

# Fields evaluated for low-torque logic.
# Current business process uses only TRGT. Add MIN, MAX, TRGT2 here if needed.
LOW_TORQUE_EVALUATION_FIELDS = [
    "TRGT",
]

# ── ACTIONABLE FIELDS ────────────────────────────────────────────────────────
# If ANY of these fields changed, the modification is actionable (ACTION = YES).
ACTIONABLE_FIELDS = [
    # Torque-related
    "TRGT",
    "MIN",
    "MAX",
    "TRGT2",
    "TORQUE SNUG TARGET",
    "TORQUE STRATEGY",
    # Applicability
    "ENGINE",
    "TRANSMISSION"
]

# ── ADMINISTRATIVE FIELDS ────────────────────────────────────────────────────
# If ONLY these fields changed, the modification is non-actionable (ACTION = NO).
ADMINISTRATIVE_FIELDS = [
    "BODY STYLE",
    "VEH LINE",
    "DEPT_REL",
    "TORQUE SAFETY",
    "TIGHTENING CLASS",
    "VSC",
    "VSC NAME",
    "CONDITION DESC",
    "NOUN NAME",
    "NOUN DESC",
    "DECISIONED CN #",
    "DECISION DATE",
    "END ITEM PART",
    "COMMENTS",
]

# ── REVIEW CATEGORY LABELS ──────────────────────────────────────────────────
# Display labels for each category. Keys are internal IDs; values are
# human-readable labels shown in Excel and the UI dashboard.
REVIEW_CATEGORIES = {
    "LOW_TORQUE":     "Low Torque Change",
    "ADMIN":          "Administrative Change",
    "TRGT":           "TRGT Change",
    "TORQUE":         "Torque Change",
    "ENGINE":         "Engine Applicability Change",
    "TRANSMISSION":   "Transmission Applicability Change",
    "APPLICABILITY":  "Vehicle/Department Applicability Change",
    "TORQUE_STRATEGY" : "Torque Strategy Change",
    "TORQUE_SAFETY" : "Torque Safety Change",
    "TORQUE_TIGHTENING_CLASS" : "Torque Tightening Class Change",
    "NEW":            "New Engineering Record",
    "NEW_LOW_TORQUE": "New Low Torque Record",
}

# ── CATEGORY PRIORITY ORDER ─────────────────────────────────────────────────
# When multiple categories apply, the FIRST matching category (highest
# priority) wins. This list controls evaluation order.
CATEGORY_PRIORITY = [
    "TRGT",
    "TORQUE",
    "LOW_TORQUE",
    "ENGINE",
    "TRANSMISSION",
    "TORQUE_STRATEGY",
    "TORQUE_SAFETY",
    "TORQUE_TIGHTENING_CLASS",
    "APPLICABILITY",
    "ADMIN",
    "NEW"
]

# ── FIELD-TO-CATEGORY MAPPING ────────────────────────────────────────────────
# Maps individual fields to their category ID for automatic classification.
FIELD_CATEGORY_MAP = {
    "ENGINE":             "ENGINE",
    "TRANSMISSION":       "TRANSMISSION",
    "VEH LINE":           "APPLICABILITY",
    "DEPT_REL":           "APPLICABILITY",
    "TRGT":               "TRGT",
    "MIN":                "TORQUE",
    "MAX":                "TORQUE",
    "TRGT2":              "TORQUE",
    "TORQUE SNUG TARGET": "TORQUE",
    "TORQUE STRATEGY":    "TORQUE_STRATEGY",
    "TORQUE SAFETY":      "TORQUE_SAFETY",
    "TIGHTENING CLASS":   "TORQUE_TIGHTENING_CLASS",
}
