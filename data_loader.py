"""
data_loader.py
Reads raw_data_budget_2026.xlsx and returns clean, validated base constants
for the Transplant Sustainability Engine.
"""

import pandas as pd
from pathlib import Path

DATA_FILE = Path(__file__).parent / "synthetic_budget_data.xlsx"


def load_all():
    """
    Returns a single dict with every constant the engine needs.
    Call once at app startup.
    """
    xl = pd.ExcelFile(DATA_FILE)

    assumptions   = _load_assumptions(xl)
    census        = _load_census(xl)
    protocols     = _load_protocols(xl)
    orphan_drugs  = _load_orphan(xl)

    return {
        "assumptions":  assumptions,
        "census":       census,
        "protocols":    protocols,
        "orphan_drugs": orphan_drugs,
    }


# ── helpers ──────────────────────────────────────────────────────────────────

def _load_assumptions(xl):
    df = pd.read_excel(xl, sheet_name="assumptions")
    df.columns = ["Parameter", "Value", "Notes"]
    d = dict(zip(df["Parameter"], df["Value"]))
    return {
        "budget_sar":             float(d["Medication_Budget_SAR"]),
        "avg_adult_weight_kg":    float(d["Avg_Adult_Weight_kg"]),
        "avg_ped_weight_kg":      float(d["Avg_Pediatric_Weight_kg"]),
        "secondary_meds_uplift":  float(d["Secondary_Meds_Uplift_Pct"]),
        "current_year":           int(d["Current_Year"]),
        "projection_horizon":     int(d["Projection_Horizon_Years"]),
        "tcmr_baseline_rate":     float(d["TCMR_Baseline_Rate"]),
        "amr_baseline_rate":      float(d["AMR_Baseline_Rate"]),
    }


def _load_census(xl):
    df = pd.read_excel(xl, sheet_name="Patient_Census")
    df.columns = ["category", "patients", "cost_per_head", "notes"]
    df = df[["category", "patients", "cost_per_head"]].copy()
    df["patients"]      = pd.to_numeric(df["patients"],      errors="coerce").fillna(0).astype(int)
    df["cost_per_head"] = pd.to_numeric(df["cost_per_head"], errors="coerce").fillna(0.0)
    df["annual_cost"]   = df["patients"] * df["cost_per_head"]

    # Return as dict keyed by category for easy lookup
    result = {}
    for _, row in df.iterrows():
        result[row["category"]] = {
            "patients":      row["patients"],
            "cost_per_head": row["cost_per_head"],
            "annual_cost":   row["annual_cost"],
        }
    return result


def _load_protocols(xl):
    """
    Returns cost-per-patient for each of the 8 protocol tabs.
    Keys: new_kidney_adult, new_kidney_ped, new_liver_adult, new_liver_ped
          old_kidney_adult, old_kidney_ped, old_liver_adult, old_liver_ped
    """
    tab_map = {
        "new_kidney_adult": "Protocols_New_Kidney_adult",
        "new_liver_adult":  "Protocols_New_Liver_adult",
        "old_kidney_adult": "Protocols_Old_Kidney_adult",
        "old_liver_adult":  "Protocols_Old_Liver_adult",
        "old_liver_ped":    "Protocols_old_Liver_Ped",
        "new_liver_ped":    "Protocols_new_Liver_Ped",
        "old_kidney_ped":   "Protocols_old_kidney_Ped",
        "new_kidney_ped":   "Protocols_new_kidney_Ped",
    }

    result = {}
    for key, sheet in tab_map.items():
        df = pd.read_excel(xl, sheet_name=sheet, header=None)
        # Some tabs have headers, some don't — detect by checking if row 0 col 1 is numeric
        try:
            float(df.iloc[0, 1])
            # No header — data starts at row 0
            cost = pd.to_numeric(df.iloc[:, 1], errors="coerce").sum()
        except (ValueError, TypeError):
            # Has header — skip row 0
            cost = pd.to_numeric(df.iloc[1:, 1], errors="coerce").sum()
        result[key] = round(cost, 2)

    return result


def _load_orphan(xl):
    df = pd.read_excel(xl, sheet_name="Orphan_Specialty_Spend")
    df.columns = ["drug_name", "annual_cost", "reference", "comment"]
    df["annual_cost"] = pd.to_numeric(df["annual_cost"], errors="coerce").fillna(0)
    drugs = df[["drug_name", "annual_cost"]].to_dict(orient="records")
    total = df["annual_cost"].sum()
    return {"drugs": drugs, "total": total}


# ── quick sanity check ────────────────────────────────────────────────────────

if __name__ == "__main__":
    data = load_all()

    print("\n=== ASSUMPTIONS ===")
    for k, v in data["assumptions"].items():
        print(f"  {k:30s}: {v}")

    print("\n=== CENSUS (annual cost per category) ===")
    total_census = 0
    for cat, d in data["census"].items():
        print(f"  {cat:30s}: {d['patients']:5d} pts × {d['cost_per_head']:8.2f} = {d['annual_cost']:>12,.2f} SAR")
        total_census += d["annual_cost"]
    print(f"  {'SUBTOTAL':50s} {total_census:>12,.2f} SAR")

    print("\n=== PROTOCOLS (cost per new patient, Year 1) ===")
    for k, v in data["protocols"].items():
        print(f"  {k:25s}: {v:>10,.2f} SAR")

    print("\n=== ORPHAN / NUKE MEDS ===")
    for d in data["orphan_drugs"]["drugs"]:
        print(f"  {d['drug_name'][:50]:50s}: {d['annual_cost']:>12,.2f} SAR")
    print(f"  {'TOTAL NUKES':50s} {data['orphan_drugs']['total']:>12,.2f} SAR")

    print("\n=== BUDGET SNAPSHOT ===")
    locked = total_census + data["orphan_drugs"]["total"]
    budget = data["assumptions"]["budget_sar"]
    print(f"  Census drain:     {total_census:>12,.2f} SAR")
    print(f"  Orphan nukes:     {data['orphan_drugs']['total']:>12,.2f} SAR")
    print(f"  TOTAL LOCKED:     {locked:>12,.2f} SAR")
    print(f"  BUDGET:           {budget:>12,.2f} SAR")
    print(f"  REMAINING:        {budget - locked:>12,.2f} SAR  {'🚨 OVER BUDGET' if locked > budget else '✅'}")
