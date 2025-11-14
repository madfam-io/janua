import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Navigation } from '@/components/Navigation'
import { Footer } from '@/components/Footer'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Plinto - Enterprise-Grade Authentication Platform',
  description: 'Open-source authentication and user management platform with MFA, passkeys, SAML/OIDC SSO, and comprehensive security features.',
  keywords: ['authentication', 'auth', 'SSO', 'SAML', 'OIDC', 'MFA', 'passkeys', 'WebAuthn', 'user management'],
  authors: [{ name: 'Plinto Team' }],
  openGraph: {
    title: 'Plinto - Enterprise-Grade Authentication Platform',
    description: 'Open-source authentication and user management with enterprise features',
    type: 'website',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Navigation />
        <main className="min-h-screen">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  )
}
