/**
 * Plinto SDK Client Configuration for Admin App
 */

import { PlintoClient } from '@plinto/typescript-sdk'

const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const apiBasePath = process.env.NEXT_PUBLIC_API_BASE_PATH || '/api/v1'

// Construct the full base URL for the SDK
const baseURL = `${apiUrl}${apiBasePath}`

export const plintoClient = new PlintoClient({
  baseURL,
  debug: process.env.NODE_ENV === 'development',
  tokenStorage: 'localStorage',
  autoRefreshTokens: true,
  timeout: 30000,
})

export const auth = plintoClient.auth
export const users = plintoClient.users
export const organizations = plintoClient.organizations

export default plintoClient
