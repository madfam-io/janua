'use client'

import { useState } from 'react'
import {
  Users,
  Building2,
  Shield,
  Server,
  Activity,
  Settings,
  AlertTriangle,
  BarChart3,
  CreditCard
} from 'lucide-react'

export default function AdminPage() {
  const [activeSection, setActiveSection] = useState('overview')

  const sections = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'tenants', label: 'Tenants', icon: Building2 },
    { id: 'users', label: 'All Users', icon: Users },
    { id: 'infrastructure', label: 'Infrastructure', icon: Server },
    { id: 'billing', label: 'Billing', icon: CreditCard },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'settings', label: 'Settings', icon: Settings },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="p-2 bg-red-100 rounded-lg">
                <Shield className="h-6 w-6 text-red-600" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Janua Superadmin</h1>
                <p className="text-sm text-gray-500">Internal Platform Management</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <span className="px-3 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full">
                INTERNAL ONLY
              </span>
              <div className="text-sm text-gray-600">
                admin@janua.dev
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside className="w-64 bg-white border-r border-gray-200 min-h-screen">
          <nav className="p-4 space-y-1">
            {sections.map((section) => {
              const Icon = section.icon
              return (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${
                    activeSection === section.id
                      ? 'bg-blue-50 text-blue-600'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  <span className="text-sm font-medium">{section.label}</span>
                </button>
              )
            })}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6">
          {activeSection === 'overview' && <OverviewSection />}
          {activeSection === 'tenants' && <TenantsSection />}
          {activeSection === 'users' && <UsersSection />}
          {activeSection === 'infrastructure' && <InfrastructureSection />}
          {activeSection === 'billing' && <BillingSection />}
          {activeSection === 'security' && <SecuritySection />}
          {activeSection === 'settings' && <SettingsSection />}
        </main>
      </div>
    </div>
  )
}

