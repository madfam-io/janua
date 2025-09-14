'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Users, GitBranch, Briefcase, Settings, Building2, Shield, Zap, Globe, ChevronRight, Check, Code2, Monitor } from 'lucide-react'
import { Badge } from '@plinto/ui'
import { Button } from '@plinto/ui'

interface EnterpriseFeature {
  icon: any
  title: string
  description: string
  capabilities: string[]
  demoAvailable: boolean
  competitorComparison: {
    auth0: boolean
    firebase: boolean
    supabase: boolean
    plinto: boolean
  }
}

export function EnterpriseShowcase() {
  const [activeTab, setActiveTab] = useState<'scim' | 'sso' | 'rbac' | 'whitelabel'>('scim')
  const [showDemo, setShowDemo] = useState(false)

  const enterpriseFeatures: EnterpriseFeature[] = [
    {
      icon: Users,
      title: 'SCIM 2.0 Provisioning',
      description: 'Automate user lifecycle management with industry-standard SCIM protocol',
      capabilities: [
        'Automatic user provisioning/deprovisioning',
        'Group synchronization',
        'Active Directory integration',
        'Okta, OneLogin, Azure AD support',
        'Real-time sync with HR systems',
        'Bulk operations support'
      ],
      demoAvailable: true,
      competitorComparison: {
        auth0: true,
        firebase: false,
        supabase: false,
        plinto: true
      }
    },
    {
      icon: Shield,
      title: 'Enterprise SSO',
      description: 'Seamless single sign-on with any identity provider',
      capabilities: [
        'SAML 2.0 support',
        'OpenID Connect (OIDC)',
        'Active Directory Federation',
        'Multi-protocol support',
        'Just-in-Time provisioning',
        'Custom attribute mapping'
      ],
      demoAvailable: true,
      competitorComparison: {
        auth0: true,
        firebase: false,
        supabase: true,
        plinto: true
      }
    },
    {
      icon: GitBranch,
      title: 'Advanced RBAC',
      description: 'Fine-grained role-based access control with custom permissions',
      capabilities: [
        'Hierarchical role structures',
        'Custom permission sets',
        'Dynamic policy evaluation',
        'Resource-level permissions',
        'Delegation capabilities',
        'Audit trail for all changes'
      ],
      demoAvailable: true,
      competitorComparison: {
        auth0: true,
        firebase: true,
        supabase: true,
        plinto: true
      }
    },
    {
      icon: Briefcase,
      title: 'White-Label Solution',
      description: 'Complete customization to match your brand identity',
      capabilities: [
        'Custom domains',
        'Branded login pages',
        'Email template customization',
        'API white-labeling',
        'Custom color schemes',
        'Logo and asset management'
      ],
      demoAvailable: true,
      competitorComparison: {
        auth0: true,
        firebase: false,
        supabase: false,
        plinto: true
      }
    }
  ]

  const multiTenantFeatures = [
    {
      title: 'Tenant Isolation',
      description: 'Complete data isolation between tenants with separate encryption keys',
      icon: '🔐'
    },
    {
      title: 'Per-Tenant Billing',
      description: 'Automated billing and usage tracking for each tenant',
      icon: '💳'
    },
    {
      title: 'Custom Branding',
      description: 'Each tenant gets their own branded experience',
      icon: '🎨'
    },
    {
      title: 'Tenant Analytics',
      description: 'Detailed insights and reporting per tenant',
      icon: '📊'
    },
    {
      title: 'Resource Limits',
      description: 'Set and enforce limits per tenant',
      icon: '⚖️'
    },
    {
      title: 'Migration Tools',
      description: 'Easy tenant onboarding and data migration',
      icon: '🚀'
    }
  ]

  const scimDemo = {
    request: `POST /scim/v2/Users
Content-Type: application/scim+json

{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
  "userName": "jane.doe@enterprise.com",
  "name": {
    "givenName": "Jane",
    "familyName": "Doe"
  },
  "emails": [{
    "value": "jane.doe@enterprise.com",
    "primary": true
  }],
  "groups": ["Engineering", "Platform Team"],
  "active": true
}`,
    response: `201 Created
Content-Type: application/scim+json

{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
  "id": "2819c223-7f76-453a-919d-ab1234567890",
  "userName": "jane.doe@enterprise.com",
  "meta": {
    "resourceType": "User",
    "created": "2025-01-14T18:29:49.793Z",
    "lastModified": "2025-01-14T18:29:49.793Z"
  }
}`
  }

  return (
    <section className="py-24 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <Badge variant="outline" className="mb-4">
            <Building2 className="w-3 h-3 mr-1" />
            Enterprise Features
          </Badge>
          <h2 className="text-4xl sm:text-5xl font-bold text-gray-900 dark:text-white mb-6">
            Built for Enterprise,
            <span className="block text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600 dark:from-blue-400 dark:to-purple-400">
              From Day One
            </span>
          </h2>
          <p className="text-xl text-gray-600 dark:text-gray-300 max-w-3xl mx-auto">
            No need to wait until you scale. Enterprise features are available from your first user,
            ready when you need them.
          </p>
        </motion.div>

        {/* Feature Tabs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="mb-12"
        >
          <div className="flex flex-wrap justify-center gap-2 mb-8">
            {enterpriseFeatures.map((feature) => (
              <Button
                key={feature.title}
                variant={activeTab === feature.title.toLowerCase().split(' ')[0] ? 'default' : 'outline'}
                onClick={() => setActiveTab(feature.title.toLowerCase().split(' ')[0] as any)}
                className="mb-2"
              >
                <feature.icon className="w-4 h-4 mr-2" />
                {feature.title}
              </Button>
            ))}
          </div>

          {/* Active Feature Display */}
          <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 overflow-hidden">
            {activeTab === 'scim' && (
              <div className="p-8">
                <div className="grid lg:grid-cols-2 gap-8">
                  <div>
                    <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                      SCIM 2.0 User Provisioning
                    </h3>
                    <p className="text-gray-600 dark:text-gray-300 mb-6">
                      Automate user lifecycle management with industry-standard SCIM protocol.
                      Seamlessly integrate with your existing identity providers.
                    </p>
                    <ul className="space-y-3 mb-6">
                      {enterpriseFeatures[0].capabilities.map((cap, i) => (
                        <li key={i} className="flex items-start">
                          <Check className="w-5 h-5 text-green-500 mr-3 flex-shrink-0 mt-0.5" />
                          <span className="text-gray-600 dark:text-gray-300">{cap}</span>
                        </li>
                      ))}
                    </ul>
                    <Button onClick={() => setShowDemo(true)}>
                      <Monitor className="w-4 h-4 mr-2" />
                      View Live Demo
                    </Button>
                  </div>
                  <div className="bg-gray-900 dark:bg-black rounded-xl p-4 overflow-x-auto">
                    <div className="flex items-center gap-2 mb-3">
                      <div className="w-3 h-3 bg-red-500 rounded-full" />
                      <div className="w-3 h-3 bg-yellow-500 rounded-full" />
                      <div className="w-3 h-3 bg-green-500 rounded-full" />
                      <span className="text-xs text-gray-400 ml-2">SCIM API Example</span>
                    </div>
                    <pre className="text-xs text-green-400 font-mono">
                      <code>{scimDemo.request}</code>
                    </pre>
                  </div>
                </div>
              </div>
            )}
          </div>
        </motion.div>

        {/* Multi-Tenant Architecture */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mb-16"
        >
          <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-8 text-center">
            True Multi-Tenant Architecture
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {multiTenantFeatures.map((feature, index) => (
              <motion.div
                key={index}
                whileHover={{ scale: 1.05 }}
                className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-all"
              >
                <div className="text-3xl mb-4">{feature.icon}</div>
                <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  {feature.title}
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  {feature.description}
                </p>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Competitor Comparison */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="mb-16"
        >
          <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-8 text-center">
            Enterprise Feature Comparison
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full bg-white dark:bg-gray-800 rounded-xl overflow-hidden">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900 dark:text-white">Feature</th>
                  <th className="px-6 py-4 text-center text-sm font-semibold text-gray-900 dark:text-white">Plinto</th>
                  <th className="px-6 py-4 text-center text-sm font-semibold text-gray-900 dark:text-white">Auth0</th>
                  <th className="px-6 py-4 text-center text-sm font-semibold text-gray-900 dark:text-white">Firebase</th>
                  <th className="px-6 py-4 text-center text-sm font-semibold text-gray-900 dark:text-white">Supabase</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {enterpriseFeatures.map((feature, index) => (
                  <tr key={index}>
                    <td className="px-6 py-4 text-sm text-gray-900 dark:text-white font-medium">
                      <div className="flex items-center">
                        <feature.icon className="w-4 h-4 mr-2 text-gray-500" />
                        {feature.title}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-center">
                      {feature.competitorComparison.plinto ? (
                        <Check className="w-5 h-5 text-green-500 mx-auto" />
                      ) : (
                        <span className="text-gray-300">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-center">
                      {feature.competitorComparison.auth0 ? (
                        <Check className="w-5 h-5 text-green-500 mx-auto" />
                      ) : (
                        <span className="text-gray-300">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-center">
                      {feature.competitorComparison.firebase ? (
                        <Check className="w-5 h-5 text-green-500 mx-auto" />
                      ) : (
                        <span className="text-gray-300">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-center">
                      {feature.competitorComparison.supabase ? (
                        <Check className="w-5 h-5 text-green-500 mx-auto" />
                      ) : (
                        <span className="text-gray-300">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>

        {/* CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="text-center"
        >
          <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950/30 dark:to-purple-950/30 rounded-2xl p-12">
            <h3 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
              Ready for Enterprise Scale?
            </h3>
            <p className="text-xl text-gray-600 dark:text-gray-300 mb-8 max-w-2xl mx-auto">
              Get a personalized demo and see how Plinto can power your enterprise authentication needs.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button size="lg" className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white">
                Schedule Enterprise Demo
                <ChevronRight className="ml-2 w-5 h-5" />
              </Button>
              <Button size="lg" variant="outline">
                <Code2 className="mr-2 w-5 h-5" />
                View API Documentation
              </Button>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}