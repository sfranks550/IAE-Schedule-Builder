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
st.caption(
    "Upload one or more cut sheet PDFs at once. Each file's name is used as the "
    "equipment tag hint (a file named CC-1.pdf is tagged CC-1) — you can always "
    "fix tags afterward in the editable table below."
)

with st.form("add_equipment_form", clear_on_submit=True):
    cut_sheets = st.file_uploader(
        "Cut Sheets (PDF) — select multiple files",
        type=["pdf"],
        accept_multiple_files=True,
        key="uploader",
    )
    submitted = st.form_submit_button("Extract & Add to Schedule", type="primary")

if submitted:
    if not cut_sheets:
        st.warning("Upload at least one cut sheet PDF before extracting.")
    else:
        progress = st.progress(0.0, text="Starting...")
        added = []
        failed = []
        total = len(cut_sheets)
        for i, cut_sheet in enumerate(cut_sheets):
            tag_hint = cut_sheet.name.rsplit(".", 1)[0].strip()
            progress.progress(i / total, text="Reading " + cut_sheet.name + "...")
            try:
                text = extract_text_from_pdf(cut_sheet.read())
                if not text.strip():
                    failed.append(cut_sheet.name + " - no extractable text (likely a scanned image)")
                    continue
                data = extract_equipment_data(text, columns, api_key, tag_hint=tag_hint)
                st.session_state.rows.append(data)
                added.append(data.get("tag", tag_hint))
            except Exception as e:
                failed.append(cut_sheet.name + " - " + str(e))
        progress.progress(1.0, text="Done.")
        progress.empty()

        if added:
            st.success("Added " + str(len(added)) + " unit(s) to the schedule: " + ", ".join(added))
        if failed:
            st.error("Some files could not be processed:\n\n" + "\n".join("- " + f for f in failed))

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
    discipline_short = discipline.split(" (")[0]
    schedule_title = discipline_short + " Equipment Schedule"
    if project_name:
        schedule_title = project_name + " — " + schedule_title

    export_rows = edited_df.rename(columns={v: k for k, v in col_labels.items()}).to_dict("records")
    xlsx_bytes = build_schedule_work