function OverviewSection() {
  const stats = [
    { label: 'Total Tenants', value: '234', change: '+12%', icon: Building2 },
    { label: 'Total Users', value: '45,678', change: '+18%', icon: Users },
    { label: 'API Calls (24h)', value: '2.3M', change: '+5%', icon: Activity },
    { label: 'Revenue (MRR)', value: '$127,450', change: '+22%', icon: CreditCard },
  ]

  const alerts = [
    { type: 'critical', message: 'High memory usage on api-server-3', time: '5 min ago' },
    { type: 'warning', message: 'Tenant "acme-corp" approaching rate limit', time: '12 min ago' },
    { type: 'info', message: 'Scheduled maintenance window in 2 hours', time: '1 hour ago' },
  ]

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Platform Overview</h2>
      
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <div key={stat.label} className="bg-white p-6 rounded-lg border border-gray-200">
              <div className="flex items-center justify-between mb-2">
                <Icon className="h-5 w-5 text-gray-400" />
                <span className={`text-sm font-medium ${
                  stat.change.startsWith('+') ? 'text-green-600' : 'text-red-600'
                }`}>
                  {stat.change}
                </span>
              </div>
              <div className="text-2xl font-bold text-gray-900">{stat.value}</div>
              <div className="text-sm text-gray-500">{stat.label}</div>
            </div>
          )
        })}
      </div>

      {/* System Alerts */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">System Alerts</h3>
        </div>
        <div className="p-6 space-y-3">
          {alerts.map((alert, index) => (
            <div key={index} className="flex items-start space-x-3">
              <AlertTriangle className={`h-5 w-5 flex-shrink-0 ${
                alert.type === 'critical' ? 'text-red-500' :
                alert.type === 'warning' ? 'text-yellow-500' : 'text-blue-500'
              }`} />
              <div className="flex-1">
                <p className="text-sm text-gray-900">{alert.message}</p>
                <p className="text-xs text-gray-500">{alert.time}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Infrastructure Status */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Infrastructure Status</h3>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <ServiceStatus name="API Servers" status="healthy" uptime="99.99%" />
            <ServiceStatus name="Database Cluster" status="healthy" uptime="99.95%" />
            <ServiceStatus name="Redis Cache" status="healthy" uptime="100%" />
            <ServiceStatus name="Edge Workers" status="healthy" uptime="99.98%" />
            <ServiceStatus name="Storage (R2)" status="healthy" uptime="100%" />
            <ServiceStatus name="CDN" status="degraded" uptime="99.90%" />
          </div>
        </div>
      </div>
    </div>
  )
}

function ServiceStatus({ name, status, uptime }: { name: string; status: string; uptime: string }) {
  const statusColors = {
    healthy: 'bg-green-100 text-green-800',
    degraded: 'bg-yellow-100 text-yellow-800',
    down: 'bg-red-100 text-red-800',
  }

  return (
    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
      <div>
        <div className="text-sm font-medium text-gray-900">{name}</div>
        <div className="text-xs text-gray-500">Uptime: {uptime}</div>
      </div>
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusColors[status as keyof typeof statusColors]}`}>
        {status}
      </span>
    </div>
  )
}

function TenantsSection() {
  const tenants = [
    { id: 'tenant_123', name: 'Acme Corporation', plan: 'Enterprise', users: 523, status: 'active', mrr: '$5,000' },
    { id: 'tenant_456', name: 'Startup Inc', plan: 'Pro', users: 45, status: 'active', mrr: '$69' },
    { id: 'tenant_789', name: 'Tech Solutions', plan: 'Scale', users: 156, status: 'active', mrr: '$299' },
    { id: 'tenant_012', name: 'Digital Agency', plan: 'Community', users: 8, status: 'suspended', mrr: '$0' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Tenant Management</h2>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          Create Tenant
        </button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tenant</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Plan</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Users</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">MRR</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody>
            {tenants.map((tenant) => (
              <tr key={tenant.id} className="border-b border-gray-200 hover:bg-gray-50">
                <td className="px-6 py-4">
                  <div>
                    <div className="text-sm font-medium text-gray-900">{tenant.name}</div>
                    <div className="text-xs text-gray-500">{tenant.id}</div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    tenant.plan === 'Enterprise' ? 'bg-purple-100 text-purple-800' :
                    tenant.plan === 'Scale' ? 'bg-blue-100 text-blue-800' :
                    tenant.plan === 'Pro' ? 'bg-green-100 text-green-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {tenant.plan}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-900">{tenant.users}</td>
                <td className="px-6 py-4 text-sm font-medium text-gray-900">{tenant.mrr}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    tenant.status === 'active' ? 'bg-green-100 text-green-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {tenant.status}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <button className="text-sm text-blue-600 hover:text-blue-800">Manage</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function UsersSection() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">User Management</h2>
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <p className="text-gray-600">Global user management across all tenants</p>
      </div>
    </div>
  )
}

function InfrastructureSection() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Infrastructure</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold mb-4">Vercel (Frontend)</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Marketing Site</span>
              <span className="text-green-600">● Deployed</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Dashboard</span>
              <span className="text-green-600">● Deployed</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Admin Portal</span>
              <span className="text-yellow-600">● Pending</span>
            </div>
          </div>
        </div>
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold mb-4">Enclii/Hetzner (Backend)</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">API Server (4100)</span>
              <span className="text-green-600">● Deployed</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">PostgreSQL</span>
              <span className="text-green-600">● Running</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Redis</span>
              <span className="text-green-600">● Running</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function BillingSection() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Billing & Revenue</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="text-sm text-gray-600 mb-2">Monthly Recurring Revenue</div>
          <div className="text-3xl font-bold text-gray-900">$127,450</div>
          <div className="text-sm text-green-600">+22% from last month</div>
        </div>
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="text-sm text-gray-600 mb-2">Annual Run Rate</div>
          <div className="text-3xl font-bold text-gray-900">$1.53M</div>
          <div className="text-sm text-green-600">+18% YoY</div>
        </div>
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="text-sm text-gray-600 mb-2">Paying Customers</div>
          <div className="text-3xl font-bold text-gray-900">189</div>
          <div className="text-sm text-green-600">+15 this month</div>
        </div>
      </div>
    </div>
  )
}

function SecuritySection() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Security & Compliance</h2>
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold mb-4">Recent Security Events</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
            <div>
              <div className="text-sm font-medium">Failed login attempts spike</div>
              <div className="text-xs text-gray-500">IP: 192.168.1.1 • 2 hours ago</div>
            </div>
            <button className="text-sm text-blue-600">Investigate</button>
          </div>
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
            <div>
              <div className="text-sm font-medium">New API key created</div>
              <div className="text-xs text-gray-500">Tenant: acme-corp • 5 hours ago</div>
            </div>
            <button className="text-sm text-blue-600">Review</button>
          </div>
        </div>
      </div>
    </div>
  )
}

function SettingsSection() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Platform Settings</h2>
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Platform Mode</label>
            <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
              <option>Production</option>
              <option>Staging</option>
              <option>Maintenance</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Rate Limiting</label>
            <input type="number" className="w-full px-3 py-2 border border-gray-300 rounded-lg" defaultValue="1000" />
            <p className="text-xs text-gray-500 mt-1">Requests per minute per tenant</p>
          </div>
        </div>
      </div>
    </div>
  )
}