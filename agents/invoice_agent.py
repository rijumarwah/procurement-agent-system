from autogen import AssistantAgent
from autogen.agentchat.agent import Agent
from typing import Optional, Union
from config import get_model_config
from run_sql import run_sql
import re
import logging

class InvoiceAgent(AssistantAgent):
    def __init__(self):
        super().__init__(
            name="invoice_agent",
            llm_config=get_model_config(),
            system_message=(
                "You are an invoice processing agent. "
                "Given invoice details, generate raw SQL INSERT statements for the 'invoice' and 'invoice_items' tables. "
                "Use only these column names:\n"
                "- invoice.invoice_no, po_number, vendor_id, invoice_date, total_amount, status, date_received, amount_paid\n"
                "- invoice_items.invoice_no, item_code, quantity, unit_price\n"
                "Only return SQL, no markdown, no explanations."
            )
        )

    def generate_reply(
        self,
        messages: Optional[list] = None,
        sender: Optional[Agent] = None,
        config: Optional[dict] = None
    ) -> Union[str, dict]:

        if messages is None and sender:
            messages = self.chat_messages.get(sender, [])

        if not messages or not isinstance(messages, list):
            logging.error("InvoiceAgent: No valid messages provided.")
            return {"content": "No valid messages provided."}

        user_input = messages[-1].get("content", "") if isinstance(messages[-1], dict) else str(messages[-1])
        user_input = user_input.strip()
        logging.info(f"[InvoiceAgent] Received input: {user_input}")

        # Relevance check (case-insensitive)
        if not re.search(r"\bprocess\s+invoice\b", user_input, re.IGNORECASE):
            logging.info("InvoiceAgent: Message not relevant.")
            return {"content": ""}

        # Pass to LLM
        try:
            raw = super().generate_reply(
                messages=[{"role": "user", "content": user_input}],
                sender=sender,
                config=config,
            )
        except Exception as e:
            logging.error(f"InvoiceAgent: LLM failed - {str(e)}")
            return {"content": "Failed to process invoice."}

        content = raw.get("content", "") if isinstance(raw, dict) else raw

        # 🧹 Clean up SQL from LLM
        content = re.sub(r"```sql|```|--.*", "", content).strip()
        content = re.sub(r"\n\s*\n", "\n", content)

        sql_statements = [
            stmt.strip() + ";" for stmt in content.split(";")
            if stmt.strip().lower().startswith("insert into")
        ]

        # Execute
        executed = []
        for stmt in sql_statements:
            run_sql(stmt)
            executed.append(stmt)

        if executed and hasattr(self, "groupchat") and self.groupchat and not self.groupchat.terminated:
            self.groupchat.terminate()
            print(f"[{self.name}] Terminated group chat after successful invoice processing.")

        return {
            "content": f"Executed {len(executed)} SQL statements:\n" + "\n".join(executed)
        }
