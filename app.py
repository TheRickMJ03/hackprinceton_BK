import asyncio
import os
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from dedalus_labs import AsyncDedalus, DedalusRunner

# --- SETUP ---
# Get the API key from the server's environment variable
# (e.g., from your Render.com 'Environment' tab)

app = Flask(__name__)
CORS(app)


async def run_dedalus_tip(interest_topic: str, difficulty_level: str):
    """
    Runs the Dedalus agent to get MULTIPLE short tips.
    """
    client = AsyncDedalus()
    runner = DedalusRunner(client)
    
    prompt_input = f"""
    A user wants 5 short, single-sentence tips for '{interest_topic}'
    at a '{difficulty_level}' level.

    Please list them. Start each tip with a bullet point '- '.
    Do not add any extra introduction or conclusion.
    """
    print(f"Flask Server: Sending request for 5 tips on '{interest_topic}'...")
    try:
        result = await runner.run(
            # input=prompt_input, model="openai/gpt-5-mini",
            mcp_servers=["therickmj03/MCPserver_HACKPRINCENTON"], stream=False
        )
        print("Flask Server: Received tips response from Dedalus.")
        return result.final_output
    except Exception as e:
        print(f"Flask Server: Error calling Dedalus for tips: {e}")
        return "Sorry, I was unable to get tips at this time."


async def run_dedalus_routine(interest_topic: str):
    """
    Runs the Dedalus agent to generate a simple 7-day routine.
    """
    client = AsyncDedalus()
    runner = DedalusRunner(client)
    prompt_input = f"""
    A user wants to get 1% better at '{interest_topic}'. 
    Please generate a 7-day routine for them.
    Start with an introduction.
    For each day, start with a clear marker like 'Day 1 — [Title of the day]'.
    """
    print(f"Flask Server: Sending request for routine on '{interest_topic}'...")
    try:
        result = await runner.run(
            input=prompt_input, model="openai/gpt-5-mini",
            mcp_servers=["therickmj03/MCPserver_HACKPRINCENTON"], stream=False
        )
        print("Flask Server: Received routine response from Dedalus.")
        return result.final_output
    except Exception as e:
        print(f"Flask Server: Error calling Dedalus: {e}")
        return "Sorry, I was unable to generate a routine at this time."


# --- DEDALUS HELPER 3: CREATE PERSONALIZED PLAN (ADVANCED) ---
async def run_dedalus_personalized_plan(user_data: dict):
    """
    Generate a 7-day plan with clean sections and no stray bracket lines.
    """
    client = AsyncDedalus()
    runner = DedalusRunner(client)

    wake_time = user_data.get('wakeUpTime', '8:00 AM')
    sleep_time = user_data.get('sleepTime', '7:00 PM')

    prompt_input = f"""
    You are an elite performance coach. A user has provided their personal data.
    Create a 7-day "1% better" plan that is SHORT, ACTIONABLE, and fits inside their day.

    Follow the Principles of Atomic Habits:
    - Make it obvious: Create clear cues for your habits.
    - Make it attractive: Increase the appeal of your habits.
    - Make it easy: Simplify the process to encourage action.
    - Make it satisfying: Ensure that the outcome is rewarding.

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
    6. Keep each task concise (1–2 sentences) but useful (what + how).
    7. After Day 7, add "Personalized Tips:" and list 5–8 bullets tailored to their data.
    8. Do NOT include square brackets [], do NOT wrap tasks in parentheses.

    REQUIRED FORMAT (copy this structure, no extra characters):

    (Short introduction, 2–4 sentences...)

    Day 1:
    Morning:
    - 8:15 AM: Drink 300 ml water and eat a quick protein snack to stabilize energy.
    - 9:30 AM: Write your top 3 priorities for today and place them somewhere visible.
    - 11:00 AM: Do a 5-minute mobility routine for hips and shoulders.
    Afternoon:
    - 12:30 PM: Eat a balanced lunch (protein, vegetables, carbs) away from screens.
    - 3:00 PM: Do a 25–50 minute focused work block on your top priority.
    - 4:30 PM: Take a 10-minute walk or light mobility to reset.
    Evening:
    - 5:15 PM: Prepare or assemble a simple dinner (protein + veg).
    - 6:00 PM: Write one sentence about what went well and one fix for tomorrow.
    - 6:40 PM: Power down screens and dim lights to start your sleep routine.

    Day 2:
    (same structure as Day 1)

    ...
    Day 7:
    (same structure)

    Personalized Tips:
    - tip 1
    - tip 2
    - tip 3
    """

    try:
        result = await runner.run(
            input=prompt_input,
            model="openai/gpt-5-mini",
            stream=False
        )
        return result.final_output
    except Exception as e:
        print(f"Flask Server: Error calling Dedalus for personalized plan: {e}")
        return "Sorry, I was unable to generate a personalized plan at this time."



