'use client'

import { useCallback, useMemo, useState } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState('')
  const [citations, setCitations] = useState<Array<{source:string; page_number:number; text:string; score:number}>>([])
  const [loadingQuery, setLoadingQuery] = useState(false)
  const [status, setStatus] = useState('')
  const [lastSource, setLastSource] = useState<string | null>(null)
  const [strictPrivacy, setStrictPrivacy] = useState<boolean>(true)
  const [traceId, setTraceId] = useState<string>('')
  const [groundedness, setGroundedness] = useState<number | null>(null)

  const activeDoc = useMemo(() => lastSource ?? 'None', [lastSource])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFile(e.target.files?.[0] ?? null)
  }

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    const f = e.dataTransfer.files?.[0]
    if (f && f.type === 'application/pdf') setFile(f)
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
  }, [])

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setStatus('Uploading…')
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch(`${API_BASE}/api/v1/ingest`, { method: 'POST', body: form })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      const chunksCount = typeof data.chunks_count === 'number' ? data.chunks_count : data.chunks
      const ocrPagesCount = typeof data.ocr_pages_count === 'number' ? data.ocr_pages_count : data.ocr_pages
      setStatus(`Ingested: ${data.document_id} (chunks: ${chunksCount}, ocr pages: ${ocrPagesCount})`)
      setLastSource(chunksCount > 0 ? (data.document_id || null) : null)
    } catch (e: any) {
      setStatus(`Error: ${e.message || 'upload failed'}`)
    } finally {
      setUploading(false)
    }
  }

  const handleQuery = async () => {
    if (!query.trim()) return
    setLoadingQuery(true)
    setAnswer('')
    setCitations([])
    setTraceId('')
    setGroundedness(null)
    try {
      const res = await fetch(`${API_BASE}/api/v1/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, source: lastSource, strict_privacy: strictPrivacy })
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setAnswer(data.answer)
      setCitations(data.citations || [])
      if (typeof data.trace_id === 'string') setTraceId(data.trace_id)
      if (typeof data.groundedness === 'number') setGroundedness(data.groundedness)
    } catch (e: any) {
      setStatus(`Error: ${e.message || 'query failed'}`)
    } finally {
      setLoadingQuery(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleQuery()
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-slate-50">
      <header className="bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600">
        <div className="mx-auto max-w-5xl px-6 py-10 text-white">
          <h1 className="text-3xl md:text-4xl font-semibold tracking-tight">Compliance Copilot</h1>
          <p className="mt-2 text-white/90">Glass‑Box RAG with citations, privacy controls, and evaluation.</p>
          <div className="mt-4 inline-flex items-center gap-2 text-xs">
            <span className="rounded-full bg-white/15 px-3 py-1">Active document: <span className="font-semibold">{activeDoc}</span></span>
            <span className="rounded-full bg-white/15 px-3 py-1">Privacy: <span className="font-semibold">{strictPrivacy ? 'Strict' : 'Standard'}</span></span>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-6 py-10 grid gap-8 md:grid-cols-2">
        <section className="bg-white rounded-xl shadow-sm ring-1 ring-black/5 p-6">
          <h2 className="text-lg font-semibold">Upload PDF</h2>
          <p className="text-sm text-slate-500 mt-1">Drag & drop a PDF or choose a file, then click Ingest.</p>

          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            className="mt-4 border-2 border-dashed rounded-lg p-6 text-center hover:border-indigo-300 transition-colors"
            aria-label="Dropzone"
          >
            <input aria-label="Upload PDF" type="file" accept="application/pdf" onChange={handleFileChange} className="hidden" id="file-input" />
            <label htmlFor="file-input" className="cursor-pointer inline-block">
              <div className="text-slate-600">
                {file ? (
                  <>
                    <div className="text-sm">Selected:</div>
                    <div className="font-medium">{file.name}</div>
                  </>
                ) : (
                  <>
                    <div className="text-sm">Drop your PDF here</div>
                    <div className="text-xs text-slate-500">or click to browse</div>
                  </>
                )}
              </div>
            </label>
          </div>

          <div className="mt-4 flex items-center gap-3">
            <button
              onClick={handleUpload}
              disabled={!file || uploading}
              className="px-4 py-2 rounded-md bg-indigo-600 text-white disabled:opacity-60"
            >{uploading ? 'Uploading…' : 'Ingest'}</button>
            {status && <span className="text-sm text-slate-600">{status}</span>}
          </div>
        </section>

        <section className="bg-white rounded-xl shadow-sm ring-1 ring-black/5 p-6">
          <h2 className="text-lg font-semibold">Ask a question</h2>
          <p className="text-sm text-slate-500 mt-1">Queries are restricted to the last ingested document.</p>

          <div className="mt-4 flex items-center gap-3">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="e.g., What is the retention policy?"
              className="flex-1 border rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              aria-label="Query"
            />
            <button
              onClick={handleQuery}
              disabled={loadingQuery}
              className="px-4 py-2 rounded-md bg-emerald-600 text-white disabled:opacity-60"
            >{loadingQuery ? 'Searching…' : 'Search'}</button>
          </div>

          <div className="mt-4 flex items-center gap-3">
            <div className="flex items-center gap-2">
              <button
                aria-label="Toggle strict privacy"
                onClick={() => setStrictPrivacy((v) => !v)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${strictPrivacy ? 'bg-indigo-600' : 'bg-slate-300'}`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${strictPrivacy ? 'translate-x-6' : 'translate-x-1'}`}
                />
              </button>
              <span className="text-sm text-slate-700">Strict privacy</span>
            </div>
          </div>

          {answer && (
            <div className="mt-6">
              <h3 className="font-semibold mb-2">Answer</h3>
              <div className="rounded-lg border p-4">
                <p className="whitespace-pre-wrap">{answer}</p>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  {traceId && (
                    <div className="text-xs text-slate-600">trace_id: <span className="font-mono">{traceId}</span></div>
                  )}
                  {typeof groundedness === 'number' && (
                    <div className="text-xs text-slate-600">groundedness: <span className="font-semibold">{groundedness.toFixed(3)}</span></div>
                  )}
                </div>
              </div>
            </div>
          )}

          {citations.length > 0 && (
            <div className="mt-6">
              <h3 className="font-semibold mb-2">Citations</h3>
              <ul className="grid gap-4 md:grid-cols-2">
                {citations.map((c, i) => (
                  <li key={i} className="rounded-lg border p-4">
                    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-700">
                      <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5">{c.source}</span>
                      <span>Page {c.page_number}</span>
                      <span>Score {Number.isFinite(c.score) ? c.score.toFixed(3) : '—'}</span>
                    </div>
                    <div className="mt-2 text-sm text-slate-900 line-clamp-6 whitespace-pre-wrap">{c.text}</div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      </div>

      <footer className="mx-auto max-w-5xl px-6 pb-12 text-xs text-slate-500">
        <div className="border-t pt-6">Glass‑Box RAG • verifiable citations • privacy by default</div>
      </footer>
    </main>
  )
}


