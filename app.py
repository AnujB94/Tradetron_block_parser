import streamlit as st
import pandas as pd
import json
from groq import Groq
from dotenv import load_dotenv
import os

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
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    completion = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "user",
                "content": (
                    "You are a JSON converter for trading strategies.\n"
                    "Convert user instructions into JSON blocks conforming to this schema:\n"
                    f"{schema}"
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

st.title("📊 Trading Strategy JSON Visualizer")
st.caption(f"Using schema: `{SCHEMA_PATH}`")

# Load schema now
schema = load_schema()

# User Input
prompt = st.text_area("Enter strategy instruction", height=120)
run = st.button("Convert to JSON")

if run:

    if not prompt.strip():
        st.error("Please enter a strategy instruction.")
        st.stop()

    with st.spinner("🔄 Generating JSON using LLM..."):
        try:
            raw_json_output = llm(schema, prompt)
            parsed_data = json.loads(raw_json_output)
        except Exception as e:
            st.error(f"❌ Error generating or parsing JSON: {e}")
            st.code(raw_json_output, language="json")
            st.stop()

    st.success("✔ JSON generated successfully!")

    # --------------------------
    # Pretty JSON Viewer
    # --------------------------
    st.subheader("🧩 Full JSON Output")
    st.json(parsed_data)