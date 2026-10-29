# Transplant Medication Budget & Capacity Planning

Interactive Python dashboard for exploring medication-budget sustainability and transplant-volume scenarios.

**Public portfolio demonstration — every supplied data value is fictional.** No hospital extracts, patient records, drug-specific purchase prices, or original Git history are included.

## What it demonstrates
- Interactive budget composition and annual expenditure projections.
- Adult and pediatric kidney/liver transplant cost modelling.
- Multiyear maintenance-cost carry-over from new transplant cohorts.
- Sensitivity to medication prices, cost uplifts, growth and census changes.
- Scenario comparisons for medication-budget planning.

## Run locally
```bash
python -m pip install -r requirements.txt
streamlit run app.py
```
The synthetic workbook is bundled; no private data or credentials are required.

## Project context and contribution
Maher Aldemerdash independently developed the original departmental analytics project, including integration, cleaning and validation of five source datasets, scenario analysis, dashboard development and presentation to hospital leadership. The underlying project examined medication-budget constraints and the financial feasibility of transplant expansion.

This repository demonstrates the dashboard and scenario engine. The original five-source data-engineering pipeline is not included. Public synthetic outputs do not reproduce or substantiate the original financial findings.

## Synthetic inputs
`synthetic_budget_data.xlsx` contains invented aggregate census, annual costs, placeholder protocol cost components and specialty-therapy costs. The illustrative SAR 12 million budget is on a comparable departmental scale, without representing an institution. All costs are illustrative and are not clinical protocols or market-price estimates.

## Scope and limitations
This copy preserves the original calculation logic; only demo inputs, default constants and identifying/display text were changed. It is an illustrative portfolio tool, not a validated operational or clinical decision system. Capacity refers to medication-budget affordability, not staffing, theatres, beds or achieved transplant activity. Annual spending is treated as evenly distributed for depletion estimates; case mix is fixed in capacity calculations. Census reductions and specialty-cost exclusions model departmental budget effects, not proven system-wide savings or recommendations to alter care.

Known inherited limitations: the standalone maximum-capacity helper double-counts specialty costs; the displayed additional-capacity card uses separate logic. Budget percentage properties use a fixed demo ceiling. Calculation corrections were outside the requested scope.
