import re
import logging
from typing import Optional

from autogen import AssistantAgent
from autogen.agentchat.agent import Agent

from config import get_model_config
from run_sql import run_sql


class ExceptionHandlerAgent(AssistantAgent):
    """Logs procurement exceptions to the `exceptions` table.

    Activates when a message contains the words 'mismatch', 'missing', or
    'not found', which are the standard signals produced by other agents when
    something goes wrong.
    """

    TRIGGER_KEYWORDS = ("mismatch", "missing", "not found")

    def __init__(self):
        super().__init__(
            name="exception_agent",
            llm_config=get_model_config(),
            system_message=(
                "You log exceptions to the `exceptions` table when a mismatch, "
                "missing data, or not-found error is reported by another agent."
            ),
        )

    def generate_reply(
        self,
        messages: Optional[list] = None,
        sender: Optional[Agent] = None,
        config: Optional[dict] = None,
    ) -> dict:

        if messages is None and sender is not None:
            messages = self.chat_messages.get(sender, [])

        if not messages or not isinstance(messages, list):
            return {"content": ""}

        last_msg = (
            messages[-1].get("content", "")
            if isinstance(messages[-1], dict)
            else str(messages[-1])
        )

        if not any(kw in last_msg.lower() for kw in self.TRIGGER_KEYWORDS):
            return {"content": ""}

        po_match = re.search(r"\bPO(\w+)\b", last_msg, re.IGNORECASE)
        inv_match = re.search(r"\bINV(\w+)\b", last_msg, re.IGNORECASE)

        if inv_match:
            po_number = po_match.group(0).upper() if po_match else "UNKNOWN"
            issue_type = "Invoice Not Found"
            details = f"Invoice INV{inv_match.group(1)} does not exist in the system."
        elif po_match:
            po_number = po_match.group(0).upper()
            issue_type = "PO Mismatch"
            details = f"Quantity mismatch detected for {po_number} during 3-way match."
        else:
            po_number = "UNKNOWN"
            issue_type = "General Exception"
            details = "Mismatch or missing data encountered during procurement processing."

        run_sql(
            "INSERT INTO exceptions (po_number, issue_type, details) VALUES (?, ?, ?)",
            (po_number, issue_type, details),
        )

        logging.info("ExceptionAgent: logged '%s' for %s", issue_type, po_number)
        return {"content": f"Exception logged for {po_number}: {issue_type}."}
