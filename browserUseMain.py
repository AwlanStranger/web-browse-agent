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

llm = ChatOpenAI(model="gpt-4.1")

# Helpers

def generate_filename(prefix="log", extension=".txt"):
    # Get current date and time
    now = datetime.now()
    # Format as YYYYMMDD_HHMMSS (safe for filenames)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    # Build filename
    return f"{prefix}_{timestamp}{extension}"

def append_to_logs(subdir: str, filename: str, text: Union[str, list, dict]):
    # Ensure the logs/subdir directory exists
    log_dir = os.path.join("logs", subdir)
    os.makedirs(log_dir, exist_ok=True)

    filepath = os.path.join(log_dir, filename)

    # Open in append mode, create if not exists
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

# endof helpers

# class Text:
#     content: str
# controller = Controller(output_model=Text)

async def main():
    sensitive_data = {
        'https://*.linkedin.com': {
            'x_username': 'hundopbrown@gmail.com',
            'x_password': 'Banana09',  # 'x_placeholder': '<actual secret value>',
        },
    }
    task = """
    Sign into linkedin using username/email x_username and password x_password.
    Do not create a new account, make sure you're signing into my existing account.
    After signing in, go to https://www.linkedin.com/in/rakeen-huq and scrape the profile.
    Give me just an appropriate json of the profile data.

    """

    browser_session = BrowserSession(
        # Path to a specific Chromium-based executable (optional)
        executable_path='C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',

        # Use a specific data directory on disk (optional, set to None for incognito)
        user_data_dir='~/.config/browseruse/profiles/edge',   # this is the default
        # ... any other BrowserProfile or playwright launch_persistnet_context config...
        headless=True,
        allowed_domains=['msn.com', 'https://*.linkedin.com']
    )
    agent = Agent(
        task=task,
        sensitive_data=sensitive_data,
        llm=llm,
        browser_session=browser_session,
        use_vision=False, # sends screenshots to the model, more expensive but potentially more accurate
    )


    start_time = time.perf_counter()
    history = await agent.run(max_steps=4)
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    
    # logging activities
    filename = generate_filename()
    append_to_logs("results", filename, history.final_result())
    append_to_logs("actions", filename, history.action_history())
    append_to_logs("thoughts", filename, history.model_thoughts())
    append_to_logs("screenshots", filename, history.screenshot_paths())
    append_to_logs("runtime", filename, str(elapsed_time))
asyncio.run(main())