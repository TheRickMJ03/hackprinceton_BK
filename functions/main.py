import asyncio
import os
import re  
from flask import Flask, request, jsonify
from flask_cors import CORS
from dedalus_labs import AsyncDedalus, DedalusRunner
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

def parse_tips(raw_text: str) -> dict:

    lines = raw_text.strip().split('\n')
    
    tips_list = []
    for line in lines:
    
        cleaned_line = line.strip()
        

        cleaned_line = re.sub(r'^(?:-\s*|Best tip\s*—\s*)', '', cleaned_line).strip()
        
        if cleaned_line:
            tips_list.append(cleaned_line)
            
    return {"tips": tips_list}

def parse_routine(raw_text: str) -> dict:
    
    parts = re.split(r'\n(?=Day \d+ —)', raw_text)
    
    if not parts:
        return {"intro": raw_text, "days": []}

    intro = parts[0].strip() 
    day_chunks = parts[1:]  
    
    days_list = []
    
    for chunk in day_chunks:
        lines = chunk.strip().split('\n')
        
        if not lines:
            continue
            
        title_line = lines[0].strip() 
        content_lines = lines[1:]
        
        title_parts = title_line.split(' — ', 1)
        
        day_number_str = re.search(r'\d+', title_parts[0]).group()
        
        day_object = {
            "day": int(day_number_str), 
            "title": title_parts[1].strip() if len(title_parts) > 1 else "",
            "tasks": '\n'.join(line.strip() for line in content_lines if line.strip())
        }
        days_list.append(day_object)
        
    return {"intro": intro, "days": days_list}

async def run_dedalus_tip(interest_topic: str, difficulty_level: str):
   
    client = AsyncDedalus()
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
    

async def run_dedalus_routine(interest_topic: str):
   
    client = AsyncDedalus()
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

# --- 3. UPDATED API ENDPOINT FOR TIPS ---
@app.route('/api/get-tip', methods=['POST'])
def get_tip_endpoint():
    """
    This is the updated API endpoint for getting MULTIPLE tips.
    App sends: { "interest": "swimming", "difficulty": "beginner" }
    """
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


if __name__ == '__main__':
    app.run(debug=True, port=5000)