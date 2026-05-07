import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage

SYSTEM_PROMPT = """
You are a marketing manager for a gym.
Your job is to build a daily outreach plan from lead data.

When given a task:
1. Review the ranked lead list from the data scientist
2. Decide the outreach priority and method for each lead (email, phone, or both)
3. Create a clear, ordered outreach plan for today
4. Specify the goal for each contact (retention, upsell, re-engagement)
Do not write email content — only create the plan.
"""

async def run(task: str) -> str:
    print(f"\n[Manager] Starting: {task}\n")
    result_text = ""

    async for message in query(
        prompt=task,
        options=ClaudeAgentOptions(
            model="claude-opus-4-6",
            allowed_tools=["Read", "Glob", "Grep", "Bash"],
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
            print(f"\n[Manager] Done (status: {message.subtype})")

    return result_text


if __name__ == "__main__":
    TASK = "Create today's outreach plan based on the lead engagement scores."
    asyncio.run(run(TASK))
