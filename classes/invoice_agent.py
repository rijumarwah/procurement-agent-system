import re
import logging
from typing import Optional, Union

from autogen import AssistantAgent
from autogen.agentchat.agent import Agent

from config import get_model_config
from run_sql import run_sql


class InvoiceAgent(AssistantAgent):
    """Parses an incoming invoice description and persists it to the database.

    The agent asks the LLM to produce raw INSERT statements for the `invoice`
    and `invoice_items` tables, then executes them.  It intentionally keeps the
    LLM in a narrow lane (SQL generation only) so the rest of the system can
    rely on the data being there immediately after this agent replies.
    """

    SYSTEM_MESSAGE = (
        "You are an invoice processing agent. "
        "Given invoice details, produce raw SQL INSERT statements for the "
        "'invoice' and 'invoice_items' tables only. "
        "Allowed columns:\n"
        "  invoice      : invoice_no, po_number, vendor_id, invoice_date, "
        "total_amount, status, date_received, amount_paid\n"
        "  invoice_items: invoice_no, item_code, quantity, unit_price\n"
        "Return only valid SQL statements separated by semicolons. "
        "No markdown, no comments, no explanations."
    )

    def __init__(self):
        super().__init__(
            name="invoice_agent",
            llm_config=get_model_config(),
            system_message=self.SYSTEM_MESSAGE,
        )

    def generate_reply(
        self,
        messages: Optional[list] = None,
        sender: Optional[Agent] = None,
        config: Optional[dict] = None,
    ) -> Union[str, dict]:

        if messages is None and sender is not None:
            messages = self.chat_messages.get(sender, [])

        if not messages or not isinstance(messages, list):
            return {"content": ""}

        user_input = (
            messages[-1].get("content", "")
            if isinstance(messages[-1], dict)
            else str(messages[-1])
        ).strip()

        if not re.search(r"\bprocess\s+invoice\b", user_input, re.IGNORECASE):
            return {"content": ""}

        try:
            raw = super().generate_reply(
                messages=[{"role": "user", "content": user_input}],
                sender=sender,
                config=config,
            )
        except Exception as exc:
            logging.error("InvoiceAgent: LLM call failed – %s", exc)
            return {"content": "Failed to generate SQL for invoice."}

        content = raw.get("content", "") if isinstance(raw, dict) else str(raw)

        # Strip any markdown fences or inline comments the LLM may have added
        content = re.sub(r"```(?:sql)?|```|--[^\n]*", "", content).strip()

        sql_statements = [
            stmt.strip()
            for stmt in content.split(";")
            if stmt.strip().lower().startswith("insert into")
        ]

        executed = []
        for stmt in sql_statements:
            result = run_sql(stmt)
            if result is not None:
                executed.append(stmt)
            else:
                logging.warning("InvoiceAgent: statement failed – %s", stmt[:80])

        if not executed:
            return {"content": "No SQL statements were executed. Check the invoice details and try again."}

        summary = "\n".join(executed)
        return {"content": f"Processed {len(executed)} SQL statement(s):\n{summary}"}
