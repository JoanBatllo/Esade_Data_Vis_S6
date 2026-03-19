import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import random
import time
import re

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
    "chat_history": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def load_default_data() -> pd.DataFrame:
    return pd.read_csv(DEFAULT_CSV)


MONEY_COLUMNS = {
    "Production Budget", "US Gross", "Worldwide Gross", "US DVD Sales",
}


def smart_fmt(col_name: str):
    """Return a tick formatter: currency style for dollar columns, plain for the rest."""
    is_money = col_name in MONEY_COLUMNS

    def _fmt(x, _pos):
        prefix = "$" if is_money else ""
        if abs(x) >= 1e9:
            return f"{prefix}{x/1e9:.1f}B"
        if abs(x) >= 1e6:
            return f"{prefix}{x/1e6:.0f}M"
        if abs(x) >= 1e3:
            return f"{prefix}{x/1e3:.0f}K"
        return f"{prefix}{x:g}"

    return mticker.FuncFormatter(_fmt)


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
        ax.xaxis.set_major_formatter(smart_fmt(x_col))
    if df[y_col].dtype in ["float64", "int64"]:
        ax.yaxis.set_major_formatter(smart_fmt(y_col))
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
        ax.yaxis.set_major_formatter(smart_fmt(y_col))
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


# ──────────────────────────────────────────────
# Chatbot — data analyst assistant
# ──────────────────────────────────────────────
def _col_match(query_lower: str, columns: list[str]) -> str | None:
    """Find the best-matching column name mentioned in the query."""
    for col in sorted(columns, key=len, reverse=True):
        if col.lower() in query_lower:
            return col
    return None


def _num_col_match(query_lower: str, df: pd.DataFrame) -> str | None:
    num_cols = df.select_dtypes("number").columns.tolist()
    return _col_match(query_lower, num_cols)


