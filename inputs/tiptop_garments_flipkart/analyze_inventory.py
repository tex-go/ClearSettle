"""
ClearSettle — Flipkart Report Inventory & Deep Analysis
Client: Tip Top Garments
Phase 1: File Discovery, Extraction, Column Analysis
"""

import os, sys, zipfile, json, re
from pathlib import Path
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# Force UTF-8 output on Windows
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR = Path("C:/Ranjith/working_dir/ClearSettle/inputs/tiptop_garments_flipkart")
OUT_DIR  = BASE_DIR / "analysis_output"
RAW_DIR  = OUT_DIR / "raw_extracted"

for d in [OUT_DIR, RAW_DIR]:
    d.mkdir(parents=True, exist_ok=True)

report = []
column_map = []
sheet_map  = []
errors     = []

# ─── helpers ────────────────────────────────────────────────────────────────

def classify_report(name: str, cols: list[str]) -> str:
    n = name.lower()
    c = " ".join(str(x).lower() for x in cols)
    if "payment" in n:        return "Payment Report"
    if "settlement" in n:     return "Settlement Report"
    if "tax" in n:            return "Tax Report"
    if "invoice" in n:        return "Invoice Report"
    if "commission" in n:     return "Commission Invoice"
    if "profit" in n and "loss" in n: return "Profit & Loss Report"
    if "fulfil" in n:         return "Fulfilment Report"
    if "pickup" in n:         return "Pickup Report"
    if "listing" in n:        return "Listings Report"
    if "order" in n:          return "Orders Report"
    if "return" in c:         return "Returns Report"
    if "settlement" in c:     return "Settlement Report"
    if "order" in c:          return "Orders Report"
    return "Unknown"

def detect_date_range(df: pd.DataFrame) -> str:
    date_cols = [c for c in df.columns if any(k in str(c).lower() for k in ["date","time","created","updated","period"])]
    for col in date_cols:
        try:
            s = pd.to_datetime(df[col], errors='coerce', dayfirst=True).dropna()
            if len(s) > 0:
                return f"{s.min().date()} → {s.max().date()}"
        except: pass
    return "N/A"

def find_id_cols(cols: list[str]) -> str:
    keys = [c for c in cols if any(k in str(c).lower() for k in
            ["order","shipment","invoice","settle","payment","sku","fsn","track","item"])]
    return ", ".join(keys[:6])

def read_excel_sheets(path: Path):
    """Read all sheets from an xlsx file, return list of (sheet_name, df)."""
    results = []
    try:
        xl = pd.ExcelFile(path, engine='openpyxl')
        for sheet in xl.sheet_names:
            try:
                df = xl.parse(sheet, dtype=str)
                df.columns = [str(c).strip() for c in df.columns]
                results.append((sheet, df))
            except Exception as e:
                errors.append(f"  Sheet read error {path.name}::{sheet}: {e}")
    except Exception as e:
        errors.append(f"Excel open error {path.name}: {e}")
    return results

def analyze_file(path: Path, source_zip: str = ""):
    fname = path.name
    suffix = path.suffix.lower()

    if suffix not in ['.xlsx', '.xls', '.csv']:
        return

    sheets_data = []
    if suffix in ['.xlsx', '.xls']:
        sheets_data = read_excel_sheets(path)
    elif suffix == '.csv':
        try:
            df = pd.read_csv(path, dtype=str, encoding='utf-8-sig')
            sheets_data = [("Sheet1", df)]
        except Exception as e:
            errors.append(f"CSV error {fname}: {e}")
            return

    for sheet_name, df in sheets_data:
        if df.empty or len(df.columns) < 2:
            continue

        # Remove fully-empty rows and cols
        df.dropna(how='all', inplace=True)
        df.dropna(axis=1, how='all', inplace=True)

        cols = list(df.columns)
        rtype = classify_report(fname + " " + sheet_name, cols)
        date_range = detect_date_range(df)
        id_cols = find_id_cols(cols)
        total_cols = len(cols)
        total_rows = len(df)

        report.append({
            "file_name": fname,
            "source_zip": source_zip,
            "sheet_name": sheet_name,
            "file_type": suffix.upper(),
            "rows": total_rows,
            "cols": total_cols,
            "report_type": rtype,
            "date_range": date_range,
            "key_columns": id_cols,
            "all_columns": " | ".join(cols),
        })

        # Column detail map
        for col in cols:
            non_null = df[col].notna().sum()
            sample = df[col].dropna().head(3).tolist()
            column_map.append({
                "source_file": fname,
                "sheet": sheet_name,
                "raw_column": col,
                "non_null_rows": non_null,
                "sample_values": " / ".join(str(x) for x in sample),
            })

        sheet_map.append({
            "file": fname,
            "sheet": sheet_name,
            "columns": cols,
            "df": df,
        })

# ─── STEP 1: Extract ZIPs ──────────────────────────────────────────────────

print("=" * 70)
print("ClearSettle — Flipkart Inventory Analysis")
print("Client: Tip Top Garments")
print("=" * 70)

