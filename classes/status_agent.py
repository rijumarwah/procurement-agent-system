import re
import logging
from typing import Optional, Union

from autogen import AssistantAgent
from autogen.agentchat.agent import Agent

from config import get_model_config
from run_sql import run_sql


class StatusAgent(AssistantAgent):
    """Returns the payment and match status for a given invoice.

    Responds only when the message contains both 'status' and 'invoice' so it
    stays quiet during unrelated turns in the group chat.
    """

    def __init__(self):
        super().__init__(
            name="status_agent",
            llm_config=get_model_config(),
            system_message=(
                "You are a status-checking agent. Given an invoice ID, retrieve "
                "the payment status from the `invoice` table and the match status "
                "from the `match_status` table, then report both clearly."
            ),
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

        user_msg = (
            messages[-1].get("content", "")
            if isinstance(messages[-1], dict)
            else str(messages[-1])
        )

        if "status" not in user_msg.lower() or "invoice" not in user_msg.lower():
            return {"content": ""}

        invoice_id = self._extract_invoice_id(user_msg)
        if not invoice_id:
            return {"content": "Please include an invoice ID in your request."}

        invoice_rows = run_sql(
            "SELECT status, po_number FROM invoice WHERE UPPER(TRIM(invoice_no)) = UPPER(?)",
            (invoice_id.strip(),),
        )
        if not invoice_rows:
            return {"content": f"Invoice '{invoice_id}' was not found."}

        payment_status, po_number = invoice_rows[0]

        match_rows = run_sql(
            "SELECT status FROM match_status WHERE po_id = ?",
            (po_number,),
        )
        match_status = match_rows[0][0] if match_rows else "No match record found"

        return {
            "content": (
                f"Status for invoice {invoice_id}:\n"
                f"  Payment status : {payment_status}\n"
                f"  Match status   : {match_status}"
            )
        }

    @staticmethod
    def _extract_invoice_id(message: str) -> Optional[str]:
        match = re.search(r"invoice\s+(\w+)", message, re.IGNORECASE)
        return match.group(1).strip() if match else None
