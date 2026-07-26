"""
European Bank — Customer Churn Analytics Dashboard
Unified Mentor Project

Run with:  streamlit run app.py
Requires:  European_Bank.csv in the same folder (or upload via the sidebar)
"""

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# --------------------------------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="European Bank | Churn Analytics",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

PRIMARY = "#1f4e79"
CHURN_COLOR = "#d9534f"
RETAIN_COLOR = "#2e7d32"

st.markdown(
    """
    <style>
    .kpi-card {
        background: #ffffff;
        border: 1px solid #e6e6e6;
        border-radius: 10px;
        padding: 16px 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .kpi-label { font-size: 0.80rem; color: #666; margin-bottom: 4px; }
    .kpi-value { font-size: 1.6rem; font-weight: 700; color: #1f4e79; }
    .kpi-sub { font-size: 0.75rem; color: #888; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# DATA LOADING & SEGMENTATION
# --------------------------------------------------------------------------
@st.cache_data
def load_data(file) -> pd.DataFrame:
    df = pd.read_csv(file)

    # --- Data validation / cleaning ---
    df = df.drop_duplicates(subset="CustomerId")
    if "Surname" in df.columns:
        df = df.drop(columns=["Surname"])
    for col in ["HasCrCard", "IsActiveMember", "Exited"]:
        df[col] = df[col].astype(int)

    # --- Derived segmentation fields ---
    df["AgeGroup"] = pd.cut(
        df["Age"], bins=[17, 30, 45, 60, 100],
        labels=["<30", "30-45", "46-60", "60+"]
    )

    df["CreditBand"] = pd.cut(
        df["CreditScore"], bins=[0, 579, 699, 900],
        labels=["Low (<580)", "Medium (580-699)", "High (700+)"]
    )

    df["TenureGroup"] = pd.cut(
        df["Tenure"], bins=[-1, 2, 6, 10],
        labels=["New (0-2 yrs)", "Mid-term (3-6 yrs)", "Long-term (7-10 yrs)"]
    )

    def balance_seg(b):
        if b == 0:
            return "Zero Balance"
        elif b < 100000:
            return "Low Balance (<100k)"
        else:
            return "High Balance (100k+)"
    df["BalanceSegment"] = df["Balance"].apply(balance_seg)

    df["ChurnLabel"] = df["Exited"].map({1: "Churned", 0: "Retained"})
    df["ActiveLabel"] = df["IsActiveMember"].map({1: "Active", 0: "Inactive"})
    df["CrCardLabel"] = df["HasCrCard"].map({1: "Has Card", 0: "No Card"})

    return df


st.sidebar.title("🏦 Churn Analytics")
uploaded = st.sidebar.file_uploader("Upload European_Bank.csv", type="csv")

if uploaded is not None:
    df_raw = load_data(uploaded)
elif __import__("os").path.exists("European_Bank.csv"):
    df_raw = load_data("European_Bank.csv")
else:
    st.warning("Upload `European_Bank.csv` in the sidebar to begin.")
    st.stop()

# --------------------------------------------------------------------------
# SIDEBAR FILTERS (segment filters -> drive dynamic KPI updates everywhere)
# --------------------------------------------------------------------------
st.sidebar.markdown("### 🔎 Segment Filters")

geo_sel = st.sidebar.multiselect(
    "Geography", sorted(df_raw["Geography"].unique()), default=list(df_raw["Geography"].unique())
)
gender_sel = st.sidebar.multiselect(
    "Gender", sorted(df_raw["Gender"].unique()), default=list(df_raw["Gender"].unique())
)
age_sel = st.sidebar.multiselect(
    "Age Group", list(df_raw["AgeGroup"].cat.categories), default=list(df_raw["AgeGroup"].cat.categories)
)
tenure_sel = st.sidebar.multiselect(
    "Tenure Group", list(df_raw["TenureGroup"].cat.categories), default=list(df_raw["TenureGroup"].cat.categories)
)
credit_sel = st.sidebar.multiselect(
    "Credit Score Band", list(df_raw["CreditBand"].cat.categories), default=list(df_raw["CreditBand"].cat.categories)
)
balance_sel = st.sidebar.multiselect(
    "Balance Segment", sorted(df_raw["BalanceSegment"].unique()), default=sorted(df_raw["BalanceSegment"].unique())
)
active_sel = st.sidebar.multiselect(
    "Activity Status", ["Active", "Inactive"], default=["Active", "Inactive"]
)
products_sel = st.sidebar.slider(
    "Number of Products", int(df_raw["NumOfProducts"].min()), int(df_raw["NumOfProducts"].max()),
    (int(df_raw["NumOfProducts"].min()), int(df_raw["NumOfProducts"].max()))
)

df = df_raw[
    df_raw["Geography"].isin(geo_sel)
    & df_raw["Gender"].isin(gender_sel)
    & df_raw["AgeGroup"].isin(age_sel)
    & df_raw["TenureGroup"].isin(tenure_sel)
    & df_raw["CreditBand"].isin(credit_sel)
    & df_raw["BalanceSegment"].isin(balance_sel)
    & df_raw["ActiveLabel"].isin(active_sel)
    & df_raw["NumOfProducts"].between(products_sel[0], products_sel[1])
].copy()

st.sidebar.markdown(f"**Filtered customers:** {len(df):,} / {len(df_raw):,}")

if len(df) == 0:
    st.error("No customers match the current filter selection. Please broaden your filters.")
    st.stop()

# --------------------------------------------------------------------------
# HEADER + KPI ROW
# --------------------------------------------------------------------------
st.title("European Bank — Customer Churn Analytics")
st.caption("Unified Mentor Project · The European Central Bank · Segmentation-driven churn analytics")

overall_churn = df["Exited"].mean() * 100
high_value_cutoff = df_raw["Balance"].quantile(0.75)
high_value_df = df[df["Balance"] >= high_value_cutoff]
hv_churn = high_value_df["Exited"].mean() * 100 if len(high_value_df) else 0
inactive_churn = df.loc[df["IsActiveMember"] == 0, "Exited"].mean() * 100 if (df["IsActiveMember"] == 0).any() else 0
active_churn = df.loc[df["IsActiveMember"] == 1, "Exited"].mean() * 100 if (df["IsActiveMember"] == 1).any() else 0
engagement_gap = inactive_churn - active_churn
revenue_at_risk = df.loc[df["Exited"] == 1, "Balance"].sum()

k1, k2, k3, k4, k5 = st.columns(5)
kpis = [
    (k1, "Overall Churn Rate", f"{overall_churn:.1f}%", f"{df['Exited'].sum():,} of {len(df):,} customers"),
    (k2, "High-Value Churn Ratio", f"{hv_churn:.1f}%", "Top 25% by balance (bank-wide)"),
    (k3, "Engagement Drop Indicator", f"{engagement_gap:+.1f} pp", "Inactive vs. active churn gap"),
    (k4, "Revenue at Risk (Balance)", f"€{revenue_at_risk/1e6:.2f}M", "Total balance held by churned customers"),
    (k5, "Avg. Products (Churned)", f"{df.loc[df['Exited']==1,'NumOfProducts'].mean():.2f}", f"vs. {df.loc[df['Exited']==0,'NumOfProducts'].mean():.2f} retained"),
]
for col, label, value, sub in kpis:
    col.markdown(
        f"""<div class="kpi-card"><div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div><div class="kpi-sub">{sub}</div></div>""",
        unsafe_allow_html=True,
    )

st.markdown("---")

# --------------------------------------------------------------------------
# TABS = CORE MODULES
# --------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Overall Summary", "🌍 Geography", "👥 Age & Tenure", "💰 High-Value Explorer"]
)

# ============================== TAB 1: OVERALL SUMMARY ====================
with tab1:
    c1, c2 = st.columns([1, 1.4])

    with c1:
        st.subheader("Churn vs. Retention")
        pie = px.pie(
            df, names="ChurnLabel", hole=0.55,
            color="ChurnLabel",
            color_discrete_map={"Churned": CHURN_COLOR, "Retained": RETAIN_COLOR},
        )
        pie.update_traces(textinfo="percent+label")
        pie.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=340)
        st.plotly_chart(pie, use_container_width=True)

    with c2:
        st.subheader("Churn Rate by Gender & Card Ownership")
        grp = df.groupby(["Gender", "CrCardLabel"])["Exited"].mean().reset_index()
        grp["Exited"] *= 100
        bar = px.bar(
            grp, x="Gender", y="Exited", color="CrCardLabel", barmode="group",
            labels={"Exited": "Churn Rate (%)"}, text_auto=".1f",
            color_discrete_sequence=[PRIMARY, "#8fb4d9"],
        )
        bar.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=340)
        st.plotly_chart(bar, use_container_width=True)

    st.subheader("Churn Rate by Number of Products")
    prod = df.groupby("NumOfProducts")["Exited"].agg(["mean", "count"]).reset_index()
    prod["mean"] *= 100
    fig = px.bar(
        prod, x="NumOfProducts", y="mean", text_auto=".1f",
        labels={"mean": "Churn Rate (%)", "NumOfProducts": "Number of Products"},
        color="mean", color_continuous_scale="Reds",
    )
    fig.update_layout(height=320, coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Credit Score Band vs. Churn")
    cband = df.groupby("CreditBand", observed=True)["Exited"].mean().reset_index()
    cband["Exited"] *= 100
    fig2 = px.bar(
        cband, x="CreditBand", y="Exited", text_auto=".1f",
        labels={"Exited": "Churn Rate (%)", "CreditBand": "Credit Score Band"},
        color="Exited", color_continuous_scale="Blues",
    )
    fig2.update_layout(height=300, coloraxis_showscale=False)
    st.plotly_chart(fig2, use_container_width=True)

# ============================== TAB 2: GEOGRAPHY ===========================
with tab2:
    st.subheader("Churn Rate by Geography")
    geo = df.groupby("Geography")["Exited"].agg(["mean", "count", "sum"]).reset_index()
    geo.columns = ["Geography", "ChurnRate", "TotalCustomers", "ChurnedCustomers"]
    geo["ChurnRate"] *= 100
    geo["ContributionShare"] = geo["ChurnedCustomers"] / geo["ChurnedCustomers"].sum() * 100

    g1, g2 = st.columns(2)
    with g1:
        fig = px.bar(
            geo.sort_values("ChurnRate", ascending=False), x="Geography", y="ChurnRate",
            text_auto=".1f", labels={"ChurnRate": "Churn Rate (%)"},
            color="ChurnRate", color_continuous_scale="Reds",
        )
        fig.update_layout(height=360, coloraxis_showscale=False, title="Regional Churn Rate")
        st.plotly_chart(fig, use_container_width=True)
    with g2:
        fig = px.bar(
            geo.sort_values("ContributionShare", ascending=False), x="Geography", y="ContributionShare",
            text_auto=".1f", labels={"ContributionShare": "Share of Total Churn (%)"},
            color="ContributionShare", color_continuous_scale="Oranges",
        )
        fig.update_layout(height=360, coloraxis_showscale=False, title="Churn Contribution by Region")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Regional Risk Table** (Geographic Risk Index)")
    geo_display = geo.copy()
    geo_display["ChurnRate"] = geo_display["ChurnRate"].round(1).astype(str) + "%"
    geo_display["ContributionShare"] = geo_display["ContributionShare"].round(1).astype(str) + "%"
    st.dataframe(geo_display, use_container_width=True, hide_index=True)

    st.subheader("Geography × Age Group Interaction")
    heat = df.groupby(["Geography", "AgeGroup"], observed=True)["Exited"].mean().reset_index()
    heat["Exited"] *= 100
    heat_p = heat.pivot(index="Geography", columns="AgeGroup", values="Exited")
    fig = px.imshow(
        heat_p, text_auto=".1f", color_continuous_scale="Reds", aspect="auto",
        labels=dict(color="Churn Rate (%)"),
    )
    fig.update_layout(height=340)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Geography × Gender Interaction")
    heat2 = df.groupby(["Geography", "Gender"])["Exited"].mean().reset_index()
    heat2["Exited"] *= 100
    heat2_p = heat2.pivot(index="Geography", columns="Gender", values="Exited")
    fig2 = px.imshow(
        heat2_p, text_auto=".1f", color_continuous_scale="Purples", aspect="auto",
        labels=dict(color="Churn Rate (%)"),
    )
    fig2.update_layout(height=300)
    st.plotly_chart(fig2, use_container_width=True)

# ============================== TAB 3: AGE & TENURE ========================
with tab3:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Churn Rate by Age Group")
        age = df.groupby("AgeGroup", observed=True)["Exited"].mean().reset_index()
        age["Exited"] *= 100
        fig = px.bar(
            age, x="AgeGroup", y="Exited", text_auto=".1f",
            labels={"Exited": "Churn Rate (%)"}, color="Exited", color_continuous_scale="Reds",
        )
        fig.update_layout(height=340, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Churn Rate by Tenure Group")
        ten = df.groupby("TenureGroup", observed=True)["Exited"].mean().reset_index()
        ten["Exited"] *= 100
        fig = px.bar(
            ten, x="TenureGroup", y="Exited", text_auto=".1f",
            labels={"Exited": "Churn Rate (%)"}, color="Exited", color_continuous_scale="Blues",
        )
        fig.update_layout(height=340, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Age Group × Tenure Group Heatmap")
    heat = df.groupby(["AgeGroup", "TenureGroup"], observed=True)["Exited"].mean().reset_index()
    heat["Exited"] *= 100
    heat_p = heat.pivot(index="AgeGroup", columns="TenureGroup", values="Exited")
    fig = px.imshow(
        heat_p, text_auto=".1f", color_continuous_scale="Reds", aspect="auto",
        labels=dict(color="Churn Rate (%)"),
    )
    fig.update_layout(height=360)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Activity Status vs. Churn (Engagement Drop Indicator)")
    act = df.groupby(["ActiveLabel", "AgeGroup"], observed=True)["Exited"].mean().reset_index()
    act["Exited"] *= 100
    fig = px.bar(
        act, x="AgeGroup", y="Exited", color="ActiveLabel", barmode="group", text_auto=".1f",
        labels={"Exited": "Churn Rate (%)"},
        color_discrete_map={"Active": RETAIN_COLOR, "Inactive": CHURN_COLOR},
    )
    fig.update_layout(height=340)
    st.plotly_chart(fig, use_container_width=True)

    st.info(
        f"Inactive members churn at **{inactive_churn:.1f}%** vs. **{active_churn:.1f}%** for active members "
        f"— a gap of **{engagement_gap:+.1f} percentage points** within the current filter selection."
    )

# ============================== TAB 4: HIGH-VALUE EXPLORER =================
with tab4:
    st.subheader("High-Value Customer Churn Explorer")
    st.caption(f"High-value = balance ≥ €{high_value_cutoff:,.0f} (top 25% bank-wide, computed on unfiltered data)")

    hv1, hv2, hv3 = st.columns(3)
    hv1.metric("High-Value Customers (filtered)", f"{len(high_value_df):,}")
    hv2.metric("High-Value Churn Rate", f"{hv_churn:.1f}%")
    hv3.metric("High-Value Revenue at Risk", f"€{high_value_df.loc[high_value_df['Exited']==1,'Balance'].sum()/1e6:.2f}M")

    st.subheader("Balance vs. Estimated Salary (colored by churn)")
    scatter_df = df.sample(min(3000, len(df)), random_state=42)
    fig = px.scatter(
        scatter_df, x="Balance", y="EstimatedSalary", color="ChurnLabel",
        color_discrete_map={"Churned": CHURN_COLOR, "Retained": RETAIN_COLOR},
        opacity=0.55, labels={"Balance": "Account Balance (€)", "EstimatedSalary": "Estimated Salary (€)"},
    )
    fig.add_vline(x=high_value_cutoff, line_dash="dash", line_color="gray",
                  annotation_text="High-value threshold")
    fig.update_layout(height=420)
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Churn Rate by Balance Segment")
        bseg = df.groupby("BalanceSegment")["Exited"].mean().reset_index()
        bseg["Exited"] *= 100
        fig = px.bar(
            bseg, x="BalanceSegment", y="Exited", text_auto=".1f",
            labels={"Exited": "Churn Rate (%)"}, color="Exited", color_continuous_scale="Reds",
        )
        fig.update_layout(height=340, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.subheader("Churned vs. Retained: Avg. Financial Profile")
        prof = df.groupby("ChurnLabel")[["Balance", "EstimatedSalary", "CreditScore"]].mean().reset_index()
        prof_melt = prof.melt(id_vars="ChurnLabel", var_name="Metric", value_name="Value")
        fig = px.bar(
            prof_melt, x="Metric", y="Value", color="ChurnLabel", barmode="group",
            color_discrete_map={"Churned": CHURN_COLOR, "Retained": RETAIN_COLOR},
        )
        fig.update_layout(height=340)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Drill-Down: Top Churned High-Value Customers")
    top_churners = (
        high_value_df[high_value_df["Exited"] == 1]
        .sort_values("Balance", ascending=False)
        [["CustomerId", "Geography", "Gender", "Age", "Balance", "NumOfProducts", "IsActiveMember", "EstimatedSalary"]]
        .head(25)
        .reset_index(drop=True)
    )
    st.dataframe(top_churners, use_container_width=True)

    csv = top_churners.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download top churned high-value customers (CSV)", csv, "top_churned_high_value.csv", "text/csv")

st.markdown("---")
st.caption("European Bank Customer Churn Analytics · Built with Streamlit & Plotly · Unified Mentor Project")
