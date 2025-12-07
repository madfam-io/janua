# Janua SSO Integration Guide

Complete guide for integrating MADFAM applications with Janua authentication.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [Integration Patterns](#integration-patterns)
5. [OAuth Providers](#oauth-providers)
6. [API Reference](#api-reference)
7. [Migration from NextAuth](#migration-from-nextauth)
8. [Security Best Practices](#security-best-practices)

---

## Overview

Janua is MADFAM's centralized authentication service providing:

- 🔐 **Email/Password Authentication** - Traditional signup/signin
- 🔗 **OAuth 2.0** - Google, GitHub, Microsoft, Apple, Discord, Twitter, LinkedIn, Slack
- ✨ **Magic Links** - Passwordless email authentication
- 🏢 **Enterprise SSO** - SAML 2.0 and OIDC for organizations
- 🔑 **Passkeys** - WebAuthn/FIDO2 passwordless authentication
- 🛡️ **MFA** - TOTP-based two-factor authentication

### Base URLs

| Environment | URL |
|-------------|-----|
| Development | `http://localhost:8000/api/v1` |
| Staging | `https://auth-staging.madfam.io/api/v1` |
| Production | `https://auth.madfam.io/api/v1` |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MADFAM Apps                              │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────┤
│   Fortuna   │  MADFAM.io  │  Blueprint  │ Bloom-Scroll│  Dhanam │
│   (Next.js) │  (Next.js)  │  Harvester  │   (Next.js) │(Next.js)│
└──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴────┬────┘
       │             │             │             │           │
       └─────────────┴─────────────┼─────────────┴───────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │         Janua            │
                    │   Authentication API     │
                    │                          │
                    │  • /auth/signup          │
                    │  • /auth/signin          │
                    │  • /auth/oauth/*         │
                    │  • /auth/magic-link      │
                    │  • /sso/*                │
                    └──────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
             ┌──────────┐  ┌──────────┐  ┌──────────────┐
             │  Google  │  │  GitHub  │  │  Enterprise  │
             │  OAuth   │  │  OAuth   │  │  SAML/OIDC   │
             └──────────┘  └──────────┘  └──────────────┘
```

---

## Quick Start

### 1. Install Dependencies

```bash
npm install jose cookie
# or
pnpm add jose cookie
```

### 2. Environment Variables

```env
# Janua Configuration
JANUA_API_URL=https://auth.madfam.io/api/v1
JANUA_PUBLIC_URL=https://auth.madfam.io

# Your app's URL (for OAuth redirects)
NEXT_PUBLIC_APP_URL=https://your-app.madfam.io
```

### 3. Create Auth Utilities

```typescript
// lib/auth.ts
import { cookies } from 'next/headers';
import { jwtVerify, decodeJwt } from 'jose';

const JANUA_API_URL = process.env.JANUA_API_URL!;
const JWT_SECRET = new TextEncoder().encode(process.env.JWT_SECRET!);

export interface User {
  id: string;
  email: string;
  firstName?: string;
  lastName?: string;
  profileImageUrl?: string;
  emailVerified: boolean;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
}

// Verify JWT and get user
export async function getSession(): Promise<User | null> {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get('access_token')?.value;
  
  if (!accessToken) return null;
  
  try {
    const { payload } = await jwtVerify(accessToken, JWT_SECRET);
    return {
      id: payload.sub as string,
      email: payload.email as string,
      firstName: payload.first_name as string,
      lastName: payload.last_name as string,
      profileImageUrl: payload.profile_image_url as string,
      emailVerified: payload.email_verified as boolean,
    };
  } catch {
    // Token expired or invalid - try refresh
    return await refreshSession();
  }
}

// Refresh tokens
async function refreshSession(): Promise<User | null> {
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get('refresh_token')?.value;
  
  if (!refreshToken) return null;
  
  try {
    const response = await fetch(`${JANUA_API_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    
    if (!response.ok) return null;
    
    const data = await response.json();
    
    // Set new cookies (in API route or middleware)
    cookieStore.set('access_token', data.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: data.expires_in,
    });
    
    cookieStore.set('refresh_token', data.refresh_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 60 * 60 * 24 * 30, // 30 days
    });
    
    const decoded = decodeJwt(data.access_token);
    return {
      id: decoded.sub as string,
      email: decoded.email as string,
      firstName: decoded.first_name as string,
      lastName: decoded.last_name as string,
      profileImageUrl: decoded.profile_image_url as string,
      emailVerified: decoded.email_verified as boolean,
    };
  } catch {
    return null;
  }
}

// Sign out
export async function signOut(): Promise<void> {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get('access_token')?.value;
  
  if (accessToken) {
    await fetch(`${JANUA_API_URL}/auth/signout`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
    });
  }
  
  cookieStore.delete('access_token');
  cookieStore.delete('refresh_token');
}
```

### 4. Create Auth API Routes

```typescript
// app/api/auth/signin/route.ts
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

const JANUA_API_URL = process.env.JANUA_API_URL!;

export async function POST(request: Request) {
  const body = await request.json();
  
  const response = await fetch(`${JANUA_API_URL}/auth/signin`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  
  const data = await response.json();
  
  if (!response.ok) {
    return NextResponse.json(data, { status: response.status });
  }
  
  // Set auth cookies
  const cookieStore = await cookies();
  cookieStore.set('access_token', data.tokens.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: data.tokens.expires_in,
  });
  
  cookieStore.set('refresh_token', data.tokens.refresh_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 60 * 60 * 24 * 30, // 30 days
  });
  
  return NextResponse.json({ user: data.user });
}
```

```typescript
// app/api/auth/oauth/[provider]/route.ts
import { NextResponse } from 'next/server';

const JANUA_API_URL = process.env.JANUA_API_URL!;
const APP_URL = process.env.NEXT_PUBLIC_APP_URL!;

export async function GET(
  request: Request,
  { params }: { params: { provider: string } }
) {
  const { provider } = params;
  const { searchParams } = new URL(request.url);
  const redirectTo = searchParams.get('redirect_to') || '/dashboard';
  
  const response = await fetch(
    `${JANUA_API_URL}/auth/oauth/authorize/${provider}?` +
    `redirect_uri=${encodeURIComponent(`${APP_URL}/api/auth/oauth/${provider}/callback`)}&` +
    `redirect_to=${encodeURIComponent(redirectTo)}`,
    { method: 'POST' }
  );
  
  const data = await response.json();
  
  if (!response.ok) {
    return NextResponse.json(data, { status: response.status });
  }
  
  return NextResponse.redirect(data.authorization_url);
}
```

```typescript
// app/api/auth/oauth/[provider]/callback/route.ts
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

const JANUA_API_URL = process.env.JANUA_API_URL!;
const APP_URL = process.env.NEXT_PUBLIC_APP_URL!;

export async function GET(
  request: Request,
  { params }: { params: { provider: string } }
) {
  const { provider } = params;
  const { searchParams } = new URL(request.url);
  const code = searchParams.get('code');
  const state = searchParams.get('state');
  const error = searchParams.get('error');
  
  if (error) {
    return NextResponse.redirect(`${APP_URL}/auth/error?error=${error}`);
  }
  
  if (!code || !state) {
    return NextResponse.redirect(`${APP_URL}/auth/error?error=missing_params`);
  }
  
  // Exchange code for tokens via Janua
  const response = await fetch(
    `${JANUA_API_URL}/auth/oauth/callback/${provider}?code=${code}&state=${state}`
  );
  
  const data = await response.json();
  
  if (!response.ok) {
    return NextResponse.redirect(`${APP_URL}/auth/error?error=oauth_failed`);
  }
  
  // Set cookies
  const cookieStore = await cookies();
  cookieStore.set('access_token', data.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: data.expires_in,
  });
  
  cookieStore.set('refresh_token', data.refresh_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 60 * 60 * 24 * 30,
  });
  
  // Redirect to app
  const redirectTo = data.is_new_user ? '/welcome' : '/dashboard';
  return NextResponse.redirect(`${APP_URL}${redirectTo}`);
}
```

### 5. Create Middleware for Protected Routes

```typescript
// middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { jwtVerify } from 'jose';

const publicPaths = [
  '/',
  '/auth/signin',
  '/auth/signup',
  '/auth/error',
  '/api/auth',
];

const JWT_SECRET = new TextEncoder().encode(process.env.JWT_SECRET!);

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // Allow public paths
  if (publicPaths.some(path => pathname.startsWith(path))) {
    return NextResponse.next();
  }
  
  // Check for access token
  const accessToken = request.cookies.get('access_token')?.value;
  
  if (!accessToken) {
    const signinUrl = new URL('/auth/signin', request.url);
    signinUrl.searchParams.set('redirect_to', pathname);
    return NextResponse.redirect(signinUrl);
  }
  
  try {
    await jwtVerify(accessToken, JWT_SECRET);
    return NextResponse.next();
  } catch {
    // Token invalid/expired - redirect to signin
    const signinUrl = new URL('/auth/signin', request.url);
    signinUrl.searchParams.set('redirect_to', pathname);
    return NextResponse.redirect(signinUrl);
  }
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
```

---

## Integration Patterns

### Pattern A: Server Components (Recommended for Next.js 14+)

```typescript
// app/dashboard/page.tsx
import { getSession } from '@/lib/auth';
import { redirect } from 'next/navigation';

export default async function DashboardPage() {
  const user = await getSession();
  
  if (!user) {
    redirect('/auth/signin');
  }
  
  return (
    <div>
      <h1>Welcome, {user.firstName || user.email}</h1>
      {/* Dashboard content */}
    </div>
  );
}
```

### Pattern B: Client Components with React Context

```typescript
// contexts/auth-context.tsx
'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import type { User } from '@/lib/auth';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    // Fetch current user on mount
    fetch('/api/auth/me')
      .then(res => res.ok ? res.json() : null)
      .then(data => setUser(data?.user || null))
      .finally(() => setLoading(false));
  }, []);
  
  const signIn = async (email: string, password: string) => {
    const res = await fetch('/api/auth/signin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || 'Sign in failed');
    }
    
    const data = await res.json();
    setUser(data.user);
  };
  
  const signOut = async () => {
    await fetch('/api/auth/signout', { method: 'POST' });
    setUser(null);
  };
  
  return (
    <AuthContext.Provider value={{ user, loading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};
```

### Pattern C: API Route Handlers

```typescript
// For API routes that need authentication
import { getSession } from '@/lib/auth';
import { NextResponse } from 'next/server';

export async function GET() {
  const user = await getSession();
  
  if (!user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }
  
  // Your authenticated logic here
  return NextResponse.json({ data: 'protected data' });
}
```

---

## OAuth Providers

### Available Providers

| Provider | Scopes | User Info |
|----------|--------|-----------|
| Google | `openid email profile` | email, name, picture |
| GitHub | `user:email read:user` | email, name, avatar |
| Microsoft | `openid email profile` | email, name, picture |
| Apple | `name email` | email, name |
| Discord | `identify email` | email, username, avatar |
| Twitter/X | `users.read tweet.read` | email, name, profile_image |
| LinkedIn | `openid profile email` | email, name, picture |
| Slack | `openid email profile` | email, name, picture |

### OAuth Button Component

```typescript
// components/oauth-buttons.tsx
'use client';

const providers = [
  { id: 'google', name: 'Google', icon: '🔵' },
  { id: 'github', name: 'GitHub', icon: '⚫' },
  { id: 'microsoft', name: 'Microsoft', icon: '🟦' },
  { id: 'apple', name: 'Apple', icon: '🍎' },
  { id: 'discord', name: 'Discord', icon: '💜' },
  { id: 'twitter', name: 'Twitter/X', icon: '🐦' },
  { id: 'linkedin', name: 'LinkedIn', icon: '🔷' },
  { id: 'slack', name: 'Slack', icon: '💬' },
];

export function OAuthButtons({ redirectTo = '/dashboard' }: { redirectTo?: string }) {
  const handleOAuth = (provider: string) => {
    window.location.href = `/api/auth/oauth/${provider}?redirect_to=${encodeURIComponent(redirectTo)}`;
  };
  
  return (
    <div className="grid grid-cols-2 gap-3">
      {providers.map(provider => (
        <button
          key={provider.id}
          onClick={() => handleOAuth(provider.id)}
          className="flex items-center justify-center gap-2 px-4 py-2 border rounded-lg hover:bg-gray-50"
        >
          <span>{provider.icon}</span>
          <span>{provider.name}</span>
        </button>
      ))}
    </div>
  );
}
```

---

## API Reference

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/signup` | Create new account |
| `POST` | `/auth/signin` | Sign in with email/password |
| `POST` | `/auth/signout` | Sign out current session |
| `POST` | `/auth/refresh` | Refresh access token |
| `GET` | `/auth/me` | Get current user |
| `POST` | `/auth/password/forgot` | Request password reset |
| `POST` | `/auth/password/reset` | Reset password with token |
| `POST` | `/auth/password/change` | Change password (authenticated) |
| `POST` | `/auth/email/verify` | Verify email with token |
| `POST` | `/auth/magic-link` | Send magic link email |
| `POST` | `/auth/magic-link/verify` | Sign in with magic link |

### OAuth Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/auth/oauth/providers` | List available OAuth providers |
| `POST` | `/auth/oauth/authorize/{provider}` | Initialize OAuth flow |
| `GET` | `/auth/oauth/callback/{provider}` | OAuth callback handler |
| `POST` | `/auth/oauth/link/{provider}` | Link OAuth to existing account |
| `DELETE` | `/auth/oauth/unlink/{provider}` | Unlink OAuth account |
| `GET` | `/auth/oauth/accounts` | List linked OAuth accounts |

### Request/Response Examples

#### Sign Up
```bash
POST /auth/signup
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe"
}
```

Response:
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "email_verified": false,
    "first_name": "John",
    "last_name": "Doe"
  },
  "tokens": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 3600
  }
}
```

#### Sign In
```bash
POST /auth/signin
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

