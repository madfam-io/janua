'use client'

import { Avatar } from '@radix-ui/react-avatar'

interface Activity {
  id: string
  user: string
  action: string
  timestamp: string
  type: 'signin' | 'signup' | 'passkey' | 'session' | 'error'
}

export function RecentActivity() {
  const activities: Activity[] = [
    {
      id: '1',
      user: 'john@example.com',
      action: 'Signed in with passkey',
      timestamp: '2 minutes ago',
      type: 'passkey'
    },
    {
      id: '2',
      user: 'sarah@example.com',
      action: 'Created new account',
      timestamp: '5 minutes ago',
      type: 'signup'
    },
    {
      id: '3',
      user: 'mike@example.com',
      action: 'Session expired',
      timestamp: '12 minutes ago',
      type: 'session'
    },
    {
      id: '4',
      user: 'emma@example.com',
      action: 'Failed login attempt',
      timestamp: '18 minutes ago',
      type: 'error'
    },
    {
      id: '5',
      user: 'alex@example.com',
      action: 'Signed in with password',
      timestamp: '25 minutes ago',
      type: 'signin'
    }
  ]

  const getActivityColor = (type: Activity['type']) => {
    switch (type) {
      case 'signin':
      case 'passkey':
        return 'text-green-600'
      case 'signup':
        return 'text-blue-600'
      case 'session':
        return 'text-yellow-600'
      case 'error':
        return 'text-red-600'
      default:
        return 'text-muted-foreground'
    }
  }

  const getActivityIcon = (type: Activity['type']) => {
    switch (type) {
      case 'signin':
        return '→'
      case 'signup':
        return '+'
      case 'passkey':
        return '🔑'
      case 'session':
        return '⏱'
      case 'error':
        return '⚠'
      default:
        return '•'
    }
  }

  return (
    <div className="space-y-4">
      {activities.map((activity) => (
        <div key={activity.id} className="flex items-start space-x-3">
          <div className={`mt-1 text-lg ${getActivityColor(activity.type)}`}>
            {getActivityIcon(activity.type)}
          </div>
          <div className="flex-1 space-y-1">
            <p className="text-sm font-medium leading-none">
              {activity.user}
            </p>
            <p className="text-sm text-muted-foreground">
              {activity.action}
            </p>
            <p className="text-xs text-muted-foreground">
              {activity.timestamp}
            </p>
          </div>
        </div>
      ))}
    </div>
  )
}