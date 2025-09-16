import { PrismaClient } from '@prisma/client'
import { createHash } from 'crypto'

// Global Prisma client instance with custom configuration
const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined
}

// Tenant-aware Prisma client factory
class TenantAwarePrismaClient {
  private static instances: Map<string, PrismaClient> = new Map()
  private static defaultClient: PrismaClient | undefined

  static getDefaultClient(): PrismaClient {
    if (!this.defaultClient) {
      this.defaultClient = new PrismaClient({
        log: process.env.NODE_ENV === 'development' ? ['query', 'info', 'warn', 'error'] : ['error'],
        errorFormat: 'pretty',
        datasources: {
          db: {
            url: process.env.DATABASE_URL,
          },
        },
      })

      // Add middleware for audit logging
      this.defaultClient.$use(async (params, next) => {
        const before = Date.now()
        const result = await next(params)
        const after = Date.now()

        // Log slow queries in development
        if (process.env.NODE_ENV === 'development' && (after - before) > 1000) {
          console.log(`Slow query detected: ${params.model}.${params.action} took ${after - before}ms`)
        }

        return result
      })

      // Add middleware for tenant isolation (Row-Level Security)
      this.defaultClient.$use(async (params, next) => {
        // Get current tenant from context (this would be set by your auth middleware)
        const currentTenant = getCurrentTenantId()

        if (currentTenant && this.isTenantAwareModel(params.model)) {
          // Ensure tenant_id is included in queries for tenant-aware models
          if (params.action === 'findMany' || params.action === 'findFirst') {
            params.args.where = {
              ...params.args.where,
              tenant_id: currentTenant,
            }
          } else if (params.action === 'create') {
            params.args.data = {
              ...params.args.data,
              tenant_id: currentTenant,
            }
          } else if (params.action === 'update' || params.action === 'updateMany') {
            params.args.where = {
              ...params.args.where,
              tenant_id: currentTenant,
            }
          } else if (params.action === 'delete' || params.action === 'deleteMany') {
            params.args.where = {
              ...params.args.where,
              tenant_id: currentTenant,
            }
          }
        }

        return next(params)
      })
    }

    return this.defaultClient
  }

  static getTenantClient(tenantConfig: {
    id: string
    database_host?: string
    database_port?: number
    database_name?: string
    database_schema?: string
  }): PrismaClient {
    const cacheKey = this.getTenantCacheKey(tenantConfig)

    if (this.instances.has(cacheKey)) {
      return this.instances.get(cacheKey)!
    }

    // For fully-isolated tenants, create dedicated client
    if (tenantConfig.database_host && tenantConfig.database_name) {
      const databaseUrl = this.buildTenantDatabaseUrl(tenantConfig)

      const client = new PrismaClient({
        datasources: {
          db: {
            url: databaseUrl,
          },
        },
        log: process.env.NODE_ENV === 'development' ? ['error'] : ['error'],
      })

      this.instances.set(cacheKey, client)
      return client
    }

    // For shared/semi-isolated tenants, use default client with schema
    if (tenantConfig.database_schema) {
      const client = new PrismaClient({
        datasources: {
          db: {
            url: `${process.env.DATABASE_URL}?schema=${tenantConfig.database_schema}`,
          },
        },
        log: process.env.NODE_ENV === 'development' ? ['error'] : ['error'],
      })

      this.instances.set(cacheKey, client)
      return client
    }

    // Default to shared client
    return this.getDefaultClient()
  }

  private static buildTenantDatabaseUrl(tenantConfig: {
    database_host?: string
    database_port?: number
    database_name?: string
  }): string {
    const host = tenantConfig.database_host || process.env.TENANT_DB_HOST
    const port = tenantConfig.database_port || process.env.TENANT_DB_PORT
    const database = tenantConfig.database_name
    const user = process.env.TENANT_DB_USER
    const password = process.env.TENANT_DB_PASSWORD

    return `postgresql://${user}:${password}@${host}:${port}/${database}`
  }

  private static getTenantCacheKey(tenantConfig: {
    id: string
    database_host?: string
    database_port?: number
    database_name?: string
    database_schema?: string
  }): string {
    const configStr = JSON.stringify({
      id: tenantConfig.id,
      host: tenantConfig.database_host,
      port: tenantConfig.database_port,
      name: tenantConfig.database_name,
      schema: tenantConfig.database_schema,
    })

    return createHash('md5').update(configStr).digest('hex')
  }

  private static isTenantAwareModel(model: string | undefined): boolean {
    if (!model) return false

    // Models that are tenant-aware (have tenant_id field)
    const tenantAwareModels = [
      'User',
      'Team',
      'TeamMember',
      'TeamInvitation',
      'TeamProject',
      'TeamResource',
      'Role',
      'RoleAssignment',
      'Policy',
      'Session',
      'AuditLog',
      'BillingSubscription',
      'BillingInvoice',
      'BillingAlert',
      'UsageRecord',
      'ApiKey',
      'WebhookEndpoint',
    ]

    return tenantAwareModels.includes(model)
  }

  // Cleanup method for graceful shutdown
  static async disconnect(): Promise<void> {
    await Promise.all([
      this.defaultClient?.$disconnect(),
      ...Array.from(this.instances.values()).map(client => client.$disconnect())
    ])
  }
}

// Helper function to get current tenant ID from context
// This should be implemented based on your authentication/context system
function getCurrentTenantId(): string | null {
  // This is a placeholder - implement based on your context system
  // For example, you might use AsyncLocalStorage or a request context
  return null
}

// Create and export the default Prisma client
export const prisma = globalForPrisma.prisma ?? TenantAwarePrismaClient.getDefaultClient()

// Export the tenant-aware client factory
export { TenantAwarePrismaClient }

// Export utility functions
export const createTenantClient = TenantAwarePrismaClient.getTenantClient
export const disconnectPrisma = TenantAwarePrismaClient.disconnect

// In development, reuse the same instance to prevent hot-reload issues
if (process.env.NODE_ENV !== 'production') {
  globalForPrisma.prisma = prisma
}

// Graceful shutdown handling
process.on('beforeExit', async () => {
  await TenantAwarePrismaClient.disconnect()
})

process.on('SIGINT', async () => {
  await TenantAwarePrismaClient.disconnect()
  process.exit(0)
})

process.on('SIGTERM', async () => {
  await TenantAwarePrismaClient.disconnect()
  process.exit(0)
})

// Type exports for TypeScript
export type {
  PrismaClient,
  Tenant,
  User,
  Team,
  TeamMember,
  Role,
  RoleAssignment,
  Session,
  AuditLog,
  BillingPlan,
  BillingSubscription,
  PaymentCustomer,
  PaymentIntent,
  MfaMethod,
  Passkey
} from '@prisma/client'