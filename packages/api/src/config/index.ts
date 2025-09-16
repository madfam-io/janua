import { z } from 'zod';
import { ServerConfig } from '@/types';

// =============================================================================
// CONFIGURATION SCHEMA
// =============================================================================

const configSchema = z.object({
  // Server configuration
  NODE_ENV: z.enum(['development', 'staging', 'production']).default('development'),
  PORT: z.string().transform(Number).default('3000'),
  HOST: z.string().default('localhost'),

  // Database configuration
  DATABASE_URL: z.string(),
  DATABASE_MAX_CONNECTIONS: z.string().transform(Number).optional(),
  DATABASE_CONNECTION_TIMEOUT: z.string().transform(Number).optional(),

  // Redis configuration
  REDIS_HOST: z.string().default('localhost'),
  REDIS_PORT: z.string().transform(Number).default('6379'),
  REDIS_PASSWORD: z.string().optional(),
  REDIS_DB: z.string().transform(Number).default('0'),
  REDIS_KEY_PREFIX: z.string().default('plinto:'),

  // JWT configuration
  JWT_ACCESS_SECRET: z.string(),
  JWT_REFRESH_SECRET: z.string(),
  JWT_ACCESS_EXPIRY: z.string().default('15m'),
  JWT_REFRESH_EXPIRY: z.string().default('7d'),
  JWT_ISSUER: z.string().default('plinto'),
  JWT_AUDIENCE: z.string().default('plinto-api'),

  // Rate limiting
  RATE_LIMIT_WINDOW_MS: z.string().transform(Number).default('900000'), // 15 minutes
  RATE_LIMIT_MAX_REQUESTS: z.string().transform(Number).default('100'),

  // Email configuration
  EMAIL_HOST: z.string().optional(),
  EMAIL_PORT: z.string().transform(Number).optional(),
  EMAIL_SECURE: z.string().transform(Boolean).default('true'),
  EMAIL_USER: z.string().optional(),
  EMAIL_PASS: z.string().optional(),
  EMAIL_FROM_NAME: z.string().default('Plinto'),
  EMAIL_FROM_ADDRESS: z.string().optional(),

  // Payment provider configuration
  STRIPE_SECRET_KEY: z.string().optional(),
  STRIPE_PUBLIC_KEY: z.string().optional(),
  STRIPE_WEBHOOK_SECRET: z.string().optional(),

  CONEKTA_PRIVATE_KEY: z.string().optional(),
  CONEKTA_PUBLIC_KEY: z.string().optional(),
  CONEKTA_WEBHOOK_SECRET: z.string().optional(),

  FUNGIES_API_KEY: z.string().optional(),
  FUNGIES_SECRET_KEY: z.string().optional(),
  FUNGIES_WEBHOOK_SECRET: z.string().optional(),

  // CORS configuration
  CORS_ORIGIN: z.string().default('*'),
  CORS_CREDENTIALS: z.string().transform(Boolean).default('true'),

  // Monitoring configuration
  MONITORING_ENABLED: z.string().transform(Boolean).default('false'),
  MONITORING_ENDPOINT: z.string().optional(),
  MONITORING_API_KEY: z.string().optional(),

  // Security configuration
  BCRYPT_ROUNDS: z.string().transform(Number).default('12'),
  SESSION_TIMEOUT_HOURS: z.string().transform(Number).default('24'),
  MAX_LOGIN_ATTEMPTS: z.string().transform(Number).default('5'),
  LOCKOUT_DURATION_MINUTES: z.string().transform(Number).default('30'),

  // WebAuthn configuration
  WEBAUTHN_RP_NAME: z.string().default('Plinto'),
  WEBAUTHN_RP_ID: z.string().optional(),
  WEBAUTHN_ORIGIN: z.string().optional(),

  // File upload configuration
  MAX_FILE_SIZE_MB: z.string().transform(Number).default('10'),
  ALLOWED_FILE_TYPES: z.string().default('image/jpeg,image/png,image/gif,application/pdf'),

  // Feature flags
  FEATURE_MFA_ENABLED: z.string().transform(Boolean).default('true'),
  FEATURE_WEBAUTHN_ENABLED: z.string().transform(Boolean).default('true'),
  FEATURE_AUDIT_LOGS_ENABLED: z.string().transform(Boolean).default('true'),
  FEATURE_RATE_LIMITING_ENABLED: z.string().transform(Boolean).default('true'),
});

