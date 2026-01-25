import { NextRequest, NextResponse } from 'next/server'

// Simple metrics collection for admin application
const metrics = {
  adminActions: 0,
  userOperations: 0,
  configChanges: 0,
  errors: 0,
  lastReset: Date.now()
}

export async function GET(_request: NextRequest) {
  const now = Date.now()
  const uptime = now - metrics.lastReset

  // Basic Prometheus format metrics
  const prometheusMetrics = `
# HELP janua_admin_actions_total Total admin actions performed
# TYPE janua_admin_actions_total counter
janua_admin_actions_total ${metrics.adminActions}

# HELP janua_admin_user_operations_total Total user operations
# TYPE janua_admin_user_operations_total counter
janua_admin_user_operations_total ${metrics.userOperations}

# HELP janua_admin_config_changes_total Total configuration changes
# TYPE janua_admin_config_changes_total counter
janua_admin_config_changes_total ${metrics.configChanges}

# HELP janua_admin_errors_total Total admin interface errors
# TYPE janua_admin_errors_total counter
janua_admin_errors_total ${metrics.errors}

# HELP janua_admin_uptime_seconds Application uptime in seconds
# TYPE janua_admin_uptime_seconds gauge
janua_admin_uptime_seconds ${Math.floor(uptime / 1000)}

# HELP janua_admin_build_info Build information
# TYPE janua_admin_build_info gauge
janua_admin_build_info{version="1.0.0",environment="${process.env.NODE_ENV || 'development'}"} 1
`.trim()

  return new NextResponse(prometheusMetrics, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8'
    }
  })
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { type, value = 1 } = body

    switch (type) {
      case 'adminAction':
        metrics.adminActions += value
        break
      case 'userOperation':
        metrics.userOperations += value
        break
      case 'configChange':
        metrics.configChanges += value
        break
      case 'error':
        metrics.errors += value
        break
      default:
        return NextResponse.json({ error: 'Invalid metric type' }, { status: 400 })
    }

    return NextResponse.json({ success: true, metrics })
  } catch {
    metrics.errors += 1
    return NextResponse.json({ error: 'Failed to record metric' }, { status: 500 })
  }
}