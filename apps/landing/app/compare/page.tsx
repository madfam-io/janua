import { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Compare - Plinto vs Auth0, Clerk, Supabase',
  description: 'Compare Plinto with other authentication platforms. See why Plinto is the best choice for your application.',
}

export default function ComparePage() {
  const competitors = [
    {
      name: 'Plinto',
      pricing: '$0 - $49/mo',
      openSource: true,
      selfHosted: true,
      saml: true,
      oidc: true,
      mfa: true,
      passkeys: true,
      rbac: true,
      scim: true,
      auditLogs: true,
      customDomain: true,
      dataResidency: 'Full control',
      sdks: 6,
      support: 'Community + Email',
    },
    {
      name: 'Auth0',
      pricing: '$23 - $240+/mo',
      openSource: false,
      selfHosted: false,
      saml: true,
      oidc: true,
      mfa: true,
      passkeys: true,
      rbac: true,
      scim: true,
      auditLogs: true,
      customDomain: true,
      dataResidency: 'Limited regions',
      sdks: 10,
      support: 'Email + Phone',
    },
    {
      name: 'Clerk',
      pricing: '$25 - $99+/mo',
      openSource: false,
      selfHosted: false,
      saml: true,
      oidc: true,
      mfa: true,
      passkeys: true,
      rbac: true,
      scim: false,
      auditLogs: true,
      customDomain: true,
      dataResidency: 'US only',
      sdks: 8,
      support: 'Email',
    },
    {
      name: 'Supabase Auth',
      pricing: '$25+/mo',
      openSource: true,
      selfHosted: true,
      saml: false,
      oidc: true,
      mfa: true,
      passkeys: false,
      rbac: true,
      scim: false,
      auditLogs: false,
      customDomain: true,
      dataResidency: 'Multiple regions',
      sdks: 12,
      support: 'Community + Email',
    },
  ]

  return (
    <div className="bg-white">
      {/* Header */}
      <div className="bg-gradient-to-br from-primary-50 to-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl font-extrabold text-gray-900">
            How Plinto Compares
          </h1>
          <p className="mt-4 text-xl text-gray-600">
            See how Plinto stacks up against other authentication platforms
          </p>
        </div>
      </div>

      {/* Comparison Table */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="overflow-x-auto">
            <table className="min-w-full bg-white border border-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Feature
                  </th>
                  {competitors.map((comp) => (
                    <th
                      key={comp.name}
                      className={`px-6 py-4 text-center text-sm font-semibold ${
                        comp.name === 'Plinto' ? 'text-primary-600 bg-primary-50' : 'text-gray-900'
                      }`}
                    >
                      {comp.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                <tr>
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">Pricing</td>
                  {competitors.map((comp) => (
                    <td
                      key={comp.name}
                      className={`px-6 py-4 text-sm text-center ${
                        comp.name === 'Plinto' ? 'bg-primary-50 font-semibold text-primary-700' : 'text-gray-600'
                      }`}
                    >
                      {comp.pricing}
                    </td>
                  ))}
                </tr>
                <tr className="bg-gray-50">
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">Open Source</td>
                  {competitors.map((comp) => (
                    <td
                      key={comp.name}
                      className={`px-6 py-4 text-center ${
                        comp.name === 'Plinto' ? 'bg-primary-50' : ''
                      }`}
                    >
                      {comp.openSource ? '✓' : '✗'}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">Self-Hosted</td>
                  {competitors.map((comp) => (
                    <td
                      key={comp.name}
                      className={`px-6 py-4 text-center ${
                        comp.name === 'Plinto' ? 'bg-primary-50' : ''
                      }`}
                    >
                      {comp.selfHosted ? '✓' : '✗'}
                    </td>
                  ))}
                </tr>
                <tr className="bg-gray-50">
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">SAML SSO</td>
                  {competitors.map((comp) => (
                    <td
                      key={comp.name}
                      className={`px-6 py-4 text-center ${
                        comp.name === 'Plinto' ? 'bg-primary-50' : ''
                      }`}
                    >
                      {comp.saml ? '✓' : '✗'}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">OIDC SSO</td>
                  {competitors.map((comp) => (
                    <td
                      key={comp.name}
                      className={`px-6 py-4 text-center ${
                        comp.name === 'Plinto' ? 'bg-primary-50' : ''
                      }`}
                    >
                      {comp.oidc ? '✓' : '✗'}
                    </td>
                  ))}
                </tr>
                <tr className="bg-gray-50">
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">MFA</td>
                  {competitors.map((comp) => (
                    <td
                      key={comp.name}
                      className={`px-6 py-4 text-center ${
                        comp.name === 'Plinto' ? 'bg-primary-50' : ''
                      }`}
                    >
                      {comp.mfa ? '✓' : '✗'}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">Passkeys (WebAuthn)</td>
                  {competitors.map((comp) => (
                    <td
                      key={comp.name}
                      className={`px-6 py-4 text-center ${
                        comp.name === 'Plinto' ? 'bg-primary-50' : ''
                      }`}
                    >
                      {comp.passkeys ? '✓' : '✗'}
                    </td>
                  ))}
                </tr>
                <tr className="bg-gray-50">
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">RBAC</td>
                  {competitors.map((comp) => (
                    <td
                      key={comp.name}
                      className={`px-6 py-4 text-center ${
                        comp.name === 'Plinto' ? 'bg-primary-50' : ''
                      }`}
                    >
                      {comp.rbac ? '✓' : '✗'}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">SCIM Provisioning</td>
                  {competitors.map((comp) => (
                    <td
                      key={comp.name}
                      className={`px-6 py-4 text-center ${
                        comp.name === 'Plinto' ? 'bg-primary-50' : ''
                      }`}
                    >
                      {comp.scim ? '✓' : '✗'}
                    </td>
                  ))}
                </tr>
                <tr className="bg-gray-50">
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">Audit Logs</td>
                  {competitors.map((comp) => (
                    <td
                      key={comp.name}
                      className={`px-6 py-4 text-center ${
                        comp.name === 'Plinto' ? 'bg-primary-50' : ''
                      }`}
                    >
                      {comp.auditLogs ? '✓' : '✗'}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">Custom Domain</td>
                  {competitors.map((comp) => (
                    <td
                      key={comp.name}
                      className={`px-6 py-4 text-center ${
                        comp.name === 'Plinto' ? 'bg-primary-50' : ''
                      }`}
                    >
                      {comp.customDomain ? '✓' : '✗'}
                    </td>
                  ))}
                </tr>
                <tr className="bg-gray-50">
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">Data Residency</td>
                  {competitors.map((comp) => (
                    <td
                      key={comp.name}
                      className={`px-6 py-4 text-sm text-center ${
                        comp.name === 'Plinto' ? 'bg-primary-50 font-semibold text-primary-700' : 'text-gray-600'
                      }`}
                    >
                      {comp.dataResidency}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">SDKs Available</td>
                  {competitors.map((comp) => (
                    <td
                      key={comp.name}
                      className={`px-6 py-4 text-sm text-center ${
                        comp.name === 'Plinto' ? 'bg-primary-50' : 'text-gray-600'
                      }`}
                    >
                      {comp.sdks}
                    </td>
                  ))}
                </tr>
                <tr className="bg-gray-50">
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">Support</td>
                  {competitors.map((comp) => (
                    <td
                      key={comp.name}
                      className={`px-6 py-4 text-sm text-center ${
                        comp.name === 'Plinto' ? 'bg-primary-50' : 'text-gray-600'
                      }`}
                    >
                      {comp.support}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Why Plinto */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">
            Why Choose Plinto?
          </h2>

          <div className="space-y-6">
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                100% Open Source
              </h3>
              <p className="text-gray-600">
                No vendor lock-in. Full access to the source code. Self-host anywhere 
                or use our managed cloud. You own your data and your authentication infrastructure.
              </p>
            </div>

            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Enterprise Features at Startup Prices
              </h3>
              <p className="text-gray-600">
                SAML SSO, SCIM provisioning, advanced RBAC, and audit logging starting at $49/month. 
                Other platforms charge $240+/month for the same features.
              </p>
            </div>

            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Full Data Control
              </h3>
              <p className="text-gray-600">
                Self-host on your infrastructure for complete data sovereignty. Deploy to any cloud 
                provider, on-premise, or air-gapped environments. Perfect for compliance requirements.
              </p>
            </div>

            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Modern Technology Stack
              </h3>
              <p className="text-gray-600">
                Built with FastAPI, PostgreSQL, and Redis. Supports the latest authentication 
                standards including passkeys (WebAuthn), FIDO2, and OAuth 2.1.
              </p>
            </div>

            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Developer-First Design
              </h3>
              <p className="text-gray-600">
                Built by developers, for developers. Comprehensive SDKs, clear documentation, 
                working code examples, and a focus on developer experience.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
