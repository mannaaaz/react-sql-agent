import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
from agent.agent_core import run_agent

# -------------------
# Session State Setup
# -------------------
if "history" not in st.session_state:
    st.session_state["history"] = []

if "example_query" not in st.session_state:
    st.session_state["example_query"] = ""

# -------------------
# Page Config
# -------------------
st.set_page_config(
    page_title="ReAct SQL Agent",
    layout="wide"
)

st.title("🧠 ReAct SQL Analytics Agent")



st.markdown(
"""
AI-powered SQL agent using:
- LangChain • OpenAI GPT-4o • SQLite • Streamlit
- ReAct reasoning
- Tool-based execution
- Deterministic SQL backend
- Structured analytics output
"""
)

st.markdown("---")
st.markdown("### 💬 Ask your data anything")

# -------------------
# Sidebar
# -------------------
with st.sidebar:
    st.title("⚙️ Controls")

    show_reasoning = st.toggle("Show Agent Reasoning", value=False)

    st.markdown("---")
    st.markdown("### 💡 Example Queries")

    example_queries = [
        "Total revenue from all orders",
        "Total revenue per country sorted descending",
        "Which product sold the most quantity?",
        "Average order quantity per product",
        "How many orders were placed in 2023?"
    ]

    for q in example_queries:
        if st.button(q):
            st.session_state["example_query"] = q

    st.markdown("---")
    st.markdown("### 🕘 Query History")

    for past_query in reversed(st.session_state["history"][-5:]):
        st.caption(past_query)

# -------------------
# User Input
# -------------------
question = st.text_input(
    "Enter your question:",
    value=st.session_state.get("example_query", "")
)

if not question:
    st.info("Try one of the example queries from the sidebar 👈")

# -------------------
# Run Query
# -------------------
if st.button("Run Query") and question:

    with st.spinner("Agent is reasoning..."):
        result = run_agent(question)

    # Save to history
    st.session_state["history"].append(question)

    if "error" in result:

        # Clean user-facing message
        st.error("Query execution failed.")

        # Show specific error summary
        st.warning(result["error"])

        # Expandable technical details
        with st.expander("🔎 Technical Details"):

            if "failed_sql" in result:
                st.markdown("**Failed SQL:**")
                st.code(result["failed_sql"], language="sql")

            if "details" in result:
                st.markdown("**Database Error:**")
                st.write(result["details"])

            if "raw_output" in result:
                st.markdown("**Raw Output:**")
                st.write(result["raw_output"])

    else:
        
        # -------------------
        # Generated SQL
        # -------------------
        st.subheader("🧾 Generated SQL")
        st.code(result["sql"], language="sql")

        # -------------------
        # Query Result
        # -------------------
        st.subheader("📋 Query Result")

        df = pd.DataFrame(result["data"])
        st.dataframe(df, use_container_width=True)
        st.caption(f"{result['row_count']} rows returned")

        # CSV Download
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
                label="Download CSV",
                data=csv,
                file_name="query_result.csv",
                mime="text/csv"
            )

        # -------------------
        # Intelligent Chart Logic
        # -------------------
        st.subheader("📊 Chart")

        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        non_numeric_cols = df.select_dtypes(exclude=["number"]).columns.tolist()

        if len(numeric_cols) == 1 and len(non_numeric_cols) == 1:
            st.bar_chart(df.set_index(non_numeric_cols[0])[numeric_cols[0]])

        elif len(numeric_cols) >= 1 and len(non_numeric_cols) == 0:
            st.line_chart(df[numeric_cols])

        else:
            st.info("No automatic chart available for this query structure.")

        # -------------------
        # Explanation
        # -------------------
        st.subheader("🧠 Explanation")
        st.write(result["explanation"])

        if show_reasoning:
            st.subheader("🔍 Agent Reasoning Steps")
            st.write(result.get("raw_steps"))