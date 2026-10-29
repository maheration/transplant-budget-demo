"""
app.py  –  Multi-Organ Transplant Department
           Medication Budget Sustainability Forecast

Run:  streamlit run app.py
Deps: pip install streamlit plotly pandas openpyxl
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from copy import deepcopy

from data_loader import load_all
from engine import SimParams, run_simulation, max_sustainable_transplants, freeze_scenario

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MOTC Budget Sustainability",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Custom CSS  –  executive look
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .main { background-color: #0f1117; color: #e0e0e0; }
    .block-container { padding-top: 1rem; }

    /* KPI cards */
    .kpi-card {
        background: #1e2130;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        text-align: center;
        border-left: 5px solid #4f8ef7;
    }
    .kpi-card.danger  { border-left-color: #e05252; }
    .kpi-card.warning { border-left-color: #f0a500; }
    .kpi-card.safe    { border-left-color: #3dbb6e; }
    .kpi-label  { font-size: 0.78rem; color: #8a8fa8; letter-spacing: 0.06em; text-transform: uppercase; }
    .kpi-value  { font-size: 1.9rem; font-weight: 700; margin: 0.2rem 0; }
    .kpi-sub    { font-size: 0.75rem; color: #8a8fa8; }
    .danger-val  { color: #e05252; }
    .warning-val { color: #f0a500; }
    .safe-val    { color: #3dbb6e; }
    .white-val   { color: #ffffff; }

    /* Alert banner */
    .alert-banner {
        background: linear-gradient(135deg, #7a1111, #b22222);
        border-radius: 10px;
        padding: 1rem 1.5rem;
        margin-bottom: 1rem;
        font-size: 1.1rem;
        font-weight: 600;
        color: #fff;
        text-align: center;
        letter-spacing: 0.03em;
    }
    .safe-banner {
        background: linear-gradient(135deg, #0a4a24, #1a7a42);
        border-radius: 10px;
        padding: 1rem 1.5rem;
        margin-bottom: 1rem;
        font-size: 1.1rem;
        font-weight: 600;
        color: #fff;
        text-align: center;
    }

    /* Section headers */
    .section-header {
        font-size: 1rem;
        font-weight: 600;
        color: #4f8ef7;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin: 1.2rem 0 0.4rem 0;
        border-bottom: 1px solid #2a2f45;
        padding-bottom: 0.3rem;
    }

    /* Sidebar */
    .css-1d391kg { background-color: #161824; }
    div[data-testid="stSidebar"] { background-color: #161824; }

    /* Streamlit default overrides */
    h1, h2, h3 { color: #e8eaf6; }
    .stMetric label { color: #8a8fa8 !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Load data (cached)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data
def get_data():
    return load_all()


data = get_data()
BUDGET = data["assumptions"]["budget_sar"]
CURRENT_YEAR = data["assumptions"]["current_year"]

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar  –  all levers
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎛️ Control Panel")
    st.caption("All charts update instantly")

    # ── Transplant volume ───────────────────────────────────────────────
    st.markdown('<div class="section-header">🔢 New Transplants (Annual Volume)</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        new_kidney_adult = st.number_input("Kidney Adult", 0, 500, 160, step=10)
        new_liver_adult  = st.number_input("Liver Adult",  0, 200, 64,  step=5)
    with col2:
        new_kidney_ped   = st.number_input("Kidney Ped",   0, 200, 40,  step=5)
        new_liver_ped    = st.number_input("Liver Ped",    0, 100, 16,  step=2)

    st.caption("Growth % applies from Year 2 onwards — does not affect current baseline.")
    kidney_growth = st.slider("Annual Kidney Growth %", 0, 25, 0, format="%d%%") / 100
    liver_growth  = st.slider("Annual Liver Growth %",  0, 25, 0, format="%d%%") / 100

    # ── Discharge levers ────────────────────────────────────────────────
    st.markdown('<div class="section-header">🚪 Discharge Levers</div>', unsafe_allow_html=True)
    dis_kidney_a = st.slider("Discharge Old Kidney (Adult) %", 0, 25, 0, format="%d%%") / 100
    dis_kidney_p = st.slider("Discharge Old Kidney (Ped) %",   0, 25, 0, format="%d%%") / 100
    dis_liver_a  = st.slider("Discharge Old Liver (Adult) %",  0, 25, 0, format="%d%%") / 100
    dis_liver_p  = st.slider("Discharge Old Liver (Ped) %",    0, 25, 0, format="%d%%") / 100
    dis_nephro   = st.slider("Discharge Gen Nephrology %",     0, 25, 0, format="%d%%") / 100
    dis_gn       = st.slider("Discharge GN Clinic %",          0, 25, 0, format="%d%%") / 100

    # ── General clinic growth ───────────────────────────────────────────
    st.markdown('<div class="section-header">📈 General Clinic Growth</div>', unsafe_allow_html=True)
    gen_nephro_growth = st.slider("Gen Nephrology Growth %",  0, 15, 0, format="%d%%") / 100
    gen_hepato_growth = st.slider("Gen Hepatology Growth %",  0, 15, 0, format="%d%%") / 100

    # ── Risk & sensitivity ──────────────────────────────────────────────
    st.markdown('<div class="section-header">⚠️ Risk & Sensitivity</div>', unsafe_allow_html=True)
    drug_price_chg  = st.slider("Drug Price Change %", -20, 20, 0, format="%d%%") / 100
    rejection_uplift = st.slider("Rejection/Complication Uplift %", 0, 30, 0, format="%d%%") / 100

    # ── Toggles ─────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">🔘 Toggles</div>', unsafe_allow_html=True)
    include_nukes = st.toggle("Include Specialty Medications", value=True,
                              help="Fictional specialty therapies — illustrative costs only")

    horizon = st.radio("Projection Horizon", [3, 5], horizontal=True)

# ─────────────────────────────────────────────────────────────────────────────
# Build simulation params & run
# ─────────────────────────────────────────────────────────────────────────────
params = SimParams(
    budget_sar              = BUDGET,
    new_kidney_adult        = new_kidney_adult,
    new_kidney_ped          = new_kidney_ped,
    new_liver_adult         = new_liver_adult,
    new_liver_ped           = new_liver_ped,
    kidney_growth_pct       = kidney_growth,
    liver_growth_pct        = liver_growth,
    discharge_old_kidney_adult = dis_kidney_a,
    discharge_old_kidney_ped   = dis_kidney_p,
    discharge_old_liver_adult  = dis_liver_a,
    discharge_old_liver_ped    = dis_liver_p,
    discharge_gen_nephro       = dis_nephro,
    discharge_gen_nephro_ped   = dis_nephro,
    discharge_gn               = dis_gn,
    drug_price_change_pct      = drug_price_chg,
    rejection_uplift_pct       = rejection_uplift,
    gen_nephro_growth_pct      = gen_nephro_growth,
    gen_hepato_growth_pct      = gen_hepato_growth,
    include_nukes              = include_nukes,
    horizon                    = horizon,
)

results      = run_simulation(data, params)
cap_info     = max_sustainable_transplants(data, params)
freeze_res   = freeze_scenario(data, params)

yr0 = results[0]
over_budget  = yr0.total_spend > BUDGET
pct_used     = yr0.pct_budget_used
gap_sar      = yr0.total_spend - BUDGET

# Find collapse year
collapse_label = "Beyond horizon ✅"
for r in results:
    if r.total_spend > BUDGET:
        collapse_label = str(r.year)
        break

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<h1 style='text-align:center; font-size:1.6rem; margin-bottom:0.2rem;'>
🏥 Multi-Organ Transplant Department
</h1>
<p style='text-align:center; color:#8a8fa8; font-size:0.9rem; margin-top:0;'>
Medication Budget Sustainability Forecast &nbsp;|&nbsp;
Fixed Annual Budget: <b style='color:#4f8ef7;'>12,000,000 SAR</b> &nbsp;|&nbsp; 2027–2030
</p>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ALERT BANNER
# ─────────────────────────────────────────────────────────────────────────────
if over_budget:
    st.markdown(f"""
    <div class="alert-banner">
    🚨 BUDGET EXCEEDED — Current spend is <b>{gap_sar:+,.0f} SAR</b> over the 12M limit
    &nbsp;|&nbsp; Collapse Year: <b>{collapse_label}</b>
    </div>""", unsafe_allow_html=True)
else:
    remaining = BUDGET - yr0.total_spend
    st.markdown(f"""
    <div class="safe-banner">
    ✅ Within Budget — <b>{remaining:,.0f} SAR</b> remaining this year
    &nbsp;|&nbsp; {pct_used:.1f}% of budget consumed
    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# KPI CARDS  (row 1)
