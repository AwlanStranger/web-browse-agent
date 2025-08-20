import asyncio
import langroid as lr
from pydantic import BaseModel

# --- Define the tool schema ---
class BrowseWeb(lr.agent.ToolMessage):
    request: str = "browse_web"
    purpose: str = (
        "Use a real browser to navigate websites, click, fill forms, and extract info. "
        "Call this when web interaction is required."
    )
    goal: str  # high-level instruction for the browsing run

# --- Coordinator agent that can call the tool ---
class Coordinator(lr.ChatAgent):
    def __init__(self, config: lr.ChatAgentConfig):
        super().__init__(config)

    # Async handler so Langroid can await the browser run
    async def browse_web_async(self, msg: BrowseWeb) -> str:
        # Lazy imports keep core agent light
        from browser_use import Agent as BrowserAgent
        from browser_use.llm import ChatOpenAI

        # Choose a fast, cheap OpenAI chat model; adjust as you like
        llm = ChatOpenAI(model="gpt-4o-mini")
        b = BrowserAgent(
            task=msg.goal,
            llm=llm,
            # Optional: keep a reusable profile for cookies/sessions
            # profile_dir=".browser-profiles/default",
        )
        result = await b.run()
        # `result` is typically a structured object; stringify or curate fields you want to return
        return str(result)

# --- Wire it up and run ---
cfg = lr.ChatAgentConfig(
    name="Planner",
    use_tools=True,            # enable Langroid's native tool mechanism
    use_functions_api=False,   # or True to use OpenAI function-calling
)

agent = Coordinator(cfg)
agent.enable_message(BrowseWeb)  # register the tool

task = lr.Task(
    agent,
    name="Bot",
    system_message=(
        """You are a planner that solves complex tasks.
        Think step-by-step and call `browse_web` whenever browsing is required.
        You are an autonomous assistant.
        Keep the user updated on every action you do browsing the web.
        Only ask for user input when needed.
        Otherwise, keep reasoning and using your tools until the task is complete.
        When done, say DONE and summarize the final answer."""
    ),
)
task.run()
