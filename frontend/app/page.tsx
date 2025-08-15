'use client'

import { useState } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState('')
  const [citations, setCitations] = useState<Array<{source:string; page_number:number; text:string; score:number}>>([])
  const [loadingQuery, setLoadingQuery] = useState(false)
  const [status, setStatus] = useState('')

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFile(e.target.files?.[0] ?? null)
  }

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setStatus('Uploading...')
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch(`${API_BASE}/api/v1/ingest`, {
        method: 'POST',
        body: form,
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setStatus(`Ingested: ${data.document_id}`)
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
    try {
      const res = await fetch(`${API_BASE}/api/v1/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setAnswer(data.answer)
      setCitations(data.citations || [])
    } catch (e: any) {
      setStatus(`Error: ${e.message || 'query failed'}`)
    } finally {
      setLoadingQuery(false)
    }
  }

  return (
    <main className="container py-10">
      <h1 className="text-3xl font-semibold mb-6">Compliance Copilot</h1>

      <section className="mb-8 p-4 bg-white rounded-lg shadow">
        <h2 className="text-lg font-medium mb-3">Upload PDF</h2>
        <div className="flex items-center gap-3">
          <input aria-label="Upload PDF" type="file" accept="application/pdf" onChange={handleFileChange} />
          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="px-4 py-2 rounded bg-blue-600 text-white disabled:opacity-60"
          >{uploading ? 'Uploading...' : 'Ingest'}</button>
        </div>
        {status && <p className="mt-2 text-sm text-gray-600">{status}</p>}
      </section>

      <section className="p-4 bg-white rounded-lg shadow">
        <h2 className="text-lg font-medium mb-3">Ask a question</h2>
        <div className="flex items-center gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g., What is the retention policy?"
            className="flex-1 border rounded px-3 py-2"
            aria-label="Query"
          />
          <button
            onClick={handleQuery}
            disabled={loadingQuery}
            className="px-4 py-2 rounded bg-green-600 text-white disabled:opacity-60"
          >{loadingQuery ? 'Searching...' : 'Search'}</button>
        </div>

        {answer && (
          <div className="mt-6">
            <h3 className="font-semibold mb-2">Answer</h3>
            <p className="whitespace-pre-wrap">{answer}</p>
          </div>
        )}

        {citations.length > 0 && (
          <div className="mt-6">
            <h3 className="font-semibold mb-2">Citations</h3>
            <ul className="space-y-3">
              {citations.map((c, i) => (
                <li key={i} className="border rounded p-3">
                  <div className="text-sm text-gray-700">Source: <span className="font-mono">{c.source}</span> — Page {c.page_number} — Score {c.score.toFixed(3)}</div>
                  <div className="mt-1 text-gray-900">{c.text}</div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>
    </main>
  )
}


