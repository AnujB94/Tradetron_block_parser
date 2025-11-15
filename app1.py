import streamlit as st
import pandas as pd
import json
from groq import Groq
import json5


SCHEMA_PATH = "schemas/test_schema.json"

def load_schema():
    with open(SCHEMA_PATH, "r") as f:
        return json.load(f)


def llm(schema, prompt):
    client = Groq(api_key="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")

    completion = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": (
                    "ONLY output valid JSON. No comments. No extra text.\n"
                    f"Schema:\n{schema}"
                )
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.0
    )

    return completion.choices[0].message.content.strip()


def safe_parse_json(raw):
    try:
        return json.loads(raw)
    except:
        pass

    try:
        return json5.loads(raw)
    except:
        pass

    try:
        cleaned = raw[raw.index("{"): raw.rindex("}") + 1]
        return json.loads(cleaned)
    except:
        raise ValueError("Invalid JSON")


def flatten_section(title, data):
    st.markdown(f"### `{title}`")

    try:
        df = pd.json_normalize(data, max_level=4)
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.warning(f"Cannot flatten `{title}`: {e}")


# --- Streamlit UI ---
st.set_page_config(layout="wide")
st.title("📊 Trading Strategy JSON Visualizer")
schema = load_schema()

prompt = st.text_area("Enter strategy instruction")
run = st.button("Convert to JSON")

if run:
    with st.spinner("Generating JSON..."):
        raw = llm(schema, prompt)

        try:
            parsed = safe_parse_json(raw)
        except Exception as e:
            st.error(f"JSON Error: {e}")
            st.code(raw)
            st.stop()

    st.success("JSON Parsed!")

    st.subheader("🧩 Full JSON Output")
    st.json(parsed)

    st.subheader("📘 Table View")

    if "sets" not in parsed:
        st.warning("No sets found.")
        st.stop()

    # --- Table 1: sets ---
    flatten_section("sets", parsed["sets"])

    # Drill down inside each set
    for i, s in enumerate(parsed["sets"]):

        # --- Table 2: conditions ---
        if "conditions" in s:
            flatten_section(f"sets[{i}].conditions", s["conditions"])

            # drill to rule level
            for j, cond in enumerate(s["conditions"]):
                if "rules" in cond:
                    flatten_section(
                        f"sets[{i}].conditions[{j}].rules",
                        cond["rules"]
                    )

        # --- Table 3: positions ---
        if "positions" in s:
            flatten_section(f"sets[{i}].positions", s["positions"])
