'use client'

import { Avatar } from '@radix-ui/react-avatar'

interface Activity {
  id: string
  user: string
  action: string
  timestamp: string
  type: 'signin' | 'signup' | 'passkey' | 'session' | 'error'
}

import { useState, useEffect } from 'react'
import { apiCall } from '@/lib/auth'

export function RecentActivity() {
  const [activities, setActivities] = useState<Activity[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchActivities()
  }, [])

  const fetchActivities = async () => {
    try {
      setIsLoading(true)
      setError(null)
      
      const response = await apiCall('/api/dashboard/recent-activity')
      
      if (!response.ok) {
        throw new Error('Failed to fetch recent activity')
      }
      
      const data = await response.json()
      setActivities(data.activities || [])
    } catch (err) {
      console.error('Error fetching activities:', err)
      setError(err instanceof Error ? err.message : 'Failed to load activities')
      
      // Fallback to empty state
      setActivities([])
    } finally {
      setIsLoading(false)
    }
  }

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

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(5)].map((_, index) => (
          <div key={index} className="flex items-start space-x-3">
            <div className="w-6 h-6 bg-muted animate-pulse rounded" />
            <div className="flex-1 space-y-2">
              <div className="h-4 w-32 bg-muted animate-pulse rounded" />
              <div className="h-3 w-24 bg-muted animate-pulse rounded" />
              <div className="h-3 w-16 bg-muted animate-pulse rounded" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-md">
        <p className="text-sm text-red-600">Error loading recent activity: {error}</p>
        <button 
          onClick={fetchActivities}
          className="mt-2 text-sm text-red-700 underline hover:no-underline"
        >
          Try again
        </button>
      </div>
    )
  }

  if (activities.length === 0) {
    return (
      <div className="p-4 text-center text-muted-foreground">
        <p className="text-sm">No recent activity found</p>
      </div>
    )
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