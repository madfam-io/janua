import { PrismaClient } from '@prisma/client';
import { config } from '@/config';

// =============================================================================
// PRISMA CLIENT CONFIGURATION
// =============================================================================

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined;
};

export const prisma =
  globalForPrisma.prisma ??
  new PrismaClient({
    log: config.env === 'development' ? ['query', 'error', 'warn'] : ['error'],
    datasources: {
      db: {
        url: config.database.url,
      },
    },
  });

if (config.env !== 'production') {
  globalForPrisma.prisma = prisma;
}

// =============================================================================
// DATABASE CONNECTION MANAGEMENT
// =============================================================================

export async function connectDatabase(): Promise<void> {
  try {
    await prisma.$connect();
    console.log('📦 Database connected successfully');

    // Run a simple query to verify connection
    await prisma.$queryRaw`SELECT 1`;
    console.log('✅ Database connectivity verified');
  } catch (error) {
    console.error('❌ Failed to connect to database:', error);
    process.exit(1);
  }
}

export async function disconnectDatabase(): Promise<void> {
  try {
    await prisma.$disconnect();
    console.log('📦 Database disconnected successfully');
  } catch (error) {
    console.error('❌ Failed to disconnect from database:', error);
  }
}

// =============================================================================
// DATABASE HEALTH CHECK
// =============================================================================

export async function checkDatabaseHealth(): Promise<{
  healthy: boolean;
  latency: number;
  error?: string;
}> {
  const start = Date.now();

  try {
    await prisma.$queryRaw`SELECT 1`;
    const latency = Date.now() - start;

    return {
      healthy: true,
      latency,
    };
  } catch (error: any) {
    const latency = Date.now() - start;

    return {
      healthy: false,
      latency,
      error: error.message,
    };
  }
}

// =============================================================================
// TRANSACTION HELPERS
// =============================================================================

export async function runInTransaction<T>(
  operation: (tx: Omit<PrismaClient, '$connect' | '$disconnect' | '$on' | '$transaction' | '$use'>) => Promise<T>
): Promise<T> {
  return prisma.$transaction(operation);
}

// =============================================================================
// PRISMA EXTENSIONS
// =============================================================================

export const extendedPrisma = prisma.$extends({
  query: {
    // Add soft delete functionality
    $allModels: {
      async delete({ args, query }) {
        // Check if model has deletedAt field
        const modelName = (query as any).model;
        const hasDeletedAt = ['User', 'Team', 'Tenant'].includes(modelName);

        if (hasDeletedAt) {
          return prisma[modelName.toLowerCase() as keyof typeof prisma].update({
            ...args,
            data: {
              status: 'deleted',
              deletedAt: new Date(),
            },
          });
        }

        return query(args);
      },

      async findMany({ args, query }) {
        // Automatically filter out soft-deleted records
        const modelName = (query as any).model;
        const hasDeletedAt = ['User', 'Team', 'Tenant'].includes(modelName);

        if (hasDeletedAt && !args.where?.status) {
          args.where = {
            ...args.where,
            status: {
              not: 'deleted',
            },
          };
        }

        return query(args);
      },

      async findFirst({ args, query }) {
        // Automatically filter out soft-deleted records
        const modelName = (query as any).model;
        const hasDeletedAt = ['User', 'Team', 'Tenant'].includes(modelName);

        if (hasDeletedAt && !args.where?.status) {
          args.where = {
            ...args.where,
            status: {
              not: 'deleted',
            },
          };
        }

        return query(args);
      },
    },
  },

  result: {
    user: {
      fullName: {
        needs: { firstName: true, lastName: true },
        compute(user) {
          const firstName = user.firstName || '';
          const lastName = user.lastName || '';
          return `${firstName} ${lastName}`.trim() || null;
        },
      },
    },

    tenant: {
      isActive: {
        needs: { status: true },
        compute(tenant) {
          return tenant.status === 'active';
        },
      },
    },

    billingSubscription: {
      isActive: {
        needs: { status: true },
        compute(subscription) {
          return ['active', 'trialing'].includes(subscription.status);
        },
      },

      daysUntilRenewal: {
        needs: { currentPeriodEnd: true },
        compute(subscription) {
          const now = new Date();
          const endDate = new Date(subscription.currentPeriodEnd);
          const diffTime = endDate.getTime() - now.getTime();
          const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
          return Math.max(0, diffDays);
        },
      },
    },
  },
});

// =============================================================================
// TENANT ISOLATION HELPERS
// =============================================================================