# async def run_dedalus_personalized_plan_chunk(user_data: dict, start_day: int, num_days: int):
#     """
#     Ask Dedalus for a partial plan, e.g. days 8–14, with the SAME structure
#     as the main 7-day generator: 3 tasks per Morning/Afternoon/Evening, with times.
#     """
#     client = AsyncDedalus()
#     runner = DedalusRunner(client)

#     prev_days_str = user_data.get("_already_generated_days", "")

#     prompt_input = f"""
#     You are an elite performance coach. A user has provided their personal data.
#     You will generate ONLY a slice of their plan.

#     USER DATA:
#     - Name: {user_data.get('name', 'N/A')}
#     - Age: {user_data.get('age', 'N/A')}
#     - Wakes Up: {user_data.get('wakeUpTime', 'N/A')}
#     - Sleeps: {user_data.get('sleepTime', 'N/A')}
#     - Eating Habits: {user_data.get('eatingHabits', 'N/A')}
#     - Exercise: {user_data.get('exerciseRoutine', 'N/A')}
#     - Focus Ability: {user_data.get('deepFocus', 'N/A')}
#     - Time Management: {user_data.get('timeManagement', 'N/A')}
#     - Notification Style: {user_data.get('notificationStyle', 'N/A')}

#     The user already has a plan for: {prev_days_str if prev_days_str else "none yet"}.
#     Do NOT regenerate any of those days.

#     TASK:
#     1. Generate ONLY days {start_day} through {start_day + num_days - 1}.
#     2. For EACH day, create three distinct, actionable tasks for Morning, Afternoon, and Evening.
#     3. ***CRITICAL***: Each task MUST start with a specific time personalized to their wake/sleep.
#        Use realistic times between {user_data.get('wakeUpTime', '8:00 AM')} and {user_data.get('sleepTime', '9:30 PM')}.
#     4. Keep it concise BUT fully informative — 2–3 short sentences per task is okay.
#     5. Do NOT add "Personalized Tips" here. Only the days.

#     REQUIRED FORMAT (copy this style):

#     Day {start_day}:
#     Morning:
#     - 8:00 AM: ...
#     - 9:30 AM: ...
#     - 11:00 AM: ...
#     Afternoon:
#     - 1:00 PM: ...
#     - 3:00 PM: ...
#     - 4:30 PM: ...
#     Evening:
#     - 6:30 PM: ...
#     - 7:30 PM: ...
#     - 8:30 PM: ...

#     Day {start_day + 1}:
#     (same structure)

#     Stop after Day {start_day + num_days - 1}.
#     """

#     try:
#         result = await runner.run(
#             input=prompt_input,
#             model="openai/gpt-5-mini",
#             stream=False
#         )
#         return result.final_output
#     except Exception as e:
#         print(f"Flask Server: Error calling Dedalus for chunk {start_day}-{start_day+num_days-1}: {e}")
#         return ""


# async def build_full_plan(user_data: dict, total_days: int = 21, chunk_size: int = 7):
#     """
#     Generate a multi-chunk plan: 1–7, 8–14, 15–21 ...
#     Returns a single dict: {"intro": "...", "days": [...], "tips": [...]}
#     """
#     all_days = []
#     intro_text = ""
#     all_tips = []

#     # we'll track which days we've made, to tell the model next time
#     already_generated_labels = []

#     for start in range(1, total_days + 1, chunk_size):
#         # how many days in this chunk?
#         this_chunk = min(chunk_size, total_days - start + 1)

#         # update user_data with what we already made, so it can go in the prompt
#         user_data["_already_generated_days"] = ", ".join(already_generated_labels)

#         raw_chunk = await run_dedalus_personalized_plan_chunk(user_data, start, this_chunk)
#         parsed_chunk = parse_personalized_plan(raw_chunk)  # reuse your existing parser

#         # first chunk can carry the intro, others usually won't
#         if start == 1 and parsed_chunk.get("intro"):
#             intro_text = parsed_chunk["intro"]

