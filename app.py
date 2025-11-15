import streamlit as st
import pandas as pd
import json
from groq import Groq
import os

# --------------------------
# Load Schema Automatically
# --------------------------
SCHEMA_PATH = "schemas/test_schema.json"

def load_schema():
    try:
        with open(SCHEMA_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"❌ Error loading schema from {SCHEMA_PATH}: {e}")
        st.stop()


# --------------------------
# LLM CALL
# --------------------------
def llm(schema, prompt):
    client = Groq(api_key="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")

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


# --------------------------
# STREAMLIT UI
# --------------------------
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

    # --------------------------
    # Table Views for List Sections
    # --------------------------
    st.subheader("📘 Table View")

    list_keys = [k for k, v in parsed_data.items() if isinstance(v, list)]

    if not list_keys:
        st.info("ℹ No list-type sections found (like legs, rules, conditions).")
    else:
        for key in list_keys:
            st.markdown(f"### `{key}`")

            try:
                df = pd.DataFrame(parsed_data[key])
                st.dataframe(df, use_container_width=True)

            except Exception:
                st.warning(f"Could not convert `{key}` to a table — maybe it's nested or not a list of objects.")
