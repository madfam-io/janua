'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { MoreHorizontal, Search, Shield, Globe, Smartphone } from 'lucide-react'

interface Session {
  id: string
  userId: string
  userEmail: string
  device: string
  browser: string
  ip: string
  location: string
  startedAt: string
  lastActivity: string
  status: 'active' | 'expired' | 'revoked'
}

export function SessionList() {
  const [searchTerm, setSearchTerm] = useState('')
  
  const sessions: Session[] = [
    {
      id: '1',
      userId: 'user_123',
      userEmail: 'john.doe@example.com',
      device: 'Desktop',
      browser: 'Chrome 120',
      ip: '192.168.1.1',
      location: 'San Francisco, US',
      startedAt: '2024-01-20 10:30',
      lastActivity: '2 minutes ago',
      status: 'active'
    },
    {
      id: '2',
      userId: 'user_456',
      userEmail: 'sarah.smith@example.com',
      device: 'Mobile',
      browser: 'Safari 17',
      ip: '10.0.0.1',
      location: 'London, UK',
      startedAt: '2024-01-20 08:15',
      lastActivity: '15 minutes ago',
      status: 'active'
    },
    {
      id: '3',
      userId: 'user_789',
      userEmail: 'mike.jones@example.com',
      device: 'Tablet',
      browser: 'Firefox 121',
      ip: '172.16.0.1',
      location: 'Tokyo, JP',
      startedAt: '2024-01-19 22:45',
      lastActivity: '1 hour ago',
      status: 'expired'
    },
    {
      id: '4',
      userId: 'user_101',
      userEmail: 'emma.wilson@example.com',
      device: 'Desktop',
      browser: 'Edge 120',
      ip: '192.168.2.1',
      location: 'Berlin, DE',
      startedAt: '2024-01-20 11:00',
      lastActivity: '30 seconds ago',
      status: 'active'
    }
  ]

  const getStatusColor = (status: Session['status']) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800'
      case 'expired':
        return 'bg-yellow-100 text-yellow-800'
      case 'revoked':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getDeviceIcon = (device: string) => {
    switch (device.toLowerCase()) {
      case 'mobile':
        return <Smartphone className="h-4 w-4" />
      case 'desktop':
        return <Globe className="h-4 w-4" />
      default:
        return <Shield className="h-4 w-4" />
    }
  }

  const filteredSessions = sessions.filter(session =>
    session.userEmail.toLowerCase().includes(searchTerm.toLowerCase()) ||
    session.location.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="space-y-4">
      {/* Search Bar */}
      <div className="flex items-center justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            placeholder="Search sessions..."
            className="w-full pl-8 pr-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <Button variant="destructive" size="sm">
          Revoke All Expired
        </Button>
      </div>

      {/* Session Table */}
      <div className="rounded-md border">
        <table className="w-full">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="p-4 text-left text-sm font-medium">User</th>
              <th className="p-4 text-left text-sm font-medium">Device & Browser</th>
              <th className="p-4 text-left text-sm font-medium">Location</th>
              <th className="p-4 text-left text-sm font-medium">Status</th>
              <th className="p-4 text-left text-sm font-medium">Last Activity</th>
              <th className="p-4 text-left text-sm font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {filteredSessions.map((session) => (
              <tr key={session.id} className="border-b hover:bg-muted/50">
                <td className="p-4">
                  <div>
                    <div className="font-medium">{session.userEmail}</div>
                    <div className="text-xs text-muted-foreground">{session.userId}</div>
                  </div>
                </td>
                <td className="p-4">
                  <div className="flex items-center gap-2">
                    {getDeviceIcon(session.device)}
                    <div>
                      <div className="text-sm font-medium">{session.device}</div>
                      <div className="text-xs text-muted-foreground">{session.browser}</div>
                    </div>
                  </div>
                </td>
                <td className="p-4">
                  <div>
                    <div className="text-sm">{session.location}</div>
                    <div className="text-xs text-muted-foreground">{session.ip}</div>
                  </div>
                </td>
                <td className="p-4">
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(session.status)}`}>
                    {session.status}
                  </span>
                </td>
                <td className="p-4 text-sm text-muted-foreground">
                  {session.lastActivity}
                </td>
                <td className="p-4">
                  <Button 
                    variant="ghost" 
                    size="sm"
                    disabled={session.status !== 'active'}
                  >
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Summary */}
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <div>
          Active sessions: {sessions.filter(s => s.status === 'active').length} | 
          Total: {sessions.length}
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