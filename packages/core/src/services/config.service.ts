/**
 * Configuration Service
 *
 * Centralized configuration management with environment-based settings
 */

export interface DatabaseConfig {
  host: string;
  port: number;
  username: string;
  password: string;
  database: string;
  ssl?: boolean;
}

export interface RedisConfig {
  host: string;
  port: number;
  password?: string;
  db?: number;
}

export interface SecurityConfig {
  jwtSecret: string;
  encryptionKey: string;
  sessionSecret: string;
  maxLoginAttempts: number;
  lockoutDuration: number;
}

export interface SecretsRotationConfig {
  rotationInterval: string;
  keyType: 'jwt' | 'api' | 'encryption' | 'signing';
  algorithm: string;
  keySize: number;
  gracePeriod: number;
  notificationChannels: string[];
}

export interface SecretsConfig {
  rotation?: SecretsRotationConfig[];
}

export interface AppConfig {
  environment: 'development' | 'staging' | 'production';
  port: number;
  database: DatabaseConfig;
  redis: RedisConfig;
  security: SecurityConfig;
  secrets?: SecretsConfig;
  enableClustering?: boolean;
  logLevel: 'debug' | 'info' | 'warn' | 'error';
  monitoringInterval?: number;
}

export class ConfigService {
  private static instance: ConfigService;
  private config: AppConfig;

  private constructor() {
    this.config = this.loadConfig();
  }

  public static getInstance(): ConfigService {
    if (!ConfigService.instance) {
      ConfigService.instance = new ConfigService();
    }
    return ConfigService.instance;
  }

  private loadConfig(): AppConfig {
    return {
      environment: (process.env.NODE_ENV as any) || 'development',
      port: parseInt(process.env.PORT || '3000'),
      database: {
        host: process.env.DB_HOST || 'localhost',
        port: parseInt(process.env.DB_PORT || '5432'),
        username: process.env.DB_USERNAME || 'postgres',
        password: process.env.DB_PASSWORD || '',
        database: process.env.DB_NAME || 'plinto',
        ssl: process.env.DB_SSL === 'true'
      },
      redis: {
        host: process.env.REDIS_HOST || 'localhost',
        port: parseInt(process.env.REDIS_PORT || '6379'),
        password: process.env.REDIS_PASSWORD,
        db: parseInt(process.env.REDIS_DB || '0')
      },
      security: this.loadSecurityConfig(),
      enableClustering: process.env.ENABLE_CLUSTERING === 'true',
      logLevel: (process.env.LOG_LEVEL as any) || 'info'
    };
  }

  private loadSecurityConfig(): SecurityConfig {
    const isProduction = (process.env.NODE_ENV as any) === 'production';

    // Get secrets from environment
    const jwtSecret = process.env.JWT_SECRET;
    const encryptionKey = process.env.ENCRYPTION_KEY;
    const sessionSecret = process.env.SESSION_SECRET;

    // In production, require all secrets to be set
    if (isProduction) {
      if (!jwtSecret || !encryptionKey || !sessionSecret) {
        throw new Error(
          'CRITICAL SECURITY ERROR: JWT_SECRET, ENCRYPTION_KEY, and SESSION_SECRET must be set in production. ' +
          'Generate secure secrets using: node -e "console.log(require(\'crypto\').randomBytes(32).toString(\'base64\'))"'
        );
      }

      // Validate secret strength (minimum 32 characters)
      if (jwtSecret.length < 32 || encryptionKey.length < 32 || sessionSecret.length < 32) {
        throw new Error(
          'CRITICAL SECURITY ERROR: All secrets must be at least 32 characters long in production'
        );
      }
    }

    return {
      jwtSecret: jwtSecret || 'dev-secret-ONLY-FOR-DEVELOPMENT',
      encryptionKey: encryptionKey || 'dev-encryption-key-ONLY-FOR-DEVELOPMENT',
      sessionSecret: sessionSecret || 'dev-session-secret-ONLY-FOR-DEVELOPMENT',
      maxLoginAttempts: parseInt(process.env.MAX_LOGIN_ATTEMPTS || '5'),
      lockoutDuration: parseInt(process.env.LOCKOUT_DURATION || '900000') // 15 minutes
    };
  }

  public get<K extends keyof AppConfig>(key: K): AppConfig[K] {
    return this.config[key];
  }

  public getAll(): AppConfig {
    return { ...this.config };
  }

  public isDevelopment(): boolean {
    return this.config.environment === 'development';
  }

  public isProduction(): boolean {
    return this.config.environment === 'production';
  }

  public isStaging(): boolean {
    return this.config.environment === 'staging';
  }
}

export const config = ConfigService.getInstance();