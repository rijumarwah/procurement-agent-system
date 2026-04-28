import logging
from typing import Optional, Union

from autogen import AssistantAgent
from autogen.agentchat.agent import Agent

from config import get_model_config
from run_sql import run_sql


class ReportingAgent(AssistantAgent):
    """Generates SQL-backed procurement reports.

    Supported report types (matched by keywords in the user message):
      - 'total billed per vendor'
      - 'overdue payments'
      - 'open exceptions'
    """

    def __init__(self):
        super().__init__(
            name="reporting_agent",
            llm_config=get_model_config(),
            system_message=(
                "You generate procurement reports by running SQL queries and "
                "returning actual figures from the database. Never fabricate numbers."
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

        user_input = (
            messages[-1]["content"]
            if isinstance(messages[-1], dict)
            else str(messages[-1])
        ).lower()

        try:
            if "total billed per vendor" in user_input:
                return self._report_billed_per_vendor()
            elif "overdue" in user_input:
                return self._report_overdue_payments()
            elif "open exception" in user_input:
                return self._report_open_exceptions()
            else:
                return {
                    "content": (
                        "Report type not recognised. Available reports:\n"
                        "  • total billed per vendor\n"
                        "  • overdue payments\n"
                        "  • open exceptions"
                    )
                }
        except Exception as exc:
            logging.error("ReportingAgent error: %s", exc)
            return {"content": f"Error generating report: {exc}"}

    # ------------------------------------------------------------------
    # Individual report methods
    # ------------------------------------------------------------------

    def _report_billed_per_vendor(self) -> dict:
        query = (
            "SELECT i.vendor_id, SUM(ii.quantity * ii.unit_price) AS total_billed "
            "FROM invoice i "
            "JOIN invoice_items ii ON i.invoice_no = ii.invoice_no "
            "GROUP BY i.vendor_id"
        )
        rows = run_sql(query)
        return {
            "content": (
                "Report: Total Billed Per Vendor\n\n"
                + self._format_rows(rows, ("Vendor ID", "Total Billed"))
            )
        }

    def _report_overdue_payments(self) -> dict:
        query = (
            "SELECT invoice_no, vendor_id, date_received, status "
            "FROM invoice "
            "WHERE status NOT IN ('Paid', 'Partially Paid') "
            "  AND DATE(date_received) < DATE('now', '-30 days')"
        )
        rows = run_sql(query)
        return {
            "content": (
                "Report: Overdue Payments (unpaid invoices older than 30 days)\n\n"
                + self._format_rows(rows, ("Invoice No", "Vendor", "Date Received", "Status"))
            )
        }

    def _report_open_exceptions(self) -> dict:
        query = "SELECT * FROM exceptions WHERE status = 'Open'"
        rows = run_sql(query)
        return {
            "content": (
                "Report: Open Exceptions\n\n"
                + self._format_rows(rows, ("ID", "PO Number", "Issue Type", "Details", "Status", "Timestamp"))
            )
        }

    @staticmethod
    def _format_rows(rows, headers: tuple) -> str:
        if not rows:
            return "No records found."
        header_line = " | ".join(str(h) for h in headers)
        separator = "-" * len(header_line)
        data_lines = "\n".join(" | ".join(str(cell) for cell in row) for row in rows)
        return f"{header_line}\n{separator}\n{data_lines}"
