/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  transpilePackages: ['@janua/ui', '@janua/react-sdk'],
  images: {
    domains: ['images.unsplash.com', 'github.com'],
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://api.janua.dev',
  },
}

module.exports = nextConfig