from autogen import AssistantAgent
from config import get_model_config
from run_sql import run_sql
from autogen.agentchat.agent import Agent
from typing import Optional, Union
import re


class MatcherAgent(AssistantAgent):
    def __init__(self):
        config = get_model_config()
        config["temperature"] = 0

        super().__init__(
            name="matcher_agent",
            llm_config=config,
            system_message="You perform 3-way matching between PO, GR, and Invoice records, and update the match_status table."
        )

    def generate_reply(
        self,
        messages: Optional[list] = None,
        sender: Optional[Agent] = None,
        config: Optional[dict] = None
    ) -> Union[str, dict]:
        if messages is None and sender:
            messages = self.chat_messages.get(sender, [])
        if not messages:
            return {"content": ""}

        user_input = messages[-1]["content"] if isinstance(messages[-1], dict) else str(messages[-1])

        if "match" not in user_input.lower() and "3-way" not in user_input.lower():
            return {"content": ""}

        po_id = self.extract_po_id(user_input)
        if not po_id:
            return {"content": "No PO ID found."}

        # Get quantities
        po_qty = run_sql(f"""
            SELECT SUM(quantity) FROM purchase_order_items WHERE po_number = '{po_id}'
        """)
        gr_qty = run_sql(f"""
            SELECT SUM(quantity_received)
            FROM goods_receipt_items
            WHERE item_code IN (SELECT item_code FROM purchase_order_items WHERE po_number = '{po_id}')
        """)
        inv_qty = run_sql(f"""
            SELECT SUM(quantity)
            FROM invoice_items
            WHERE item_code IN (SELECT item_code FROM purchase_order_items WHERE po_number = '{po_id}')
        """)

        po_qty_val = po_qty[0][0] if po_qty and po_qty[0][0] is not None else 0
        gr_qty_val = gr_qty[0][0] if gr_qty and gr_qty[0][0] is not None else 0
        inv_qty_val = inv_qty[0][0] if inv_qty and inv_qty[0][0] is not None else 0

        # skip if everything is zero
        if po_qty_val == 0 and gr_qty_val == 0 and inv_qty_val == 0:
            if hasattr(self, "groupchat") and self.groupchat and not self.groupchat.terminated:
                self.groupchat.terminate()
            return {
                "content": f"No records found for PO{po_id}. Skipping matching."
            }

        matched = (po_qty_val == gr_qty_val == inv_qty_val)
        status = "Matched" if matched else "Mismatched"
        detail_msg = f"PO: {po_qty_val} units, GR: {gr_qty_val} units, Invoice: {inv_qty_val} units"

        run_sql(f"""
            INSERT INTO match_status (po_id, status, details)
            VALUES ('{po_id}', '{status}', '{detail_msg}')
        """)

        if hasattr(self, "groupchat") and self.groupchat and not self.groupchat.terminated:
            self.groupchat.terminate()

        return {
            "content": f"Matching complete for PO{po_id}. Status: **{status}**\n{detail_msg}"
        }

    def extract_po_id(self, message: str) -> Optional[str]:
        match = re.search(r"(?:PO\s*#?|po_number\s*=?\s*|po_id\s*=?\s*|po\s+)(\w+)", message, re.IGNORECASE)
        return match.group(1).strip().upper() if match else None
