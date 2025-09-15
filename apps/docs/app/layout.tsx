import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { Providers } from './providers';
import { DocsLayout } from '@/components/Layout/DocsLayout';
import '@/styles/globals.css';
import '@/styles/tokens.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Plinto Documentation',
  description: 'Complete documentation for the Plinto identity platform',
  openGraph: {
    title: 'Plinto Documentation',
    description: 'Complete documentation for the Plinto identity platform',
    type: 'website',
    url: 'https://docs.plinto.dev',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Plinto Documentation',
    description: 'Complete documentation for the Plinto identity platform',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>
          <DocsLayout>{children}</DocsLayout>
        </Providers>
      </body>
    </html>
  );
}