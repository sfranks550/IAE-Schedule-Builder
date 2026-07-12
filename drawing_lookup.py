"""
Auto-fill "Location / Area Served" by reading a floor plan drawing set.

Renders each page of the uploaded drawing set PDF to an image, then sends
batches of pages to Claude (vision) asking it to spot any of the schedule's
equipment tags on the plan and report the room/area name printed nearest to
that tag callout. Runs page-batch by page-batch, stopping early once every
tag has been located, to keep API cost down on large drawing sets.

Findings are suggestions, not gospel — plan legibility varies, and small
or oddly-placed tags can be missed. The app only fills in blank Location
fields, never overwrites something the user already typed or edited.
"""

import base64
import json

import fitz  # PyMuPDF
import anthropic

PAGES_PER_BATCH = 4  # how many drawing sheets to send Claude per API call
RENDER_DPI = 150      # resolution for rasterizing PDF pages to images


def render_pdf_pages(file_bytes: bytes, dpi: int = RENDER_DPI):
    """Return a list of (page_number, png_bytes) for every page in the PDF."""
    pages = []
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=matrix)
        pages.append((i + 1, pix.tobytes("png")))
    doc.close()
    return pages


def _build_lookup_tool(remaining_tags):
    return {
        "name": "report_tag_locations",
        "description": "Report the room/area name for any of the target equipment tags found on these drawing sheets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "found": {
                    "type": "array",
                    "description": "One entry per equipment tag found on these sheets.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tag": {
                                "type": "string",
                                "description": f"Must exactly match one of: {', '.join(remaining_tags)}",
                            },
                            "location": {
                                "type": "string",
                                "description": "The room name or number printed on the plan nearest to this tag's callout (e.g. 'Corridor - Left', 'Stair 1', 'Room 214').",
                            },
                        },
                        "required": ["tag", "location"],
                    },
                }
            },
            "required": ["found"],
        },
    }


def find_tag_locations(pages, tags, api_key, progress_callback=None):
    """
    pages: list of (page_number, png_bytes) from render_pdf_pages()
    tags: list of equipment tag strings to search for (e.g. ["CC-1", "MSW-1"])
    api_key: Anthropic API key
    progress_callback: optional fn(current_batch, total_batches, found_so_far_count)

    Returns dict {tag: location_string} for every tag it could find.
    Tags not found on any sheet are simply absent from the result.
    """
    client = anthropic.Anthropic(api_key=api_key)
    remaining = set(tags)
    results = {}

    batches = [pages[i:i + PAGES_PER_BATCH] for i in range(0, len(pages), PAGES_PER_BATCH)]

    for batch_idx, batch in enumerate(batches):
        if not remaining:
            break

        if progress_callback:
            progress_callback(batch_idx, len(batches), len(results))

        content = [
            {
                "type": "text",
                "text": (
                    "These are floor plan / drawing sheets from a construction project. "
                    "Look for these equipment tags: " + ", ".join(sorted(remaining)) + ". "
                    "Tags are usually shown as a callout bubble or label directly next to "
                    "the equipment symbol on the plan. For each tag you can find on these "
                    "specific sheets, report the room name or room number printed on the "
                    "plan closest to that tag - this is usually the room the equipment "
                    "serves or is located in. If a tag isn't visible on any of these sheets, "
                    "don't report it - don't guess."
                ),
            }
        ]
        for page_num, png_bytes in batch:
            content.append({"type": "text", "text": f"--- Sheet (page {page_num}) ---"})
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": base64.b64encode(png_bytes).decode("utf-8"),
                    },
                }
            )

        tool = _build_lookup_tool(sorted(remaining))
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            tools=[tool],
            tool_choice={"type": "tool", "name": "report_tag_locations"},
            messages=[{"role": "user", "content": content}],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "report_tag_locations":
                for item in block.input.get("found", []):
                    tag = item.get("tag", "").strip()
                    location = item.get("location", "").strip()
                    if tag in remaining and location:
                        results[tag] = location
                        remaining.discard(tag)

    if progress_callback:
        progress_callback(len(batches), len(batches), len(results))

    return results
