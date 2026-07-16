'use client'

import { Suspense, useEffect, useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle } from '@janua/ui'
import { CheckCircle2, Loader2, ShieldAlert, ShieldCheck } from 'lucide-react'
import { januaClient } from '@/lib/janua-client'

type VerifyStatus = 'verifying' | 'success' | 'error' | 'missing-token'

// Target of the link sent by POST /api/v1/auth/signup (see
// apps/api/app/services/email_service.py send_verification_email). Public
// route (see middleware.ts PUBLIC_ROUTES) — verification must work for a
// signed-out visitor who opened the email link in a fresh browser/session.
function VerifyEmailFlow() {
  const searchParams = useSearchParams()
  const token = searchParams.get('token')

  const [status, setStatus] = useState<VerifyStatus>(token ? 'verifying' : 'missing-token')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return

    let cancelled = false
    januaClient.auth
      .verifyEmail(token)
      .then(() => {
        if (!cancelled) setStatus('success')
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(
          err instanceof Error && err.message
            ? err.message
            : 'The verification link is invalid or has expired.'
        )
        setStatus('error')
      })

    return () => {
      cancelled = true
    }
  }, [token])

  if (status === 'verifying') {
    return (
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mb-2 flex justify-center">
            <Loader2 className="text-primary size-10 animate-spin" />
          </div>
          <CardTitle className="text-2xl">Verifying your email</CardTitle>
          <CardDescription>Hang on while we confirm your verification link...</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  if (status === 'success') {
    return (
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mb-2 flex justify-center">
            <CheckCircle2 className="size-10 text-green-600 dark:text-green-400" />
          </div>
          <CardTitle className="text-2xl">Email verified</CardTitle>
          <CardDescription>Your email address has been successfully verified.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button className="w-full" asChild>
            <Link href="/">Continue to dashboard</Link>
          </Button>
        </CardContent>
      </Card>
    )
  }

  // 'error' | 'missing-token'
  return (
    <Card className="w-full max-w-md">
      <CardHeader className="text-center">
        <div className="mb-2 flex justify-center">
          <ShieldAlert className="text-destructive size-10" />
        </div>
        <CardTitle className="text-2xl">Verification failed</CardTitle>
        <CardDescription>
          {status === 'missing-token'
            ? 'This verification link is missing its token. Please use the link from your email.'
            : error || 'The verification link is invalid or has expired.'}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <Button className="w-full" asChild>
          <Link href="/login">Continue to sign in</Link>
        </Button>
        <p className="text-muted-foreground text-center text-xs">
          You can request a new verification email from your account settings after signing in.
        </p>
      </CardContent>
    </Card>
  )
}

function VerifyEmailFallback() {
  return (
    <Card className="w-full max-w-md">
      <CardHeader className="text-center">
        <div className="mb-2 flex justify-center">
          <ShieldCheck className="text-primary size-10" />
        </div>
        <CardTitle className="text-2xl">Verify your email</CardTitle>
        <CardDescription>Loading...</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex justify-center py-8">
          <Loader2 className="text-primary size-8 animate-spin" />
        </div>
      </CardContent>
    </Card>
  )
}

export default function VerifyEmailPage() {
  return (
    <div className="bg-background flex min-h-screen items-center justify-center p-4">
      <Suspense fallback={<VerifyEmailFallback />}>
        <VerifyEmailFlow />
      </Suspense>
    </div>
  )
}
