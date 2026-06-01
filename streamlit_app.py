import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SLA Breach Monitor",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }
    .stApp {
        background-color: #0d0d0d;
        color: #f0f0f0;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    h1, h2, h3 {
        font-family: 'IBM Plex Mono', monospace !important;
        color: #ff4444 !important;
        letter-spacing: -0.5px;
    }
    .metric-card {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-left: 3px solid #ff4444;
        border-radius: 4px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
    }
    .metric-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 2.4rem;
        font-weight: 600;
        color: #ff4444;
        line-height: 1;
    }
    .metric-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #888;
        margin-top: 0.4rem;
    }
    .section-divider {
        border: none;
        border-top: 1px solid #2a2a2a;
        margin: 1.5rem 0;
    }
    .stDataFrame {
        border: 1px solid #2a2a2a !important;
    }
    .sidebar .sidebar-content {
        background: #111;
    }
    [data-testid="stSidebar"] {
        background-color: #111111;
        border-right: 1px solid #2a2a2a;
    }
    .stSelectbox label, .stSlider label, .stFileUploader label {
        color: #aaa !important;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .badge-critical {
        background: #3d0000;
        color: #ff4444;
        border: 1px solid #ff4444;
        border-radius: 3px;
        padding: 2px 8px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.75rem;
        letter-spacing: 1px;
    }
    .top-bar {
        background: #111;
        border-bottom: 1px solid #2a2a2a;
        padding: 0.5rem 0;
        margin-bottom: 1.5rem;
    }
    .tag-breach {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.7rem;
        background: #1a0000;
        border: 1px solid #660000;
        color: #ff6666;
        padding: 2px 6px;
        border-radius: 2px;
        margin-right: 4px;
    }
