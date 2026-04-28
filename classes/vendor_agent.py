import logging
import re
from typing import Optional, Union

from autogen import AssistantAgent
from autogen.agentchat.agent import Agent

from config import get_model_config
from run_sql import run_sql


class VendorCommunicationAgent(AssistantAgent):
    """Generates a friendly status update for a specific vendor.

    Queries live procurement data (POs, invoices, payments, exceptions) and
    passes a structured summary to the LLM, which writes the final message.
    This keeps fabrication impossible — the LLM only receives real numbers.
    """

    def __init__(self):
        super().__init__(
            name="vendor_communication_agent",
            llm_config=get_model_config(),
            system_message=(
                "You are a vendor communication agent. Given structured procurement "
                "data for a specific vendor, write a friendly, concise status update "
                "covering purchase orders, invoices, payments, and any open exceptions. "
                "Return only the vendor-facing message text."
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

        user_message = (
            messages[-1].get("content", "")
            if isinstance(messages[-1], dict)
            else str(messages[-1])
        )

        vendor_id = self._extract_vendor_id(user_message)
        if not vendor_id:
            return {"content": "Please specify a vendor ID (e.g. 'vendor V001')."}

        po_rows = run_sql(
            "SELECT po_number FROM purchase_order WHERE vendor_id = ?",
            (vendor_id,),
        )
        total_pos = len(po_rows) if po_rows else 0

        invoice_rows = run_sql(
            "SELECT status FROM invoice WHERE vendor_id = ?",
            (vendor_id,),
        )
        invoice_statuses = [r[0] for r in invoice_rows] if invoice_rows else []

        payment_rows = run_sql(
            """SELECT amount_paid, payment_date
               FROM payments
               WHERE invoice_no IN (
                   SELECT invoice_no FROM invoice WHERE vendor_id = ?
               )
               ORDER BY payment_date DESC
               LIMIT 1""",
            (vendor_id,),
        )
        last_payment = payment_rows[0] if payment_rows else None

        exception_rows = run_sql(
            """SELECT COUNT(*) FROM match_status
               WHERE po_id IN (
                   SELECT po_number FROM purchase_order WHERE vendor_id = ?
               ) AND status = 'EXCEPTION'""",
            (vendor_id,),
        )
        exception_count = exception_rows[0][0] if exception_rows else 0

        summary_prompt = (
            f"Write a vendor status update for vendor {vendor_id} using this data:\n"
            f"  - Total purchase orders : {total_pos}\n"
            f"  - Total invoices        : {len(invoice_statuses)}\n"
            f"  - Invoice statuses      : {invoice_statuses}\n"
            f"  - Last payment          : {last_payment or 'none on record'}\n"
            f"  - Open exceptions       : {exception_count}\n\n"
            "Be friendly and concise. Return only the message text."
        )

        reply = super().generate_reply(
            messages=[{"role": "user", "content": summary_prompt}],
            sender=sender,
            config=config,
        )

        content = reply.get("content", "") if isinstance(reply, dict) else str(reply)
        return {"content": content}

    @staticmethod
    def _extract_vendor_id(message: str) -> Optional[str]:
        # Accepts: 'vendor V001', 'vendor ID V001', 'vendor: V001'
        match = re.search(r"vendor(?:\s+id)?[\s:]+(\w+)", message, re.IGNORECASE)
        return match.group(1).strip() if match else None
