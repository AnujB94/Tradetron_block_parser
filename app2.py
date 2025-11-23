import streamlit as st
import pandas as pd
import json
from groq import Groq
from dotenv import load_dotenv
import os
from json_to_yaml import convert_json_to_text

load_dotenv()

SCHEMA_PATH = "schemas/test_schemav2.json"

def load_schema():
    try:
        with open(SCHEMA_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading schema from {SCHEMA_PATH}: {e}")
        st.stop()

def llm(schema, prompt):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error("GROQ_API_KEY not found in environment variables.")
        st.stop()

    client = Groq(api_key=api_key)

    system_rules = """
    CRITICAL RULES:
    1. DEFAULT CONDITION: If the user DOES NOT specify an explicit entry condition (e.g., they just say "Buy Call"), you MUST generate this default condition:
       LTP(Underlying Instrument) > 0.
       Do NOT generate "1 >= 1" or empty groups.
    
    2. OFFSET PARSING:
       - If user says "ATM+2" or "2 strikes OTM", set 'selection_method': 'ATM' and 'offset': 2.
       - If user says "ATM-1", set 'selection_method': 'ATM' and 'offset': -1.
       - If user says "ITM", set 'selection_method': 'ITM' (or offset as appropriate).

    3. STRANGLE / OTM LOGIC (VERY IMPORTANT):
       - If the user asks for a "Strangle" or mentions "+/- X strikes" (e.g. "+-2"):
         - The CALL option MUST have a POSITIVE offset (e.g., offset: 2).
         - The PUT option MUST have a NEGATIVE offset (e.g., offset: -2).
       - Never use the same positive offset for both legs in a Strangle.
    """
    completion = client.chat.completions.create(
        model="openai/gpt-oss-20b", # Ensure this model is available in your Groq tier
        messages=[
            {
                "role": "user",
                "content": (
                    "You are a JSON converter for trading strategies.\n"
                    "You are a trading strategy assistant. Output ONLY valid JSON.\n"
                    f"{system_rules}\n"
                    "Convert user instructions into JSON blocks conforming to this schema:\n"
                    f"{schema}"
                )
            },
            {
                "role": "user",
                "content": (
                    "CRITICAL: Output ONLY the raw, complete, and valid JSON object for the following strategy. "
                    "DO NOT include any explanation, markdown formatting (like ```json), or extra text before or after the JSON."
                )
            },
            {
                "role": "user",
                "content": "Now convert the following input into JSON. And only give the final json nothing else:"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,
        max_completion_tokens=4096,
        top_p=1,
    )

    return completion.choices[0].message.content

st.set_page_config(page_title="Strategy JSON Visualizer", layout="wide")

st.title("Trading Strategy JSON Visualizer")
st.caption(f"Using schema: `{SCHEMA_PATH}`")

# Load schema now
schema = load_schema()

# Create layout
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Input")
    prompt = st.text_area("Enter strategy instruction", height=150, placeholder="e.g. Buy Nifty ATM Call if Time > 9:30")
    run = st.button("Convert to JSON")

if run:
    if not prompt.strip():
        st.error("Please enter a strategy instruction.")
        st.stop()

    with st.spinner("🔄 Generating Output"):
        try:
            raw_json_output = llm(schema, prompt)
            parsed_data = json.loads(raw_json_output)
            
            # --- CONVERSION STEP ---
            readable_text = convert_json_to_text(parsed_data)
            
        except Exception as e:
            st.error(f"Error generating or parsing JSON: {e}")
            if 'raw_json_output' in locals():
                with st.expander("See Raw Output"):
                    st.code(raw_json_output, language="json")
            st.stop()

    st.success("✔ Generated successfully!")

    # Show Readable Text in the second column
    with col2:
        st.subheader("Output")
        st.code(readable_text, language="yaml")
        
        with st.expander("View Raw JSON"):
            st.json(parsed_data)