</style>
""", unsafe_allow_html=True)


# ── Helper: generate sample data ─────────────────────────────────────────────
def generate_sample_data() -> pd.DataFrame:
    np.random.seed(42)
    vendors = ["Accenture", "Infosys", "TCS", "Wipro", "Cognizant", "HCL", "Capgemini"]
    priorities = ["Critical", "High", "Medium", "Low"]
    priority_weights = [0.25, 0.35, 0.25, 0.15]

    rows = []
    base = datetime(2024, 1, 1)
    for i in range(300):
        vendor = np.random.choice(vendors)
        priority = np.random.choice(priorities, p=priority_weights)
        created = base + pd.Timedelta(hours=np.random.randint(0, 2000))
        
        # MODIFIED: Generates severe backlogs across all categories spanning up to 200 hours (over a week)
        if priority == "Critical":
            hours = np.random.choice(
                [np.random.uniform(0.5, 4), np.random.uniform(4.1, 200)],
                p=[0.45, 0.55],
            )
        else:
            hours = np.random.uniform(1, 200)
            
        resolved = created + pd.Timedelta(hours=hours)
        rows.append({
            "Vendor_Name": vendor,
            "Ticket_ID": f"TKT-{10000 + i}",
            "Priority": priority,
            "Created_Time": created.strftime("%Y-%m-%d %H:%M:%S"),
            "Resolved_Time": resolved.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return pd.DataFrame(rows)


# ── Core processing ───────────────────────────────────────────────────────────
def process_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Created_Time"] = pd.to_datetime(df["Created_Time"])
    df["Resolved_Time"] = pd.to_datetime(df["Resolved_Time"])
    df["Resolution_Hours"] = (
        (df["Resolved_Time"] - df["Created_Time"]).dt.total_seconds() / 3600
    ).round(2)
    return df


def get_sla_breaches(df: pd.DataFrame, sla_threshold: float = 4.0) -> pd.DataFrame:
    # MODIFIED: Removed strict Critical filter so ALL categories exceeding the threshold appear
    return df[df["Resolution_Hours"] > sla_threshold].copy()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙ CONFIG")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Upload vendor_logs.csv", type=["csv"])

    # MODIFIED: Scaled slider to 200 hours to handle long, multi-day, or week-long backlogs easily
    sla_limit = st.slider(
        "SLA Threshold (hours)", min_value=1.0, max_value=200.0, value=4.0, step=1.0
    )

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown("##### Vendor Filter")

    # Loaded after data is available (populated below)
    vendor_filter_placeholder = st.empty()

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown(
        '<span style="font-size:0.7rem;color:#555;font-family:\'IBM Plex Mono\',monospace;">'
        "SLA BREACH MONITOR v1.0<br>All Priority Categories · Resolution > Threshold</span>",
        unsafe_allow_html=True,
    )


# ── Load data ─────────────────────────────────────────────────────────────────
if uploaded_file:
    raw_df = pd.read_csv(uploaded_file)
    using_sample = False
else:
    raw_df = generate_sample_data()
    using_sample = True

df = process_data(raw_df)

# Vendor multi-select (now that df is ready)
all_vendors = sorted(df["Vendor_Name"].unique().tolist())
selected_vendors = vendor_filter_placeholder.multiselect(
    "Select vendors", all_vendors, default=all_vendors
)
df = df[df["Vendor_Name"].isin(selected_vendors)]

breach_df = get_sla_breaches(df, sla_threshold=sla_limit)
breach_by_vendor = (
    breach_df.groupby("Vendor_Name")
    .size()
    .reset_index(name="SLA_Breaches")
    .sort_values("SLA_Breaches", ascending=False)
)


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    '<h1 style="margin-bottom:0;">🚨 SLA BREACH MONITOR</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<p style="color:#666;font-size:0.85rem;font-family:\'IBM Plex Mono\',monospace;margin-top:4px;">'
    f'Cross-Category Performance · Resolution > {sla_limit}h threshold'
    f'{"&nbsp;&nbsp;|&nbsp;&nbsp;<span style=\'color:#ff9900\'>⚠ Using generated sample data</span>" if using_sample else ""}'
    f"</p>",
    unsafe_allow_html=True,
)
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)


# ── KPI Cards ─────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        f'<div class="metric-card"><div class="metric-value">{len(breach_df)}</div>'
        '<div class="metric-label">Total SLA Breaches</div></div>',
        unsafe_allow_html=True,
    )
with col2:
    worst = breach_by_vendor.iloc[0]["Vendor_Name"] if not breach_by_vendor.empty else "—"
    st.markdown(
        f'<div class="metric-card"><div class="metric-value" style="font-size:1.4rem;padding-top:6px;">{worst}</div>'
        '<div class="metric-label">Worst Offender</div></div>',
        unsafe_allow_html=True,
    )
with col3:
    avg_hours = breach_df["Resolution_Hours"].mean() if not breach_df.empty else 0
    st.markdown(
        f'<div class="metric-card"><div class="metric-value">{avg_hours:.1f}h</div>'
        '<div class="metric-label">Avg Breach Duration</div></div>',
        unsafe_allow_html=True,
    )
with col4:
    # MODIFIED: Dynamically maps the overall systemic breach rate across all ticket sets
    total_tickets = len(df)
    breach_rate = (len(breach_df) / total_tickets * 100) if total_tickets else 0
    st.markdown(
        f'<div class="metric-card"><div class="metric-value">{breach_rate:.0f}%</div>'
        '<div class="metric-label">Overall Breach Rate</div></div>',
        unsafe_allow_html=True,
    )


# ── Main Chart ────────────────────────────────────────────────────────────────
st.markdown("### SLA Breaches by Vendor")

if breach_by_vendor.empty:
    st.info("✅ No SLA breaches found for the selected vendors and threshold.")
else:
    # Color: brightest red for worst, fading to dark red
    n = len(breach_by_vendor)
    colors = [
        f"rgba(255, {int(40 + (i / max(n - 1, 1)) * 80)}, {int(40 + (i / max(n - 1, 1)) * 40)}, {1 - (i / max(n - 1, 1)) * 0.45})"
        for i in range(n)
    ]

    fig = go.Figure(
        go.Bar(
            x=breach_by_vendor["Vendor_Name"],
            y=breach_by_vendor["SLA_Breaches"],
            marker=dict(color=colors, line=dict(color="#ff4444", width=0.5)),
            text=breach_by_vendor["SLA_Breaches"],
            textposition="outside",
            textfont=dict(family="IBM Plex Mono", size=13, color="#ff4444"),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "SLA Breaches: <b>%{y}</b><br>"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        plot_bgcolor="#0d0d0d",
        paper_bgcolor="#0d0d0d",
        font=dict(family="IBM Plex Sans", color="#aaa"),
        xaxis=dict(
            title="Vendor",
            title_font=dict(size=11, color="#555", family="IBM Plex Mono"),
            tickfont=dict(size=12, color="#ccc"),
            gridcolor="#1a1a1a",
            linecolor="#2a2a2a",
        ),
        yaxis=dict(
            title="# SLA Breaches (All Categories)",
            title_font=dict(size=11, color="#555", family="IBM Plex Mono"),
            tickfont=dict(size=11, color="#888"),
            gridcolor="#1a1a1a",
            linecolor="#2a2a2a",
            zeroline=False,
        ),
        margin=dict(t=30, b=60, l=60, r=30),
        height=420,
        bargap=0.35,
        hoverlabel=dict(
            bgcolor="#1a1a1a",
            bordercolor="#ff4444",
            font=dict(family="IBM Plex Mono", color="#f0f0f0"),
        ),
        shapes=[
            dict(
                type="line",
                xref="paper", x0=0, x1=1,
                yref="y", y0=0, y1=0,
                line=dict(color="#2a2a2a", width=1),
            )
        ],
    )

    st.plotly_chart(fig, use_container_width=True)


# ── Secondary: Avg resolution time per vendor (breaches only) ────────────────
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
st.markdown("### Avg Resolution Time on Breached Tickets (hours)")

if not breach_df.empty:
    avg_res = (
        breach_df.groupby("Vendor_Name")["Resolution_Hours"]
        .mean()
        .reset_index()
        .rename(columns={"Resolution_Hours": "Avg_Hours"})
        .sort_values("Avg_Hours", ascending=False)
    )
    avg_res["Avg_Hours"] = avg_res["Avg_Hours"].round(1)

    fig2 = px.bar(
        avg_res,
        x="Vendor_Name",
        y="Avg_Hours",
        text="Avg_Hours",
        color="Avg_Hours",
        color_continuous_scale=[[0, "#3d0000"], [0.5, "#aa2200"], [1, "#ff4444"]],
    )
    fig2.update_traces(
        texttemplate="%{text}h",
        textposition="outside",
        textfont=dict(family="IBM Plex Mono", size=12, color="#ff8888"),
        marker_line_width=0,
    )
    fig2.update_layout(
        plot_bgcolor="#0d0d0d",
        paper_bgcolor="#0d0d0d",
        font=dict(family="IBM Plex Sans", color="#aaa"),
        coloraxis_showscale=False,
        xaxis=dict(
            title="Vendor",
            title_font=dict(size=11, color="#555", family="IBM Plex Mono"),
            tickfont=dict(size=12, color="#ccc"),
            gridcolor="#1a1a1a",
            linecolor="#2a2a2a",
        ),
        yaxis=dict(
            title="Avg Hours",
            title_font=dict(size=11, color="#555", family="IBM Plex Mono"),
            tickfont=dict(size=11, color="#888"),
            gridcolor="#1a1a1a",
            linecolor="#2a2a2a",
            zeroline=False,
        ),
        margin=dict(t=30, b=60, l=60, r=30),
        height=360,
        bargap=0.35,
        hoverlabel=dict(
            bgcolor="#1a1a1a",
            bordercolor="#ff4444",
            font=dict(family="IBM Plex Mono", color="#f0f0f0"),
        ),
    )
    st.plotly_chart(fig2, use_container_width=True)


# ── Raw breach table ──────────────────────────────────────────────────────────
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

with st.expander("📋  View Raw Breach Records", expanded=False):
    display_cols = ["Vendor_Name", "Ticket_ID", "Priority", "Created_Time", "Resolved_Time", "Resolution_Hours"]
    st.dataframe(
        breach_df[display_cols].sort_values("Resolution_Hours", ascending=False).reset_index(drop=True),
        use_container_width=True,
        height=350,
    )

    csv_out = breach_df[display_cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇  Export Breach Data as CSV",
        data=csv_out,
        file_name="sla_breaches_export.csv",
        mime="text/csv",
    )
