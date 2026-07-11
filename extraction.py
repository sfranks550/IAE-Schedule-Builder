"""
Cut sheet extraction via the Claude API.

Takes raw text pulled from an equipment cut sheet PDF and a target column schema,
returns a structured dict of {column_key: value} using Claude's tool-use / structured
output. This runs server-side using the app owner's API key, so end users never need
their own Claude account.
"""

import json
import anthropic


def build_extraction_tool(columns):
    """Build a tool schema whose input matches the discipline's column schema."""
    properties = {}
    for col in columns:
        properties[col["key"]] = {
            "type": "string",
            "description": f"{col['label']}. Leave as empty string if not found on the cut sheet.",
        }
    return {
        "name": "record_equipment_specs",
        "description": "Record the equipment specifications extracted from a cut sheet.",
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": [c["key"] for c in columns if c["required"]],
        },
    }


def extract_equipment_data(cut_sheet_text: str, columns: list, api_key: str, tag_hint: str = "") -> dict:
    """
    Call Claude to extract structured equipment data from cut sheet text.

    cut_sheet_text: raw text extracted from the PDF (via pdfplumber / PyPDF2, etc.)
    columns: the discipline's column schema (see schema.py)
    api_key: Anthropic API key (from the app owner, stored as a deployment secret)
    tag_hint: optional equipment tag to assign (e.g. "AHU-1") if the user specifies one
              rather than relying on the cut sheet itself.

    Returns a dict of {column_key: value}.
    """
    client = anthropic.Anthropic(api_key=api_key)
    tool = build_extraction_tool(columns)

    tag_instruction = (
        f"\n\nThe equipment tag for this unit is: {tag_hint}. Use exactly this value for the 'tag' field."
        if tag_hint
        else "\n\nIf no tag/mark number is printed on the cut sheet, leave 'tag' empty — the user will fill it in."
    )

    prompt = (
        "You are reading a manufacturer's equipment cut sheet (spec sheet) for a construction "
        "project equipment schedule. Extract the fields defined in the record_equipment_specs tool. "
        "Use the exact values printed on the cut sheet (numbers, units as shown). If a field has "
        "multiple values (e.g. a range of voltages for different models), pick the value that matches "
        "the specific model number circled or highlighted, or the first/base model if none is indicated. "
        "If a field cannot be found on the cut sheet, return an empty string for it — do not guess or "
        "invent values." + tag_instruction
    )

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        tools=[tool],
        tool_choice={"type": "tool", "name": "record_equipment_specs"},
        messages=[
            {
                "role": "user",
                "content": f"{prompt}\n\n--- CUT SHEET TEXT ---\n{cut_sheet_text}",
            }
        ],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "record_equipment_specs":
            return block.input

    return {}


def extract_text_from_pdf(file_bytes) -> str:
    """Extract raw text from an uploaded PDF cut sheet."""
    import pdfplumber
    import io

    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)
