/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  output: 'standalone',
  transpilePackages: ['@plinto/typescript-sdk'],
  images: {
    domains: ['plinto.dev'],
  },
}

module.exports = nextConfig
