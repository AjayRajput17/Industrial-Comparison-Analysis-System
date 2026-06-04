"""
Smart Re-Match Simulator Configuration.

Controls the ANALYTICAL ONLY post-comparison re-match simulation.
This feature does NOT affect production comparison output.

Set SMART_REMATCH_ANALYSIS_ENABLED = True to run the analysis.
Set SMART_REMATCH_ANALYSIS_ENABLED = False for zero overhead.
"""

# ── MASTER TOGGLE ─────────────────────────────────────────────────────────────
# When False: nothing runs, zero CPU/memory impact.
# When True:  analysis runs AFTER comparison completes, generates report.
SMART_REMATCH_ANALYSIS_ENABLED = False

# ── SIMILARITY SCORING WEIGHTS ───────────────────────────────────────────────
# Used to score candidate matches within duplicate identity groups.
# Higher weight = more important for determining "best" match.
SIMILARITY_WEIGHTS = {
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