// =============================================================================
// PARSE AND VALIDATE ENVIRONMENT
// =============================================================================

const rawConfig = {
  NODE_ENV: process.env.NODE_ENV,
  PORT: process.env.PORT,
  HOST: process.env.HOST,
  DATABASE_URL: process.env.DATABASE_URL,
  DATABASE_MAX_CONNECTIONS: process.env.DATABASE_MAX_CONNECTIONS,
  DATABASE_CONNECTION_TIMEOUT: process.env.DATABASE_CONNECTION_TIMEOUT,
  REDIS_HOST: process.env.REDIS_HOST,
  REDIS_PORT: process.env.REDIS_PORT,
  REDIS_PASSWORD: process.env.REDIS_PASSWORD,
  REDIS_DB: process.env.REDIS_DB,
  REDIS_KEY_PREFIX: process.env.REDIS_KEY_PREFIX,
  JWT_ACCESS_SECRET: process.env.JWT_ACCESS_SECRET,
  JWT_REFRESH_SECRET: process.env.JWT_REFRESH_SECRET,
  JWT_ACCESS_EXPIRY: process.env.JWT_ACCESS_EXPIRY,
  JWT_REFRESH_EXPIRY: process.env.JWT_REFRESH_EXPIRY,
  JWT_ISSUER: process.env.JWT_ISSUER,
  JWT_AUDIENCE: process.env.JWT_AUDIENCE,
  RATE_LIMIT_WINDOW_MS: process.env.RATE_LIMIT_WINDOW_MS,
  RATE_LIMIT_MAX_REQUESTS: process.env.RATE_LIMIT_MAX_REQUESTS,
  EMAIL_HOST: process.env.EMAIL_HOST,
  EMAIL_PORT: process.env.EMAIL_PORT,
  EMAIL_SECURE: process.env.EMAIL_SECURE,
  EMAIL_USER: process.env.EMAIL_USER,
  EMAIL_PASS: process.env.EMAIL_PASS,
  EMAIL_FROM_NAME: process.env.EMAIL_FROM_NAME,
  EMAIL_FROM_ADDRESS: process.env.EMAIL_FROM_ADDRESS,
  STRIPE_SECRET_KEY: process.env.STRIPE_SECRET_KEY,
  STRIPE_PUBLIC_KEY: process.env.STRIPE_PUBLIC_KEY,
  STRIPE_WEBHOOK_SECRET: process.env.STRIPE_WEBHOOK_SECRET,
  CONEKTA_PRIVATE_KEY: process.env.CONEKTA_PRIVATE_KEY,
  CONEKTA_PUBLIC_KEY: process.env.CONEKTA_PUBLIC_KEY,
  CONEKTA_WEBHOOK_SECRET: process.env.CONEKTA_WEBHOOK_SECRET,
  FUNGIES_API_KEY: process.env.FUNGIES_API_KEY,
  FUNGIES_SECRET_KEY: process.env.FUNGIES_SECRET_KEY,
  FUNGIES_WEBHOOK_SECRET: process.env.FUNGIES_WEBHOOK_SECRET,
  CORS_ORIGIN: process.env.CORS_ORIGIN,
  CORS_CREDENTIALS: process.env.CORS_CREDENTIALS,
  MONITORING_ENABLED: process.env.MONITORING_ENABLED,
  MONITORING_ENDPOINT: process.env.MONITORING_ENDPOINT,
  MONITORING_API_KEY: process.env.MONITORING_API_KEY,
  BCRYPT_ROUNDS: process.env.BCRYPT_ROUNDS,
  SESSION_TIMEOUT_HOURS: process.env.SESSION_TIMEOUT_HOURS,
  MAX_LOGIN_ATTEMPTS: process.env.MAX_LOGIN_ATTEMPTS,
  LOCKOUT_DURATION_MINUTES: process.env.LOCKOUT_DURATION_MINUTES,
  WEBAUTHN_RP_NAME: process.env.WEBAUTHN_RP_NAME,
  WEBAUTHN_RP_ID: process.env.WEBAUTHN_RP_ID,
  WEBAUTHN_ORIGIN: process.env.WEBAUTHN_ORIGIN,
  MAX_FILE_SIZE_MB: process.env.MAX_FILE_SIZE_MB,
  ALLOWED_FILE_TYPES: process.env.ALLOWED_FILE_TYPES,
  FEATURE_MFA_ENABLED: process.env.FEATURE_MFA_ENABLED,
  FEATURE_WEBAUTHN_ENABLED: process.env.FEATURE_WEBAUTHN_ENABLED,
  FEATURE_AUDIT_LOGS_ENABLED: process.env.FEATURE_AUDIT_LOGS_ENABLED,
  FEATURE_RATE_LIMITING_ENABLED: process.env.FEATURE_RATE_LIMITING_ENABLED,
};

