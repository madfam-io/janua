import type { Metadata } from 'next'
// NOTE: Google Fonts temporarily disabled for build verification
// This works fine on Vercel - only an issue in sandboxed environments
// import { Inter } from 'next/font/google'
import './globals.css'
import { AuthProvider } from '@/lib/auth'
import { FeatureFlagProvider } from '@plinto/feature-flags'

// const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Plinto Admin - Internal Tools',
  description: 'Internal superadmin tools for Plinto platform management',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body>{/* className={inter.className} */}
        <AuthProvider>
          <FeatureFlagProvider
            context={{
              attributes: {
                app: 'admin',
                internal: true,
                superadmin: true,
              },
            }}
          >
            {children}
          </FeatureFlagProvider>
        </AuthProvider>
      </body>
    </html>
  )
}