#         # merge days
#         for day_obj in parsed_chunk.get("days", []):
#             all_days.append(day_obj)
#             # remember that we now have "Day X"
#             already_generated_labels.append(f"Day {day_obj['day']}")

#         # collect tips if model emitted them
#         if parsed_chunk.get("tips"):
#             all_tips.extend(parsed_chunk["tips"])

#     # dedupe tips a little
#     seen = set()
#     unique_tips = []
#     for t in all_tips:
#         if t not in seen:
#             seen.add(t)
#             unique_tips.append(t)

#     return {
#         "intro": intro_text,
#         "days": all_days,
#         "tips": unique_tips
#     }


def parse_tips(raw_text: str) -> dict:
    """
    Parses a block of text containing bulleted tips into a
    structured list of strings.
    """
    lines = raw_text.strip().split('\n')
    tips_list = []
    for line in lines:
        cleaned_line = line.strip()
        # Remove leading bullets or common prefixes
        cleaned_line = re.sub(r'^(?:-\s*|Best tip\s*—\s*)', '', cleaned_line).strip()
        if cleaned_line:
            tips_list.append(cleaned_line)
    return {"tips": tips_list}


def parse_routine(raw_text: str) -> dict:
    """
    Parses the simple 7-day routine.
    """
    parts = re.split(r'\n(?=Day \d+ —)', raw_text)
    if len(parts) < 2: return {"intro": raw_text, "days": []}
    intro = parts[0].strip()
    day_chunks = parts[1:]
    days_list = []
    for chunk in day_chunks:
        lines = chunk.strip().split('\n')
        if not lines: continue
        title_line = lines[0].strip()
        content_lines = lines[1:]
        title_parts = title_line.split(' — ', 1)
        day_number_match = re.search(r'\d+', title_parts[0])
        if not day_number_match: continue
        day_number_str = day_number_match.group()
        day_object = {
            "day": int(day_number_str), 
            "title": title_parts[1].strip() if len(title_parts) > 1 else "Daily Task",
            "tasks": '\n'.join(line.strip() for line in content_lines if line.strip())
        }
        days_list.append(day_object)
    return {"intro": intro, "days": days_list}


def parse_personalized_plan(raw_text: str) -> dict:
    """
    An advanced parser for the hyper-personalized plan
    that now expects a list of tasks for each period.
    """
    plan = {"intro": "", "days": [], "tips": []}
    
    try:
        plan_text, tips_text = re.split(r'\nPersonalized Tips:\s*', raw_text, 1)
    except ValueError:
        plan_text = raw_text
        tips_text = ""

    if tips_text:
        plan["tips"] = [tip.strip().lstrip('- ') for tip in tips_text.strip().split('\n') if tip.strip()]

    day_matches = list(re.finditer(r'\nDay (\d+):\s*([\s\S]*?)(?=\nDay \d+:|\Z)', plan_text))
    
    if not day_matches:
        plan["intro"] = plan_text.strip()
        return plan

    plan["intro"] = plan_text.split("Day 1:", 1)[0].strip()
    
    for match in day_matches:
        day_number = int(match.group(1))
        day_content = match.group(2).strip()
        
        morning_match = re.search(r'Morning:([\s\S]*?)(?=\nAfternoon:|\nEvening:|\Z)', day_content, re.IGNORECASE)
        afternoon_match = re.search(r'Afternoon:([\s\S]*?)(?=\nEvening:|\Z)', day_content, re.IGNORECASE)
        evening_match = re.search(r'Evening:([\s\S]*)(\Z)', day_content, re.IGNORECASE)
        
        def clean_tasks(task_block):
            if not task_block:
                return []
            raw_string = task_block.group(1).strip()
            return [task.strip().lstrip('- ') for task in raw_string.split('\n') if task.strip()]

        plan["days"].append({
            "day": day_number,
            "morning": clean_tasks(morning_match),    
            "afternoon": clean_tasks(afternoon_match),  
            "evening": clean_tasks(evening_match)     
        })

    return plan


