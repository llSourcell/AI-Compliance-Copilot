from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from src.api.v1 import endpoints
from src.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

# CORS for local Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})

app.include_router(endpoints.router, prefix=settings.API_V1_STR)


@app.get("/", response_class=HTMLResponse)
def root_ui() -> str:
    return """
<!DOCTYPE html>
<html lang=\"en\">\n<head>\n<meta charset=\"UTF-8\" />\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />\n<title>Compliance Copilot</title>\n<style>body{font-family:ui-sans-serif,system-ui,-apple-system;max-width:860px;margin:40px auto;padding:0 16px}h1{font-size:22px;margin:0 0 12px}section{border:1px solid #ddd;padding:16px;border-radius:10px;margin-bottom:18px}label{display:block;margin:8px 0 6px;font-weight:600}input[type=file],input[type=text]{width:100%;padding:8px;border:1px solid #ccc;border-radius:8px}button{background:#111;color:#fff;padding:10px 14px;border:none;border-radius:8px;cursor:pointer}button:disabled{opacity:.5}pre{white-space:pre-wrap;word-break:break-word;background:#fafafa;border:1px solid #eee;padding:12px;border-radius:8px}</style>\n</head>\n<body>\n<h1>Compliance Copilot</h1>\n<section>\n  <h2>1) Ingest PDF</h2>\n  <label for=\"file\">PDF file</label>\n  <input id=\"file\" type=\"file\" accept=\"application/pdf\" />\n  <div style=\"margin-top:10px\"><button id=\"ingestBtn\">Ingest</button></div>\n  <pre id=\"ingestOut\"></pre>\n</section>\n<section>\n  <h2>2) Query</h2>\n  <label for=\"question\">Question</label>\n  <input id=\"question\" type=\"text\" placeholder=\"Ask a question...\" />\n  <label for=\"source\">Source (filename, optional)</label>\n  <input id=\"source\" type=\"text\" placeholder=\"e.g., gdpr.pdf\" />\n  <div style=\"margin-top:10px\"><label><input id=\"strict\" type=\"checkbox\" checked /> Strict privacy</label></div>\n  <div style=\"margin-top:10px\"><button id=\"queryBtn\">Search</button></div>\n  <pre id=\"queryOut\"></pre>\n</section>\n<script>\nconst apiBase = location.origin + '/api/v1';\nconst sel = id => document.getElementById(id);\nsel('ingestBtn').onclick = async () => {\n  const f = sel('file').files[0];\n  if(!f){ sel('ingestOut').textContent='Select a PDF first.'; return; }\n  const fd = new FormData();\n  fd.append('file', f);\n  sel('ingestBtn').disabled = true;\n  sel('ingestOut').textContent = 'Uploading...';\n  try {\n    const r = await fetch(apiBase + '/ingest', { method: 'POST', body: fd });\n    const j = await r.json();\n    sel('ingestOut').textContent = JSON.stringify(j, null, 2);\n    if(j.document_id){ sel('source').value = j.document_id; }\n  } catch(e){ sel('ingestOut').textContent = String(e); }\n  sel('ingestBtn').disabled = false;\n};\nsel('queryBtn').onclick = async () => {\n  const q = sel('question').value.trim();\n  const s = sel('source').value.trim() || null;\n  const strict = sel('strict').checked;\n  if(!q){ sel('queryOut').textContent='Enter a question.'; return; }\n  sel('queryBtn').disabled = true;\n  sel('queryOut').textContent = 'Searching...';\n  try {\n    const r = await fetch(apiBase + '/query', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: q, source: s, strict_privacy: strict }) });\n    const j = await r.json();\n    sel('queryOut').textContent = JSON.stringify(j, null, 2);\n  } catch(e){ sel('queryOut').textContent = String(e); }\n  sel('queryBtn').disabled = false;\n};\n</script>\n</body>\n</html>\n"""
