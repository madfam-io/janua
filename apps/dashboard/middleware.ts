import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const token = request.cookies.get('plinto_token')?.value
  const isLoginPage = request.nextUrl.pathname === '/login'
  const isPublicRoute = request.nextUrl.pathname.startsWith('/api/') || 
                       request.nextUrl.pathname.startsWith('/_next/') ||
                       request.nextUrl.pathname === '/favicon.ico'

  // Allow access to login page and public routes
  if (isLoginPage || isPublicRoute) {
    return NextResponse.next()
  }

  // Redirect to login if no token
  if (!token) {
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('redirect', request.nextUrl.pathname)
    return NextResponse.redirect(loginUrl)
  }

  // TODO: Add token validation against API
  // For now, allow if token exists
  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}