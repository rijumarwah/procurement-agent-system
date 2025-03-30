from autogen import GroupChat, GroupChatManager, UserProxyAgent
from agents.invoice_agent import InvoiceAgent
from agents.matching_agent import MatcherAgent
from agents.exception_agent import ExceptionHandlerAgent
from agents.payment_agent import PaymentProcessingAgent
from agents.status_agent import StatusAgent
from agents.vendor_agent import VendorCommunicationAgent
from agents.reporting_agent import ReportingAgent
from config import get_model_config

# Load LLM config
llm_config = get_model_config()

# Instantiate agents
invoice_agent = InvoiceAgent()
matcher_agent = MatcherAgent()
exception_agent = ExceptionHandlerAgent()
payment_agent = PaymentProcessingAgent()
status_agent = StatusAgent()
vendor_agent = VendorCommunicationAgent()
reporting_agent = ReportingAgent()

# Create UserProxyAgent
user_proxy = UserProxyAgent(
    name="user",
    human_input_mode="TERMINATE",
    code_execution_config=False,
)

# Create GroupChat with automatic speaker selection
group_chat = GroupChat(
    agents=[
        user_proxy,
        invoice_agent,
        matcher_agent,
        exception_agent,
        payment_agent,
        status_agent,
        vendor_agent,
        reporting_agent,
    ],
    messages=[],
    speaker_selection_method="auto",
    allow_repeat_speaker=False,
    max_round=3,
)

# Create the GroupChatManager
chat_manager = GroupChatManager(groupchat=group_chat, llm_config=llm_config)

# Run the conversation loop
if __name__ == "__main__":
    print("---🤖 Procurement Group Chat Ready.---")
    try:
        user_input = input("---📥 Enter your instruction (multi-line supported). End with an empty line:---\n\n")
        user_proxy.initiate_chat(chat_manager, message=user_input)
    except KeyboardInterrupt:
        print("\n---Chat session interrupted by user.---")
