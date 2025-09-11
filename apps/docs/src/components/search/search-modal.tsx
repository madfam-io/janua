'use client'

import { Fragment, useEffect, useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { Search, X, FileText, Hash, Code, Book, Layers } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { searchDocumentation, type SearchResult } from '@/lib/search'

interface SearchModalProps {
  isOpen: boolean
  onClose: () => void
}

export function SearchModal({ isOpen, onClose }: SearchModalProps) {
  const router = useRouter()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [selectedIndex, setSelectedIndex] = useState(0)

  useEffect(() => {
    if (query.length > 1) {
      const searchResults = searchDocumentation(query)
      setResults(searchResults)
      setSelectedIndex(0)
    } else {
      setResults([])
    }
  }, [query])

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        onClose()
      }
      
      if (!isOpen) return

      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex((prev) => (prev + 1) % results.length)
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex((prev) => (prev - 1 + results.length) % results.length)
      } else if (e.key === 'Enter' && results.length > 0) {
        e.preventDefault()
        router.push(results[selectedIndex].url)
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, results, selectedIndex, router, onClose])

  const getIcon = (type: SearchResult['type']) => {
    switch (type) {
      case 'guide':
        return <Book className="h-4 w-4" />
      case 'api':
        return <Hash className="h-4 w-4" />
      case 'example':
        return <Code className="h-4 w-4" />
      case 'sdk':
        return <Layers className="h-4 w-4" />
      default:
        return <FileText className="h-4 w-4" />
    }
  }

  return (
    <Transition.Root show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 bg-opacity-25 dark:bg-gray-900 dark:bg-opacity-50 backdrop-blur-sm" />
        </Transition.Child>

        <div className="fixed inset-0 z-10 overflow-y-auto p-4 sm:p-6 md:p-20">
          <Transition.Child
            as={Fragment}
            enter="ease-out duration-300"
            enterFrom="opacity-0 scale-95"
            enterTo="opacity-100 scale-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100 scale-100"
            leaveTo="opacity-0 scale-95"
          >
            <Dialog.Panel className="mx-auto max-w-2xl transform overflow-hidden rounded-xl bg-white dark:bg-gray-900 shadow-2xl ring-1 ring-black ring-opacity-5 transition-all">
              <div className="relative">
                <Search className="pointer-events-none absolute left-4 top-3.5 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  className="h-12 w-full border-0 bg-transparent pl-11 pr-4 text-gray-800 dark:text-gray-200 placeholder-gray-400 focus:ring-0 sm:text-sm"
                  placeholder="Search documentation..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
                <button
                  onClick={onClose}
                  className="absolute right-3 top-3 text-gray-400 hover:text-gray-500"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {results.length > 0 && (
                <div className="max-h-96 scroll-py-2 overflow-y-auto border-t border-gray-200 dark:border-gray-800">
                  <ul className="p-2">
                    {results.map((result, index) => (
                      <li key={result.id}>
                        <button
                          className={`flex w-full items-start gap-3 rounded-lg px-3 py-2 transition-colors ${
                            index === selectedIndex
                              ? 'bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400'
                              : 'hover:bg-gray-50 dark:hover:bg-gray-800'
                          }`}
                          onClick={() => {
                            router.push(result.url)
                            onClose()
                          }}
                        >
                          <div className={`mt-0.5 ${
                            index === selectedIndex
                              ? 'text-blue-600 dark:text-blue-400'
                              : 'text-gray-400'
                          }`}>
                            {getIcon(result.type)}
                          </div>
                          <div className="flex-1 text-left">
                            <div className={`text-sm font-medium ${
                              index === selectedIndex
                                ? 'text-blue-600 dark:text-blue-400'
                                : 'text-gray-900 dark:text-white'
                            }`}>
                              {result.title}
                            </div>
                            <div className="text-xs text-gray-500 dark:text-gray-400">
                              {result.section && `${result.section} › `}
                              {result.description}
                            </div>
                          </div>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {query && results.length === 0 && (
                <div className="border-t border-gray-200 dark:border-gray-800 px-6 py-14 text-center text-sm">
                  <p className="text-gray-500 dark:text-gray-400">
                    No results found for "{query}"
                  </p>
                </div>
              )}

              <div className="flex items-center justify-between border-t border-gray-200 dark:border-gray-800 px-4 py-2.5 text-xs text-gray-500 dark:text-gray-400">
                <div className="flex items-center gap-2">
                  <kbd className="rounded border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-1.5 py-0.5">↑↓</kbd>
                  <span>Navigate</span>
                  <kbd className="rounded border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-1.5 py-0.5">↵</kbd>
                  <span>Select</span>
                  <kbd className="rounded border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-1.5 py-0.5">ESC</kbd>
                  <span>Close</span>
                </div>
                <div>
                  Powered by Plinto Search
                </div>
              </div>
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition.Root>
  )
}