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
from drawing_lookup import render_pdf_pages, find_tag_locations

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

has_location_col = any(c["key"] == "location_served" for c in columns)

if has_location_col and st.session_state.rows:
    st.subheader("2. Auto-Fill Locations from Drawing Set (optional)")
    st.caption(
        "Upload the full floor plan drawing set (one PDF, all sheets). Claude will scan "
        "every sheet for each equipment tag currently in your schedule and fill in the "
        "room/area name it finds printed next to that tag's callout. This only fills in "
        "blank Location fields — anything you've already typed or edited is left alone. "
        "Treat results as a starting point and double-check against the plans."
    )
    drawing_set = st.file_uploader("Drawing Set (PDF)", type=["pdf"], key="drawing_set_uploader")

    if st.button("Find Locations for All Tags", disabled=not drawing_set):
        blank_tag_rows = [
            r for r in st.session_state.rows
            if r.get("tag") and not r.get("location_served")
        ]
        if not blank_tag_rows:
            st.info("Every row already has a location filled in — nothing to look up.")
        else:
            tags_to_find = [r["tag"] for r in blank_tag_rows]
            with st.spinner("Rendering drawing sheets..."):
                pages = render_pdf_pages(drawing_set.read())

            progress = st.progress(0.0, text="Searching sheets...")

            def _on_progress(batch_i, total_batches, found_count):
                pct = batch_i / total_batches if total_batches else 1.0
                progress.progress(
                    pct,
                    text=f"Searched {batch_i}/{total_batches} sheet batches — {found_count} tag(s) located so far...",
                )

            try:
                found = find_tag_locations(pages, tags_to_find, api_key, progress_callback=_on_progress)
            except Exception as e:
                found = {}
                st.error(f"Drawing lookup failed: {e}")
            progress.empty()

            if found:
                for r in st.session_state.rows:
                    if r.get("tag") in found and not r.get("location_served"):
                        r["location_served"] = found[r["tag"]]
                st.success(f"Filled in {len(found)} location(s): " + ", ".join(f"{t} → {loc}" for t, loc in found.items()))

            not_found = [t for t in tags_to_find if t not in found]
            if not_found:
                st.warning("Couldn't find these tags on the drawing set: " + ", ".join(not_found))

st.subheader("3. Review & Edit Schedule")

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

    st.subheader("4. Export")
    discipline_short = discipline.split(" (")[0]
    schedule_title = discipline_short + " Equipment Schedule"
    if project_name:
        schedule_title = project_name + " — " + schedule_title

    export_rows = edited_df.rename(columns={v: k for k, v in col_labels.items()}).to_dict("records")
    xlsx_bytes = build_schedule_workbook(export_rows, columns, title=schedule_title)

    file_name = (project_no or "IAE") + "_" + discipline_short.split(" ")[0] + "_Equipment_Schedule.xlsx"

    st.download_button(
        "Download Branded Excel Schedule",
        data=xlsx_bytes,
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
    st.caption(
        "Open in Excel, then use AutoCAD's Insert to OLE Object (or Data Link to Table) "
        "to place it on your drawing sheet."
    )
else:
    st.info("No equipment added yet. Upload a cut sheet above to get started.")
