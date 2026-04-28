import re
import logging
from typing import Optional

from autogen import AssistantAgent
from autogen.agentchat.agent import Agent

from config import get_model_config
from run_sql import run_sql


class PaymentProcessingAgent(AssistantAgent):
    """Processes payment for an invoice that has passed 3-way matching.

    Before recording a payment, the agent checks that:
      1. The invoice exists.
      2. The associated PO has a 'Matched' status in `match_status`.
    If both conditions hold, it inserts a record into `payments` and marks
    the invoice as 'Paid'.
    """

    def __init__(self):
        super().__init__(
            name="payment_processing_agent",
            llm_config=get_model_config(),
            system_message=(
                "You are a payment processing agent. Decide whether an invoice "
                "is eligible for payment based on its match status, then record "
                "the payment.  Only respond to explicit payment requests."
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

        user_message = (
            messages[-1].get("content", "")
            if isinstance(messages[-1], dict)
            else str(messages[-1])
        )

        if "pay" not in user_message.lower():
            return {"content": ""}

        invoice_id = self._extract_invoice_id(user_message)
        if not invoice_id:
            return {"content": "No invoice ID found in the request."}

        invoice_rows = run_sql(
            "SELECT invoice_no, po_number, total_amount FROM invoice WHERE invoice_no = ?",
            (invoice_id,),
        )
        if not invoice_rows:
            return {"content": f"Invoice {invoice_id} does not exist."}

        _, po_number, total_amount = invoice_rows[0]

        match_rows = run_sql(
            "SELECT status FROM match_status WHERE po_id = ?",
            (po_number,),
        )
        if not match_rows or match_rows[0][0].lower() != "matched":
            current = match_rows[0][0] if match_rows else "unknown"
            return {
                "content": (
                    f"Cannot process payment for {invoice_id}. "
                    f"Match status is '{current}' (must be 'Matched')."
                )
            }

        run_sql(
            "INSERT INTO payments (invoice_no, payment_date, amount_paid, status) "
            "VALUES (?, DATE('now'), ?, 'Paid')",
            (invoice_id, total_amount),
        )
        run_sql(
            "UPDATE invoice SET status = 'Paid', amount_paid = ? WHERE invoice_no = ?",
            (total_amount, invoice_id),
        )

        logging.info("PaymentAgent: paid %s (amount: %s)", invoice_id, total_amount)
        return {"content": f"Payment of {total_amount} for invoice {invoice_id} processed successfully."}

    @staticmethod
    def _extract_invoice_id(message: str) -> str:
        match = re.search(r"invoice\s+(\S+)", message, re.IGNORECASE)
        return match.group(1).strip() if match else ""