# ─────────────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)

def kpi_html(label, value, sub, card_class, val_class):
    return f"""
    <div class="kpi-card {card_class}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value {val_class}">{value}</div>
        <div class="kpi-sub">{sub}</div>
    </div>"""

with k1:
    val_class = "danger-val" if over_budget else "safe-val"
    card_class = "danger" if over_budget else "safe"
    st.markdown(kpi_html(
        "Current Annual Spend",
        f"{yr0.total_spend/1e6:.2f}M SAR",
        f"Budget: 12.0M SAR",
        card_class, val_class
    ), unsafe_allow_html=True)

with k2:
    maint_pct = yr0.total_maintenance / BUDGET * 100
    val_class  = "danger-val" if pct_used > 100 else ("warning-val" if pct_used > 85 else "safe-val")
    card_class = "danger" if pct_used > 100 else ("warning" if pct_used > 85 else "safe")
    st.markdown(kpi_html(
        "% Budget Consumed",
        f"{pct_used:.1f}%",
        ("Existing patients only" if abs(pct_used - maint_pct) < 0.5 else f"Maintenance: {maint_pct:.1f}% | Total incl. new Tx: {pct_used:.1f}%"),
        card_class, val_class
    ), unsafe_allow_html=True)

with k3:
    import math
    month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    if collapse_label == "Beyond horizon ✅":
        st.markdown(kpi_html("Budget Collapse", "Safe ✅",
                             f"Beyond {CURRENT_YEAR + horizon}", "safe", "safe-val"),
                    unsafe_allow_html=True)
    else:
        # Find first over-budget year and calculate month
        for r in results:
            if r.total_spend > BUDGET:
                monthly_spend = r.total_spend / 12
                month_num = min(math.ceil(BUDGET / monthly_spend), 12)
                month_name = month_names[month_num - 1]
                collapse_month_label = f"{month_name} {r.year}"
                break
        st.markdown(kpi_html("Budget Collapse",
                             collapse_month_label,
                             "Estimated month of depletion",
                             "danger", "danger-val"),
                    unsafe_allow_html=True)

