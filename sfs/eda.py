#!/usr/bin/env python3
"""
Exploratory Data Analysis — SFS PUMF
=====================================
Loads the downloaded SFS PUMF CSV, prints descriptive statistics, and
writes a summary report to sfs/report.txt.

Run *after* download_sfs_pumf.py has successfully fetched the data:

    python3 download_sfs_pumf.py   # download & extract
    python3 eda.py                 # this script
"""

import glob
import os
import sys

import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
REPORT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.txt")

# ── Key variable groups ──────────────────────────────────────────────
# We try to detect columns by prefix patterns used across SFS PUMF cycles.
VARIABLE_GROUPS = {
    "Demographics": {
        "prefixes": ["PEFMJSEX", "PAGEMIEG", "PEFMJAGE", "PEDUCMIE", "PMATSTAT",
                      "PEFSIZE", "PFMTYPG", "PPROVRES", "PREGION", "PIMMIG"],
        "description": "Sex, age, education, marital status, family size/type, province",
    },
    "Income": {
        "prefixes": ["PFMTINC", "PEFATINC", "PFEMPLOY", "PFINCOME", "PGVTRANS",
                      "PFMINCG"],
        "description": "Total family income, after-tax income, employment income, "
                       "investment income, government transfers",
    },
    "Assets": {
        "prefixes": ["PWAPRVAL", "PWASTRST", "PWAVHCLE", "PWABUSEQ", "PWACNTNT",
                      "PATDEP", "PATRRSP", "PATRRIF", "PATTFSA", "PATRESP",
                      "PATSTCK", "PATMUTF", "PATEPP", "PATOTAST", "PWASTTOT",
                      "PATFEQ", "PATNFEQ"],
        "description": "Principal residence value, other real estate, vehicles, "
                       "business equity, deposits, RRSPs, TFSAs, stocks, mutual funds, "
                       "employer pensions, total assets",
    },
    "Debts": {
        "prefixes": ["PDTMRPR", "PDTMORE", "PDTVHCLE", "PDTSLOA", "PDTCRCL",
                      "PDTLOC", "PDTBUS", "PDTOTHER", "PDTTOTDT", "PDTTOTAL"],
        "description": "Mortgage (principal residence & other), vehicle loans, "
                       "student loans, credit cards, lines of credit, total debts",
    },
    "Net Worth": {
        "prefixes": ["PWNETWPG", "PWNETWPT", "PNTWRTHQ", "PNTWRTHD"],
        "description": "Net worth (going-concern and termination basis), "
                       "net-worth quintile/decile",
    },
    "Housing": {
        "prefixes": ["POWNRENT", "PPRSTYPE", "PPRSYRAQ", "PPRSDOWN"],
        "description": "Home ownership status, dwelling type, year of acquisition, "
                       "down payment",
    },
}


def find_data_file():
    """Locate the PUMF CSV or fixed-width text file in the data directory."""
    # Look for CSV first, then TXT
    for ext in ("csv", "CSV", "txt", "TXT"):
        pattern = os.path.join(DATA_DIR, "**", f"*.{ext}")
        matches = glob.glob(pattern, recursive=True)
        # Filter out readme / layout files — we want the big data file
        data_files = [
            f for f in matches
            if os.path.getsize(f) > 100_000  # data file should be >100 KB
        ]
        if data_files:
            # Return the largest file (most likely the main data)
            return max(data_files, key=os.path.getsize)
    return None


def load_pumf(path):
    """Try to load the PUMF data file as a DataFrame."""
    ext = os.path.splitext(path)[1].lower()
    print(f"Loading: {path}")

    # Try comma-separated first, then tab
    for sep in (",", "\t", "|"):
        try:
            df = pd.read_csv(path, sep=sep, low_memory=False)
            if len(df.columns) > 5:
                print(f"  Loaded with sep={sep!r}: {df.shape[0]:,} rows x {df.shape[1]} columns")
                return df
        except Exception:
            continue

    # Fall back to fixed-width (SFS sometimes ships fixed-width .txt)
    print("  Attempting fixed-width read...")
    df = pd.read_fwf(path)
    print(f"  Loaded as fixed-width: {df.shape[0]:,} rows x {df.shape[1]} columns")
    return df