export function createTenantContext(tenantId: string) {
  return {
    prisma: extendedPrisma.$extends({
      query: {
        $allModels: {
          async create({ args, query }) {
            // Automatically add tenantId to create operations for tenant-isolated models
            const modelName = (query as any).model;
            const hasTenantId = [
              'User', 'Team', 'TeamMember', 'TeamInvitation', 'TeamProject', 'TeamResource',
              'Role', 'RoleAssignment', 'Policy', 'BillingSubscription', 'BillingInvoice',
              'BillingAlert', 'UsageRecord', 'AuditLog', 'ApiKey', 'WebhookEndpoint'
            ].includes(modelName);

            if (hasTenantId && !args.data.tenantId) {
              args.data.tenantId = tenantId;
            }

            return query(args);
          },

          async findMany({ args, query }) {
            // Automatically filter by tenantId for tenant-isolated models
            const modelName = (query as any).model;
            const hasTenantId = [
              'User', 'Team', 'TeamMember', 'TeamInvitation', 'TeamProject', 'TeamResource',
              'Role', 'RoleAssignment', 'Policy', 'BillingSubscription', 'BillingInvoice',
              'BillingAlert', 'UsageRecord', 'AuditLog', 'ApiKey', 'WebhookEndpoint'
            ].includes(modelName);

            if (hasTenantId && !args.where?.tenantId) {
              args.where = {
                ...args.where,
                tenantId,
              };
            }

            return query(args);
          },

          async findFirst({ args, query }) {
            // Automatically filter by tenantId for tenant-isolated models
            const modelName = (query as any).model;
            const hasTenantId = [
              'User', 'Team', 'TeamMember', 'TeamInvitation', 'TeamProject', 'TeamResource',
              'Role', 'RoleAssignment', 'Policy', 'BillingSubscription', 'BillingInvoice',
              'BillingAlert', 'UsageRecord', 'AuditLog', 'ApiKey', 'WebhookEndpoint'
            ].includes(modelName);

            if (hasTenantId && !args.where?.tenantId) {
              args.where = {
                ...args.where,
                tenantId,
              };
            }

            return query(args);
          },

          async update({ args, query }) {
            // Ensure updates are scoped to tenant
            const modelName = (query as any).model;
            const hasTenantId = [
              'User', 'Team', 'TeamMember', 'TeamInvitation', 'TeamProject', 'TeamResource',
              'Role', 'RoleAssignment', 'Policy', 'BillingSubscription', 'BillingInvoice',
              'BillingAlert', 'UsageRecord', 'AuditLog', 'ApiKey', 'WebhookEndpoint'
            ].includes(modelName);

            if (hasTenantId && !args.where?.tenantId) {
              args.where = {
                ...args.where,
                tenantId,
              };
            }

            return query(args);
          },

          async delete({ args, query }) {
            // Ensure deletes are scoped to tenant
            const modelName = (query as any).model;
            const hasTenantId = [
              'User', 'Team', 'TeamMember', 'TeamInvitation', 'TeamProject', 'TeamResource',
              'Role', 'RoleAssignment', 'Policy', 'BillingSubscription', 'BillingInvoice',
              'BillingAlert', 'UsageRecord', 'AuditLog', 'ApiKey', 'WebhookEndpoint'
            ].includes(modelName);

            if (hasTenantId && !args.where?.tenantId) {
              args.where = {
                ...args.where,
                tenantId,
              };
            }

            return query(args);
          },
        },
      },
    }),
  };
}

// =============================================================================
// PAGINATION HELPERS
// =============================================================================

export function createPaginationArgs(page: number = 1, limit: number = 10) {
  const skip = (page - 1) * limit;
  const take = Math.min(limit, 100); // Maximum 100 items per page

  return {
    skip,
    take,
  };
}

export async function paginateQuery<T>(
  query: () => Promise<T[]>,
  countQuery: () => Promise<number>,
  page: number = 1,
  limit: number = 10
) {
  const [data, total] = await Promise.all([
    query(),
    countQuery(),
  ]);

  const totalPages = Math.ceil(total / limit);

  return {
    data,
    pagination: {
      page,
      limit,
      total,
      totalPages,
      hasNext: page < totalPages,
      hasPrev: page > 1,
    },
  };
}

// =============================================================================
// SEEDING HELPERS
// =============================================================================

export async function upsertTenant(data: {
  slug: string;
  name: string;
  domain?: string;
  subdomain?: string;
}) {
  return prisma.tenant.upsert({
    where: { slug: data.slug },
    update: {
      name: data.name,
      domain: data.domain,
      subdomain: data.subdomain,
    },
    create: data,
  });
}

export async function upsertUser(data: {
  email: string;
  tenantId: string;
  firstName?: string;
  lastName?: string;
  passwordHash?: string;
}) {
  return prisma.user.upsert({
    where: {
      tenantId_email: {
        tenantId: data.tenantId,
        email: data.email,
      },
    },
    update: {
      firstName: data.firstName,
      lastName: data.lastName,
      passwordHash: data.passwordHash,
    },
    create: data,
  });
}

// =============================================================================
// EXPORT DEFAULT
// =============================================================================

export default extendedPrisma;