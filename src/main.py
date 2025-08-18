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
<html lang=\"en\">\n<head>\n<meta charset=\"UTF-8\" />\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />\n<title>Compliance Copilot</title>\n<style>\n  :root{--bg:#0b1020;--card:#10162a;--muted:#7f8aa3;--accent:#3b82f6;--accent2:#22d3ee;--text:#e5e7eb}\n  body{font-family:ui-sans-serif,system-ui,-apple-system;background:radial-gradient(1000px 500px at 20% -10%,#182245,transparent),radial-gradient(800px 400px at 120% 10%,#0c1a3b,transparent),var(--bg);color:var(--text);min-height:100vh;margin:0;padding:40px 16px;}\n  .wrap{max-width:980px;margin:0 auto}\n  .title{font-size:28px;font-weight:700;margin:0 0 18px;letter-spacing:.2px}\n  .subtitle{color:var(--muted);margin:0 0 24px}\n  section{background:linear-gradient(180deg,#0e1428,#0a1124);border:1px solid #1d2a4a;padding:18px;border-radius:14px;margin-bottom:22px;box-shadow:0 6px 24px rgba(0,0,0,.25)}\n  label{display:block;margin:8px 0 6px;font-weight:600;color:#cbd5e1}\n  input[type=file],input[type=text]{width:100%;padding:10px 12px;background:#0b1329;color:#e5e7eb;border:1px solid #1f2b4d;border-radius:10px}\n  .row{display:flex;gap:12px;align-items:center}\n  .btn{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#0b1020;padding:10px 16px;border:none;border-radius:10px;cursor:pointer;font-weight:700}\n  .btn:disabled{filter:grayscale(.6);opacity:.7}\n  pre{white-space:pre-wrap;word-break:break-word;background:#0b1329;border:1px solid #1f2b4d;padding:12px;border-radius:10px;color:#cbd5e1}\n  .answer{font-size:16px;line-height:1.6}\n  .cit{margin-top:10px}\n  .badge{display:inline-block;background:#0b1329;border:1px solid #1f2b4d;border-radius:999px;padding:4px 10px;margin-right:8px;color:#9fb1d1}\n</style>\n</head>\n<body>\n<div class=\"wrap\">\n<h1 class=\"title\">Compliance Copilot</h1>\n<p class=\"subtitle\">Glass-box RAG with verifiable citations, privacy-first redaction, and observability.</p>\n<section>\n  <h2>1) Ingest PDF</h2>\n  <label for=\"file\">PDF file</label>\n  <input id=\"file\" type=\"file\" accept=\"application/pdf\" />\n  <div style=\"margin-top:10px\"><button class=\"btn\" id=\"ingestBtn\">Ingest</button></div>\n  <pre id=\"ingestOut\"></pre>\n</section>\n<section>\n  <h2>2) Query</h2>\n  <label for=\"question\">Question</label>\n  <input id=\"question\" type=\"text\" placeholder=\"Ask a question...\" />\n  <label for=\"source\">Source (filename, optional)</label>\n  <input id=\"source\" type=\"text\" placeholder=\"e.g., gdpr.pdf\" />\n  <div class=\"row\" style=\"margin-top:10px\"><label><input id=\"strict\" type=\"checkbox\" checked /> Strict privacy</label><button class=\"btn\" id=\"queryBtn\">Search</button></div>\n  <div id=\"answerWrap\" class=\"answer\"></div>\n  <div id=\"cits\" class=\"cit\"></div>\n</section>\n</div>\n<script>\nconst apiBase = location.origin + '/api/v1';\nconst sel = id => document.getElementById(id);\nsel('ingestBtn').onclick = async () => {\n  const f = sel('file').files[0];\n  if(!f){ sel('ingestOut').textContent='Select a PDF first.'; return; }\n  const fd = new FormData();\n  fd.append('file', f);\n  sel('ingestBtn').disabled = true;\n  sel('ingestOut').textContent = 'Uploading...';\n  try {\n    const r = await fetch(apiBase + '/ingest', { method: 'POST', body: fd });\n    const txt = await r.text(); let j; try{ j = JSON.parse(txt); }catch{ throw new Error(txt); }\n    sel('ingestOut').textContent = JSON.stringify(j, null, 2);\n    if(j.document_id){ sel('source').value = j.document_id; }\n  } catch(e){ sel('ingestOut').textContent = String(e); }\n  sel('ingestBtn').disabled = false;\n};\nsel('queryBtn').onclick = async () => {\n  const q = sel('question').value.trim();\n  const s = sel('source').value.trim() || null;\n  const strict = sel('strict').checked;\n  if(!q){ sel('answerWrap').textContent='Enter a question.'; return; }\n  sel('queryBtn').disabled = true;\n  sel('answerWrap').textContent = 'Searching...'; sel('cits').innerHTML='';\n  try {\n    const r = await fetch(apiBase + '/query', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: q, source: s, strict_privacy: strict }) });\n    const txt = await r.text(); let j; try{ j = JSON.parse(txt); }catch{ throw new Error(txt); }\n    sel('answerWrap').innerHTML = `<div class=\\"badge\\">trace</div> ${j.trace_id || ''} <br/><br/>${(j.answer||'').replace(/\\n/g,'<br/>')}`;\n    const cits = (j.citations||[]).map(c => `<div class=\\"badge\\">score ${((''+(c.score||0))).slice(0,5)}</div> [Source: ${c.source}, Page: ${c.page_number}]`).join('<br/>');\n    sel('cits').innerHTML = cits || '';\n  } catch(e){ sel('answerWrap').textContent = String(e); }\n  sel('queryBtn').disabled = false;\n};\n</script>\n</body>\n</html>\n"""
