'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Users, Shield, Key, Activity, TrendingUp, TrendingDown } from 'lucide-react'

interface StatCard {
  title: string
  value: string | number
  change: string
  trend: 'up' | 'down' | 'neutral'
  icon: React.ReactNode
}

export function DashboardStats() {
  const stats: StatCard[] = [
    {
      title: 'Total Identities',
      value: '12,345',
      change: '+12%',
      trend: 'up',
      icon: <Users className="h-4 w-4 text-muted-foreground" />
    },
    {
      title: 'Active Sessions',
      value: '3,456',
      change: '+8%',
      trend: 'up',
      icon: <Key className="h-4 w-4 text-muted-foreground" />
    },
    {
      title: 'Organizations',
      value: '234',
      change: '+23%',
      trend: 'up',
      icon: <Shield className="h-4 w-4 text-muted-foreground" />
    },
    {
      title: 'Auth Events',
      value: '45.6K',
      change: '-2%',
      trend: 'down',
      icon: <Activity className="h-4 w-4 text-muted-foreground" />
    }
  ]

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat, index) => (
        <Card key={index}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {stat.title}
            </CardTitle>
            {stat.icon}
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stat.value}</div>
            <p className="text-xs text-muted-foreground flex items-center">
              {stat.trend === 'up' ? (
                <TrendingUp className="h-3 w-3 text-green-500 mr-1" />
              ) : stat.trend === 'down' ? (
                <TrendingDown className="h-3 w-3 text-red-500 mr-1" />
              ) : null}
              <span className={
                stat.trend === 'up' ? 'text-green-500' : 
                stat.trend === 'down' ? 'text-red-500' : 
                'text-muted-foreground'
              }>
                {stat.change}
              </span>
              <span className="text-muted-foreground ml-1">from last month</span>
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}