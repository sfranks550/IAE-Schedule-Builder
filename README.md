# IAE Equipment Schedule Builder

Upload manufacturer cut sheets, auto-extract specs with Claude, review the table, and export a branded Excel equipment schedule your team can drop into AutoCAD (Insert → OLE Object, or Data Link → Table).

Pilot discipline: **Mechanical (HVAC)**. Plumbing, Electrical, and Fire Protection column schemas are already stubbed in `schema.py` — flip the discipline dropdown once those are tested.

## How it works

- `app.py` — the Streamlit UI (upload, extract, edit, export)
- `schema.py` — equipment schedule column definitions per discipline
- `extraction.py` — reads the cut sheet PDF text and calls Claude to pull structured specs
- `excel_export.py` — builds the branded .xlsx (maroon header, alternating rows, matching your FHA report template)

Your team never needs a Claude account — the API key lives in the app's server-side secrets, not in each person's browser.

## Deploy it (Streamlit Community Cloud — free, ~10 minutes)

1. **Get an Anthropic API key** at https://console.anthropic.com (Settings → API Keys). This is billed to your account based on usage — cut sheet extraction is cheap (a few cents per unit).
2. **Push this folder to a GitHub repo.** Create a new repo (can be private), upload all files in `schedule_app/`.
3. **Go to** https://share.streamlit.io and sign in with GitHub.
4. **Click "New app"**, point it at your repo, set the main file path to `app.py`.
5. **Before deploying, add your secret:** in the app settings, under "Secrets", paste:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
6. **Deploy.** You'll get a shareable URL like `https://your-app-name.streamlit.app` — send that link to your team. No installs needed on their end, just a browser.

## Run it locally first (recommended before deploying)

```bash
cd schedule_app
pip install -r requirements.txt
mkdir -p .streamlit
echo 'ANTHROPIC_API_KEY = "sk-ant-..."' > .streamlit/secrets.toml
streamlit run app.py
```

Opens at `http://localhost:8501`.

## Known limitations / next steps

- **Scanned (image-only) PDFs won't extract.** If a cut sheet is a scan with no selectable text, the app will flag it — add OCR (e.g. `pytesseract`) if this comes up often.
- **Swis721 LtCn BT font** isn't a standard font — the exported Excel file specifies it, but if a teammate's machine doesn't have it installed, Excel will silently substitute a default font. Everything else (colors, layout, borders) will still match.
- **No AutoCAD automation yet** — this produces the formatted Excel schedule; placing it on a sheet is still a manual OLE/data-link step in AutoCAD. That's a good phase-two addition once the schema and extraction are proven out on real projects.
- **No login/access control** — anyone with the app URL can use it (and consume your API budget). If that's a concern, Streamlit Community Cloud supports restricting apps to specific viewers, or you can add a simple shared password gate.
