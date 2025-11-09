from typing import Any, Dict
import json
import asyncio
import re

from firebase_functions import https_fn
from firebase_admin import initialize_app

# this makes sure Firebase Admin is ready (even if no Firestore used right now)
initialize_app()

# =========================
# DEDALUS / PLAN LOGIC
# =========================
from dedalus_labs import AsyncDedalus, DedalusRunner


async def run_dedalus_personalized_plan(user_data: dict) -> str:
    """
    Ask the model for a 7-day plan, same idea as in your Flask app.
    Keep the prompt tight so we get clean sections.
    """
    client = AsyncDedalus()
    runner = DedalusRunner(client)

    wake_time = user_data.get("wakeUpTime", "8:00 AM")
    sleep_time = user_data.get("sleepTime", "7:00 PM")

    prompt_input = f"""
    You are an elite performance coach. A user has provided their personal data.
    Create a 7-day "1% better" plan that is SHORT, ACTIONABLE, and fits inside their day.

    USER DATA:
    - Name: {user_data.get('name', 'N/A')}
    - Age: {user_data.get('age', 'N/A')}
    - Wakes Up: {wake_time}
    - Sleeps: {sleep_time}
    - Eating Habits: {user_data.get('eatingHabits', 'N/A')}
    - Exercise: {user_data.get('exerciseRoutine', 'N/A')}
    - Focus Ability: {user_data.get('deepFocus', 'N/A')}
    - Time Management: {user_data.get('timeManagement', 'N/A')}
    - Notification Style: {user_data.get('notificationStyle', 'N/A')}

    TASK:
    1. Start with a brief, motivating introduction addressed to the user by name.
    2. Then generate EXACTLY 7 days.
    3. For EACH day, create three sections: Morning, Afternoon, Evening.
    4. For EACH section, write EXACTLY 3 bullet tasks.
    5. EVERY task MUST start with a specific time inside their day
       (morning between {wake_time} and 11:30 AM;
        afternoon between 12:00 PM and 5:00 PM;
        evening between 5:00 PM and {sleep_time}).
    6. After Day 7, add "Personalized Tips:" and list 5–8 bullets.
    7. Do NOT wrap tasks in parentheses. Do NOT add stray brackets.

    REQUIRED FORMAT:

    (Short intro...)

    Day 1:
    Morning:
    - 8:15 AM: ...
    - ...
    Afternoon:
    - 12:30 PM: ...
    Evening:
    - 5:15 PM: ...

    Day 2:
    ...

    Day 7:
    ...

    Personalized Tips:
    - ...
    """

    result = await runner.run(
        input=prompt_input,
        model="openai/gpt-5-mini",
        stream=False,
        # keep your mcp server here if you were using one in app.py
        mcp_servers=["therick"]
    )
    return result.final_output


def parse_personalized_plan(text: str) -> Dict[str, Any]:
    """
    A lightweight parser to turn the model text into JSON like your Flask version.
    This mirrors the structure you’ve been using.
    """
    days: list[dict] = []
    intro = ""
    tips: list[str] = []

    # split intro from the rest
    parts = text.split("Day 1:", 1)
    if len(parts) == 2:
        intro = parts[0].strip()
        rest = "Day 1:" + parts[1]
    else:
        rest = text

    # split into day chunks
    day_chunks = re.split(r"(Day\s+\d+:)", rest)
    # re.split gives us ["", "Day 1:", "...", "Day 2:", "...", ...]
    current_day = None
    for i in range(1, len(day_chunks), 2):
        day_header = day_chunks[i]           # e.g. "Day 1:"
        day_body = day_chunks[i + 1]         # the text after it
        m = re.search(r"Day\s+(\d+):", day_header)
        if not m:
            continue
        day_number = int(m.group(1))

        # get sections
        morning = _extract_section(day_body, "Morning:")
        afternoon = _extract_section(day_body, "Afternoon:")
        evening = _extract_section(day_body, "Evening:")

        days.append({
            "day": day_number,
            "morning": morning,
            "afternoon": afternoon,
            "evening": evening,
        })

    # tips
    tips_match = re.search(r"Personalized Tips:\s*(.*)", text, re.DOTALL | re.IGNORECASE)
    if tips_match:
        tips_block = tips_match.group(1)
        for line in tips_block.split("\n"):
            line = line.strip()
            if line.startswith("-"):
                tip = line.lstrip("-").strip()
                if tip and tip not in tips:
                    tips.append(tip)

    # sort days by number
    days = sorted(days, key=lambda d: d["day"])

    return {
        "intro": intro,
        "days": days,
        "tips": tips,
    }


def _extract_section(body: str, section_name: str) -> list[str]:
    """
    Pulls lines under 'Morning:'/'Afternoon:'/'Evening:' until next section or empty.
    """
    pattern = re.compile(rf"{section_name}\s*(.*)", re.IGNORECASE | re.DOTALL)
    match = pattern.search(body)
    if not match:
        return []
    # take everything after the section name, but stop at the next section
    tail = match.group(1)
    tail = re.split(r"\n\s*(Morning:|Afternoon:|Evening:|Day\s+\d+:|Personalized Tips:)", tail)[0]
    tasks = []
    for line in tail.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("-"):
            line = line.lstrip("-").strip()
        if line and line not in ("[", "]"):
            tasks.append(line)
    return tasks


# =========================
# HELPERS FOR RESPONSES
# =========================
def json_resp(payload: Any, status: int = 200) -> https_fn.Response:
    return https_fn.Response(
        json.dumps(payload),
        status=status,
        headers={"Content-Type": "application/json"},
    )


def parse_json_body(request: https_fn.Request) -> Dict[str, Any]:
    try:
        if request.data:
            return json.loads(request.data.decode("utf-8"))
        return {}
    except Exception:
        return {}


# =========================
# HTTP ENDPOINTS
# =========================

@https_fn.on_request(region="us-central1")
def create_personalized_plan(request: https_fn.Request) -> https_fn.Response:
    """
    POST /create_personalized_plan
    Body: same JSON you were sending from Postman / Swift.
    Returns: { intro, days: [...], tips: [...] }
    """
    if request.method != "POST":
        return json_resp({"error": "Use POST"}, 405)

    user_data = parse_json_body(request)
    if not user_data:
        return json_resp({"error": "Missing user data in request body"}, 400)

    try:
        # run the async Dedalus call
        raw_text = asyncio.run(run_dedalus_personalized_plan(user_data))
        structured = parse_personalized_plan(raw_text)
        return json_resp(structured, 200)
    except Exception as e:
        # log e in real code
        return json_resp({"error": "Internal server error"}, 500)


@https_fn.on_request(region="us-central1")
def health(request: https_fn.Request) -> https_fn.Response:
    return json_resp({"ok": True}, 200)