def match_columns(df, prefixes):
    """Return columns in df whose name matches any of the given prefixes."""
    cols = []
    for col in df.columns:
        upper = col.upper()
        for pfx in prefixes:
            if upper == pfx.upper() or upper.startswith(pfx.upper()):
                cols.append(col)
                break
    return cols


def weighted_mean(df, col, weight_col):
    """Compute weighted mean, ignoring NaN in both value and weight."""
    mask = df[col].notna() & df[weight_col].notna()
    if mask.sum() == 0:
        return float("nan")
    return (df.loc[mask, col] * df.loc[mask, weight_col]).sum() / df.loc[mask, weight_col].sum()


def weighted_median(df, col, weight_col):
    """Approximate weighted median."""
    sub = df[[col, weight_col]].dropna()
    if sub.empty:
        return float("nan")
    sub = sub.sort_values(col)
    cumw = sub[weight_col].cumsum()
    half = sub[weight_col].sum() / 2
    idx = (cumw >= half).idxmax()
    return sub.loc[idx, col]


def detect_weight_col(df):
    """Find the survey weight column."""
    for candidate in ["PWEIGHT", "pweight", "WEIGHT", "weight"]:
        if candidate in df.columns:
            return candidate
    # Fuzzy match
    for col in df.columns:
        if "WEIGHT" in col.upper() and "BOOT" not in col.upper():
            return col
    return None


