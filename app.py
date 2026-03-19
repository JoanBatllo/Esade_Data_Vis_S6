import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import random
import time

# ──────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────
st.set_page_config(page_title="A/B Chart Testing", layout="centered")

BUSINESS_QUESTION = "Does a higher production budget lead to higher worldwide gross revenue?"
DEFAULT_CSV = "movies.csv"
DEFAULT_X = "Production Budget"
DEFAULT_Y = "Worldwide Gross"

# ──────────────────────────────────────────────
# Session state defaults
# ──────────────────────────────────────────────
for key, val in {
    "chart_picked": None,
    "start_time": None,
    "elapsed": None,
    "ab_log": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def load_default_data() -> pd.DataFrame:
    return pd.read_csv(DEFAULT_CSV)


def currency_fmt(x, _):
    if x >= 1e9:
        return f"${x/1e9:.1f}B"
    if x >= 1e6:
        return f"${x/1e6:.0f}M"
    if x >= 1e3:
        return f"${x/1e3:.0f}K"
    return f"${x:.0f}"


def draw_chart_a(df: pd.DataFrame, x_col: str, y_col: str):
    """Scatter plot with regression line."""
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.regplot(
        data=df,
        x=x_col,
        y=y_col,
        scatter_kws={"alpha": 0.35, "s": 18, "color": "#4C72B0"},
        line_kws={"color": "#C44E52", "linewidth": 2},
        ax=ax,
    )
    ax.set_title(f"{y_col} vs {x_col}", fontsize=14, weight="bold")
    ax.set_xlabel(x_col, fontsize=11)
    ax.set_ylabel(y_col, fontsize=11)
    if df[x_col].dtype in ["float64", "int64"]:
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(currency_fmt))
    if df[y_col].dtype in ["float64", "int64"]:
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(currency_fmt))
    fig.tight_layout()
    return fig


def draw_chart_b(df: pd.DataFrame, x_col: str, y_col: str):
    """Bar chart of mean y grouped into x-bins."""
    tmp = df[[x_col, y_col]].dropna()
    try:
        tmp["bin"] = pd.qcut(tmp[x_col], q=6, duplicates="drop")
    except (ValueError, TypeError):
        tmp["bin"] = pd.cut(tmp[x_col], bins=6)
    grouped = tmp.groupby("bin", observed=True)[y_col].mean().reset_index()
    grouped["label"] = grouped["bin"].astype(str)

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.barplot(data=grouped, x="label", y=y_col, palette="Blues_d", ax=ax)
    ax.set_title(f"Average {y_col} by {x_col} range", fontsize=14, weight="bold")
    ax.set_xlabel(f"{x_col} range", fontsize=11)
    ax.set_ylabel(f"Mean {y_col}", fontsize=11)
    if grouped[y_col].dtype in ["float64", "int64"]:
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(currency_fmt))
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    return fig


# ──────────────────────────────────────────────
# Sidebar — dataset & variable selection (100%)
# ──────────────────────────────────────────────
st.sidebar.header("Dataset & Variables")
uploaded = st.sidebar.file_uploader("Upload a CSV file", type=["csv"])

if uploaded is not None:
    df = pd.read_csv(uploaded)
    st.sidebar.success(f"Loaded **{uploaded.name}** ({len(df)} rows)")
else:
    df = load_default_data()
    st.sidebar.info(f"Using default dataset: **{DEFAULT_CSV}** ({len(df)} rows)")

numeric_cols = df.select_dtypes("number").columns.tolist()

if len(numeric_cols) < 2:
    st.error("The dataset needs at least two numeric columns.")
    st.stop()

x_col = st.sidebar.selectbox(
    "X-axis variable",
    numeric_cols,
    index=numeric_cols.index(DEFAULT_X) if DEFAULT_X in numeric_cols else 0,
)
y_col = st.sidebar.selectbox(
    "Y-axis variable",
    numeric_cols,
    index=numeric_cols.index(DEFAULT_Y) if DEFAULT_Y in numeric_cols else 1,
)

# ──────────────────────────────────────────────
# Main UI
# ──────────────────────────────────────────────
st.title("A/B Chart Testing Experiment")
st.markdown(
    f"### Business question\n"
    f"> **{BUSINESS_QUESTION}**\n\n"
    f"*Analysing **{y_col}** vs **{x_col}***"
)

st.divider()

# ── Step 1: pick a random chart ──
if st.button("Show me a random chart", type="primary", use_container_width=True):
    st.session_state.chart_picked = random.choice(["A", "B"])
    st.session_state.start_time = time.time()
    st.session_state.elapsed = None

# ── Step 2: display chart + "answered" button ──
if st.session_state.chart_picked is not None and st.session_state.elapsed is None:
    chart_id = st.session_state.chart_picked
    st.info(f"Chart **{chart_id}** was randomly selected.")

    if chart_id == "A":
        fig = draw_chart_a(df, x_col, y_col)
        st.caption("Chart A — Scatter plot with trend line")
    else:
        fig = draw_chart_b(df, x_col, y_col)
        st.caption("Chart B — Bar chart of averages by range")

    st.pyplot(fig)
    plt.close(fig)

    if st.button("Did I answer your question?", type="secondary", use_container_width=True):
        elapsed = time.time() - st.session_state.start_time
        st.session_state.elapsed = elapsed
        st.session_state.ab_log.append(
            {"chart": chart_id, "seconds": round(elapsed, 2)}
        )

# ── Step 3: show timing result ──
if st.session_state.elapsed is not None:
    chart_id = st.session_state.chart_picked
    elapsed = st.session_state.elapsed

    st.success(
        f"You took **{elapsed:.2f} seconds** to answer the question using "
        f"**Chart {chart_id}**."
    )

    if chart_id == "A":
        fig = draw_chart_a(df, x_col, y_col)
        st.caption("Chart A — Scatter plot with trend line")
    else:
        fig = draw_chart_b(df, x_col, y_col)
        st.caption("Chart B — Bar chart of averages by range")
    st.pyplot(fig)
    plt.close(fig)

    # ── Cumulative results table ──
    if st.session_state.ab_log:
        st.divider()
        st.subheader("Experiment results so far")
        log_df = pd.DataFrame(st.session_state.ab_log)
        summary = (
            log_df.groupby("chart")["seconds"]
            .agg(["count", "mean", "median"])
            .rename(columns={"count": "Trials", "mean": "Avg time (s)", "median": "Median time (s)"})
        )
        st.dataframe(summary.style.format({"Avg time (s)": "{:.2f}", "Median time (s)": "{:.2f}"}))

    st.info("Click **Show me a random chart** again to run another trial.")