---

## Migration from NextAuth

### Step 1: Remove NextAuth Dependencies

```bash
npm uninstall next-auth @auth/prisma-adapter
# or
pnpm remove next-auth @auth/prisma-adapter
```

### Step 2: Remove NextAuth Configuration

Delete or rename:
- `app/api/auth/[...nextauth]/route.ts`
- `auth.ts` or `auth.config.ts`
- Any `authOptions` configuration

### Step 3: Update Environment Variables

```diff
- NEXTAUTH_SECRET=xxx
- NEXTAUTH_URL=xxx
- GOOGLE_CLIENT_ID=xxx
- GOOGLE_CLIENT_SECRET=xxx

+ JANUA_API_URL=https://auth.madfam.io/api/v1
+ JANUA_PUBLIC_URL=https://auth.madfam.io
+ JWT_SECRET=xxx  # Get from Janua admin
+ NEXT_PUBLIC_APP_URL=https://your-app.madfam.io
```

### Step 4: Replace Session Handling

```diff
- import { getServerSession } from 'next-auth';
- import { authOptions } from '@/auth';
+ import { getSession } from '@/lib/auth';

export default async function Page() {
-  const session = await getServerSession(authOptions);
-  const user = session?.user;
+  const user = await getSession();
  
  // ...
}
```

