import re
import logging
from typing import Optional, Union

from autogen import AssistantAgent
from autogen.agentchat.agent import Agent

from config import get_model_config
from run_sql import run_sql


class MatcherAgent(AssistantAgent):
    """Performs a 3-way quantity match across PO, goods receipt, and invoice.

    Compares total quantities in `purchase_order_items`, `goods_receipt_items`,
    and `invoice_items` for a given PO number, then writes the result to
    `match_status`.  Uses INSERT OR REPLACE so re-running a match always
    reflects the latest data.
    """

    def __init__(self):
        config = get_model_config()
        config = {**config, "temperature": 0}
        super().__init__(
            name="matcher_agent",
            llm_config=config,
            system_message=(
                "You perform 3-way matching between PO, GR, and Invoice records "
                "and update the match_status table."
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

        if not messages:
            return {"content": ""}

        user_input = (
            messages[-1]["content"]
            if isinstance(messages[-1], dict)
            else str(messages[-1])
        )

        if "match" not in user_input.lower() and "3-way" not in user_input.lower():
            return {"content": ""}

        po_id = self._extract_po_id(user_input)
        if not po_id:
            return {"content": "No PO ID found in the request."}

        po_qty = self._scalar(run_sql(
            "SELECT SUM(quantity) FROM purchase_order_items WHERE po_number = ?",
            (po_id,),
        ))
        gr_qty = self._scalar(run_sql(
            """SELECT SUM(gri.quantity_received)
               FROM goods_receipt_items gri
               JOIN purchase_order_items poi
                 ON gri.item_code = poi.item_code
              WHERE poi.po_number = ?""",
            (po_id,),
        ))
        inv_qty = self._scalar(run_sql(
            """SELECT SUM(ii.quantity)
               FROM invoice_items ii
               JOIN purchase_order_items poi
                 ON ii.item_code = poi.item_code
              WHERE poi.po_number = ?""",
            (po_id,),
        ))

        if po_qty == 0 and gr_qty == 0 and inv_qty == 0:
            return {"content": f"No records found for PO {po_id}. Cannot perform match."}

        matched = po_qty == gr_qty == inv_qty
        status = "Matched" if matched else "Mismatched"
        details = f"PO: {po_qty} units | GR: {gr_qty} units | Invoice: {inv_qty} units"

        # INSERT OR REPLACE handles the PRIMARY KEY constraint on po_id
        run_sql(
            "INSERT OR REPLACE INTO match_status (po_id, status, details) VALUES (?, ?, ?)",
            (po_id, status, details),
        )

        logging.info("MatcherAgent: %s → %s", po_id, status)
        return {"content": f"3-way match for {po_id}: **{status}**\n{details}"}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _scalar(rows) -> float:
        """Return the first cell of a query result as a float (0 if NULL)."""
        if rows and rows[0][0] is not None:
            return float(rows[0][0])
        return 0.0

    @staticmethod
    def _extract_po_id(message: str) -> Optional[str]:
        """Pull a PO number from free-form text.

        Accepts formats like 'PO1001', 'PO #1001', 'po_number = 1001'.
        Always returns the value with the 'PO' prefix stripped so we store
        a consistent identifier (e.g. '1001', not 'PO1001').
        """
        pattern = r"(?:po[\s_#-]*(?:number|id)?\s*[=:]?\s*)(PO)?(\w+)"
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(2).upper()
        # Fallback: bare 'PO1001' anywhere in the text
        bare = re.search(r"\bPO(\w+)\b", message, re.IGNORECASE)
        return bare.group(1).upper() if bare else None
