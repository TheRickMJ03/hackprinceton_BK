import asyncio
import os
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from dedalus_labs import AsyncDedalus, DedalusRunner

# --- SETUP ---
# Get the API key from the server's environment variable
# We will set this in the Firebase website
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

app = Flask(__name__)
CORS(app)


# --- DEDALUS HELPER 1: GET TIP ---
async def run_dedalus_tip(interest_topic: str, difficulty_level: str):
    # Pass the key to the client
    client = AsyncDedalus(openai_api_key=OPENAI_API_KEY)
    runner = DedalusRunner(client)
    prompt_input = f"""
    A user wants 5 short, single-sentence tips for '{interest_topic}'
    at a '{difficulty_level}' level.
    Please list them. Start each tip with a bullet point '- '.
    Do not add any extra introduction or conclusion.
    """
    print(f"Flask Server: Sending request to Dedalus for 5 tips on '{interest_topic}'...")
    try:
        result = await runner.run(
            input=prompt_input,
            model="openai/gpt-5-mini",
            mcp_servers=["therickmj03/MCPserver_HACKPRINCENTON"],
            stream=False
        )
        print("Flask Server: Received tips response from Dedalus.")
        return result.final_output
    except Exception as e:
        print(f"Flask Server: Error calling Dedalus for tips: {e}")
        return "Sorry, I was unable to get tips at this time."


# --- DEDALUS HELPER 2: GET ROUTINE ---
async def run_dedalus_routine(interest_topic: str):
    # Pass the key to the client
    client = AsyncDedalus(openai_api_key=OPENAI_API_KEY)
    runner = DedalusRunner(client)
    prompt_input = f"""
    A user wants to get 1% better at '{interest_topic}'. 
    Please generate a 21-day routine for them.
    Start with an introduction.
    For each day, start with a clear marker like 'Day 1 — [Title of the day]'.
    """
    print(f"Flask Server: Sending request to Dedalus for '{interest_topic}'...")
    try:
        result = await runner.run(
            input=prompt_input,
            model="openai/gpt-5-mini",
            mcp_servers=["therickmj03/MCPserver_HACKPRINCENTON"],
            stream=False
        )
        print("Flask Server: Received response from Dedalus.")
        return result.final_output
    except Exception as e:
        print(f"Flask Server: Error calling Dedalus: {e}")
        return "Sorry, I was unable to generate a routine at this time."


# --- PARSER 1: PARSE TIPS ---
def parse_tips(raw_text: str) -> dict:
    lines = raw_text.strip().split('\n')
    tips_list = []
    for line in lines:
        cleaned_line = line.strip()
        cleaned_line = re.sub(r'^(?:-\s*|Best tip\s*—\s*)', '', cleaned_line).strip()
        if cleaned_line:
            tips_list.append(cleaned_line)
    return {"tips": tips_list}


# --- PARSER 2: PARSE ROUTINE ---
def parse_routine(raw_text: str) -> dict:
    parts = re.split(r'\n(?=Day \d+ —)', raw_text)
    if len(parts) < 2:
        return {"intro": raw_text, "days": []}
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


# --- API ENDPOINT 1: GET ROUTINE ---
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


# --- API ENDPOINT 2: GET TIP ---
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


# --- RUN THE SERVER ---
# This block lets you test locally with `python app.py`
# The deployed server will use the `gunicorn` command from the Dockerfile
if __name__ == '__main__':
    app.run(debug=True, port=8080)