"""
IAE Equipment Schedule Builder

Upload manufacturer cut sheets, auto-extract specs via Claude, review/edit the
table, export a branded Excel schedule ready to place or data-link into AutoCAD.

Run locally:      streamlit run app.py
Deploy:            see README.md (Streamlit Community Cloud)
"""

import streamlit as st
import pandas as pd

from schema import DISCIPLINES
from extraction import extract_text_from_pdf, extract_equipment_data
from excel_export import build_schedule_workbook

st.set_page_config(page_title="IAE Equipment Schedule Builder", layout="wide")

IAE_MAROON = "#5F3844"
IAE_ALT_ROW = "#F5EDEF"

st.markdown(
    f"""
    <style>
    .iae-banner {{
        background-color: {IAE_MAROON};
        color: white;
        padding: 14px 20px;
        font-size: 22px;
        font-weight: 700;
        border-radius: 4px;
        margin-bottom: 20px;
    }}
    </style>
    <div class="iae-banner">Inglese Architecture + Engineering — Equipment Schedule Builder</div>
    """,
    unsafe_allow_html=True,
)

# --- API key: pulled from deployment secrets, never entered by end users ---
api_key = st.secrets.get("ANTHROPIC_API_KEY", None)
if not api_key:
    st.error(
        "No Anthropic API key configured. The app owner needs to set ANTHROPIC_API_KEY "
        "in the Streamlit secrets (see README.md)."
    )
    st.stop()

if "rows" not in st.session_state:
    st.session_state.rows = []

# --- Sidebar: project + discipline ---
with st.sidebar:
    st.header("Project")
    project_name = st.text_input("Project Name", value="")
    project_no = st.text_input("IAE Project No.", value="")
    discipline = st.selectbox("Discipline", list(DISCIPLINES.keys()), index=0)
    columns = DISCIPLINES[discipline]

    st.divider()
    if st.button("Clear all rows", use_container_width=True):
        st.session_state.rows = []
        st.rerun()

st.subheader(f"1. Add Equipment — {discipline}")

with st.form("add_equipment_form", clear_on_submit=True):
    col1, col2 = st.columns([1, 2])
    with col1:
        tag_input = st.text_input("Equipment Tag (e.g. AHU-1, RTU-3)", value="")
    with col2:
        cut_sheet = st.file_uploader("Cut Sheet (PDF)", type=["pdf"], key="uploader")
    submitted = st.form_submit_button("Extract & Add to Schedule", type="primary")

if submitted:
    if not cut_sheet:
        st.warning("Upload a cut sheet PDF before extracting.")
    else:
        with st.spinner(f"Reading cut sheet and extracting specs for {tag_input or 'this unit'}..."):
            try:
                text = extract_text_from_pdf(cut_sheet.read())
                if not text.strip():
                    st.error(
                        "Couldn't extract any text from this PDF — it may be a scanned image. "
                        "Try an OCR'd version, or enter the specs manually below."
                    )
                else:
                    data = extract_equipment_data(text, columns, api_key, tag_hint=tag_input)
                    st.session_state.rows.append(data)
                    st.success(f"Added {data.get('tag', tag_input or 'equipment')} to the schedule.")
            except Exception as e:
                st.error(f"Extraction failed: {e}")

st.subheader("2. Review & Edit Schedule")

if st.session_state.rows:
    df = pd.DataFrame(st.session_state.rows)
    # Ensure all schema columns exist and are ordered correctly
    col_keys = [c["key"] for c in columns]
    col_labels = {c["key"]: c["label"] for c in columns}
    for k in col_keys:
        if k not in df.columns:
            df[k] = ""
    df = df[col_keys].rename(columns=col_labels)

    edited_df = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        key="schedule_editor",
    )

    st.subheader("3. Export")
    schedule_title = f"{discipline.split(' (')[0]} Equipment Schedule"
    if project_name:
        schedule_title = f"{project_name} — {schedule_title}"

    export_rows = edited_df.rename(columns={v: k for k, v in col_labels.items()}).to_dict("records")
    xlsx_bytes = build_schedule_workbook(export_rows, columns, title=schedule_title)

    st.download_button(
        "Download Branded Excel Schedule",
        data=xlsx_bytes,
        file_name=f"{(project_no or 'IAE')}_{discipline.split(' ')[0]}_Equipment_Schedule.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
    st.caption(
        "Open in Excel, then use AutoCAD's Insert → OLE Object (or Data Link → Table) "
        "to place it on your drawing sheet."
    )
else:
    st.info("No equipment added yet. Upload a cut sheet above to get started.")