// Parse and validate configuration
const parsedConfig = configSchema.parse(rawConfig);

// =============================================================================
// BUILD CONFIGURATION OBJECT
// =============================================================================

export const config: ServerConfig = {
  port: parsedConfig.PORT,
  host: parsedConfig.HOST,
  env: parsedConfig.NODE_ENV,

  database: {
    url: parsedConfig.DATABASE_URL,
    maxConnections: parsedConfig.DATABASE_MAX_CONNECTIONS,
    connectionTimeout: parsedConfig.DATABASE_CONNECTION_TIMEOUT,
    ssl: parsedConfig.NODE_ENV === 'production',
  },

  redis: {
    host: parsedConfig.REDIS_HOST,
    port: parsedConfig.REDIS_PORT,
    password: parsedConfig.REDIS_PASSWORD,
    db: parsedConfig.REDIS_DB,
    keyPrefix: parsedConfig.REDIS_KEY_PREFIX,
  },

  jwt: {
    accessTokenSecret: parsedConfig.JWT_ACCESS_SECRET,
    refreshTokenSecret: parsedConfig.JWT_REFRESH_SECRET,
    accessTokenExpiry: parsedConfig.JWT_ACCESS_EXPIRY,
    refreshTokenExpiry: parsedConfig.JWT_REFRESH_EXPIRY,
    issuer: parsedConfig.JWT_ISSUER,
    audience: parsedConfig.JWT_AUDIENCE,
  },

  rateLimit: {
    windowMs: parsedConfig.RATE_LIMIT_WINDOW_MS,
    maxRequests: parsedConfig.RATE_LIMIT_MAX_REQUESTS,
    skipSuccessfulRequests: false,
    skipFailedRequests: false,
  },

  email: {
    host: parsedConfig.EMAIL_HOST || '',
    port: parsedConfig.EMAIL_PORT || 587,
    secure: parsedConfig.EMAIL_SECURE,
    auth: {
      user: parsedConfig.EMAIL_USER || '',
      pass: parsedConfig.EMAIL_PASS || '',
    },
    from: {
      name: parsedConfig.EMAIL_FROM_NAME,
      address: parsedConfig.EMAIL_FROM_ADDRESS || '',
    },
  },

  paymentProviders: {
    stripe: parsedConfig.STRIPE_SECRET_KEY ? {
      secretKey: parsedConfig.STRIPE_SECRET_KEY,
      publicKey: parsedConfig.STRIPE_PUBLIC_KEY || '',
      webhookSecret: parsedConfig.STRIPE_WEBHOOK_SECRET || '',
    } : undefined,

    conekta: parsedConfig.CONEKTA_PRIVATE_KEY ? {
      privateKey: parsedConfig.CONEKTA_PRIVATE_KEY,
      publicKey: parsedConfig.CONEKTA_PUBLIC_KEY || '',
      webhookSecret: parsedConfig.CONEKTA_WEBHOOK_SECRET || '',
    } : undefined,

    fungies: parsedConfig.FUNGIES_API_KEY ? {
      apiKey: parsedConfig.FUNGIES_API_KEY,
      secretKey: parsedConfig.FUNGIES_SECRET_KEY || '',
      webhookSecret: parsedConfig.FUNGIES_WEBHOOK_SECRET || '',
    } : undefined,
  },

  cors: {
    origin: parsedConfig.CORS_ORIGIN === '*' ? '*' : parsedConfig.CORS_ORIGIN.split(','),
    credentials: parsedConfig.CORS_CREDENTIALS,
  },

  monitoring: {
    enabled: parsedConfig.MONITORING_ENABLED,
    endpoint: parsedConfig.MONITORING_ENDPOINT,
    apiKey: parsedConfig.MONITORING_API_KEY,
  },
};

