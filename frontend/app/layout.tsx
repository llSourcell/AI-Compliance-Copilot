import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Compliance Copilot',
  description: 'Upload PDFs and query with citations',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900">{children}</body>
    </html>
  )
}