### Step 5: Replace useSession Hook

```diff
- import { useSession } from 'next-auth/react';
+ import { useAuth } from '@/contexts/auth-context';

function Component() {
-  const { data: session, status } = useSession();
-  const user = session?.user;
-  const loading = status === 'loading';
+  const { user, loading } = useAuth();
  
  // ...
}
```

### Step 6: Replace signIn/signOut

```diff
- import { signIn, signOut } from 'next-auth/react';
+ import { useAuth } from '@/contexts/auth-context';

function Component() {
+  const { signIn, signOut } = useAuth();
  
-  const handleSignIn = () => signIn('google');
+  const handleSignIn = () => {
+    window.location.href = '/api/auth/oauth/google';
+  };
  
-  const handleSignOut = () => signOut();
+  const handleSignOut = () => signOut();
  
  // ...
}
```

### Step 7: Update Middleware

Replace NextAuth middleware with Janua middleware (see Quick Start section).

### Step 8: Database Migration

If using Prisma with NextAuth adapter, migrate user data:

```sql
-- Janua uses its own user table, migrate existing users
INSERT INTO janua_users (id, email, email_verified, first_name, last_name, profile_image_url, created_at)
SELECT id, email, "emailVerified" IS NOT NULL, name, NULL, image, "createdAt"
FROM nextauth_users;

-- Migrate OAuth accounts
INSERT INTO janua_oauth_accounts (user_id, provider, provider_user_id, provider_email, access_token, refresh_token)
SELECT "userId", provider, "providerAccountId", NULL, access_token, refresh_token
FROM nextauth_accounts;
```

