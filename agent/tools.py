from langchain.tools import tool
import sqlite3
import pandas as pd
import json 
import re 

DB_PATH = "database/sales.db"

FORBIDDEN_KEYWORDS = [
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate",
    "create",
    "replace"
]

def is_safe_sql(sql: str):
    lower_sql = sql.lower()
    return not any(keyword in lower_sql for keyword in FORBIDDEN_KEYWORDS) 

# ---------- Tool 1: List Tables ----------
@tool
def list_tables(input:str) -> str:
    """Returns all table names in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    conn.close()
    return ", ".join([t[0] for t in tables])


# ---------- Tool 2: Describe Table ----------
@tool
def describe_table(table_name: str) -> str:
    """Returns column names and types for a given table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    conn.close()

    if not columns:
        return f"No such table: {table_name}"

    return "\n".join([f"{col[1]} ({col[2]})" for col in columns])


# ---------- Tool 3: Execute SQL ---------- V1
# successfully tested but output is not structured and not very useful for the agent to reason with.
# @tool
# def execute_sql(query: str) -> str:
#     """
#     Executes a read-only SQL query and returns first 20 rows.
#     Only SELECT queries are allowed.
#     """
#     if not query.strip().lower().startswith("select"):
#         return "Only SELECT queries are allowed."

#     try:
#         conn = sqlite3.connect(DB_PATH)
#         df = pd.read_sql_query(query, conn)
#         conn.close()

#         if df.empty:
#             return "Query executed successfully but returned no data."

#         return df.head(20).to_string(index=False)

#     except Exception as e:
#         return f"SQL Error: {str(e)}"

# ---------- Tool 3: Execute SQL ---------- V2
# @tool
# def execute_sql(query: str) -> str:
#     """Executes a SQL query and returns structured results."""

#     conn = sqlite3.connect(DB_PATH)
#     df = pd.read_sql_query(query, conn)
#     conn.close()

#     result = {
#         "sql": query,
#         "columns": list(df.columns),
#         "data": df.to_dict(orient="records"),
#         "row_count": len(df)
#     }

#     return str(result)

# @tool
# def execute_sql(query: str) -> str:
#     """Executes a read-only SQL query and returns structured results."""

#     # 🔥 Remove markdown code fences if present
#     query = re.sub(r"```sql", "", query, flags=re.IGNORECASE)
#     query = re.sub(r"```", "", query)
#     query = query.strip()

#     conn = sqlite3.connect(DB_PATH)

#     try:
#         df = pd.read_sql_query(query, conn)

#         result = {
#             "sql": query,
#             "columns": df.columns.tolist(),
#             "data": df.to_dict(orient="records"),
#             "row_count": len(df)
#         }

#         return str(result)

#     except Exception as e:
#         return str({"error": str(e)})

#     finally:
#         conn.close()

def enforce_limit(sql: str, max_rows: int = 100):
    if "limit" not in sql.lower():
        sql = sql.strip().rstrip(";")
        sql += f" LIMIT {max_rows}"
    return sql

@tool
def execute_sql(query: str):
    """Executes a read-only SQL query and returns structured results."""

    # 🔥 Remove markdown code fences if present
    query = re.sub(r"```sql", "", query, flags=re.IGNORECASE)
    query = re.sub(r"```", "", query)
    query = query.strip()

    # 🔐 Block dangerous keywords
    if not is_safe_sql(query):
        return str({"error": "Only read-only SELECT queries are allowed."})

    # 🔐 Must start with SELECT
    if not query.lower().startswith("select"):
        return str({"error": "Only SELECT queries are allowed."})

    # 📏 Enforce row limit
    query = enforce_limit(query)

    conn = sqlite3.connect(DB_PATH)

    try:
        df = pd.read_sql_query(query, conn)

        result = {
            "sql": query,
            "columns": df.columns.tolist(),
            "data": df.to_dict(orient="records"),
            "row_count": len(df)
        }

        return str(result)

    except Exception as e:
        return str({
            "error": "SQL execution failed.",
            "details": str(e),
            "sql": query
        })

    finally:
        conn.close()