with k4:
    # Available SAR = what's left after EVERYTHING (existing + nukes + new tx already planned)
    available_sar = BUDGET - yr0.total_spend

    if available_sar <= 0:
        st.markdown(kpi_html(
            "Additional Tx Capacity",
            "0",
            f"Over budget by {abs(available_sar)/1e6:.2f}M SAR",
            "danger", "danger-val"
        ), unsafe_allow_html=True)
    else:
        # How many more transplants can fit in the remaining SAR
        proto        = data["protocols"]
        price_mult   = 1 + params.drug_price_change_pct
        reject_mult  = 1 + params.rejection_uplift_pct
        adult_ped_r  = 0.80
        kl_ratio     = 200 / 280
        avg_k = (adult_ped_r * proto["new_kidney_adult"] + (1 - adult_ped_r) * proto["new_kidney_ped"]) * price_mult * reject_mult
        avg_l = (adult_ped_r * proto["new_liver_adult"]  + (1 - adult_ped_r) * proto["new_liver_ped"])  * price_mult * reject_mult
        blended = kl_ratio * avg_k + (1 - kl_ratio) * avg_l
        extra_total = int(available_sar / blended) if blended > 0 else 0
        extra_k     = int(extra_total * kl_ratio)
        extra_l     = extra_total - extra_k
        val_class   = "warning-val" if extra_total < 50 else "safe-val"
        card_class  = "warning" if extra_total < 50 else "safe"
        st.markdown(kpi_html(
            "Additional Tx Capacity",
            f"{extra_total}",
            f"+{extra_k} kidney + {extra_l} liver still possible",
            card_class, val_class
        ), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CHARTS  –  row 1: breakdown bar  |  projection line
# ─────────────────────────────────────────────────────────────────────────────
col_bar, col_line = st.columns([1, 1.6])

with col_bar:
    st.markdown('<div class="section-header">💰 Budget Composition (Current Baseline)</div>', unsafe_allow_html=True)

    categories = [
        "Old Kidney\n(Adult)",
        "Old Kidney\n(Ped)",
        "Old Liver\n(Adult)",
        "Old Liver\n(Ped)",
        "Gen Nephrology",
        "GN Clinic",
        "New Kidney",
        "New Liver",
        "Orphan Meds",
    ]
    values = [
        yr0.cost_old_kidney_adult,
        yr0.cost_old_kidney_ped,
        yr0.cost_old_liver_adult,
        yr0.cost_old_liver_ped,
        yr0.cost_gen_nephro + yr0.cost_gen_nephro_ped,
        yr0.cost_gn,
        yr0.cost_new_kidney_adult + yr0.cost_new_kidney_ped,
        yr0.cost_new_liver_adult  + yr0.cost_new_liver_ped,
        yr0.cost_nukes,
    ]
    colors = [
        "#4f8ef7","#7ab3fa","#f0a500","#f5c842",
        "#3dbb6e","#5dd68a","#e05252","#ea8080","#b040b0"
    ]

    fig_bar = go.Figure(go.Bar(
        x=categories, y=values,
        marker_color=colors,
        text=[f"{v/1e6:.2f}M" for v in values],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{y:,.0f} SAR<extra></extra>",
    ))
    fig_bar.add_hline(y=BUDGET, line_dash="dash", line_color="#e05252",
                      annotation_text="12M Budget", annotation_font_color="#e05252")
    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c0c0c0", showlegend=False,
        yaxis=dict(gridcolor="#2a2f45", tickformat=",.0f"),
        xaxis=dict(tickfont=dict(size=10)),
        margin=dict(t=20, b=10),
        height=360,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col_line:
    st.markdown('<div class="section-header">📈 3–5 Year Sustainability Projection</div>', unsafe_allow_html=True)

    years = [r.year for r in results]
    spend_base   = [r.total_spend for r in results]
    spend_freeze = [r.total_spend for r in freeze_res]

    # Discharge 15% scenario
    p_dis = deepcopy(params)
    p_dis.discharge_old_kidney_adult = 0.15
    p_dis.discharge_old_kidney_ped   = 0.15
    p_dis.discharge_old_liver_adult  = 0.15
    p_dis.discharge_old_liver_ped    = 0.15
    p_dis.discharge_gen_nephro       = 0.15
    p_dis.discharge_gen_nephro_ped   = 0.15
    p_dis.discharge_gn               = 0.15
    spend_discharge = [r.total_spend for r in run_simulation(data, p_dis)]

    fig_line = go.Figure()

    # Budget ceiling
    fig_line.add_hline(y=BUDGET, line_color="#e05252", line_width=2.5,
                       annotation_text="  12M Budget Ceiling",
                       annotation_font_color="#e05252",
                       annotation_position="bottom right")

    # Scenarios
    fig_line.add_trace(go.Scatter(
        x=years, y=spend_base, name="Current Scenario",
        line=dict(color="#4f8ef7", width=3),
        mode="lines+markers+text",
        text=[f"{v/1e6:.1f}M" for v in spend_base],
        textposition="top center", textfont=dict(size=10, color="#4f8ef7"),
        hovertemplate="<b>%{x}</b>: %{y:,.0f} SAR<extra>Current</extra>",
    ))
    fig_line.add_trace(go.Scatter(
        x=years, y=spend_freeze, name="Freeze All New Tx",
        line=dict(color="#3dbb6e", width=2, dash="dot"),
        hovertemplate="<b>%{x}</b>: %{y:,.0f} SAR<extra>Freeze</extra>",
    ))
    fig_line.add_trace(go.Scatter(
        x=years, y=spend_discharge, name="Discharge 15%",
        line=dict(color="#f0a500", width=2, dash="dash"),
        hovertemplate="<b>%{x}</b>: %{y:,.0f} SAR<extra>Discharge 15%</extra>",
    ))

    # Shade over-budget zone
    fig_line.add_hrect(y0=BUDGET, y1=max(spend_base)*1.05,
                       fillcolor="rgba(224,82,82,0.08)", line_width=0)

    fig_line.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c0c0c0",
        legend=dict(bgcolor="rgba(0,0,0,0)", font_size=11),
        yaxis=dict(gridcolor="#2a2f45", tickformat=",.0f", title="SAR"),
        xaxis=dict(gridcolor="#2a2f45", tickvals=years),
        margin=dict(t=20, b=10),
        height=360,
    )
    st.plotly_chart(fig_line, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# CHARTS  –  row 2: budget gap + lever impact (full width)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📉 Budget Gap & Lever Impact</div>', unsafe_allow_html=True)
st.caption("Red bars = annual budget gap. Green bars = SAR saved by each lever under current slider settings.")

col_gap, col_lev = st.columns(2)

with col_gap:
    # Annual budget gap bars (red) — how much over budget each year
    gap_years  = [r.year for r in results]
    gap_vals   = [max(0, r.total_spend - BUDGET) for r in results]
    gap_colors = ["#e05252"] * len(gap_vals)

    fig_gap = go.Figure(go.Bar(
        x=[str(y) for y in gap_years],
        y=gap_vals,
        marker_color=gap_colors,
        text=[f"{v/1e6:.2f}M" for v in gap_vals],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Gap: %{y:,.0f} SAR<extra></extra>",
    ))
    fig_gap.add_hline(y=0, line_color="#666", line_width=1)
    fig_gap.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c0c0c0", showlegend=False,
        title=dict(text="Annual Budget Gap (SAR over 12M)", font=dict(size=12, color="#8a8fa8")),
        yaxis=dict(gridcolor="#2a2f45", tickformat=",.0f", title="SAR Over Budget"),
        xaxis=dict(title="Year"),
        margin=dict(t=40, b=10),
        height=320,
    )
    st.plotly_chart(fig_gap, use_container_width=True)