---

## Security Best Practices

### 1. Token Storage

- ✅ Store tokens in HTTP-only cookies
- ✅ Use `secure` flag in production
- ✅ Use `sameSite: 'lax'` or `'strict'`
- ❌ Never store tokens in localStorage
- ❌ Never expose tokens to client JavaScript

### 2. CSRF Protection

```typescript
// Use state parameter for OAuth flows
const state = crypto.randomUUID();
// Store state in session/cookie before redirect
// Verify state on callback
```

### 3. Redirect URL Validation

```typescript
// Always validate redirect URLs
const allowedHosts = ['your-app.madfam.io', 'localhost:3000'];

function isValidRedirect(url: string): boolean {
  try {
    const parsed = new URL(url, 'https://your-app.madfam.io');
    return allowedHosts.includes(parsed.host);
  } catch {
    return false;
  }
}
```

### 4. Rate Limiting

Janua implements rate limiting on auth endpoints:
- Sign up: 3/minute
- Sign in: 5/minute
- Password reset: 3/hour
- Magic link: 5/hour

### 5. Session Management

```typescript
// Implement session timeouts
const SESSION_TIMEOUT = 30 * 60 * 1000; // 30 minutes

// Refresh tokens before expiry
const TOKEN_REFRESH_THRESHOLD = 5 * 60 * 1000; // 5 minutes before expiry
```

---

## Troubleshooting

### Common Issues

**1. "Invalid or expired state token"**
- State tokens expire after 10 minutes
- Ensure Redis is running for state storage
- Check that provider in callback matches authorize

**2. "CORS error on OAuth callback"**
- Add your app's URL to Janua's CORS_ALLOWED_ORIGINS
- Ensure redirect_uri matches exactly

**3. "JWT verification failed"**
- Ensure JWT_SECRET matches between Janua and your app
- Check token hasn't expired
- Verify token is being passed correctly in Authorization header

**4. "OAuth provider not configured"**
- Check Janua environment variables for provider credentials
- Verify provider is enabled in Janua config

### Debug Mode

```typescript
// Enable debug logging
if (process.env.NODE_ENV === 'development') {
  console.log('Auth debug:', { accessToken, user });
}
```

---

## Support

- 📚 [Janua Repository](https://github.com/madfam-io/janua)
- 🐛 [Report Issues](https://github.com/madfam-io/janua/issues)
- 💬 Internal: #auth-support Slack channel

---

*Last updated: November 2024*
