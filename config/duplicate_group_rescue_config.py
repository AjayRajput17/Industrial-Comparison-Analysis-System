"""
Duplicate Group Rescue Configuration.

Controls the post-comparison rescue layer that corrects positional matching
mistakes inside duplicate identity groups.

Set ENABLE_DUPLICATE_GROUP_RESCUE = True to activate.
Set ENABLE_DUPLICATE_GROUP_RESCUE = False for zero overhead.
"""

# ── MASTER TOGGLE ─────────────────────────────────────────────────────────────
ENABLE_DUPLICATE_GROUP_RESCUE = True

# ── SIMILARITY SCORING WEIGHTS ───────────────────────────────────────────────
# Used to score candidate matches within duplicate identity groups.
RESCUE_SIMILARITY_WEIGHTS = {
    "DECISIONED CN #": 50,
    "DECISION DATE":   50,
    "TRGT":            30,
    "MIN":             15,
    "MAX":             15,
    "VSC":             10,
    "VSC NAME":        10,
    "END ITEM PART":   10,
    "CONDITION DESC":  10,
}

# ── MINIMUM SCORE THRESHOLD ─────────────────────────────────────────────────
# Only rescue if the best match score meets or exceeds this value.
DUPLICATE_GROUP_RESCUE_MIN_SCORE = 145

# ── DIAGNOSTICS ──────────────────────────────────────────────────────────────
DUPLICATE_GROUP_RESCUE_DIAGNOSTICS = True
