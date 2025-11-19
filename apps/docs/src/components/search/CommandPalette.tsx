'use client';

import { Fragment, useState, useEffect } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { Search, FileText, Hash, ArrowRight } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';

interface SearchResult {
  id: string;
  title: string;
  description?: string;
  category: string;
  href: string;
  icon?: React.ReactNode;
}

// Mock search data - in production, this would come from Algolia or similar
const searchData: SearchResult[] = [
  // Getting Started
  { id: '1', title: 'Quick Start', category: 'Getting Started', href: '/getting-started/quick-start', icon: <FileText className="h-4 w-4" /> },
  { id: '2', title: 'Installation', category: 'Getting Started', href: '/getting-started/installation', icon: <FileText className="h-4 w-4" /> },
  { id: '3', title: 'Authentication Basics', category: 'Getting Started', href: '/getting-started/auth-basics', icon: <FileText className="h-4 w-4" /> },
  
  // API Reference
  { id: '4', title: 'POST /auth/signin', category: 'API Reference', href: '/api/authentication#signin', icon: <Hash className="h-4 w-4" /> },
  { id: '5', title: 'POST /auth/signup', category: 'API Reference', href: '/api/authentication#signup', icon: <Hash className="h-4 w-4" /> },
  { id: '6', title: 'GET /users/me', category: 'API Reference', href: '/api/users#current-user', icon: <Hash className="h-4 w-4" /> },
  
  // Guides
  { id: '7', title: 'Email/Password Authentication', category: 'Guides', href: '/guides/auth/email-password', icon: <FileText className="h-4 w-4" /> },
  { id: '8', title: 'Passkeys and WebAuthn', category: 'Guides', href: '/guides/auth/passkeys', icon: <FileText className="h-4 w-4" /> },
  { id: '9', title: 'Social Login', category: 'Guides', href: '/guides/auth/social', icon: <FileText className="h-4 w-4" /> },
  
  // SDKs
  { id: '10', title: 'JavaScript SDK', category: 'SDKs', href: '/sdks/javascript', icon: <FileText className="h-4 w-4" /> },
  { id: '11', title: 'React SDK', category: 'SDKs', href: '/sdks/react', icon: <FileText className="h-4 w-4" /> },
  { id: '12', title: 'Next.js SDK', category: 'SDKs', href: '/sdks/nextjs', icon: <FileText className="h-4 w-4" /> },
];

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

export function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);

  const filteredResults = query === ''
    ? searchData.slice(0, 5)
    : searchData.filter((item) =>
        item.title.toLowerCase().includes(query.toLowerCase()) ||
        item.category.toLowerCase().includes(query.toLowerCase()) ||
        item.description?.toLowerCase().includes(query.toLowerCase())
      );

  // Group results by category
  const groupedResults = filteredResults.reduce((acc, result) => {
    if (!acc[result.category]) {
      acc[result.category] = [];
    }
    acc[result.category].push(result);
    return acc;
  }, {} as Record<string, SearchResult[]>);

  // Reset selected index when results change
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Handle keyboard navigation
  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % filteredResults.length);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + filteredResults.length) % filteredResults.length);
      } else if (e.key === 'Enter' && filteredResults[selectedIndex]) {
        e.preventDefault();
        router.push(filteredResults[selectedIndex].href);
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, selectedIndex, filteredResults, router, onClose]);

  return (
    <Transition.Root show={open} as={Fragment}>
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
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" />
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
            <Dialog.Panel className="mx-auto max-w-2xl transform divide-y divide-gray-200 overflow-hidden rounded-xl bg-white shadow-2xl ring-1 ring-black/5 transition-all dark:divide-gray-700 dark:bg-gray-900">
              <div className="relative">
                <Search className="pointer-events-none absolute left-4 top-3.5 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  className="h-12 w-full border-0 bg-transparent pl-11 pr-4 text-gray-900 placeholder-gray-400 focus:ring-0 dark:text-gray-100 dark:placeholder-gray-500 sm:text-sm"
                  placeholder="Search documentation..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </div>

              {filteredResults.length > 0 && (
                <div className="max-h-96 scroll-py-2 overflow-y-auto py-2">
                  {Object.entries(groupedResults).map(([category, results]) => (
                    <div key={category}>
                      <h2 className="bg-gray-50 px-4 py-2 text-xs font-semibold text-gray-900 dark:bg-gray-800 dark:text-gray-100">
                        {category}
                      </h2>
                      <ul>
                        {results.map((result, _index) => {
                          const globalIndex = filteredResults.indexOf(result);
                          return (
                            <li key={result.id}>
                              <button
                                className={cn(
                                  'flex w-full cursor-pointer items-center justify-between px-4 py-2 text-sm',
                                  globalIndex === selectedIndex
                                    ? 'bg-indigo-50 text-indigo-600 dark:bg-indigo-950 dark:text-indigo-400'
                                    : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800'
                                )}
                                onClick={() => {
                                  router.push(result.href);
                                  onClose();
                                }}
                              >
                                <div className="flex items-center">
                                  {result.icon}
                                  <span className="ml-3">{result.title}</span>
                                </div>
                                <ArrowRight className="h-4 w-4 opacity-50" />
                              </button>
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  ))}
                </div>
              )}

              {filteredResults.length === 0 && query !== '' && (
                <div className="px-6 py-14 text-center sm:px-14">
                  <p className="text-sm text-gray-900 dark:text-gray-100">
                    No results found for "{query}"
                  </p>
                </div>
              )}

              <div className="flex items-center justify-between border-t border-gray-200 bg-gray-50 px-4 py-2.5 text-xs text-gray-700 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300">
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-1">
                    <kbd className="rounded bg-gray-200 px-1.5 py-0.5 font-medium dark:bg-gray-700">↑</kbd>
                    <kbd className="rounded bg-gray-200 px-1.5 py-0.5 font-medium dark:bg-gray-700">↓</kbd>
                    <span>Navigate</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <kbd className="rounded bg-gray-200 px-1.5 py-0.5 font-medium dark:bg-gray-700">↵</kbd>
                    <span>Select</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <kbd className="rounded bg-gray-200 px-1.5 py-0.5 font-medium dark:bg-gray-700">esc</kbd>
                    <span>Close</span>
                  </div>
                </div>
                <div className="text-gray-500 dark:text-gray-400">
                  Powered by Plinto Search
                </div>
              </div>
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition.Root>
  );
}