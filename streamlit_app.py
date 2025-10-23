import streamlit as st
import openai
import base64
import json
import io
from PIL import Image
from datetime import datetime

# --- Configure page ---
st.set_page_config(page_title="Calibration Extractor", layout="centered")
st.title("📊 Calibration Screenshot → Report Generator")

# --- Load OpenAI API key from Streamlit secrets ---
openai.api_key = st.secrets["openai"]["api_key"]

# --- File upload ---

# --- Load sample image from project folder ---
sample_image_path = "assets/sample_calibration.png"  # path relative to your streamlit_app.py

try:
    # Open image
    image = Image.open(sample_image_path).convert("RGB")
    
    # Display image in Streamlit
    st.image(image, caption="Sample Calibration Screenshot", use_container_width=True)

    # Encode image to base64 for OpenAI API
    img_buffer = io.BytesIO()
    image.save(img_buffer, format="PNG")
    img_str = base64.b64encode(img_buffer.getvalue()).decode("utf-8")

except Exception as e:
    st.error(f"❌ Could not load sample image: {e}")
    st.stop()


# --- Process with OpenAI ---
if st.button("🔍 Extract Calibration Data"):
    with st.spinner("Analyzing image with OpenAI Vision..."):
        try:
            client = openai.OpenAI(api_key=openai.api_key)

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a vision assistant that analyzes calibration screenshots "
                        "from X-ray or radiography QA systems. Extract all calibration parameters "
                        "and output them as structured JSON. Fields: kV, Dose, Dose rate, "
                        "Dose per frame, HVL, Exposure time, Sensor, Trigger level, "
                        "Exposure number, Serial number, Exposure date/time."
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract calibration values in JSON format."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_str}"}}
                    ]
                }
            ]

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.1,
                max_tokens=1000
            )

            raw_output = response.choices[0].message.content

        except Exception as e:
            st.error(f"❌ OpenAI API call failed: {e}")
            st.stop()

    # --- Display results ---
    st.subheader("🧾 Raw Model Output")
    st.text_area("Response", raw_output, height=250)

    # Try parsing JSON
    parsed = None
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", raw_output, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except Exception:
                parsed = None

    if parsed:
        st.subheader("✅ Extracted Calibration Data")
        st.json(parsed)

        # --- Generate simple text report ---
        report_lines = [
            "# Calibration Report",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Extracted Values"
        ]

        main_keys = ["kV", "Dose", "Dose rate", "Dose per frame", "HVL", "Exposure time"]
        for k in main_keys:
            v = parsed.get(k)
            if v:
                report_lines.append(f"- **{k}:** {v}")

        report_lines.append("")
        report_lines.append("## Metadata")
        meta_keys = ["Sensor", "Trigger level", "Exposure number", "Serial number", "Exposure date/time"]
        for k in meta_keys:
            v = parsed.get(k)
            if v:
                report_lines.append(f"- **{k}:** {v}")

        report_text = "\n".join(report_lines)

        st.subheader("📋 Generated Report")
        st.markdown(report_text)

        # Download button
        b64 = base64.b64encode(report_text.encode()).decode()
        href = f'<a href="data:text/plain;base64,{b64}" download="calibration_report.txt">📥 Download Report</a>'
        st.markdown(href, unsafe_allow_html=True)
    else:
        st.error("⚠️ Could not parse JSON from model output.")