@app.route('/api/get-routine', methods=['POST'])
def get_routine_endpoint():
    data = request.json
    if not data or 'interest' not in data:
        return jsonify({"error": "Missing 'interest' in request body"}), 400
    interest = data['interest']
    try:
        raw_routine_text = asyncio.run(run_dedalus_routine(interest))
        structured_routine = parse_routine(raw_routine_text)
        return jsonify(structured_routine)
    except Exception as e:
        print(f"Flask Server: Error in asyncio: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500


@app.route('/api/get-tip', methods=['POST'])
def get_tip_endpoint():
    data = request.json
    if not data or 'interest' not in data:
        return jsonify({"error": "Missing 'interest' in request body"}), 400
    if 'difficulty' not in data:
        return jsonify({"error": "Missing 'difficulty' in request body"}), 400
    interest = data['interest']
    difficulty = data['difficulty']
    try:
        raw_tips_text = asyncio.run(run_dedalus_tip(interest, difficulty))
        structured_tips = parse_tips(raw_tips_text)
        return jsonify(structured_tips)
    except Exception as e:
        print(f"Flask Server: Error in asyncio: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500


@app.route('/api/create-personalized-plan', methods=['POST'])
def create_personalized_plan_endpoint():
    """
    This is the new API endpoint for the hyper-personalized plan.
    It accepts a large JSON body with all the user's data.
    """
    user_data = request.json
    if not user_data:
        return jsonify({"error": "Missing user data in request body"}), 400

    try:
        raw_plan_text = asyncio.run(run_dedalus_personalized_plan(user_data))
        
        structured_plan = parse_personalized_plan(raw_plan_text)
        
        return jsonify(structured_plan)
    
    except Exception as e:
        print(f"Flask Server: Error in asyncio for personalized plan: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# @app.route('/api/create-personalized-plan-full', methods=['POST'])
# def create_personalized_plan_full_endpoint():
#     user_data = request.json
#     if not user_data:
#         return jsonify({"error": "Missing user data in request body"}), 400

#     try:
#         # run the async builder
#         full_plan = asyncio.run(build_full_plan(user_data, total_days=21, chunk_size=7))
#         return jsonify(full_plan)
#     except Exception as e:
#         print(f"Flask Server: Error building full plan: {e}")
#         return jsonify({"error": "An internal server error occurred"}), 500

# @app.route('/api/create-personalized-plan-chunk', methods=['POST'])
# def create_personalized_plan_chunk_endpoint():
#     """
#     Body JSON example:
#     {
#       "user": { ... },            # whatever user_data you already send
#       "start_day": 1,
#       "num_days": 7,
#       "already_generated": ["Day 1","Day 2","Day 3"]   # optional
#     }
#     """
#     data = request.json
#     if not data:
#         return jsonify({"error": "Missing body"}), 400

#     user_data = data.get("user", {})
#     start_day = int(data.get("start_day", 1))
#     num_days = int(data.get("num_days", 7))

#     # pass what we already have back into the prompt so it doesn't repeat
#     already_generated = data.get("already_generated", [])
#     if already_generated:
#         user_data["_already_generated_days"] = ", ".join(already_generated)

#     try:
#         raw_chunk = asyncio.run(
#             run_dedalus_personalized_plan_chunk(user_data, start_day, num_days)
#         )
#         parsed = parse_personalized_plan(raw_chunk)
#         return jsonify(parsed)
#     except Exception as e:
#         print(f"Flask Server: error generating chunk: {e}")
#         return jsonify({"error": "Internal error"}), 500

# @app.route('/api/create-personalized-plan-week', methods=['POST'])
# def create_personalized_plan_week_endpoint():
#     data = request.json
#     if not data:
#         return jsonify({"error": "Missing body"}), 400

#     user_data = data.get("user", {})
#     week_number = int(data.get("week_number", 1))  # 1 = days 1–7, 2 = days 8–14, etc.

#     # figure out start/end days for this week
#     start_day = (week_number - 1) * 7 + 1
#     num_days = 7

#     # tell the model what days we *already* had (only for week > 1)
#     already_generated = []
#     if week_number > 1:
#         already_generated = [f"Day {d}" for d in range(1, start_day)]
#         user_data["_already_generated_days"] = ", ".join(already_generated)

#     try:
#         raw_chunk = asyncio.run(
#             run_dedalus_personalized_plan_chunk(user_data, start_day, num_days)
#         )
#         parsed = parse_personalized_plan(raw_chunk)
#         return jsonify(parsed)
#     except Exception as e:
#         print(f"Flask Server: error generating week {week_number}: {e}")
#         return jsonify({"error": "Internal error"}), 500

@app.route('/', methods=['GET'])
def health():
    return "API is running", 200


# if __name__ == '__main__':
#     app.run(
#         host='0.0.0.0',
#         port=8080,
#         ssl_context=('cert.pem', 'key.pem')
#     )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
