from autogen import AssistantAgent
from run_sql import run_sql
from config import get_model_config
from autogen.agentchat.agent import Agent
from typing import Optional, Union
import re
import logging

class StatusAgent(AssistantAgent):
    def __init__(self):
        super().__init__(
            name="status_agent",
            llm_config=get_model_config(),
            system_message=(
                "You are a status-checking agent. When provided with an invoice ID, "
                "retrieve the payment status from the `invoice` table and match status from the `match_status` table. "
                "Respond clearly with both statuses. If the invoice doesn't exist, report that."
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

        if not messages or not isinstance(messages, list) or not messages[-1].get("content", "").strip():
            return {"content": ""}  # Not relevant

        user_msg = messages[-1].get("content", "")
        if "status" not in user_msg.lower() or "invoice" not in user_msg.lower():
            return {"content": ""}

        invoice_id = self.extract_invoice_id(user_msg)
        logging.debug(f"[DEBUG] Extracted invoice ID: {invoice_id} (len={len(invoice_id) if invoice_id else 'None'})")
        if not invoice_id:
            return {"content": "No invoice ID found in your request."}

        # Add test: Fetch all invoice IDs
        test_data = run_sql("SELECT invoice_no FROM invoice")
        logging.debug(f"[DEBUG] Available invoice_no entries: {test_data}")

        # Main query with debug
        invoice_query = f"""
            SELECT status, po_number FROM invoice
            WHERE UPPER(TRIM(invoice_no)) = UPPER('{invoice_id.strip()}')
        """
        logging.debug(f"[DEBUG] SQL query: {invoice_query}")
        invoice_data = run_sql(invoice_query)
        logging.debug(f"[DEBUG] Raw invoice_data result: {invoice_data} (type: {type(invoice_data)})")

        if not invoice_data:
            return {"content": f"Invoice `{invoice_id}` not found."}

        payment_status = invoice_data[0][0]
        po_number = invoice_data[0][1]

        match_data = run_sql(f"SELECT status FROM match_status WHERE po_id = '{po_number}'")
        match_status = match_data[0][0] if match_data else "Unknown"

        result = {
            "content": (
                f"📄 Status for Invoice `{invoice_id}`:\n"
                f"- Payment Status: **{payment_status}**\n"
                f"- Match Status: **{match_status}**"
            )
        }

        if hasattr(self, "groupchat") and self.groupchat and not self.groupchat.terminated:
            self.groupchat.terminate()
            print(f"[{self.name}] terminated the group chat after status check.")

        return result

    def extract_invoice_id(self, message: str) -> Optional[str]:
        match = re.search(r"invoice\s+(\w+)", message, re.IGNORECASE)
        return match.group(1).strip() if match else None
