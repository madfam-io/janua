import { EnhancedHeroSection } from '@/components/sections/enhanced-hero'
import { SecurityTrustCenter } from '@/components/sections/security-trust-center'
import { EnterpriseShowcase } from '@/components/sections/enterprise-showcase'
import { GlobalPaymentDisplay } from '@/components/sections/global-payment-display'
import { TrustSection } from '@/components/sections/trust'
import { FeaturesGrid } from '@/components/sections/features'
import { DeveloperExperience } from '@/components/sections/developer-experience'
import { PlaygroundSection } from '@/components/sections/playground'
import { ComparisonSection } from '@/components/sections/comparison'
import { UseCases } from '@/components/sections/use-cases'
import { PricingPreview } from '@/components/sections/pricing-preview'
import { Testimonials } from '@/components/sections/testimonials'
import { CTASection } from '@/components/sections/cta'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'

export default function LandingPage() {
  return (
    <>
      <Navigation />
      <main className="relative">
        {/* Enhanced Hero Section with geo-targeting */}
        <EnhancedHeroSection />

        {/* Trust indicators */}
        <TrustSection />

        {/* Security Trust Center */}
        <SecurityTrustCenter />

        {/* Enterprise Showcase */}
        <EnterpriseShowcase />

        {/* Global Payment Display */}
        <GlobalPaymentDisplay />

        {/* Core features */}
        <section className="py-24 px-4 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <FeaturesGrid />
          </div>
        </section>

        {/* Developer Experience */}
        <section className="py-24 px-4 sm:px-6 lg:px-8 bg-gray-50 dark:bg-gray-900/50">
          <div className="max-w-7xl mx-auto">
            <DeveloperExperience />
          </div>
        </section>

        {/* Interactive Playground */}
        <section className="py-24 px-4 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <PlaygroundSection />
          </div>
        </section>

        {/* Performance Comparison */}
        <section className="py-24 px-4 sm:px-6 lg:px-8 bg-gray-50 dark:bg-gray-900/50">
          <div className="max-w-7xl mx-auto">
            <ComparisonSection />
          </div>
        </section>

        {/* Use Cases */}
        <section className="py-24 px-4 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <UseCases />
          </div>
        </section>

        {/* Pricing Preview */}
        <section className="py-24 px-4 sm:px-6 lg:px-8 bg-gray-50 dark:bg-gray-900/50">
          <div className="max-w-7xl mx-auto">
            <PricingPreview />
          </div>
        </section>

        {/* Testimonials */}
        <section className="py-24 px-4 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <Testimonials />
          </div>
        </section>

        {/* Final CTA */}
        <section className="py-32 px-4 sm:px-6 lg:px-8 bg-gradient-to-br from-blue-600 to-purple-600 dark:from-blue-800 dark:to-purple-800">
          <div className="max-w-4xl mx-auto">
            <CTASection />
          </div>
        </section>
      </main>
      <Footer />
    </>
  )
}