from autogen import AssistantAgent
from config import get_model_config
from run_sql import run_sql
from autogen.agentchat.agent import Agent
from typing import Optional, Union
import re
import logging


class VendorCommunicationAgent(AssistantAgent):
    def __init__(self):
        super().__init__(
            name="vendor_communication_agent",
            llm_config=get_model_config(),
            system_message=(
                "You are a vendor communication agent. Given structured procurement data for a specific vendor, "
                "you write a friendly, concise status update covering purchase orders, invoices, payments, and any exceptions."
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
            return {"content": "No valid messages provided."}

        user_message = messages[-1].get("content", "") if isinstance(messages[-1], dict) else str(messages[-1])
        vendor_id = self.extract_vendor_id(user_message)
        if not vendor_id:
            return {"content": "No vendor ID found in the request."}

        # Safe PO Query (status column doesn't exist)
        po_data = run_sql(f"""
            SELECT po_number FROM purchase_order WHERE vendor_id = '{vendor_id}'
        """)
        po_numbers = [row[0] for row in po_data] if po_data else []
        total_pos = len(po_numbers)

        # Invoice statuses
        invoice_data = run_sql(f"""
            SELECT status FROM invoice WHERE vendor_id = '{vendor_id}'
        """)
        invoice_statuses = [row[0] for row in invoice_data] if invoice_data else []
        total_invoices = len(invoice_statuses)

        # Last payment (if any)
        payment_data = run_sql(f"""
            SELECT amount, payment_date FROM payments 
            WHERE invoice_no IN (SELECT invoice_no FROM invoice WHERE vendor_id = '{vendor_id}')
            ORDER BY payment_date DESC
        """)
        last_payment = payment_data[0] if payment_data else None

        # Exception count
        exception_data = run_sql(f"""
            SELECT COUNT(*) FROM match_status 
            WHERE po_id IN (SELECT po_number FROM purchase_order WHERE vendor_id = '{vendor_id}')
            AND status = 'EXCEPTION'
        """)
        exception_count = exception_data[0][0] if exception_data else 0

        # Structuring data for LLM
        summary_prompt = f"""
Given the following real procurement data for vendor {vendor_id}, generate a friendly vendor-facing status update.

- Total POs: {total_pos}
- Total Invoices: {total_invoices}
- Invoice Statuses: {invoice_statuses}
- Last Payment: {last_payment if last_payment else "None"}
- Exceptions Logged: {exception_count}

Keep the message clear and concise. Return only the vendor message, no extra formatting.
"""

        reply = super().generate_reply(
            messages=[{"role": "user", "content": summary_prompt}],
            sender=sender,
            config=config,
        )

        content = reply.get("content", "") if isinstance(reply, dict) else reply
        return {"content": content}

    def extract_vendor_id(self, message: str) -> Optional[str]:
        match = re.search(r"vendor\s+ID\s+(\w+)", message, re.IGNORECASE)
        return match.group(1).strip() if match else None
