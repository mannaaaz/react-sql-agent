from langchain.agents import initialize_agent
from langchain.agents import AgentType
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()

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
        "prefix": """
You are a SQL agent.
You MUST use tools to answer questions about the database.
Never assume values.
If a question asks for a count, sum, or numeric result,
you MUST call execute_sql.
Only give Final Answer after using tools.
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

    result = agent.invoke({"input": question})
    steps = result.get("intermediate_steps", [])

    if not steps:
        return {"error": "No SQL execution detected."}

    last_tool_output = steps[-1][1]

    # 🔥 Convert string to dict if needed
    if isinstance(last_tool_output, str):
        try:
            last_tool_output = ast.literal_eval(last_tool_output)
        except:
            return {
                "error": "Tool output parsing failed.",
                "raw_output": last_tool_output
            }

    if isinstance(last_tool_output, dict):

        explanation = generate_explanation(
            question,
            last_tool_output.get("sql", "")
        )

        last_tool_output["explanation"] = explanation
        return last_tool_output

    return {
        "error": "Unexpected tool output type.",
        "raw_output": last_tool_output,
        "raw_steps": steps
    }