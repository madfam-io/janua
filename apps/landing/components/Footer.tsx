import Link from 'next/link'

export function Footer() {
  return (
    <footer className="bg-gray-50 border-t border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div>
            <h3 className="text-lg font-bold text-primary-600 mb-4">Plinto</h3>
            <p className="text-gray-600 text-sm">
              Enterprise-grade authentication platform for modern applications.
            </p>
          </div>
          <div>
            <h4 className="font-semibold text-gray-900 mb-4">Product</h4>
            <ul className="space-y-2 text-sm">
              <li><Link href="/features" className="text-gray-600 hover:text-primary-600">Features</Link></li>
              <li><Link href="/pricing" className="text-gray-600 hover:text-primary-600">Pricing</Link></li>
              <li><Link href="/compare" className="text-gray-600 hover:text-primary-600">Compare</Link></li>
              <li><Link href="/docs" className="text-gray-600 hover:text-primary-600">Documentation</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold text-gray-900 mb-4">Resources</h4>
            <ul className="space-y-2 text-sm">
              <li><Link href="/docs/quickstart" className="text-gray-600 hover:text-primary-600">Quickstart</Link></li>
              <li><Link href="/docs/api" className="text-gray-600 hover:text-primary-600">API Reference</Link></li>
              <li><a href="https://github.com/madfam-io/plinto" className="text-gray-600 hover:text-primary-600">GitHub</a></li>
              <li><a href="https://github.com/madfam-io/plinto/issues" className="text-gray-600 hover:text-primary-600">Support</a></li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold text-gray-900 mb-4">Legal</h4>
            <ul className="space-y-2 text-sm">
              <li><Link href="/privacy" className="text-gray-600 hover:text-primary-600">Privacy Policy</Link></li>
              <li><Link href="/terms" className="text-gray-600 hover:text-primary-600">Terms of Service</Link></li>
              <li><Link href="/security" className="text-gray-600 hover:text-primary-600">Security</Link></li>
            </ul>
          </div>
        </div>
        <div className="mt-8 pt-8 border-t border-gray-200 text-center text-sm text-gray-600">
          <p>&copy; {new Date().getFullYear()} Plinto. Open-source authentication platform.</p>
        </div>
      </div>
    </footer>
  )
}
