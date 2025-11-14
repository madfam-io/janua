'use client'

import Link from 'next/link'
import { useState } from 'react'

export function Navigation() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <nav className="bg-white shadow-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <Link href="/" className="flex items-center">
              <span className="text-2xl font-bold text-primary-600">Plinto</span>
            </Link>
            <div className="hidden sm:ml-8 sm:flex sm:space-x-8">
              <Link href="/features" className="inline-flex items-center px-1 pt-1 text-gray-700 hover:text-primary-600 transition-colors">
                Features
              </Link>
              <Link href="/pricing" className="inline-flex items-center px-1 pt-1 text-gray-700 hover:text-primary-600 transition-colors">
                Pricing
              </Link>
              <Link href="/docs" className="inline-flex items-center px-1 pt-1 text-gray-700 hover:text-primary-600 transition-colors">
                Docs
              </Link>
              <Link href="/compare" className="inline-flex items-center px-1 pt-1 text-gray-700 hover:text-primary-600 transition-colors">
                Compare
              </Link>
            </div>
          </div>
          <div className="hidden sm:ml-6 sm:flex sm:items-center space-x-4">
            <a 
              href="https://github.com/madfam-io/plinto" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-gray-700 hover:text-primary-600 transition-colors"
            >
              GitHub
            </a>
            <Link 
              href="/docs/quickstart" 
              className="bg-primary-600 text-white px-4 py-2 rounded-md hover:bg-primary-700 transition-colors"
            >
              Get Started
            </Link>
          </div>
          <div className="flex items-center sm:hidden">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="inline-flex items-center justify-center p-2 rounded-md text-gray-700 hover:text-primary-600 focus:outline-none"
            >
              <span className="sr-only">Open main menu</span>
              {mobileMenuOpen ? (
                <svg className="block h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="block h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </div>

      {mobileMenuOpen && (
        <div className="sm:hidden">
          <div className="pt-2 pb-3 space-y-1">
            <Link href="/features" className="block pl-3 pr-4 py-2 text-gray-700 hover:bg-gray-50">
              Features
            </Link>
            <Link href="/pricing" className="block pl-3 pr-4 py-2 text-gray-700 hover:bg-gray-50">
              Pricing
            </Link>
            <Link href="/docs" className="block pl-3 pr-4 py-2 text-gray-700 hover:bg-gray-50">
              Docs
            </Link>
            <Link href="/compare" className="block pl-3 pr-4 py-2 text-gray-700 hover:bg-gray-50">
              Compare
            </Link>
            <a href="https://github.com/madfam-io/plinto" className="block pl-3 pr-4 py-2 text-gray-700 hover:bg-gray-50">
              GitHub
            </a>
            <Link href="/docs/quickstart" className="block pl-3 pr-4 py-2 bg-primary-600 text-white hover:bg-primary-700 mx-3 rounded-md text-center">
              Get Started
            </Link>
          </div>
        </div>
      )}
    </nav>
  )
}