def chatbot_respond(query: str, df: pd.DataFrame, x_col: str, y_col: str) -> str:
    """Generate a plain-text answer about the dataset without any LLM."""
    q = query.lower().strip()
    num_cols = df.select_dtypes("number").columns.tolist()
    all_cols = df.columns.tolist()

    # ── greetings ──
    if q in ("hi", "hello", "hey", "hola"):
        return (
            "Hello! I'm your data assistant. Ask me about the dataset — "
            "try *describe*, *columns*, *correlation*, *top 5*, *mean of …*, etc."
        )

    # ── help ──
    if q in ("help", "?"):
        return (
            "Here are things you can ask me:\n"
            "- **columns** — list all columns\n"
            "- **shape** — number of rows and columns\n"
            "- **describe** — summary statistics\n"
            "- **describe `<column>`** — stats for one column\n"
            "- **mean / median / min / max / std of `<column>`**\n"
            "- **correlation** — correlation between the selected X and Y\n"
            "- **correlation matrix** — full numeric correlation table\n"
            "- **top N `<column>`** — largest N rows by that column\n"
            "- **bottom N `<column>`** — smallest N rows\n"
            "- **missing** — missing-value counts\n"
            "- **unique `<column>`** — unique values\n"
            "- **distribution `<column>`** — histogram\n"
            "- **sample** — show 5 random rows"
        )

    # ── columns ──
    if q in ("columns", "cols", "fields", "variables"):
        return "**Columns:** " + ", ".join(f"`{c}`" for c in all_cols)

    # ── shape ──
    if "shape" in q or "how many rows" in q or "size" in q:
        return f"The dataset has **{df.shape[0]}** rows and **{df.shape[1]}** columns."

    # ── missing values ──
    if "missing" in q or "null" in q or "nan" in q:
        miss = df.isnull().sum()
        miss = miss[miss > 0].sort_values(ascending=False)
        if miss.empty:
            return "No missing values in the dataset."
        lines = [f"- `{c}`: {n} missing ({n/len(df)*100:.1f}%)" for c, n in miss.items()]
        return "**Missing values:**\n" + "\n".join(lines)

    # ── sample ──
    if "sample" in q:
        return f"Here are 5 random rows:\n\n{df.sample(min(5, len(df))).to_markdown(index=False)}"

    # ── full describe ──
    if q in ("describe", "summary", "statistics", "stats"):
        desc = df[num_cols].describe().round(2)
        return f"**Summary statistics:**\n\n{desc.to_markdown()}"

    # ── describe a single column ──
    if q.startswith("describe "):
        col = _col_match(q, all_cols)
        if col:
            desc = df[col].describe().round(2)
            return f"**`{col}` statistics:**\n\n{desc.to_markdown()}"
        return "I couldn't find that column. Type **columns** to see the list."

    # ── correlation between selected X & Y ──
    if q in ("correlation", "corr", "r"):
        clean = df[[x_col, y_col]].dropna()
        r = clean[x_col].corr(clean[y_col])
        strength = "weak" if abs(r) < 0.3 else "moderate" if abs(r) < 0.7 else "strong"
        direction = "positive" if r > 0 else "negative"
        return (
            f"Pearson correlation between **{x_col}** and **{y_col}**: "
            f"**r = {r:.4f}** ({strength} {direction} relationship)."
        )

    # ── full correlation matrix ──
    if "correlation matrix" in q or "corr matrix" in q:
        corr = df[num_cols].corr().round(2)
        return f"**Correlation matrix:**\n\n{corr.to_markdown()}"

    # ── top N ──
    m = re.search(r"top\s+(\d+)", q)
    if m:
        n = int(m.group(1))
        col = _num_col_match(q, df) or y_col
        top = df.nlargest(n, col)
        display_cols = [c for c in all_cols if not c.startswith("_")][:6]
        if col not in display_cols:
            display_cols.append(col)
        return f"**Top {n} by `{col}`:**\n\n{top[display_cols].to_markdown(index=False)}"

    # ── bottom N ──
    m = re.search(r"bottom\s+(\d+)", q)
    if m:
        n = int(m.group(1))
        col = _num_col_match(q, df) or y_col
        bot = df.nsmallest(n, col)
        display_cols = [c for c in all_cols if not c.startswith("_")][:6]
        if col not in display_cols:
            display_cols.append(col)
        return f"**Bottom {n} by `{col}`:**\n\n{bot[display_cols].to_markdown(index=False)}"

    # ── single-stat queries (mean, median, min, max, std) ──
    for stat, fn in [("mean", "mean"), ("average", "mean"), ("median", "median"),
                     ("min", "min"), ("max", "max"), ("std", "std"),
                     ("standard deviation", "std")]:
        if stat in q:
            col = _num_col_match(q, df) or y_col
            val = getattr(df[col].dropna(), fn)()
            return f"The **{fn}** of `{col}` is **{val:,.2f}**."

    # ── unique values ──
    if "unique" in q or "distinct" in q:
        col = _col_match(q, all_cols)
        if col is None:
            col = all_cols[0]
        nuniq = df[col].nunique()
        if nuniq <= 30:
            vals = ", ".join(str(v) for v in df[col].dropna().unique()[:30])
            return f"`{col}` has **{nuniq}** unique values: {vals}"
        return f"`{col}` has **{nuniq}** unique values (too many to list)."

    # ── distribution (returns a chart) ──
    if "distribution" in q or "histogram" in q or "hist" in q:
        col = _num_col_match(q, df)
        if col is None:
            col = y_col
        return f"__CHART_HIST__{col}"

    # ── fallback ──
    return (
        "I'm not sure how to answer that. Try one of these:\n"
        "- **help** — see all available commands\n"
        "- **describe** — summary statistics\n"
        "- **correlation** — relationship between X and Y\n"
        "- **top 5** — highest values\n"
        "- **missing** — missing value counts"
    )


st.divider()
st.subheader("Data Assistant")
st.caption("Ask questions about the loaded dataset — no API key needed.")

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        if msg.get("chart_col"):
            fig, ax = plt.subplots(figsize=(7, 4))
            sns.histplot(df[msg["chart_col"]].dropna(), kde=True, ax=ax, color="#4C72B0")
            ax.set_title(f"Distribution of {msg['chart_col']}", fontsize=13, weight="bold")
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
        else:
            st.markdown(msg["content"])

if prompt := st.chat_input("Ask about the data (try: describe, correlation, top 5 …)"):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    answer = chatbot_respond(prompt, df, x_col, y_col)

    with st.chat_message("assistant"):
        if answer.startswith("__CHART_HIST__"):
            col = answer.replace("__CHART_HIST__", "")
            fig, ax = plt.subplots(figsize=(7, 4))
            sns.histplot(df[col].dropna(), kde=True, ax=ax, color="#4C72B0")
            ax.set_title(f"Distribution of {col}", fontsize=13, weight="bold")
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
            st.session_state.chat_history.append(
                {"role": "assistant", "content": "", "chart_col": col}
            )
        else:
            st.markdown(answer)
            st.session_state.chat_history.append(
                {"role": "assistant", "content": answer}
            )
