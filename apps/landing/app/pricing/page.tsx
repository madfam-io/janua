import { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Pricing - Plinto Authentication Platform',
  description: 'Transparent pricing for teams of all sizes. Start free, scale as you grow.',
}

export default function PricingPage() {
  const tiers = [
    {
      name: 'Free',
      price: '$0',
      period: 'forever',
      description: 'Perfect for side projects and MVPs',
      features: [
        'Up to 1,000 users',
        'Email/password authentication',
        'MFA (TOTP)',
        'Passkeys (WebAuthn)',
        'Profile management',
        'Session management',
        'Basic RBAC',
        'Community support',
        'All SDKs included'
      ],
      cta: 'Get Started Free',
      ctaLink: '/docs/quickstart',
      highlighted: false
    },
    {
      name: 'Pro',
      price: '$49',
      period: 'per month',
      description: 'For growing teams and production apps',
      features: [
        'Up to 10,000 users',
        'Everything in Free, plus:',
        'SAML 2.0 SSO',
        'OIDC SSO',
        'Advanced RBAC',
        'Audit logging',
        'Email support',
        'SLA: 99.9% uptime',
        'Custom branding',
        'Multiple environments'
      ],
      cta: 'Start Pro Trial',
      ctaLink: '/docs/quickstart',
      highlighted: true
    },
    {
      name: 'Enterprise',
      price: 'Custom',
      period: 'contact sales',
      description: 'For large organizations with custom needs',
      features: [
        'Unlimited users',
        'Everything in Pro, plus:',
        'SCIM provisioning',
        'Custom SSO integrations',
        'Priority support',
        'SLA: 99.99% uptime',
        'Dedicated account manager',
        'Custom SLA',
        'On-premise deployment',
        'Professional services'
      ],
      cta: 'Contact Sales',
      ctaLink: 'mailto:sales@plinto.dev',
      highlighted: false
    }
  ]

  return (
    <div className="bg-white">
      {/* Header */}
      <div className="bg-gradient-to-br from-primary-50 to-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl font-extrabold text-gray-900">Pricing</h1>
          <p className="mt-4 text-xl text-gray-600">
            Transparent pricing that scales with your business
          </p>
        </div>
      </div>

      {/* Pricing Tiers */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
            {tiers.map((tier) => (
              <div
                key={tier.name}
                className={`relative rounded-lg border ${
                  tier.highlighted
                    ? 'border-primary-600 shadow-xl scale-105'
                    : 'border-gray-200'
                } bg-white p-8`}
              >
                {tier.highlighted && (
                  <div className="absolute top-0 right-0 -translate-y-1/2 translate-x-4">
                    <span className="inline-flex rounded-full bg-primary-600 px-4 py-1 text-sm font-semibold text-white">
                      Most Popular
                    </span>
                  </div>
                )}

                <h3 className="text-2xl font-bold text-gray-900">{tier.name}</h3>
                <p className="mt-2 text-sm text-gray-600">{tier.description}</p>

                <div className="mt-6">
                  <span className="text-4xl font-extrabold text-gray-900">{tier.price}</span>
                  {tier.period && (
                    <span className="ml-2 text-base text-gray-600">/ {tier.period}</span>
                  )}
                </div>

                <ul className="mt-8 space-y-4">
                  {tier.features.map((feature, index) => (
                    <li key={index} className="flex items-start">
                      <svg
                        className="h-6 w-6 flex-shrink-0 text-primary-600"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                      <span className="ml-3 text-gray-700">{feature}</span>
                    </li>
                  ))}
                </ul>

                <div className="mt-8">
                  <Link
                    href={tier.ctaLink}
                    className={`block w-full text-center px-6 py-3 border border-transparent text-base font-medium rounded-md ${
                      tier.highlighted
                        ? 'text-white bg-primary-600 hover:bg-primary-700'
                        : 'text-primary-600 bg-white border-primary-600 hover:bg-primary-50'
                    } transition-colors`}
                  >
                    {tier.cta}
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Feature Comparison */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">
            Feature Comparison
          </h2>

          <div className="overflow-x-auto">
            <table className="min-w-full bg-white border border-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                    Feature
                  </th>
                  <th className="px-6 py-3 text-center text-sm font-semibold text-gray-900">
                    Free
                  </th>
                  <th className="px-6 py-3 text-center text-sm font-semibold text-gray-900">
                    Pro
                  </th>
                  <th className="px-6 py-3 text-center text-sm font-semibold text-gray-900">
                    Enterprise
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                <tr>
                  <td className="px-6 py-4 text-sm text-gray-900">User Limit</td>
                  <td className="px-6 py-4 text-sm text-gray-600 text-center">1,000</td>
                  <td className="px-6 py-4 text-sm text-gray-600 text-center">10,000</td>
                  <td className="px-6 py-4 text-sm text-gray-600 text-center">Unlimited</td>
                </tr>
                <tr className="bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-900">Email/Password Auth</td>
                  <td className="px-6 py-4 text-center">✓</td>
                  <td className="px-6 py-4 text-center">✓</td>
                  <td className="px-6 py-4 text-center">✓</td>
                </tr>
                <tr>
                  <td className="px-6 py-4 text-sm text-gray-900">MFA (TOTP)</td>
                  <td className="px-6 py-4 text-center">✓</td>
                  <td className="px-6 py-4 text-center">✓</td>
                  <td className="px-6 py-4 text-center">✓</td>
                </tr>
                <tr className="bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-900">Passkeys (WebAuthn)</td>
                  <td className="px-6 py-4 text-center">✓</td>
                  <td className="px-6 py-4 text-center">✓</td>
                  <td className="px-6 py-4 text-center">✓</td>
                </tr>
                <tr>
                  <td className="px-6 py-4 text-sm text-gray-900">SAML 2.0 SSO</td>
                  <td className="px-6 py-4 text-center">-</td>
                  <td className="px-6 py-4 text-center">✓</td>
                  <td className="px-6 py-4 text-center">✓</td>
                </tr>
                <tr className="bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-900">OIDC SSO</td>
                  <td className="px-6 py-4 text-center">-</td>
                  <td className="px-6 py-4 text-center">✓</td>
                  <td className="px-6 py-4 text-center">✓</td>
                </tr>
                <tr>
                  <td className="px-6 py-4 text-sm text-gray-900">SCIM Provisioning</td>
                  <td className="px-6 py-4 text-center">-</td>
                  <td className="px-6 py-4 text-center">-</td>
                  <td className="px-6 py-4 text-center">✓</td>
                </tr>
                <tr className="bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-900">Audit Logging</td>
                  <td className="px-6 py-4 text-center">-</td>
                  <td className="px-6 py-4 text-center">✓</td>
                  <td className="px-6 py-4 text-center">✓</td>
                </tr>
                <tr>
                  <td className="px-6 py-4 text-sm text-gray-900">SLA Uptime</td>
                  <td className="px-6 py-4 text-sm text-gray-600 text-center">99%</td>
                  <td className="px-6 py-4 text-sm text-gray-600 text-center">99.9%</td>
                  <td className="px-6 py-4 text-sm text-gray-600 text-center">99.99%</td>
                </tr>
                <tr className="bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-900">Support</td>
                  <td className="px-6 py-4 text-sm text-gray-600 text-center">Community</td>
                  <td className="px-6 py-4 text-sm text-gray-600 text-center">Email</td>
                  <td className="px-6 py-4 text-sm text-gray-600 text-center">Priority</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-16">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">
            Frequently Asked Questions
          </h2>

          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Can I self-host Plinto?
              </h3>
              <p className="text-gray-600">
                Yes! Plinto is fully open-source and can be self-hosted on your infrastructure. 
                All tiers include self-hosting capabilities with Docker and Kubernetes support.
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                What happens if I exceed my user limit?
              </h3>
              <p className="text-gray-600">
                We'll contact you to upgrade your plan. Your service won't be interrupted, 
                but you'll need to upgrade within 30 days to avoid service degradation.
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Are there any hidden fees?
              </h3>
              <p className="text-gray-600">
                No hidden fees. All features listed are included in the tier price. 
                Enterprise tier pricing is custom based on your specific requirements.
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Can I switch between tiers?
              </h3>
              <p className="text-gray-600">
                Yes, you can upgrade or downgrade at any time. Upgrades take effect immediately, 
                and downgrades take effect at the end of your billing period.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
