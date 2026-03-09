from langchain.agents import initialize_agent
from langchain.agents import AgentType
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
import logging
from datetime import datetime

load_dotenv()

logging.basicConfig(
    filename="agent.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log_event(level, message):
    if level == "info":
        logging.info(message)
    elif level == "error":
        logging.error(message)

api_key = os.getenv("OPEN_API_KEY")

from agent.tools import list_tables, describe_table, execute_sql

# ---------------------------
# Initialize LLM
# ---------------------------
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    api_key=api_key
)

# ---------------------------
# Register tools
# ---------------------------
tools = [list_tables, describe_table, execute_sql]

SCHEMA_DESCRIPTION = """
Database Schema:

Table: customers
- id (INTEGER)
- name (TEXT)
- country (TEXT)
- signup_date (TEXT)

Table: products
- id (INTEGER)
- name (TEXT)
- category (TEXT)
- price (REAL)

Table: orders
- id (INTEGER)
- customer_id (INTEGER)
- product_id (INTEGER)
- quantity (INTEGER)
- order_date (TEXT)

Relationships:
- orders.customer_id → customers.id
- orders.product_id → products.id
"""

# ---------------------------
# Create ReAct Agent
# ---------------------------
agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    return_intermediate_steps=True,
    agent_kwargs={
        "prefix": f"""
You are a SQL agent.

You MUST use tools to answer questions about the database.
Never assume values.

Use the following schema information carefully when writing SQL:

{SCHEMA_DESCRIPTION}

Rules:
- Only generate read-only SELECT queries.
- Use proper joins based on relationships.
- Always verify column names.
- If a question asks for numeric result, you MUST call execute_sql.
- Only give Final Answer after using tools.
"""
    }
)

# ---------------------------
# Explanation Generator
# ---------------------------
def generate_explanation(question, sql):
    explanation_prompt = f"""
Explain briefly what this SQL query does.

User Question: {question}
SQL Query: {sql}

Return a short 1-2 sentence explanation.
"""

    explanation_llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        api_key=api_key
    )

    response = explanation_llm.invoke(explanation_prompt)
    return response.content


# ---------------------------
# Run Agent (STRUCTURED OUTPUT)
# ---------------------------
import ast

def run_agent(question: str):

    # 🔹 1️⃣ LOG AT START (PASTE HERE)
    log_event("info", f"New question: {question}")

    # 1️⃣ First attempt
    result = agent.invoke({"input": question})
    steps = result.get("intermediate_steps", [])

    if not steps:
        log_event("error", "No SQL execution detected.")
        return {"error": "No SQL execution detected."}
    

    last_tool_output = steps[-1][1]

    # Convert string → dict
    if isinstance(last_tool_output, str):
        try:
            last_tool_output = ast.literal_eval(last_tool_output)
        except:
            return {
                "error": "Tool output parsing failed.",
                "raw_output": last_tool_output
            }

    # 2️⃣ If execution returned SQL error → Retry once
    if isinstance(last_tool_output, dict) and "error" in last_tool_output:

        error_message = last_tool_output.get("details", "Unknown SQL error")
        failed_sql = last_tool_output.get("sql", "")

        # 🔹 2️⃣ LOG FIRST FAILURE (PASTE HERE)
        log_event("error", f"Initial SQL failed: {failed_sql}")
        log_event("error", f"Error details: {error_message}")


        retry_prompt = f"""
The following SQL query failed:

SQL:
{failed_sql}

Error:
{error_message}

Fix the SQL and return ONLY the corrected SQL query.
Do not include explanations.
"""

        retry_response = llm.invoke(retry_prompt)
        corrected_sql = retry_response.content.strip()

        # Execute corrected SQL safely
        from agent.tools import execute_sql
        retry_result = execute_sql(corrected_sql)

        # Convert retry result
        if isinstance(retry_result, str):
            try:
                retry_result = ast.literal_eval(retry_result)
            except:
                log_event("error", "Retry parsing failed.")
                return {
                    "error": "Retry parsing failed.",
                    "raw_output": retry_result
                }

         # If second attempt also fails → return error
        if "error" in retry_result:

            # 🔹 3️⃣ LOG RETRY FAILURE (PASTE HERE)
            log_event("error", f"Retry failed: {corrected_sql}")
            log_event("error", f"Retry error: {retry_result.get('details')}")

            return {
                "error": "SQL failed after retry.",
                "details": retry_result.get("details"),
                "failed_sql": corrected_sql
            }

        # 🔹 4️⃣ LOG RETRY SUCCESS (PASTE HERE)
        log_event("info", f"Retry successful: {retry_result.get('sql')}")

        explanation = generate_explanation(question, retry_result.get("sql", ""))
        retry_result["explanation"] = explanation
        return retry_result

    # 3️⃣ If first attempt succeeded
    if isinstance(last_tool_output, dict):

        # 🔹 5️⃣ LOG SUCCESS (PASTE HERE)
        log_event("info", f"SQL executed successfully: {last_tool_output.get('sql')}")

        explanation = generate_explanation(
            question,
            last_tool_output.get("sql", "")
        )

        last_tool_output["explanation"] = explanation
        return last_tool_output

    log_event("error", "Unexpected tool output type.")
    return {
        "error": "Unexpected tool output type.",
        "raw_output": last_tool_output,
        "raw_steps": steps
    }