with col_lev:
    # Dynamic lever savings — all linked to actual sidebar settings
    base_spend = yr0.total_spend

    def test_lever(field, value):
        p = deepcopy(params)
        setattr(p, field, value)
        return run_simulation(data, p)[0].total_spend

    # Discharge lever: use actual sidebar discharge values → compare vs zero discharge
    p_no_discharge = deepcopy(params)
    p_no_discharge.discharge_old_kidney_adult = 0.0
    p_no_discharge.discharge_old_kidney_ped   = 0.0
    p_no_discharge.discharge_old_liver_adult  = 0.0
    p_no_discharge.discharge_old_liver_ped    = 0.0
    p_no_discharge.discharge_gen_nephro       = 0.0
    p_no_discharge.discharge_gen_nephro_ped   = 0.0
    p_no_discharge.discharge_gn               = 0.0
    no_discharge_spend = run_simulation(data, p_no_discharge)[0].total_spend
    discharge_saving = no_discharge_spend - base_spend  # positive = saving

    # Drug price lever: saving vs zero price change
    p_no_price = deepcopy(params)
    p_no_price.drug_price_change_pct = 0.0
    no_price_spend   = run_simulation(data, p_no_price)[0].total_spend
    drug_price_impact = no_price_spend - base_spend  # positive = saving (if slider is negative)

    # Nukes: saving if currently ON, 0 if already OFF
    nuke_saving = (base_spend - test_lever("include_nukes", False)) if params.include_nukes else 0.0

    # Freeze: always a fixed reference
    freeze_saving = base_spend - freeze_res[0].total_spend

    # Any discharge % set?
    any_discharge = max(dis_kidney_a, dis_kidney_p, dis_liver_a, dis_liver_p, dis_nephro, dis_gn)
    discharge_label = f"Discharge levers ({int(any_discharge*100)}%)" if any_discharge > 0 else "Discharge levers (0% — set sliders)"

    lever_names = [
        "Freeze new transplants",
        discharge_label,
        "Remove orphan meds",
        f"Drug price ({int(drug_price_chg*100):+d}%)",
    ]
    lever_vals = [freeze_saving, discharge_saving, nuke_saving, drug_price_impact]
    lever_colors = ["#3dbb6e" if v > 0 else "#e05252" for v in lever_vals]

    fig_lev = go.Figure(go.Bar(
        x=lever_vals,
        y=lever_names,
        orientation="h",
        marker_color=lever_colors,
        text=[f"{v/1e6:+.2f}M SAR" for v in lever_vals],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Impact: %{x:,.0f} SAR<extra></extra>",
    ))
    fig_lev.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c0c0c0", showlegend=False,
        title=dict(text="Lever Impact vs Current Settings", font=dict(size=12, color="#8a8fa8")),
        xaxis=dict(gridcolor="#2a2f45", tickformat=",.0f", title="SAR Saved (+) / Added Cost (-)"),
        yaxis=dict(tickfont=dict(size=11)),
        margin=dict(t=40, b=10, l=10),
        height=320,
    )
    st.plotly_chart(fig_lev, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<hr style='border-color:#2a2f45; margin-top:2rem;'>
<p style='text-align:center; color:#4a5068; font-size:0.75rem;'>
MOTC Medication Budget Sustainability Engine &nbsp;|&nbsp; Data: Synthetic demonstration inputs &nbsp;|&nbsp;
Portfolio demonstration — all data are fictional
</p>
""", unsafe_allow_html=True)
