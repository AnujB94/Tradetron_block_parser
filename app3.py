import streamlit as st
import json
import yaml
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
                    "ONLY output valid JSON. No comments, no text, no trailing commas.\n"
                    "Must match this schema:\n"
                    f"{schema}"
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

    cleaned = raw[raw.index("{") : raw.rindex("}") + 1]
    return json.loads(cleaned)


# --------------------------
# Extract YAML for conditions
# --------------------------
def extract_condition_yaml(condition):
    """
    Expected:
    condition = {
      "logic": "AND",
      "rules": [
         { "left": {...}, "operator": "=", "right": {...} }
      ]
    }
    """
    rule = condition["rules"][0]

    transformed = {
        "left": rule["left"],
        "operator": rule["operator"],
        "right": rule["right"]
    }

    return yaml.safe_dump(transformed, sort_keys=False)


# --------------------------
# Extract YAML for positions
# --------------------------
def extract_positions_yaml(positions):
    """
    Positions is already a list of objects
    """
    return yaml.safe_dump(positions, sort_keys=False)


# --------------------------
# STREAMLIT UI
# --------------------------
st.set_page_config(layout="wide")
st.title("📘 Strategy YAML Visualizer")

schema = load_schema()
prompt = st.text_area("Enter strategy instruction")
run = st.button("Convert to YAML")

if run:

    with st.spinner("Generating JSON using LLM..."):
        raw = llm(schema, prompt)
        try:
            data = safe_parse_json(raw)
        except Exception as e:
            st.error(f"JSON parsing failed: {e}")
            st.code(raw, language="json")
            st.stop()

    st.success("JSON Parsed Successfully!")

    sets = data.get("sets", [])

    st.header("📄 Output Sets")

    for i, s in enumerate(sets):
        st.subheader(f"### Set {i} → Type: **{s.get('type', 'Unknown')}**")

        # ---- CONDITIONS YAML ----
        if "conditions" in s and s["conditions"]:
            condition_yaml = extract_condition_yaml(s["conditions"][0])

            st.markdown("#### 🟦 Conditions (YAML)")
            st.code(condition_yaml, language="yaml")

        # ---- POSITIONS YAML ----
        if "positions" in s:
            positions_yaml = extract_positions_yaml(s["positions"])

            st.markdown("#### 🟩 Positions (YAML)")
            st.code(positions_yaml, language="yaml")
