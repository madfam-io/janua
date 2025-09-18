import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { email, password } = body

    if (!email || !password) {
      return NextResponse.json(
        { message: 'Email and password are required' },
        { status: 400 }
      )
    }

    // Forward the login request to the Railway API
    const apiResponse = await fetch('https://plinto-api.railway.app/api/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    })

    const data = await apiResponse.json()

    if (!apiResponse.ok) {
      return NextResponse.json(
        { message: data.message || 'Login failed' },
        { status: apiResponse.status }
      )
    }

    // Return the token and user data
    return NextResponse.json({
      token: data.access_token || data.token,
      user: data.user || { email, name: email.split('@')[0] },
      message: 'Login successful'
    })

  } catch (error) {
    console.error('Login API error:', error)
    return NextResponse.json(
      { message: 'Internal server error' },
      { status: 500 }
    )
  }
}