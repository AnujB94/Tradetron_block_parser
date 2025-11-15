import streamlit as st
import json
import yaml
from groq import Groq
import json5

# ------------------------------------------------
# CONFIG
# ------------------------------------------------
SCHEMA_PATH = "schemas/test_schema.json"
API_KEY = "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"


# ------------------------------------------------
# LOAD SCHEMA
# ------------------------------------------------
def load_schema():
    with open(SCHEMA_PATH, "r") as f:
        return json.load(f)


# ------------------------------------------------
# LLM: GENERATE JSON
# ------------------------------------------------
def llm_generate(schema, prompt):
    client = Groq(api_key=API_KEY)

    completion = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": (
                    "ONLY output valid JSON. No comments. No text. No explanations.\n"
                    "It MUST strictly match this schema:\n"
                    f"{schema}"
                )
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.0
    )

    return completion.choices[0].message.content.strip()


# ------------------------------------------------
# LLM: VALIDATE JSON
# ------------------------------------------------
def llm_validate(schema, json_text):
    client = Groq(api_key=API_KEY)

    validation_prompt = f"""
You must validate the JSON against the schema.

Schema:
{schema}

JSON:
{json_text}

Respond ONLY with:
VALID
or
INVALID
"""

    completion = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": validation_prompt}],
        temperature=0.0
    )

    return completion.choices[0].message.content.strip()


# ------------------------------------------------
# AUTO-RETRY GENERATION UNTIL VALID
# ------------------------------------------------
def generate_valid_json(schema, prompt, max_attempts=3):
    for attempt in range(max_attempts):

        raw = llm_generate(schema, prompt)
        verdict = llm_validate(schema, raw)

        if verdict.upper().strip() == "VALID":
            return raw  # Success

        # Regenerate with instructive correction
        regenerate_prompt = f"""
The JSON you generated was INVALID.
Regenerate a NEW JSON that matches the schema exactly.
Output ONLY JSON.

Schema:
{schema}

Original request:
{prompt}
"""

        raw = llm_generate(schema, regenerate_prompt)
        verdict = llm_validate(schema, raw)

        if verdict.upper().strip() == "VALID":
            return raw

    raise ValueError("Model failed to generate valid JSON after several attempts.")


# ------------------------------------------------
# JSON SAFEPARSER
# ------------------------------------------------
def safe_parse_json(raw):
    # Try strict first
    try:
        return json.loads(raw)
    except:
        pass

    # Try relaxed JSON5
    try:
        return json5.loads(raw)
    except:
        pass

    # Extract substring between { ... }
    try:
        cleaned = raw[raw.index("{") : raw.rindex("}") + 1]
        return json.loads(cleaned)
    except:
        pass

    raise ValueError("INVALID JSON (unable to repair)")


# ------------------------------------------------
# YAML BUILDERS
# ------------------------------------------------
def extract_condition_yaml(condition):
    """
    We remove logic/rules and flatten:
    left
    operator
    right
    """
    rule = condition["rules"][0]

    transformed = {
        "left": rule["left"],
        "operator": rule["operator"],
        "right": rule["right"]
    }

    return yaml.safe_dump(transformed, sort_keys=False)


def extract_positions_yaml(positions):
    return yaml.safe_dump(positions, sort_keys=False)


# ------------------------------------------------
# STREAMLIT UI
# ------------------------------------------------
st.set_page_config(layout="wide")
st.title("📘 Strategy to Block Converter")

schema = load_schema()
prompt = st.text_area("Enter strategy instruction")
run = st.button("Convert")

if run:

    with st.spinner("Generating & Validating JSON using LLM..."):
        try:
            raw = generate_valid_json(schema, prompt)
            data = safe_parse_json(raw)
        except Exception as e:
            st.error(f"❌ Failed after multiple attempts: {e}")
            st.code(raw, language="json")
            st.stop()

    st.success("✔ Valid JSON generated!")

    sets = data.get("sets", [])

    st.header("📄 Output Sets")

    for i, s in enumerate(sets):
        st.subheader(f"Set {i} → Type: **{s.get('type', 'Unknown')}**")

        # ---- CONDITIONS YAML ----
        if "conditions" in s and s["conditions"]:
            condition_yaml = extract_condition_yaml(s["conditions"][0])
            st.markdown("#### 🟦 Conditions")
            st.code(condition_yaml, language="yaml")

        # ---- POSITIONS YAML ----
        if "positions" in s:
            positions_yaml = extract_positions_yaml(s["positions"])
            st.markdown("#### 🟩 Positions")
            st.code(positions_yaml, language="yaml")