zip_files = list(BASE_DIR.glob("*.zip"))
print(f"\n[ZIP] Found {len(zip_files)} ZIP files:")
for zf in zip_files:
    extract_dir = RAW_DIR / zf.stem
    extract_dir.mkdir(exist_ok=True)
    print(f"  Extracting: {zf.name} → {extract_dir}")
    try:
        with zipfile.ZipFile(zf, 'r') as z:
            z.extractall(extract_dir)
            names = z.namelist()
            print(f"    Contains: {', '.join(names)}")
    except Exception as e:
        errors.append(f"ZIP error {zf.name}: {e}")
        print(f"    ERROR: {e}")

# ─── STEP 2: Analyze all root-level Excel/CSV ─────────────────────────────

print("\n[FILES] Scanning root-level files...")
for f in sorted(BASE_DIR.glob("*.xlsx")) :
    print(f"  → {f.name}")
    analyze_file(f)

for f in sorted(BASE_DIR.glob("*.csv")):
    print(f"  → {f.name}")
    analyze_file(f)

# ─── STEP 3: Analyze extracted ZIP contents ───────────────────────────────

print("\n[ZIP CONTENTS] Scanning extracted files...")
for zdir in sorted(RAW_DIR.iterdir()):
    if zdir.is_dir():
        for f in sorted(zdir.rglob("*")):
            if f.suffix.lower() in ['.xlsx', '.xls', '.csv'] and f.is_file():
                print(f"  → {f.relative_to(RAW_DIR)}")
                analyze_file(f, source_zip=zdir.name)

# ─── STEP 4: Save inventory report ────────────────────────────────────────

inv_df = pd.DataFrame(report)
col_df = pd.DataFrame(column_map)

with pd.ExcelWriter(OUT_DIR / "01_file_inventory.xlsx", engine='openpyxl') as w:
    inv_df.to_excel(w, sheet_name="Report Inventory", index=False)
    col_df.to_excel(w, sheet_name="Column Dictionary", index=False)

print(f"\n[INVENTORY] Saved: 01_file_inventory.xlsx")
print(f"  Reports found: {len(report)}")
print(f"  Total columns catalogued: {len(column_map)}")

# ─── STEP 5: Print summary table ──────────────────────────────────────────

print("\n" + "=" * 70)
print("REPORT INVENTORY TABLE")
print("=" * 70)
print(f"{'#':<3} {'File Name':<50} {'Sheet':<25} {'Type':<25} {'Rows':>6} {'Cols':>4} {'Date Range':<25}")
print("-" * 140)
for i, r in enumerate(report):
    fname = r['file_name'][:48]
    sheet = r['sheet_name'][:23]
    rtype = r['report_type'][:23]
    print(f"{i+1:<3} {fname:<50} {sheet:<25} {rtype:<25} {r['rows']:>6} {r['cols']:>4}  {r['date_range']:<25}")

# ─── STEP 6: Print column highlights ──────────────────────────────────────

print("\n" + "=" * 70)
print("KEY COLUMN HIGHLIGHTS PER REPORT")
print("=" * 70)
for r in report:
    print(f"\n  [{r['report_type']}] {r['file_name']} :: {r['sheet_name']}")
    print(f"    KEY COLS : {r['key_columns'] or 'none detected'}")
    print(f"    ALL COLS : {r['all_columns'][:200]}")

# ─── STEP 7: Save sheets for downstream use ───────────────────────────────

sheets_meta = []
for sm in sheet_map:
    sm_copy = {k: v for k, v in sm.items() if k != 'df'}
    sheets_meta.append(sm_copy)

with open(OUT_DIR / "sheets_meta.json", 'w') as f:
    json.dump(sheets_meta, f, indent=2)

# ─── STEP 8: Quick numeric summary on each sheet ─────────────────────────

print("\n" + "=" * 70)
print("NUMERIC COLUMN SUMMARY (amounts/fees detected)")
print("=" * 70)

for sm in sheet_map:
    df = sm['df']
    fname = sm['file']
    sheet = sm['sheet']
    # Try to find amount columns
    amount_cols = [c for c in df.columns if any(k in str(c).lower() for k in
                   ["amount","fee","charge","total","rate","price","cost","settlement","payment","gst","tax","tcs","tds"])]
    if amount_cols:
        print(f"\n  {fname} :: {sheet}")
        for col in amount_cols[:10]:
            try:
                numeric = pd.to_numeric(df[col].str.replace(',','', regex=False), errors='coerce').dropna()
                if len(numeric) > 0:
                    print(f"    {col:<45} count={len(numeric):>5}  sum={numeric.sum():>15,.2f}  min={numeric.min():>10,.2f}  max={numeric.max():>10,.2f}")
            except: pass

if errors:
    print("\n" + "=" * 70)
    print("ERRORS / WARNINGS")
    for e in errors:
        print(f"  {e}")

print("\n[DONE] Phase 1 inventory complete.")
print(f"Output: {OUT_DIR}")