def generate_report(df):
    """Build report lines."""
    lines = []

    def heading(text):
        lines.append("")
        lines.append("=" * 70)
        lines.append(text)
        lines.append("=" * 70)

    def subheading(text):
        lines.append("")
        lines.append(f"--- {text} ---")

    weight_col = detect_weight_col(df)

    # ── Header ────────────────────────────────────────────────────────
    heading("SFS PUMF — Exploratory Data Analysis Report")
    lines.append("")

    lines.append("1. DATASET OVERVIEW")
    lines.append("-" * 40)
    lines.append(f"  Records (family units):  {df.shape[0]:,}")
    lines.append(f"  Variables:               {df.shape[1]}")
    if weight_col:
        pop = df[weight_col].sum()
        lines.append(f"  Survey weight column:    {weight_col}")
        lines.append(f"  Estimated population:    {pop:,.0f} family units")
    lines.append("")

    # ── Purpose & unit of observation ─────────────────────────────────
    lines.append("2. UNIT OF OBSERVATION")
    lines.append("-" * 40)
    lines.append("  The unit of observation is the ECONOMIC FAMILY (or unattached")
    lines.append("  individual). An economic family is a group of two or more persons")
    lines.append("  living in the same dwelling who are related by blood, marriage,")
    lines.append("  common-law union, or adoption. Each row represents one family unit.")
    lines.append("")

    lines.append("3. PURPOSE OF DATA COLLECTION")
    lines.append("-" * 40)
    lines.append("  The Survey of Financial Security (SFS) collects information on the")
    lines.append("  assets, debts, employment, income, and education of Canadian")
    lines.append("  families. It provides a comprehensive picture of household net worth")
    lines.append("  and financial well-being, supporting research on wealth inequality,")
    lines.append("  retirement preparedness, and household indebtedness.")
    lines.append("")

    # ── Variable inventory ────────────────────────────────────────────
    lines.append("4. KEY VARIABLES")
    lines.append("-" * 40)
    for group_name, info in VARIABLE_GROUPS.items():
        matched = match_columns(df, info["prefixes"])
        subheading(f"{group_name}  ({info['description']})")
        if matched:
            for col in matched:
                dtype = str(df[col].dtype)
                n_valid = df[col].notna().sum()
                lines.append(f"    {col:<20s}  dtype={dtype:<10s}  non-null={n_valid:,}")
        else:
            lines.append(f"    (no matching columns found in data)")

    # ── All columns list ──────────────────────────────────────────────
    subheading("Full column listing")
    for i, col in enumerate(df.columns):
        lines.append(f"    [{i:3d}] {col}")

    # ── Descriptive statistics ────────────────────────────────────────
    heading("5. DESCRIPTIVE STATISTICS")

    # Numeric columns
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if weight_col and weight_col in numeric_cols:
        numeric_cols.remove(weight_col)

    # Standard pandas describe
    subheading("Unweighted summary (pandas .describe())")
    desc = df[numeric_cols].describe().T
    desc_str = desc.to_string(float_format=lambda x: f"{x:,.2f}")
    for line in desc_str.split("\n"):
        lines.append("  " + line)

    # Weighted means and medians for key dollar variables
    dollar_prefixes = (
        VARIABLE_GROUPS["Income"]["prefixes"]
        + VARIABLE_GROUPS["Assets"]["prefixes"]
        + VARIABLE_GROUPS["Debts"]["prefixes"]
        + VARIABLE_GROUPS["Net Worth"]["prefixes"]
    )
    dollar_cols = match_columns(df, dollar_prefixes)
    # Keep only numeric ones
    dollar_cols = [c for c in dollar_cols if c in numeric_cols]

    if weight_col and dollar_cols:
        subheading("Weighted estimates (key financial variables)")
        lines.append(f"  {'Variable':<20s}  {'Wtd Mean':>16s}  {'Wtd Median':>16s}  {'Min':>16s}  {'Max':>16s}")
        lines.append("  " + "-" * 88)
        for col in dollar_cols:
            wmean = weighted_mean(df, col, weight_col)
            wmed = weighted_median(df, col, weight_col)
            cmin = df[col].min()
            cmax = df[col].max()
            lines.append(
                f"  {col:<20s}  {wmean:>16,.0f}  {wmed:>16,.0f}  {cmin:>16,.0f}  {cmax:>16,.0f}"
            )

    # Categorical breakdowns for key demographics
    demo_cols = match_columns(df, VARIABLE_GROUPS["Demographics"]["prefixes"])
    categorical_cols = [c for c in demo_cols if df[c].nunique() <= 20]

    if categorical_cols:
        subheading("Frequency tables (demographic variables)")
        for col in categorical_cols:
            lines.append(f"  {col}:")
            if weight_col:
                freq = df.groupby(col)[weight_col].sum()
                freq_pct = freq / freq.sum() * 100
                for val in freq.index:
                    lines.append(f"    {val!s:<30s}  pop={freq[val]:>12,.0f}  ({freq_pct[val]:5.1f}%)")
            else:
                freq = df[col].value_counts()
                for val in freq.index:
                    lines.append(f"    {val!s:<30s}  n={freq[val]:>8,}")
            lines.append("")

    # Homeownership rate
    own_cols = match_columns(df, ["POWNRENT"])
    if own_cols:
        subheading("Homeownership")
        col = own_cols[0]
        if weight_col:
            freq = df.groupby(col)[weight_col].sum()
            total = freq.sum()
            for val in freq.index:
                lines.append(f"    {val!s:<30s}  {freq[val]/total*100:5.1f}%")
        else:
            lines.append(f"  {df[col].value_counts().to_string()}")

    heading("END OF REPORT")
    return "\n".join(lines)


def main():
    data_file = find_data_file()
    if data_file is None:
        print("ERROR: No data file found in", DATA_DIR)
        print("Run download_sfs_pumf.py first to download the PUMF.")
        return 1

    df = load_pumf(data_file)
    report = generate_report(df)

    # Print to console
    print(report)

    # Save to file
    with open(REPORT_PATH, "w") as f:
        f.write(report)
    print(f"\nReport saved to: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
