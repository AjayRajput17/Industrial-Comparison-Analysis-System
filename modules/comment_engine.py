"""
comment_engine.py — Rule-based comment generation with priority ordering.

NO AI / LLM is used. Comments are built from the CHANGES dictionary
using a strict priority field order, then remaining fields.
"""

import pandas as pd


PRIORITY_FIELDS = [
    "TORQUE STRATEGY",
    "TRGT",
    "TORQUE SNUG TARGET",
    "TRGT2",
    "PART USAGE DESC",
    "PHYSCL DESC",
    "QUANTITY",
    "ENGINE",
    "TRANSMISSION",
    "NOUN DESC",
]


def generate_comment(changes_dict, selected_fields=None):
    """
    Convert a changes_dict into a single formatted comment string.

    Parameters
    ----------
    changes_dict : dict
        {column: "old_value → new_value"}
    selected_fields : list[str] or None
        Which fields to include. None = use PRIORITY_FIELDS as default.

    Returns
    -------
    str : "FIELD: old → new | FIELD: old → new"
    """
    if not changes_dict:
        return ""

    if selected_fields is None:
        selected_fields = PRIORITY_FIELDS

    # Filter to only selected fields
    filtered = {k: v for k, v in changes_dict.items()
                if k in selected_fields}

    if not filtered:
        return ""

    # Order: priority fields first (in PRIORITY_FIELDS order), then others
    ordered_keys = []
    for field in PRIORITY_FIELDS:
        if field in filtered:
            ordered_keys.append(field)
    for field in filtered:
        if field not in ordered_keys:
            ordered_keys.append(field)

    return "\n".join(f"{k}: {filtered[k]}" for k in ordered_keys)


def generate_comments_batch(df, mode, selected_fields=None):
    """
    Apply comments to an entire DataFrame.

    Parameters
    ----------
    df : DataFrame
    mode : str
        "modified"  → build from CHANGES column
        "new"       → static "Completely New Part Added"
        "deleted"   → static "Part Removed in New Report"
        "nochange"  → static "No Changes Detected"
    selected_fields : list[str] or None

    Returns
    -------
    DataFrame with COMMENTS column added.
    CHANGES column is dropped for modified mode.
    """
    if df.empty:
        return df

    df = df.copy()

    if mode == "modified":
        df["COMMENTS"] = df["CHANGES"].apply(
            lambda ch: generate_comment(ch, selected_fields)
                       if isinstance(ch, dict) else str(ch)
        )
        # Drop the raw CHANGES dict column — COMMENTS replaces it
        df.drop(columns=["CHANGES"], inplace=True, errors="ignore")

    elif mode == "new":
        df["COMMENTS"] = "Completely New Part Added"

    elif mode == "deleted":
        df["COMMENTS"] = "Part Removed in New Report"

    elif mode == "nochange":
        df["COMMENTS"] = "No Changes Detected"

    return df
