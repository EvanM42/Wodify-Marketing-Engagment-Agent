import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage

SYSTEM_PROMPT = """
You are a marketer for a gym.
Your job is to write and send personalized follow-up emails to leads.

When given a task:
1. Review the outreach plan and each lead's engagement history
2. Write a personalized email for each contact based on their goal (retention, upsell, re-engagement)
3. Keep emails concise, friendly, and action-oriented
4. Send each email via the available API or tool
5. Log the name, email, phone number, and outcome for each contact
"""

async def run(task: str) -> str:
    print(f"\n[Marketer] Starting: {task}\n")
    result_text = ""

    async for message in query(
        prompt=task,
        options=ClaudeAgentOptions(
            model="claude-sonnet-4-6",
            allowed_tools=["Read", "Bash", "Write"],
            system_prompt=SYSTEM_PROMPT,
        ),
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text") and block.text:
                    print(block.text)
                elif hasattr(block, "name"):
                    print(f"[Tool: {block.name}]")
        elif isinstance(message, ResultMessage):
            result_text = message.result or ""
            print(f"\n[Marketer] Done (status: {message.subtype})")

    return result_text


if __name__ == "__main__":
    TASK = "Write and send personalized follow-up emails based on today's outreach plan."
    asyncio.run(run(TASK))
