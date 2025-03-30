from autogen import AssistantAgent
from run_sql import run_sql
from config import get_model_config
from typing import Optional
from autogen.agentchat.agent import Agent
import logging
import re


class PaymentProcessingAgent(AssistantAgent):
    def __init__(self):
        super().__init__(
            name="payment_processing_agent",
            llm_config=get_model_config(),
            system_message=(
                "You are a payment processing agent. You decide whether an invoice is eligible for payment "
                "based on matching records in purchase_order, goods_receipt, and invoice. "
                "Respond ONLY if the user actually wants to pay an invoice; otherwise do nothing."
            )
        )

    def generate_reply(
        self,
        messages: Optional[list] = None,
        sender: Optional[Agent] = None,
        config: Optional[dict] = None
    ) -> dict:
        if messages is None and sender is not None:
            messages = self.chat_messages.get(sender, [])

        if not messages or not isinstance(messages, list) or not messages[-1].get("content", "").strip():
            return {"content": "No valid messages provided to process."}

        user_message = messages[-1].get("content", "")
        if "payment" not in user_message.lower() and "pay" not in user_message.lower():
            return {"content": ""}  # Not a payment request, silently ignore

        invoice_id = self.extract_invoice_id(user_message)
        if not invoice_id:
            return {"content": "No invoice ID found in the message."}

        invoice_data = run_sql(f"SELECT * FROM invoice WHERE invoice_no = '{invoice_id}'")
        if not invoice_data:
            return {"content": f"Invoice {invoice_id} does not exist."}

        # Get PO ID from invoice (assumes po_number == po_id)
        po_data = run_sql(f"SELECT po_number FROM invoice WHERE invoice_no = '{invoice_id}'")
        po_id = po_data[0][0] if po_data else None
        if not po_id:
            return {"content": f"No PO found for invoice {invoice_id}."}

        match_status = run_sql(f"SELECT status FROM match_status WHERE po_id = '{po_id}'")
        if not match_status or match_status[0][0].lower() != 'matched':
            return {
                "content": f"Invoice {invoice_id} cannot be processed for payment. "
                           f"The match status is not 'Matched'."
            }

        # Get total amount from invoice
        invoice_total = invoice_data[0][4]  # total_amount column

        # Insert payment and update invoice status
        run_sql(f"""
            INSERT INTO payments (invoice_no, amount, payment_date, status)
            VALUES ('{invoice_id}', {invoice_total}, DATE('now'), 'PAID')
        """)

        run_sql(f"""
            UPDATE invoice SET status = 'Paid', amount_paid = {invoice_total}
            WHERE invoice_no = '{invoice_id}'
        """)

        return {"content": f"Payment for invoice {invoice_id} has been processed successfully."}

    def extract_invoice_id(self, message: str) -> str:
        match_obj = re.search(r"invoice\s+(\S+)", message, re.IGNORECASE)
        return match_obj.group(1).strip() if match_obj else ""
