'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { MoreHorizontal, Search, Plus, Building2, Users } from 'lucide-react'

interface Organization {
  id: string
  name: string
  slug: string
  plan: 'community' | 'pro' | 'scale' | 'enterprise'
  members: number
  owner: string
  createdAt: string
  status: 'active' | 'inactive' | 'suspended'
}

export function OrganizationList() {
  const [searchTerm, setSearchTerm] = useState('')
  
  const organizations: Organization[] = [
    {
      id: 'org_1',
      name: 'Acme Corporation',
      slug: 'acme-corp',
      plan: 'enterprise',
      members: 156,
      owner: 'john.doe@acme.com',
      createdAt: '2023-06-15',
      status: 'active'
    },
    {
      id: 'org_2',
      name: 'Startup Inc',
      slug: 'startup-inc',
      plan: 'pro',
      members: 12,
      owner: 'sarah@startup.com',
      createdAt: '2024-01-05',
      status: 'active'
    },
    {
      id: 'org_3',
      name: 'Tech Solutions',
      slug: 'tech-solutions',
      plan: 'scale',
      members: 45,
      owner: 'mike@techsolutions.io',
      createdAt: '2023-09-20',
      status: 'active'
    },
    {
      id: 'org_4',
      name: 'Digital Agency',
      slug: 'digital-agency',
      plan: 'community',
      members: 5,
      owner: 'emma@agency.co',
      createdAt: '2024-01-10',
      status: 'inactive'
    },
    {
      id: 'org_5',
      name: 'Global Enterprises',
      slug: 'global-enterprises',
      plan: 'enterprise',
      members: 523,
      owner: 'alex@global.com',
      createdAt: '2022-03-01',
      status: 'active'
    }
  ]

  const getPlanColor = (plan: Organization['plan']) => {
    switch (plan) {
      case 'enterprise':
        return 'bg-purple-100 text-purple-800'
      case 'scale':
        return 'bg-blue-100 text-blue-800'
      case 'pro':
        return 'bg-green-100 text-green-800'
      case 'community':
        return 'bg-gray-100 text-gray-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusColor = (status: Organization['status']) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800'
      case 'inactive':
        return 'bg-yellow-100 text-yellow-800'
      case 'suspended':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const filteredOrganizations = organizations.filter(org =>
    org.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    org.slug.toLowerCase().includes(searchTerm.toLowerCase()) ||
    org.owner.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="space-y-4">
      {/* Search and Create Bar */}
      <div className="flex items-center justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            placeholder="Search organizations..."
            className="w-full pl-8 pr-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <Button size="sm">
          <Plus className="h-4 w-4 mr-2" />
          Create Organization
        </Button>
      </div>

      {/* Organization Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filteredOrganizations.map((org) => (
          <div key={org.id} className="rounded-lg border bg-card p-6 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-muted rounded-lg">
                  <Building2 className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-semibold">{org.name}</h3>
                  <p className="text-sm text-muted-foreground">/{org.slug}</p>
                </div>
              </div>
              <Button variant="ghost" size="sm">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </div>
            
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Plan</span>
                <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getPlanColor(org.plan)}`}>
                  {org.plan}
                </span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Status</span>
                <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(org.status)}`}>
                  {org.status}
                </span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Members</span>
                <div className="flex items-center gap-1">
                  <Users className="h-3 w-3" />
                  <span className="text-sm font-medium">{org.members}</span>
                </div>
              </div>
              
              <div className="pt-3 border-t">
                <div className="text-xs text-muted-foreground">
                  Owner: {org.owner}
                </div>
                <div className="text-xs text-muted-foreground">
                  Created: {org.createdAt}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <div>
          Showing {filteredOrganizations.length} of {organizations.length} organizations
        </div>
        <div className="flex items-center gap-4">
          <div>
            Total members: {organizations.reduce((sum, org) => sum + org.members, 0)}
          </div>
        </div>
      </div>
    </div>
  )
}