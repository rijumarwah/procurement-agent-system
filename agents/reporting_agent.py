import sqlite3
import re
import logging
from autogen import AssistantAgent
from config import get_model_config
from run_sql import run_sql
from autogen.agentchat.agent import Agent
from typing import Optional, Union


class ReportingAgent(AssistantAgent):
    def __init__(self):
        super().__init__(
            name="reporting_agent",
            llm_config=get_model_config(),
            system_message=(
                "You generate SQL-based procurement reports, run the query using `run_sql()`, "
                "and return actual figures from the database. Do not fabricate or guess numbers. "
                "Your job is to return real data based on available tables."
            )
        )

    def generate_reply(
        self,
        messages: Optional[list] = None,
        sender: Optional[Agent] = None,
        config: Optional[dict] = None
    ) -> Union[str, dict]:

        if messages is None and sender is not None:
            messages = self.chat_messages.get(sender, [])

        if not messages or not isinstance(messages, list):
            logging.error("No valid messages provided.")
            return {"content": "No valid messages provided."}

        user_input = messages[-1]["content"] if isinstance(messages[-1], dict) else str(messages[-1])
        user_input_lower = user_input.lower()

        try:
            # Report: Total Billed Per Vendor
            if "total billed per vendor" in user_input_lower:
                query = """
                    SELECT invoice.vendor_id, 
                           SUM(invoice_items.quantity * invoice_items.unit_price) AS total_billed
                    FROM invoice
                    JOIN invoice_items ON invoice.invoice_no = invoice_items.invoice_no
                    GROUP BY invoice.vendor_id;
                """
                result = run_sql(query)
                return {
                    "content": (
                        "Report: Total Billed Per Vendor\n"
                        f"SQL Query:\n{query.strip()}\n\n"
                        "Explanation: This shows the total billed amount per vendor using quantity × unit_price.\n"
                        f"Result:\n{result}"
                    )
                }

            # Report: Overdue Payments
            elif "overdue payments" in user_input_lower:
                query = """
                    SELECT invoice_no, vendor_id, due_date, payment_status
                    FROM invoice
                    WHERE payment_status NOT IN ('PAID', 'Partially Paid')
                    AND DATE(due_date) < DATE('now');
                """
                result = run_sql(query)
                return {
                    "content": (
                        "Report: Overdue Payments\n"
                        f"SQL Query:\n{query.strip()}\n\n"
                        "Explanation: These are unpaid invoices past their due date.\n"
                        f"Result:\n{result}"
                    )
                }

            # Report: Open Exceptions
            elif "open exceptions" in user_input_lower:
                query = """
                    SELECT * FROM match_status WHERE status = 'EXCEPTION';
                """
                result = run_sql(query)
                return {
                    "content": (
                        "Report: Open Exceptions\n"
                        f"SQL Query:\n{query.strip()}\n\n"
                        "Explanation: Entries from match_status table flagged as EXCEPTION.\n"
                        f"Result:\n{result}"
                    )
                }

            # Unknown report
            else:
                return {
                    "content": (
                        "I didn’t recognize the report type. Please use one of the supported ones:\n"
                        "- Total billed per vendor\n"
                        "- Overdue payments\n"
                        "- Open exceptions"
                    )
                }

        except Exception as e:
            logging.error(f"Error generating report: {e}")
            return {"content": f"Error executing SQL query: {e}"}
