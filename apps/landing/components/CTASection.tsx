import Link from 'next/link'

export function CTASection() {
  return (
    <section className="bg-primary-600 py-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <h2 className="text-3xl font-extrabold text-white sm:text-4xl">
          Ready to get started?
        </h2>
        <p className="mt-4 text-xl text-primary-100">
          Start building with Plinto in minutes. No credit card required.
        </p>
        <div className="mt-8 flex justify-center gap-4">
          <Link
            href="/docs/quickstart"
            className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-primary-600 bg-white hover:bg-gray-50 transition-colors"
          >
            Start Free Trial
          </Link>
          <Link
            href="/pricing"
            className="inline-flex items-center px-6 py-3 border border-white text-base font-medium rounded-md text-white hover:bg-primary-700 transition-colors"
          >
            View Pricing
          </Link>
        </div>
      </div>
    </section>
  )
}
