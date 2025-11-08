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
            input=prompt_input, model="openai/gpt-5-mini",
            mcp_servers=["therickmj03/MCPserver_HACKPRINCENTON"], stream=False
        )
        print("Flask Server: Received tips response from Dedalus.")
        return result.final_output
    except Exception as e:
        print(f"Flask Server: Error calling Dedalus for tips: {e}")
        return "Sorry, I was unable to get tips at this time."


async def run_dedalus_routine(interest_topic: str):
    """
    Runs the Dedalus agent to generate a simple 21-day routine.
    """
    client = AsyncDedalus()
    runner = DedalusRunner(client)
    prompt_input = f"""
    A user wants to get 1% better at '{interest_topic}'. 
    Please generate a 21-day routine for them.
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
    Runs the Dedalus agent to GENERATE a hyper-personalized plan
    with 3 tasks per period, including specific times.
    """
    client = AsyncDedalus()
    runner = DedalusRunner(client)

    prompt_input = f"""
    You are an elite performance coach. A user has provided their personal data. 
    Your task is to create a hyper-personalized 21-day "1% better" plan to help 
    them improve their life, built around their specific schedule and habits.

    USER DATA:
    - Name: {user_data.get('name', 'N/A')}
    - Age: {user_data.get('age', 'N/A')}
    - Wakes Up: {user_data.get('wakeUpTime', 'N/A')}
    - Sleeps: {user_data.get('sleepTime', 'N/A')}
    - Eating Habits: {user_data.get('eatingHabits', 'N/A')}
    - Exercise: {user_data.get('exerciseRoutine', 'N/A')}
    - Focus Ability: {user_data.get('deepFocus', 'N/A')}
    - Time Management: {user_data.get('timeManagement', 'N/A')}
    - Notification Style: {user_data.get('notificationStyle', 'N/A')}

    TASK:
    1.  Write a brief, motivating introduction.
    2.  Generate a 21-day plan. For each day, create three distinct, actionable
        tasks for "Morning", "Afternoon", and "Evening".
    3.  ***CRITICAL***: Each task MUST start with a specific time 
        (e.g., "9:00 AM: ...", "3:30 PM: ...") that is personalized 
        to their sleep/wake schedule.
    4.  After the 21-day plan, provide a list of 5-7 "Personalized Tips"
        based on their specific data.

    REQUIRED FORMAT:
    (Introduction text...)

    Day 1:
    Morning:
    - 9:00 AM: (Task 1...)
    - 10:30 AM: (Task 2...)
    - 11:45 AM: (Task 3...)
    Afternoon:
    - 1:30 PM: (Task 1...)
    - 3:00 PM: (Task 2...)
    - 4:30 PM: (Task 3...)
    Evening:
    - 7:00 PM: (Task 1...)
    - 9:30 PM: (Task 2...)
    - 12:30 AM: (Task 3...)

    Day 2:
    (Repeat the same structure...)

    (...and so on for 21 days...)

    Personalized Tips:
    - (Tip 1...)
    - (Tip 2...)
    - (Tip 3...)
    """
    
    print(f"Flask Server: Sending request to Dedalus for personalized plan for {user_data.get('name')}...")
    
    try:
        result = await runner.run(
            input=prompt_input,
            model="openai/gpt-5-mini",
            stream=False
        )
        print("Flask Server: Received personalized plan from Dedalus.")
        return result.final_output
    except Exception as e:
        print(f"Flask Server: Error calling Dedalus for personalized plan: {e}")
        return "Sorry, I was unable to generate a personalized plan at this time."


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
    Parses the simple 21-day routine.
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



if __name__ == '__main__':
    app.run(debug=True, port=8080)