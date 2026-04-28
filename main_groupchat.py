import logging
from autogen import GroupChat, GroupChatManager, UserProxyAgent

from agents import (
    InvoiceAgent,
    MatcherAgent,
    ExceptionHandlerAgent,
    PaymentProcessingAgent,
    StatusAgent,
    VendorCommunicationAgent,
    ReportingAgent,
)
from config import get_model_config

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")


def build_group_chat() -> tuple[UserProxyAgent, GroupChatManager]:
    llm_config = get_model_config()

    user_proxy = UserProxyAgent(
        name="user",
        human_input_mode="TERMINATE",
        code_execution_config=False,
    )

    agents = [
        user_proxy,
        InvoiceAgent(),
        MatcherAgent(),
        ExceptionHandlerAgent(),
        PaymentProcessingAgent(),
        StatusAgent(),
        VendorCommunicationAgent(),
        ReportingAgent(),
    ]

    group_chat = GroupChat(
        agents=agents,
        messages=[],
        speaker_selection_method="auto",
        allow_repeat_speaker=False,
        max_round=10,
    )

    manager = GroupChatManager(groupchat=group_chat, llm_config=llm_config)
    return user_proxy, manager


if __name__ == "__main__":
    print("🤖  Procurement Agent System — ready.")
    print("    Type your instruction and press Enter. Ctrl-C to quit.\n")

    user_proxy, manager = build_group_chat()

    try:
        user_input = input("📥  Instruction: ").strip()
        if user_input:
            user_proxy.initiate_chat(manager, message=user_input)
    except KeyboardInterrupt:
        print("\nSession ended.")
