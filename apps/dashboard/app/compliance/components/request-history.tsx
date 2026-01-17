'use client'

import { FileText, Download, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@janua/ui'
import { Button } from '@janua/ui'
import { Badge } from '@janua/ui'
import type { DataSubjectRequest } from '../types'
import { STATUS_CONFIG, REQUEST_TYPES } from '../constants'
import { formatDate } from '../utils'

interface RequestHistoryProps {
  requests: DataSubjectRequest[]
  onRefresh: () => void
}

export function RequestHistory({ requests, onRefresh }: RequestHistoryProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Request History</CardTitle>
            <CardDescription>Track the status of your data requests</CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={onRefresh}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {requests.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No data requests submitted yet</p>
          </div>
        ) : (
          <div className="space-y-3">
            {requests.map((request) => {
              const config = STATUS_CONFIG[request.status]
              const StatusIcon = config.icon
              const type = REQUEST_TYPES.find((t) => t.value === request.request_type)

              return (
                <div key={request.id} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex items-center gap-4">
                    <div className="p-2 rounded-full bg-muted">
                      <StatusIcon className={`h-4 w-4 ${config.color}`} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{type?.label || request.request_type}</span>
                        <Badge variant={config.badge}>{config.label}</Badge>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        Submitted {formatDate(request.requested_at)}
                        {request.completed_at && <> &bull; Completed {formatDate(request.completed_at)}</>}
                      </div>
                      {request.response_message && <p className="mt-1 text-sm">{request.response_message}</p>}
                    </div>
                  </div>
                  {request.data_export_url && request.status === 'completed' && (
                    <Button variant="outline" size="sm" asChild>
                      <a href={request.data_export_url} target="_blank" rel="noopener noreferrer">
                        <Download className="h-4 w-4 mr-1" />
                        Download
                      </a>
                    </Button>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