// =============================================================================
// ADDITIONAL CONFIGURATION
// =============================================================================

export const securityConfig = {
  bcryptRounds: parsedConfig.BCRYPT_ROUNDS,
  sessionTimeoutHours: parsedConfig.SESSION_TIMEOUT_HOURS,
  maxLoginAttempts: parsedConfig.MAX_LOGIN_ATTEMPTS,
  lockoutDurationMinutes: parsedConfig.LOCKOUT_DURATION_MINUTES,
};

export const webAuthnConfig = {
  rpName: parsedConfig.WEBAUTHN_RP_NAME,
  rpID: parsedConfig.WEBAUTHN_RP_ID || (config.env === 'production' ? undefined : 'localhost'),
  origin: parsedConfig.WEBAUTHN_ORIGIN || (config.env === 'production' ? undefined : `http://localhost:${config.port}`),
};

export const uploadConfig = {
  maxFileSizeMB: parsedConfig.MAX_FILE_SIZE_MB,
  allowedFileTypes: parsedConfig.ALLOWED_FILE_TYPES.split(','),
  maxFileSizeBytes: parsedConfig.MAX_FILE_SIZE_MB * 1024 * 1024,
};

export const featureFlags = {
  mfaEnabled: parsedConfig.FEATURE_MFA_ENABLED,
  webAuthnEnabled: parsedConfig.FEATURE_WEBAUTHN_ENABLED,
  auditLogsEnabled: parsedConfig.FEATURE_AUDIT_LOGS_ENABLED,
  rateLimitingEnabled: parsedConfig.FEATURE_RATE_LIMITING_ENABLED,
};

// =============================================================================
// VALIDATION HELPER
// =============================================================================

export function validateConfig(): void {
  const requiredFields = [
    'DATABASE_URL',
    'JWT_ACCESS_SECRET',
    'JWT_REFRESH_SECRET',
  ];

  const missingFields = requiredFields.filter(field => !process.env[field]);

  if (missingFields.length > 0) {
    throw new Error(
      `Missing required environment variables: ${missingFields.join(', ')}`
    );
  }

  // Validate JWT secrets are different
  if (config.jwt.accessTokenSecret === config.jwt.refreshTokenSecret) {
    throw new Error('JWT access and refresh secrets must be different');
  }

  // Validate JWT secrets are strong enough
  if (config.jwt.accessTokenSecret.length < 32) {
    throw new Error('JWT access token secret must be at least 32 characters');
  }

  if (config.jwt.refreshTokenSecret.length < 32) {
    throw new Error('JWT refresh token secret must be at least 32 characters');
  }

  // Validate production settings
  if (config.env === 'production') {
    if (!config.paymentProviders.stripe && !config.paymentProviders.conekta && !config.paymentProviders.fungies) {
      throw new Error('At least one payment provider must be configured in production');
    }

    if (config.cors.origin === '*') {
      console.warn('Warning: CORS is set to allow all origins in production');
    }

    if (!config.monitoring.enabled) {
      console.warn('Warning: Monitoring is disabled in production');
    }
  }
}

// =============================================================================
// CONFIGURATION LOGGING
// =============================================================================

export function logConfiguration(): void {
  console.log('🔧 Server Configuration:');
  console.log(`   Environment: ${config.env}`);
  console.log(`   Server: http://${config.host}:${config.port}`);
  console.log(`   Database: ${config.database.url.replace(/\/\/.*@/, '//***:***@')}`);
  console.log(`   Redis: ${config.redis.host}:${config.redis.port}`);
  console.log(`   JWT Expiry: ${config.jwt.accessTokenExpiry} / ${config.jwt.refreshTokenExpiry}`);
  console.log(`   Rate Limit: ${config.rateLimit.maxRequests} per ${config.rateLimit.windowMs}ms`);

  const enabledProviders = Object.keys(config.paymentProviders).filter(
    key => config.paymentProviders[key as keyof typeof config.paymentProviders]
  );
  console.log(`   Payment Providers: ${enabledProviders.join(', ') || 'None'}`);

  const enabledFeatures = Object.entries(featureFlags)
    .filter(([, enabled]) => enabled)
    .map(([feature]) => feature);
  console.log(`   Features: ${enabledFeatures.join(', ')}`);
}

// Validate configuration on import
validateConfig();