'use client'

import { useState } from 'react'

interface CodeExampleProps {
  title: string
  language: string
  code: string
}

export function CodeExample({ title, language, code }: CodeExampleProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="rounded-lg border border-gray-200 overflow-hidden bg-gray-50">
      <div className="flex items-center justify-between px-4 py-2 bg-gray-100 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">{title}</span>
          <span className="text-xs text-gray-500">{language}</span>
        </div>
        <button
          onClick={handleCopy}
          className="text-sm text-gray-600 hover:text-primary-600 transition-colors"
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <pre className="p-4 overflow-x-auto text-sm bg-gray-900">
        <code className="text-gray-300">{code}</code>
      </pre>
    </div>
  )
}
