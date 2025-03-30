from autogen import AssistantAgent
from run_sql import run_sql
from config import get_model_config
from autogen.agentchat.agent import Agent
from typing import Optional
import logging
import re

class ExceptionHandlerAgent(AssistantAgent):
    def __init__(self):
        super().__init__(
            name="exception_agent",
            llm_config=get_model_config(),
            system_message="You are responsible for logging exceptions into the `exceptions` table based on mismatch, missing data, or not found errors."
        )

    def generate_reply(
        self,
        messages: Optional[list] = None,
        sender: Optional[Agent] = None,
        config: Optional[dict] = None
    ) -> dict:
        if messages is None and sender:
            messages = self.chat_messages.get(sender, [])

        if not messages or not isinstance(messages, list):
            logging.error("No valid messages provided.")
            return {"content": ""}

        last_msg = messages[-1].get("content", "")
        if not any(keyword in last_msg.lower() for keyword in ["mismatch", "missing", "not found"]):
            return {"content": ""}

        # Extract PO or Invoice ID
        po_match = re.search(r"\bPO\d+\b", last_msg, re.IGNORECASE)
        inv_match = re.search(r"\bINV\d+\b", last_msg, re.IGNORECASE)

        po_number = po_match.group().upper() if po_match else None
        invoice_id = inv_match.group().upper() if inv_match else None

        if invoice_id:
            issue_type = "Invoice Not Found"
            details = f"Invoice {invoice_id} does not exist in the system."
        elif po_number:
            issue_type = "PO Mismatch"
            details = f"Mismatch detected in PO {po_number} during 3-way match."
        else:
            issue_type = "General Exception"
            details = "Mismatch or missing data encountered in procurement process."

        po_column = po_number if po_number else "UNKNOWN"

        try:
            sql = f"""
                INSERT INTO exceptions (po_number, issue_type, details)
                VALUES ('{po_column}', '{issue_type}', '{details}')
            """
            run_sql(sql)
            return {
                "content": f"Logged exception for {po_column}: {issue_type}"
            }
        except Exception as e:
            logging.error(f"Failed to log exception: {e}")
            return {
                "content": f"Failed to log exception: {str(e)}"
            }
