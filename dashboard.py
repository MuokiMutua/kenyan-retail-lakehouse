import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pymongo
import psycopg2
from psycopg2.extras import RealDictCursor
from streamlit_autorefresh import st_autorefresh

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Retail Command Center",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family:'Plus Jakarta Sans',sans-serif; background:#04070f; }
.stApp { background:#04070f; }
section[data-testid="stSidebar"] { background:#070c18 !important; border-right:1px solid #0f1e35 !important; }
#MainMenu, footer, header { visibility:hidden; }
.block-container { padding:1rem 1.75rem 2rem !important; max-width:100% !important; }

.kpi { background:#080f1f; border:1px solid #0f1e35; border-radius:14px;
       padding:1.2rem 1.4rem; position:relative; overflow:hidden;
       transition:border-color .25s,transform .2s; }
.kpi:hover { border-color:#1e3a5f; transform:translateY(-3px); }
.kpi-accent { position:absolute; top:0; left:0; right:0; height:3px; background:var(--ac); }
.kpi-label { color:#475569; font-size:.68rem; font-weight:700; letter-spacing:.1em;
             text-transform:uppercase; margin-bottom:.5rem; }
.kpi-value { color:#f1f5f9; font-size:1.6rem; font-weight:800;
             font-family:'JetBrains Mono',monospace; letter-spacing:-.03em; }
.kpi-sub   { color:#1e3a5f; font-size:.7rem; margin-top:.35rem; }
.live-ring { display:inline-block; width:7px; height:7px; border-radius:50%;
             background:var(--ac); margin-right:5px;
             animation:ring 1.6s ease-in-out infinite; vertical-align:middle; }
@keyframes ring {
  0%,100%{box-shadow:0 0 0 0 rgba(255,255,255,.25)}
  50%{box-shadow:0 0 0 5px rgba(255,255,255,0)}
}

.sec-label { font-size:.68rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase;
             color:#334155; border-left:2px solid #1d4ed8; padding-left:.55rem; margin-bottom:.9rem; }

.pill { display:inline-flex; align-items:center; gap:.35rem; font-size:.7rem; font-weight:700;
        letter-spacing:.06em; padding:.25rem .7rem; border-radius:9999px; border:1px solid; }
.pill-ok  { background:#03100a; border-color:#134e2a; color:#4ade80; }
.pill-err { background:#100303; border-color:#7f1d1d; color:#f87171; }
.pill-dot { width:5px; height:5px; border-radius:50%; background:currentColor; }

.stButton>button { background:#0d1f3a; border:1px solid #1d4ed8; color:#60a5fa;
                   font-weight:700; font-size:.8rem; border-radius:9px; padding:.45rem 1.2rem;
                   transition:all .2s; }
.stButton>button:hover { background:#1d4ed8; color:#fff; border-color:#3b82f6; }

.atbl { width:100%; border-collapse:collapse; font-size:.8rem; }
.atbl th { color:#334155; font-weight:700; font-size:.65rem; text-transform:uppercase;
           letter-spacing:.08em; padding:.55rem .9rem; border-bottom:1px solid #0f1e35; white-space:nowrap; }
.atbl td { padding:.6rem .9rem; border-bottom:1px solid #080f1f; color:#64748b; white-space:nowrap; }
.atbl tr:hover td { background:#0a1428; }
.mono    { font-family:'JetBrains Mono',monospace; font-size:.76rem; color:#94a3b8; }
.emerald { font-family:'JetBrains Mono',monospace; color:#34d399; text-align:right; }
.pay-badge { display:inline-block; font-size:.6rem; font-weight:700;
             padding:.15rem .45rem; border-radius:5px; border:1px solid; }

.ac { background:#060e1c; border:1px solid #0f1e35; border-radius:10px;
      padding:.7rem 1rem; margin-bottom:.4rem; }
.ac-w { border-left:3px solid #f59e0b !important; }
.ac-s { border-left:3px solid #10b981 !important; }
.ac-i { border-left:3px solid #3b82f6 !important; }
.ac-time { font-family:'JetBrains Mono',monospace; font-size:.66rem; color:#334155; }
.ac-text { font-size:.8rem; color:#64748b; margin-top:.18rem; line-height:1.5; }

.sidebar-hd { color:#1e3a5f; font-size:.65rem; font-weight:800; text-transform:uppercase;
              letter-spacing:.12em; margin:1.2rem 0 .35rem; }

::-webkit-scrollbar { width:4px; height:4px; }
::-webkit-scrollbar-track { background:#04070f; }
::-webkit-scrollbar-thumb { background:#0f1e35; border-radius:9999px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PLOTLY HELPERS
# ─────────────────────────────────────────────
_PLOT_BASE = dict(
    plot_bgcolor  = "rgba(0,0,0,0)",
    paper_bgcolor = "rgba(0,0,0,0)",
    font          = dict(family="Plus Jakarta Sans, sans-serif", color="#475569", size=11),
    hoverlabel    = dict(bgcolor="#0d1525", bordercolor="#1e293b",
                         font=dict(family="JetBrains Mono", size=11)),
)
_GRID = dict(gridcolor="#0a1428", zeroline=False, linecolor="#0f1e35", tickfont=dict(size=10))

def _fig(**layout_kwargs) -> go.Figure:
    """Return a pre-styled empty Figure. Pass ALL per-chart layout keys here."""
    fig = go.Figure()
    fig.update_layout(**_PLOT_BASE, **layout_kwargs)
    return fig

PAY_COLORS = {
    "M-Pesa":    "#10b981",
    "Cash":       "#3b82f6",
    "Visa Card":  "#8b5cf6",
    "Mastercard": "#f59e0b",
    "Pesalink":   "#64748b",
}

# ─────────────────────────────────────────────
# DB HELPERS
# ─────────────────────────────────────────────
@st.cache_resource
def _mongo():
    client = pymongo.MongoClient(
        "mongodb://mongo_retail_admin:QuickmartPassword2026@localhost:27017/?authSource=admin",
        serverSelectionTimeoutMS=3000,
    )
    client.server_info()
    return client["supermarket_audit_logs"]["raw_receipts"]

@st.cache_resource
def _pg():
    return psycopg2.connect(
        host="localhost", port="5433",
        database="supermarket_metadata",
        user="kenyan_retail_admin",
        password="NaivasPassword2026",
        cursor_factory=RealDictCursor,
    )

def pgq(sql: str, params=None) -> list:
    conn = _pg()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
    except psycopg2.OperationalError:
        st.cache_resource.clear()
        raise
    except Exception:
        conn.rollback()
        raise

# ─────────────────────────────────────────────
# CONNECTION CHECK  
# ─────────────────────────────────────────────
mongo_col = None
mongo_ok  = False
pg_ok     = False

try:
    mongo_col = _mongo()
    mongo_ok  = True
except Exception as exc:
    st.error(f"MongoDB: {exc}")

try:
    pgq("SELECT 1")
    pg_ok = True
except Exception as exc:
    st.error(f"PostgreSQL: {exc}")

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div style="padding:.6rem 0 .4rem">
            <div style="font-size:1.1rem;font-weight:800;color:#f1f5f9;letter-spacing:-.02em">
                ⬡ Command Center
            </div>
            <div style="font-size:.68rem;color:#1e3a5f;margin-top:.2rem;
                        text-transform:uppercase;letter-spacing:.08em">
                Retail Lakehouse · Executive View
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # Live toggle - NOW DEFAULTS TO TRUE
    st.markdown('<p class="sidebar-hd">Live Feed</p>', unsafe_allow_html=True)
    live_on = st.toggle("🟢 Auto-Refresh (5 s)", value=True)

    # Date range
    st.markdown('<p class="sidebar-hd">Date Range</p>', unsafe_allow_html=True)
    date_mode = st.radio("", ["Today", "Last 7 Days", "Last 30 Days", "Custom"],
                         horizontal=False, label_visibility="collapsed")
    today = datetime.date.today()
    if date_mode == "Today":
        d_start, d_end = today, today
    elif date_mode == "Last 7 Days":
        d_start, d_end = today - datetime.timedelta(days=7), today
    elif date_mode == "Last 30 Days":
        d_start, d_end = today - datetime.timedelta(days=30), today
    else:
        d_start = st.date_input("From", value=today - datetime.timedelta(days=7))
        d_end   = st.date_input("To",   value=today)

    ts_start    = datetime.datetime.combine(d_start, datetime.time.min).isoformat() + "Z"
    ts_end      = datetime.datetime.combine(d_end,   datetime.time.max).isoformat() + "Z"
    date_filter = {"timestamp": {"$gte": ts_start, "$lte": ts_end}}

    # Payment filter
    st.markdown('<p class="sidebar-hd">Payment Channel</p>', unsafe_allow_html=True)
    selected_pay = st.selectbox("", ["All","M-Pesa","Cash","Visa Card","Mastercard","Pesalink"],
                                label_visibility="collapsed")

    # Sector filter
    st.markdown('<p class="sidebar-hd">Sector</p>', unsafe_allow_html=True)
    all_sectors = []
    if pg_ok:
        try:
            all_sectors = [r["sector_name"] for r in
                           pgq("SELECT DISTINCT sector_name FROM products ORDER BY sector_name")]
        except Exception:
            pass
    selected_sector = st.selectbox(" ", ["All Sectors"] + all_sectors,
                                   label_visibility="collapsed")

    st.markdown("---")
    st.markdown('<p class="sidebar-hd">Connections</p>', unsafe_allow_html=True)
    for lbl, ok in [("MongoDB", mongo_ok), ("PostgreSQL", pg_ok)]:
        cls = "pill-ok" if ok else "pill-err"
        st.markdown(f'<div class="pill {cls}" style="margin-bottom:.35rem">'
                    f'<span class="pill-dot"></span>{lbl} {"Live" if ok else "Offline"}</div>',
                    unsafe_allow_html=True)

# ─────────────────────────────────────────────
# BUILD QUERY
# ─────────────────────────────────────────────
query = dict(date_filter)
if selected_pay != "All":
    query["payment_method"] = selected_pay

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
hc1, hc2, hc3 = st.columns([4, 2, 1])
with hc1:
    st.markdown(f"""
        <div style="margin-bottom:.6rem">
            <div style="font-size:1.45rem;font-weight:800;color:#f1f5f9;
                        letter-spacing:-.03em;line-height:1.15">
                Retail Lakehouse
                <span style="color:#2563eb"> Command Center</span>
            </div>
            <div style="color:#1e3a5f;font-size:.72rem;margin-top:.3rem;
                        text-transform:uppercase;letter-spacing:.08em">
                {d_start.strftime('%d %b %Y')} → {d_end.strftime('%d %b %Y')}
                &nbsp;·&nbsp; {selected_pay} &nbsp;·&nbsp; {selected_sector}
            </div>
        </div>
    """, unsafe_allow_html=True)
with hc2:
    cls = "pill-ok" if (mongo_ok and pg_ok) else "pill-err"
    lbl = "All Systems Live" if (mongo_ok and pg_ok) else "Degraded"
    st.markdown(f'<div style="text-align:right;padding-top:.9rem">'
                f'<span class="pill {cls}"><span class="pill-dot"></span>{lbl}</span></div>',
                unsafe_allow_html=True)
with hc3:
    refresh_now = st.button("⟳ Refresh", use_container_width=True)

st.markdown("<div style='height:.1rem'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DATA FETCH
# ─────────────────────────────────────────────
total_txns    = 0
total_revenue = 0.0
mpesa_pct     = 0.0
avg_basket    = 0.0
pay_df        = pd.DataFrame()
sector_df     = pd.DataFrame()
top5_df       = pd.DataFrame()
hourly_df     = pd.DataFrame()
recent_txns   = []
pay_agg       = []

if mongo_col is not None:
    total_txns    = mongo_col.count_documents(query)
    rev_agg       = list(mongo_col.aggregate([
        {"$match": query},
        {"$group": {"_id": None, "t": {"$sum": "$total_amount"}}},
    ]))
    total_revenue = rev_agg[0]["t"] if rev_agg else 0.0
    avg_basket    = total_revenue / total_txns if total_txns else 0.0

    pay_agg = list(mongo_col.aggregate([
        {"$match": query},
        {"$group": {"_id": "$payment_method",
                    "count":   {"$sum": 1},
                    "revenue": {"$sum": "$total_amount"}}},
        {"$sort": {"count": -1}},
    ]))
    if pay_agg:
        pay_df    = pd.DataFrame(pay_agg).rename(columns={"_id": "Method"})
        mpesa_row = pay_df[pay_df["Method"] == "M-Pesa"]
        mpesa_pct = round(mpesa_row["count"].iloc[0] / total_txns * 100, 1) \
                    if not mpesa_row.empty else 0.0

    sect_match = dict(query)
    if selected_sector != "All Sectors":
        sect_match["items.sector"] = selected_sector
    sector_agg = list(mongo_col.aggregate([
        {"$match": sect_match},
        {"$unwind": "$items"},
        {"$group": {"_id": "$items.sector",
                    "revenue": {"$sum": "$items.subtotal"},
                    "units":   {"$sum": "$items.quantity"}}},
        {"$sort": {"revenue": -1}},
    ]))
    if sector_agg:
        sector_df = pd.DataFrame(sector_agg).rename(columns={"_id": "Sector"})

    top5_agg = list(mongo_col.aggregate([
        {"$match": query},
        {"$unwind": "$items"},
        {"$group": {"_id": "$items.name",
                    "revenue": {"$sum": "$items.subtotal"},
                    "units":   {"$sum": "$items.quantity"}}},
        {"$sort": {"revenue": -1}},
        {"$limit": 5},
    ]))
    if top5_agg:
        top5_df = pd.DataFrame(top5_agg).rename(columns={"_id": "Product"})

    hourly_agg = list(mongo_col.aggregate([
        {"$match": query},
        {"$addFields": {"hour": {"$substr": ["$timestamp", 11, 2]}}},
        {"$group": {"_id": "$hour",
                    "revenue": {"$sum": "$total_amount"},
                    "txns":    {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]))
    if hourly_agg:
        hourly_df         = pd.DataFrame(hourly_agg).rename(columns={"_id": "Hour"})
        hourly_df["Hour"] = hourly_df["Hour"].astype(str) + ":00"

    recent_txns = list(
        mongo_col.find(query, {"_id": 0}).sort("timestamp", -1).limit(20)
    )

# ─────────────────────────────────────────────
# KPI ROW
# ─────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
kpi_defs = [
    (k1, "Total Revenue",   f"KES {total_revenue:,.0f}", f"{total_txns:,} transactions", "#10b981"),
    (k2, "Transactions",    f"{total_txns:,}",            f"{d_start} → {d_end}",        "#3b82f6"),
    (k3, "M-Pesa Share",    f"{mpesa_pct}%",              "of all payments",             "#8b5cf6"),
    (k4, "Avg Basket",      f"KES {avg_basket:,.0f}",     "per transaction",             "#f59e0b"),
    (k5, "Active Sectors",  f"{len(sector_df)}",          "contributing revenue",        "#06b6d4"),
]
for col, label, value, sub, accent in kpi_defs:
    with col:
        ring = (f'<span class="live-ring" style="--ac:{accent}"></span>'
                if live_on and mongo_ok else "")
        st.markdown(f"""
            <div class="kpi" style="--ac:{accent}">
                <div class="kpi-accent"></div>
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{ring}{value}</div>
                <div class="kpi-sub">{sub}</div>
            </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ROW 1: Sector bar | Hourly trend | Payment donut
# ─────────────────────────────────────────────
r1a, r1b, r1c = st.columns([2.2, 2.2, 1.6], gap="medium")

with r1a:
    st.markdown('<div class="sec-label">Revenue by Sector</div>', unsafe_allow_html=True)
    if not sector_df.empty:
        sd     = sector_df.head(12).sort_values("revenue")
        n      = len(sd)
        colors = [f"rgba(37,99,235,{0.35 + 0.65*(i/max(n-1,1))})" for i in range(n)]
        fig = _fig(
            height=280,
            margin=dict(l=0, r=10, t=10, b=0),
            xaxis={**_GRID, "tickprefix": "KES ", "tickformat": ".2s"},
            yaxis={**_GRID, "tickfont": dict(size=9.5)}
        )
        fig.add_trace(go.Bar(
            x=sd["revenue"], y=sd["Sector"], orientation="h",
            marker=dict(color=colors, line_width=0),
            hovertemplate="<b>%{y}</b><br>KES %{x:,.0f}<extra></extra>",
        ))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.markdown('<div style="height:280px;display:flex;align-items:center;'
                    'justify-content:center;color:#1e3a5f;font-size:.82rem">'
                    'No sector data for this filter</div>', unsafe_allow_html=True)

with r1b:
    st.markdown('<div class="sec-label">Hourly Revenue Trend</div>', unsafe_allow_html=True)
    if not hourly_df.empty:
        fig2 = _fig(
            height=280,
            margin=dict(l=0, r=10, t=10, b=0),
            xaxis={**_GRID, "tickangle": -45, "tickfont": dict(size=9)},
            yaxis={**_GRID, "tickprefix": "KES ", "tickformat": ".2s"}
        )
        fig2.add_trace(go.Scatter(
            x=hourly_df["Hour"], y=hourly_df["revenue"],
            mode="lines+markers",
            line=dict(color="#2563eb", width=2.5),
            marker=dict(color="#60a5fa", size=5),
            fill="tozeroy",
            fillcolor="rgba(37,99,235,0.08)",
            hovertemplate="<b>%{x}</b><br>KES %{y:,.0f}<extra></extra>",
        ))
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
    else:
        st.markdown('<div style="height:280px;display:flex;align-items:center;'
                    'justify-content:center;color:#1e3a5f;font-size:.82rem">'
                    'No hourly data</div>', unsafe_allow_html=True)

with r1c:
    st.markdown('<div class="sec-label">Payment Mix</div>', unsafe_allow_html=True)
    if not pay_df.empty:
        methods = pay_df["Method"].tolist()
        counts  = pay_df["count"].tolist()
        clrs    = [PAY_COLORS.get(m, "#64748b") for m in methods]
        fig3 = _fig(
            height=280,
            margin=dict(l=0, r=0, t=10, b=10),
            legend=dict(orientation="v", x=0, y=0,
                        bgcolor="rgba(0,0,0,0)", font=dict(size=9.5)),
            annotations=[dict(
                text=f"<b>{total_txns:,}</b><br>"
                     f"<span style='font-size:9px'>txns</span>",
                x=.5, y=.5, showarrow=False,
                font=dict(size=13, color="#f1f5f9"),
            )],
        )
        fig3.add_trace(go.Pie(
            labels=methods, values=counts,
            hole=.60,
            marker=dict(colors=clrs, line=dict(color="#04070f", width=3)),
            textinfo="none",
            hovertemplate="<b>%{label}</b><br>%{value:,} txns (%{percent})<extra></extra>",
        ))
        st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
    else:
        st.markdown('<div style="height:280px;display:flex;align-items:center;'
                    'justify-content:center;color:#1e3a5f;font-size:.82rem">'
                    'Awaiting data…</div>', unsafe_allow_html=True)

st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ROW 2: Top 5 | Sector vs Target | Revenue by payment
# ─────────────────────────────────────────────
r2a, r2b, r2c = st.columns([1.6, 2.4, 2], gap="medium")

with r2a:
    st.markdown('<div class="sec-label">Top 5 Products</div>', unsafe_allow_html=True)
    if not top5_df.empty:
        fig4 = _fig(
            height=240,
            margin=dict(l=0, r=40, t=10, b=0),
            xaxis={**_GRID, "tickprefix": "KES ", "tickformat": ".2s"},
            yaxis={**_GRID, "tickfont": dict(size=9), "autorange": "reversed"}
        )
        fig4.add_trace(go.Bar(
            x=top5_df["revenue"],
            y=top5_df["Product"].str[:26],
            orientation="h",
            marker=dict(
                color=["#10b981","#34d399","#6ee7b7","#a7f3d0","#d1fae5"],
                line_width=0,
            ),
            text=[f"KES {v:,.0f}" for v in top5_df["revenue"]],
            textposition="outside",
            textfont=dict(size=9, color="#64748b"),
            hovertemplate="<b>%{y}</b><br>KES %{x:,.0f}<extra></extra>",
        ))
        st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})
    else:
        st.markdown('<div style="height:240px;display:flex;align-items:center;'
                    'justify-content:center;color:#1e3a5f;font-size:.82rem">'
                    'No product data</div>', unsafe_allow_html=True)

with r2b:
    st.markdown('<div class="sec-label">Sector Actual vs Daily Target</div>', unsafe_allow_html=True)
    if pg_ok and not sector_df.empty:
        try:
            tgt_rows = pgq('SELECT sector_name AS "Sector", daily_target_kes AS "Target" '
                           'FROM sector_targets')
            tgt_df   = pd.DataFrame(tgt_rows)
            merged   = sector_df.merge(tgt_df, on="Sector", how="left")
            merged["Target"] = pd.to_numeric(merged["Target"], errors="coerce").fillna(0)
            merged   = merged.sort_values("revenue", ascending=False).head(10)

            fig5 = _fig(
                height=240,
                margin=dict(l=0, r=10, t=10, b=50),
                barmode="group",
                xaxis={**_GRID, "tickangle": -30, "tickfont": dict(size=9)},
                yaxis={**_GRID, "tickprefix": "KES ", "tickformat": ".2s"},
                legend=dict(orientation="h", yanchor="bottom", y=1.02,
                            xanchor="right", x=1,
                            bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
            )
            fig5.add_trace(go.Bar(
                name="Actual", x=merged["Sector"], y=merged["revenue"],
                marker=dict(color="#2563eb", line_width=0),
                hovertemplate="<b>%{x}</b><br>Actual: KES %{y:,.0f}<extra></extra>",
            ))
            fig5.add_trace(go.Bar(
                name="Target", x=merged["Sector"], y=merged["Target"],
                marker=dict(color="rgba(37,99,235,0.18)",
                            line=dict(color="#3b82f6", width=1)),
                hovertemplate="<b>%{x}</b><br>Target: KES %{y:,.0f}<extra></extra>",
            ))
            st.plotly_chart(fig5, use_container_width=True, config={"displayModeBar": False})
        except Exception as exc:
            st.warning(f"Target data unavailable: {exc}")
    else:
        st.markdown('<div style="height:240px;display:flex;align-items:center;'
                    'justify-content:center;color:#1e3a5f;font-size:.82rem">'
                    'No target data</div>', unsafe_allow_html=True)

with r2c:
    st.markdown('<div class="sec-label">Revenue by Payment Method</div>', unsafe_allow_html=True)
    if not pay_df.empty:
        prs  = pay_df.sort_values("revenue", ascending=True)
        fig6 = _fig(
            height=240,
            margin=dict(l=0, r=10, t=10, b=0),
            xaxis={**_GRID, "tickprefix": "KES ", "tickformat": ".2s"},
            yaxis={**_GRID, "tickfont": dict(size=10)}
        )
        fig6.add_trace(go.Bar(
            x=prs["revenue"], y=prs["Method"],
            orientation="h",
            marker=dict(
                color=[PAY_COLORS.get(m, "#64748b") for m in prs["Method"]],
                opacity=0.85, line_width=0,
            ),
            hovertemplate="<b>%{y}</b><br>KES %{x:,.0f}<extra></extra>",
        ))
        st.plotly_chart(fig6, use_container_width=True, config={"displayModeBar": False})
    else:
        st.markdown('<div style="height:240px;display:flex;align-items:center;'
                    'justify-content:center;color:#1e3a5f;font-size:.82rem">'
                    'No data</div>', unsafe_allow_html=True)

st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ROW 3: Audit log | Alert feed
# ─────────────────────────────────────────────
r3a, r3b = st.columns([3, 2], gap="medium")

PAY_BADGE_COLORS = {
    "M-Pesa":    ("rgba(16,185,129,.12)",  "#10b981"),
    "Cash":       ("rgba(59,130,246,.12)",  "#3b82f6"),
    "Visa Card":  ("rgba(139,92,246,.12)",  "#8b5cf6"),
    "Mastercard": ("rgba(245,158,11,.12)",  "#f59e0b"),
    "Pesalink":   ("rgba(100,116,139,.12)", "#64748b"),
}

with r3a:
    st.markdown('<div class="sec-label">&gt;_ MongoDB Audit Log</div>', unsafe_allow_html=True)
    if recent_txns:
        rows_html = ""
        for txn in recent_txns:
            amt    = txn.get("total_amount", 0)
            ts     = txn.get("timestamp", "")[:19].replace("T", " ")
            tid    = txn.get("transaction_id", "—")
            pay    = txn.get("payment_method", "—")
            till   = txn.get("till_number", "—")
            items  = txn.get("items", [])
            n      = len(items)
            bg, fg = PAY_BADGE_COLORS.get(pay, ("rgba(100,116,139,.12)", "#64748b"))
            rows_html += (
                f"<tr>"
                f'<td class="mono">{tid}</td>'
                f"<td>{ts}</td>"
                f"<td>{till}</td>"
                f'<td>{n} item{"s" if n!=1 else ""}</td>'
                f'<td><span class="pay-badge" style="background:{bg};'
                f'border-color:{fg};color:{fg}">{pay}</span></td>'
                f'<td class="emerald">KES {amt:,.2f}</td>'
                f"</tr>"
            )
        st.markdown(
            f'<div style="max-height:280px;overflow-y:auto">'
            f'<table class="atbl"><thead><tr>'
            f"<th>Txn ID</th><th>Timestamp</th><th>Till</th>"
            f'<th>Items</th><th>Payment</th><th style="text-align:right">Amount</th>'
            f"</tr></thead><tbody>{rows_html}</tbody></table></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="text-align:center;color:#1e3a5f;padding:3rem;font-size:.85rem">'
            'No transactions match the current filter.</div>',
            unsafe_allow_html=True,
        )

with r3b:
    st.markdown('<div class="sec-label">⬡ Agentic Decision Log</div>', unsafe_allow_html=True)
    TYPE_MAP = {
        "w": ("ac-w", "WARN", "#f59e0b"),
        "s": ("ac-s", "OK",   "#10b981"),
        "i": ("ac-i", "INFO", "#3b82f6"),
    }
    alerts: list[tuple] = []
    now_ts = datetime.datetime.now().strftime("%H:%M:%S")

    if not pay_df.empty and total_txns > 0:
        top_pay = pay_df.iloc[0]
        pct     = round(top_pay["count"] / total_txns * 100, 1)
        alerts.append(("i", now_ts,
            f"Dominant channel: <strong>{top_pay['Method']}</strong> "
            f"({pct}% · {top_pay['count']:,} txns · KES {top_pay['revenue']:,.0f})"))

    if not top5_df.empty:
        p = top5_df.iloc[0]
        alerts.append(("s", now_ts,
            f"Top product: <strong>{p['Product']}</strong> "
            f"→ KES {p['revenue']:,.0f} · {int(p['units']):,} units"))

    if pg_ok and not sector_df.empty:
        try:
            tgt_map = {r["sector_name"]: float(r["daily_target_kes"])
                       for r in pgq("SELECT sector_name, daily_target_kes FROM sector_targets")}
            for _, row in sector_df.iterrows():
                tgt = tgt_map.get(row["Sector"], 0)
                if tgt > 0 and row["revenue"] >= tgt:
                    alerts.append(("s", now_ts,
                        f"<strong>{row['Sector']}</strong> hit daily target! "
                        f"KES {row['revenue']:,.0f} / {tgt:,.0f}"))
                elif tgt > 0 and row["revenue"] < tgt * 0.5:
                    alerts.append(("w", now_ts,
                        f"<strong>{row['Sector']}</strong> below 50% of target — "
                        f"KES {row['revenue']:,.0f} / {tgt:,.0f}"))
        except Exception:
            pass

    alerts.append(("s" if mongo_ok else "w", now_ts,
        "MongoDB audit pipeline active." if mongo_ok
        else "MongoDB unreachable — audit logging disabled."))
    alerts.append(("s" if pg_ok else "w", now_ts,
        "PostgreSQL catalogue synced." if pg_ok
        else "PostgreSQL unreachable — target comparisons unavailable."))

    html_alerts = ""
    for typ, ts, txt in alerts[:10]:
        cls, badge_lbl, badge_c = TYPE_MAP.get(typ, TYPE_MAP["i"])
        html_alerts += (
            f'<div class="ac {cls}">'
            f'<div class="ac-time">{ts}'
            f'<span style="display:inline-block;font-size:.58rem;font-weight:800;'
            f'padding:.12rem .4rem;border-radius:4px;margin-left:.4rem;'
            f'background:rgba(0,0,0,.3);color:{badge_c};'
            f'border:1px solid {badge_c}40">{badge_lbl}</span></div>'
            f'<div class="ac-text">{txt}</div>'
            f'</div>'
        )

    st.markdown(
        f'<div style="max-height:280px;overflow-y:auto">'
        f'{html_alerts or "<div style=color:#1e3a5f;text-align:center;padding:2rem>No alerts.</div>"}'
        f'</div>',
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────
# AUTO-REFRESH
# ─────────────────────────────────────────────
if live_on:
    # Safely ping the frontend to reload every 5 seconds (5000ms)
    st_autorefresh(interval=5000, limit=None, key="data_refresh")

if live_on or refresh_now:
    ts_display = datetime.datetime.now().strftime("%H:%M:%S")
    st.markdown(
        f'<div style="text-align:right;font-size:.68rem;color:#1e3a5f;'
        f'font-family:JetBrains Mono,monospace;margin-top:.5rem">'
        f'⟳ Last refresh: {ts_display}</div>',
        unsafe_allow_html=True,
    )