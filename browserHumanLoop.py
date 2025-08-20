from dotenv import load_dotenv
load_dotenv()

from browser_use.llm import ChatOpenAI
from browser_use import Agent, BrowserSession, Controller
from playwright.async_api import async_playwright
import asyncio
from datetime import datetime
import time
import os
from typing import Union
from pydantic import BaseModel, Field

llm = ChatOpenAI(model="gpt-4.1")

# ---------- Helpers (unchanged) ----------
def generate_filename(prefix="log", extension=".txt"):
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}{extension}"

def append_to_logs(subdir: str, filename: str, text: Union[str, list, dict]):
    log_dir = os.path.join("logs", subdir)
    os.makedirs(log_dir, exist_ok=True)
    filepath = os.path.join(log_dir, filename)
    with open(filepath, "a", encoding="utf-8") as f:
        if os.path.getsize(filepath) > 0:
            f.write("\n")
        if isinstance(text, list):
            for item in text:
                f.write(str(item) + "\n")
        elif isinstance(text, dict):
            f.write(str(text) + "\n")
        else:
            f.write(str(text))
    return filepath
# ----------------------------------------

# ---------- Human-in-the-loop tool ----------
class AskHumanArgs(BaseModel):
    reason: str = Field(
        ...,
        description=(
            "Why you need help (e.g., 'captcha', '2FA code', "
            "'which option should I click', 'site blocked', etc.)"
        ),
    )
    question: str = Field(
        ...,
        description="The exact question to show the human."
    )
    hint: str | None = Field(
        None,
        description="Optional extra context (e.g., the URL or what you tried)."
    )

# blocking console prompt, but async-safe
async def _prompt_async(prompt: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: input(prompt))

async def ask_human_tool(args: AskHumanArgs) -> str:
    # Pretty console message
    print("\n" + "="*60)
    print("🤝  Agent needs your help")
    print(f"Reason : {args.reason}")
    if args.hint:
        print(f"Hint   : {args.hint}")
    print(f"Question:\n{args.question}")
    print("-"*60)
    answer = await _prompt_async("Your answer: ")
    print("="*60 + "\n")
    return answer
# --------------------------------------------

async def main():
    # Tell the model it can ask you for help via the tool
    system_instructions = """
    You are operating a real browser. If you hit a blocker (captcha, MFA, paywall, cookie wall), ambiguous UI, or need the user's preference, CALL THE TOOL `ask_human` with a clear question.
    Keep asks concise and specific (e.g., 'Paste the 6-digit 2FA code from SMS' or 'Should I click "View profile" or "People results"?').
    Only continue once you receive the human's answer.
    """

    task = """
    Ask the user what they need help with.
    """

    # Wire the tool through the Controller
    controller = Controller()
    controller.register_tool(
        name="ask_human",
        description="Ask the human for input when blocked or when a decision is needed.",
        args_model=AskHumanArgs,
        func=ask_human_tool,
    )

    browser_session = BrowserSession(
        executable_path='C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
        user_data_dir='~/.config/browseruse/profiles/edge',
        headless=False,
    )

    agent = Agent(
        task=task,
        llm=llm,
        browser_session=browser_session,
        use_vision=True,
        controller=controller,
        system_prompt=system_instructions,  # nudge the model to use the tool
    )

    start_time = time.perf_counter()
    history = await agent.run()
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time

    # ----- logging -----
    filename = generate_filename()
    append_to_logs("results", filename, history.final_result())
    append_to_logs("actions", filename, history.action_history())
    append_to_logs("thoughts", filename, history.model_thoughts())
    append_to_logs("screenshots", filename, history.screenshot_paths())
    append_to_logs("runtime", filename, str(elapsed_time))
    # If your controller surfaces tool calls in history.action_history(), they'll be captured above.
    # If you want a separate log of human Q&A, you can also intercept inside ask_human_tool
    # by appending to a dedicated log file from there.
    # -------------------
    
asyncio.run(main())
