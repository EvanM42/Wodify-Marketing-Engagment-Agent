import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage

SYSTEM_PROMPT = """
You are a data scientist for a gym marketing team.
Your job is to analyze member email engagement and score leads.

When given a task:
1. Review the contact and engagement data provided
2. Score each lead based on opens, clicks, and reply frequency
3. Segment leads: high engagement, low engagement, inactive
4. Identify the top contacts who should be reached out to today
5. Output a ranked list with name, email, phone, and engagement score
Do not write or send any emails — only analyze and rank.
"""

async def run(task: str) -> str:
    print(f"\n[Data Scientist] Starting: {task}\n")
    result_text = ""

    async for message in query(
        prompt=task,
        options=ClaudeAgentOptions(
            model="claude-sonnet-4-6",
            allowed_tools=["Read", "Bash"],
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
            print(f"\n[Data Scientist] Done (status: {message.subtype})")

    return result_text


if __name__ == "__main__":
    TASK = "Analyze the engagement data and return a ranked list of leads to contact today."
    asyncio.run(run(TASK))
