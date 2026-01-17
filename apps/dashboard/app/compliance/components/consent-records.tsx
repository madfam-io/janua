'use client'

import { Shield } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@janua/ui'
import { Button } from '@janua/ui'
import { Badge } from '@janua/ui'
import type { ConsentRecord } from '../types'
import { formatDate } from '../utils'

interface ConsentRecordsProps {
  consents: ConsentRecord[]
  onWithdraw: (consent: ConsentRecord) => void
}

export function ConsentRecords({ consents, onWithdraw }: ConsentRecordsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Consent Records</CardTitle>
        <CardDescription>View and manage your consent preferences for data processing purposes</CardDescription>
      </CardHeader>
      <CardContent>
        {consents.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Shield className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No consent records found</p>
            <p className="text-sm mt-2">
              Your consent preferences will appear here once you interact with consent prompts
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {consents.map((consent) => (
              <div
                key={consent.id}
                className={`flex items-center justify-between p-4 border rounded-lg ${
                  consent.granted
                    ? 'border-green-500/30 bg-green-500/10'
                    : 'border-border'
                }`}
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{consent.purpose_description || consent.purpose}</span>
                    <Badge variant={consent.granted ? 'default' : 'outline'}>
                      {consent.granted ? 'Granted' : 'Withdrawn'}
                    </Badge>
                  </div>
                  <div className="text-sm text-muted-foreground mt-1">
                    Legal basis: {consent.legal_basis}
                    {consent.granted && consent.granted_at && <> &bull; Granted {formatDate(consent.granted_at)}</>}
                    {!consent.granted && consent.withdrawn_at && (
                      <> &bull; Withdrawn {formatDate(consent.withdrawn_at)}</>
                    )}
                  </div>
                </div>
                {consent.granted && (
                  <Button variant="outline" size="sm" onClick={() => onWithdraw(consent)}>
                    Withdraw
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
