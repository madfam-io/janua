'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { MoreHorizontal, Search, Filter, Download } from 'lucide-react'

interface Identity {
  id: string
  email: string
  name: string
  status: 'active' | 'inactive' | 'suspended'
  createdAt: string
  lastSignIn: string
  authMethods: string[]
}

export function IdentityList() {
  const [searchTerm, setSearchTerm] = useState('')
  
  const identities: Identity[] = [
    {
      id: '1',
      email: 'john.doe@example.com',
      name: 'John Doe',
      status: 'active',
      createdAt: '2024-01-15',
      lastSignIn: '2 hours ago',
      authMethods: ['passkey', 'email']
    },
    {
      id: '2',
      email: 'sarah.smith@example.com',
      name: 'Sarah Smith',
      status: 'active',
      createdAt: '2024-01-10',
      lastSignIn: '1 day ago',
      authMethods: ['email']
    },
    {
      id: '3',
      email: 'mike.jones@example.com',
      name: 'Mike Jones',
      status: 'inactive',
      createdAt: '2023-12-20',
      lastSignIn: '1 week ago',
      authMethods: ['passkey']
    },
    {
      id: '4',
      email: 'emma.wilson@example.com',
      name: 'Emma Wilson',
      status: 'active',
      createdAt: '2024-01-08',
      lastSignIn: '3 hours ago',
      authMethods: ['email', 'google']
    },
    {
      id: '5',
      email: 'alex.brown@example.com',
      name: 'Alex Brown',
      status: 'suspended',
      createdAt: '2023-11-15',
      lastSignIn: '2 weeks ago',
      authMethods: ['email']
    }
  ]

  const getStatusColor = (status: Identity['status']) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800'
      case 'inactive':
        return 'bg-gray-100 text-gray-800'
      case 'suspended':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const filteredIdentities = identities.filter(identity =>
    identity.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    identity.name.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="space-y-4">
      {/* Search and Filter Bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <input
              placeholder="Search identities..."
              className="pl-8 pr-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <Button variant="outline" size="sm">
            <Filter className="h-4 w-4 mr-2" />
            Filter
          </Button>
        </div>
        <Button variant="outline" size="sm">
          <Download className="h-4 w-4 mr-2" />
          Export
        </Button>
      </div>

      {/* Identity Table */}
      <div className="rounded-md border">
        <table className="w-full">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="p-4 text-left text-sm font-medium">Identity</th>
              <th className="p-4 text-left text-sm font-medium">Status</th>
              <th className="p-4 text-left text-sm font-medium">Auth Methods</th>
              <th className="p-4 text-left text-sm font-medium">Last Sign In</th>
              <th className="p-4 text-left text-sm font-medium">Created</th>
              <th className="p-4 text-left text-sm font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {filteredIdentities.map((identity) => (
              <tr key={identity.id} className="border-b hover:bg-muted/50">
                <td className="p-4">
                  <div>
                    <div className="font-medium">{identity.name}</div>
                    <div className="text-sm text-muted-foreground">{identity.email}</div>
                  </div>
                </td>
                <td className="p-4">
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(identity.status)}`}>
                    {identity.status}
                  </span>
                </td>
                <td className="p-4">
                  <div className="flex gap-1">
                    {identity.authMethods.map((method) => (
                      <span key={method} className="inline-flex items-center px-2 py-1 rounded-md bg-muted text-xs">
                        {method}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="p-4 text-sm text-muted-foreground">
                  {identity.lastSignIn}
                </td>
                <td className="p-4 text-sm text-muted-foreground">
                  {identity.createdAt}
                </td>
                <td className="p-4">
                  <Button variant="ghost" size="sm">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          Showing {filteredIdentities.length} of {identities.length} identities
        </div>
        <div className="flex space-x-2">
          <Button variant="outline" size="sm" disabled>
            Previous
          </Button>
          <Button variant="outline" size="sm">
            Next
          </Button>
        </div>
      </div>
    </div>
  )
}