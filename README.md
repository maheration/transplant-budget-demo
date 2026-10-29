# Transplant Medication Budget & Capacity Planning

An interactive dashboard for exploring medication expenditure, budget sustainability, and the financial feasibility of transplant service expansion.

Built by **Maher Aldemerdash, Consultant Transplant Nephrologist**.

## Project background

The original project addressed a 50% reduction in a transplant department’s medication budget. It examined spending patterns and opportunities to accommodate increased transplant activity within the revised medication budget.

I independently delivered the project from data preparation through analysis, dashboard development, and presentation to hospital leadership.

## Analytical functionality

- Medication expenditure breakdown by patient group.
- Adult and pediatric kidney and liver transplant scenarios.
- Multiyear projections incorporating ongoing maintenance costs.
- Sensitivity analyses for medication prices, complication-related costs, and activity growth.
- Interactive comparisons of expenditure and available medication budget.

## Data preparation

The original analysis required linking, cleaning, reconciling, and validating data from five sources.

This repository contains the dashboard and calculation engine. The original source datasets and upstream data-engineering pipeline are not included.

## Public demonstration

**All bundled data are synthetic.** Patient counts, costs, and budget assumptions are fictional examples created to demonstrate the interface. They do not represent hospital records or reproduce the original findings.

Financial feasibility refers to medication-budget affordability; it does not establish staffing, bed, theatre, or total departmental capacity.

## Run locally

Requires Python 3.10 or later.

```bash
pip install -r requirements.txt
streamlit run app.py
```

The synthetic workbook is included; no private datasets or credentials are required.

## Technology

Python · Streamlit · pandas · Plotly · Excel

## Scope

This portfolio demonstration preserves the original modelling approach. It is intended to illustrate analytical functionality.
