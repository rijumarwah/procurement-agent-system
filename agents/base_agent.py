from autogen import AssistantAgent
from run_sql import run_sql

class BaseAgent:
    def __init__(self, name: str, model_config: dict, system_message: str):
        self.agent = AssistantAgent(name=name, llm_config=model_config, system_message=system_message)

    def run_prompt(self, prompt: str):
        # Generate the reply from the assistant agent
        sql = self.agent.generate_reply([{"role": "user", "content": prompt}]).get("content", "")

        # Split the response into individual SQL statements
        statements = [stmt.strip() for stmt in sql.split(";") if stmt.strip()]

        # Run the SQL statements
        results = [run_sql(stmt) for stmt in statements]

        # Return a summary of the SQL execution
        return f"Executed {len(statements)} SQL statements.\n\n{sql}"
