import winston from 'winston';
import { config } from '@/config';

// =============================================================================
// LOGGER CONFIGURATION
// =============================================================================

const logLevels = {
  error: 0,
  warn: 1,
  info: 2,
  http: 3,
  debug: 4,
};

const logColors = {
  error: 'red',
  warn: 'yellow',
  info: 'green',
  http: 'magenta',
  debug: 'white',
};

winston.addColors(logColors);

// =============================================================================
// FORMATTERS
// =============================================================================

const consoleFormat = winston.format.combine(
  winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss:ms' }),
  winston.format.colorize({ all: true }),
  winston.format.printf((info) => {
    const { timestamp, level, message, ...meta } = info;
    const metaString = Object.keys(meta).length ? JSON.stringify(meta, null, 2) : '';
    return `${timestamp} [${level}]: ${message} ${metaString}`;
  })
);

const fileFormat = winston.format.combine(
  winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss:ms' }),
  winston.format.errors({ stack: true }),
  winston.format.json()
);

// =============================================================================
// TRANSPORTS
// =============================================================================

const transports: winston.transport[] = [];

// Console transport (always enabled in development)
if (config.env === 'development') {
  transports.push(
    new winston.transports.Console({
      format: consoleFormat,
      level: 'debug',
    })
  );
} else {
  transports.push(
    new winston.transports.Console({
      format: fileFormat,
      level: 'info',
    })
  );
}

// File transports (for production and staging)
if (config.env !== 'development') {
  // Error logs
  transports.push(
    new winston.transports.File({
      filename: 'logs/error.log',
      level: 'error',
      format: fileFormat,
      maxsize: 5242880, // 5MB
      maxFiles: 5,
    })
  );

  // Combined logs
  transports.push(
    new winston.transports.File({
      filename: 'logs/combined.log',
      format: fileFormat,
      maxsize: 5242880, // 5MB
      maxFiles: 5,
    })
  );

  // HTTP logs
  transports.push(
    new winston.transports.File({
      filename: 'logs/http.log',
      level: 'http',
      format: fileFormat,
      maxsize: 5242880, // 5MB
      maxFiles: 3,
    })
  );
}

// =============================================================================
// LOGGER INSTANCE
// =============================================================================

export const logger = winston.createLogger({
  level: config.env === 'development' ? 'debug' : 'info',
  levels: logLevels,
  format: fileFormat,
  transports,
  exitOnError: false,
  silent: process.env.NODE_ENV === 'test',
});

// =============================================================================
// ENHANCED LOGGING METHODS
// =============================================================================

export class Logger {
  private context?: string;

  constructor(context?: string) {
    this.context = context;
  }

  private formatMessage(message: string, meta?: any): { message: string; meta: any } {
    const contextPrefix = this.context ? `[${this.context}] ` : '';
    return {
      message: `${contextPrefix}${message}`,
      meta: meta || {},
    };
  }

  debug(message: string, meta?: any): void {
    const { message: formattedMessage, meta: formattedMeta } = this.formatMessage(message, meta);
    logger.debug(formattedMessage, formattedMeta);
  }

  info(message: string, meta?: any): void {
    const { message: formattedMessage, meta: formattedMeta } = this.formatMessage(message, meta);
    logger.info(formattedMessage, formattedMeta);
  }

  warn(message: string, meta?: any): void {
    const { message: formattedMessage, meta: formattedMeta } = this.formatMessage(message, meta);
    logger.warn(formattedMessage, formattedMeta);
  }

  error(message: string, error?: Error | any, meta?: any): void {
    const { message: formattedMessage, meta: formattedMeta } = this.formatMessage(message, meta);

    if (error instanceof Error) {
      logger.error(formattedMessage, {
        ...formattedMeta,
        error: {
          message: error.message,
          stack: error.stack,
          name: error.name,
        },
      });
    } else if (error) {
      logger.error(formattedMessage, {
        ...formattedMeta,
        error,
      });
    } else {
      logger.error(formattedMessage, formattedMeta);
    }
  }

  http(message: string, meta?: any): void {
    const { message: formattedMessage, meta: formattedMeta } = this.formatMessage(message, meta);
    logger.http(formattedMessage, formattedMeta);
  }

  // Security-specific logging
  security(event: string, details: any, severity: 'low' | 'medium' | 'high' | 'critical' = 'medium'): void {
    const message = `SECURITY EVENT: ${event}`;
    const meta = {
      securityEvent: true,
      severity,
      timestamp: new Date().toISOString(),
      ...details,
    };

    if (severity === 'critical' || severity === 'high') {
      logger.error(message, meta);
    } else if (severity === 'medium') {
      logger.warn(message, meta);
    } else {
      logger.info(message, meta);
    }
  }

  // Audit logging
  audit(action: string, details: any): void {
    const message = `AUDIT: ${action}`;
    const meta = {
      auditLog: true,
      timestamp: new Date().toISOString(),
      ...details,
    };

    logger.info(message, meta);
  }

  // Performance logging
  performance(operation: string, duration: number, details?: any): void {
    const message = `PERFORMANCE: ${operation} completed in ${duration}ms`;
    const meta = {
      performanceLog: true,
      operation,
      duration,
      timestamp: new Date().toISOString(),
      ...details,
    };

    if (duration > 5000) { // Log as warning if operation takes > 5 seconds
      logger.warn(message, meta);
    } else {
      logger.info(message, meta);
    }
  }

  // Business logic logging
  business(event: string, details: any): void {
    const message = `BUSINESS EVENT: ${event}`;
    const meta = {
      businessEvent: true,
      timestamp: new Date().toISOString(),
      ...details,
    };

    logger.info(message, meta);
  }
}

// =============================================================================
// LOGGER FACTORY
// =============================================================================

export function createLogger(context: string): Logger {
  return new Logger(context);
}

// =============================================================================
// DEFAULT LOGGER INSTANCE
// =============================================================================

export const defaultLogger = new Logger();

// =============================================================================
// HTTP REQUEST LOGGER MIDDLEWARE
// =============================================================================

export function createHttpLogger() {
  return (req: any, res: any, next: any) => {
    const start = Date.now();

    // Log request
    logger.http('HTTP Request', {
      method: req.method,
      url: req.url,
      userAgent: req.get('User-Agent'),
      ip: req.ip,
      requestId: req.context?.requestId,
      tenantId: req.context?.tenant?.id,
      userId: req.context?.user?.id,
    });

    // Override res.end to log response
    const originalEnd = res.end;
    res.end = function(...args: any[]) {
      const duration = Date.now() - start;

      logger.http('HTTP Response', {
        method: req.method,
        url: req.url,
        statusCode: res.statusCode,
        duration,
        requestId: req.context?.requestId,
        tenantId: req.context?.tenant?.id,
        userId: req.context?.user?.id,
      });

      originalEnd.apply(this, args);
    };

    next();
  };
}

// =============================================================================
// ERROR HANDLER
// =============================================================================

export function logError(error: Error, context?: any): void {
  logger.error('Unhandled error', error, context);
}

export function logUnhandledRejection(reason: any, promise: Promise<any>): void {
  logger.error('Unhandled promise rejection', {
    reason,
    promise,
  });
}

export function logUncaughtException(error: Error): void {
  logger.error('Uncaught exception', error);
}

// =============================================================================
// HEALTH CHECK LOGGING
// =============================================================================

export function logHealthCheck(service: string, healthy: boolean, details?: any): void {
  const message = `Health check: ${service} is ${healthy ? 'healthy' : 'unhealthy'}`;

  if (healthy) {
    logger.info(message, { service, healthy, ...details });
  } else {
    logger.error(message, { service, healthy, ...details });
  }
}

// =============================================================================
// STARTUP LOGGING
// =============================================================================

export function logStartup(port: number, env: string): void {
  logger.info(`🚀 Server started on port ${port} in ${env} environment`);
}

export function logShutdown(signal: string): void {
  logger.info(`🛑 Server shutting down due to ${signal}`);
}

// =============================================================================
// DEPRECATION WARNING
// =============================================================================

export function logDeprecation(feature: string, alternative?: string): void {
  const message = `DEPRECATION WARNING: ${feature} is deprecated${alternative ? ` and will be replaced by ${alternative}` : ''}`;
  logger.warn(message, { deprecation: true, feature, alternative });
}

// =============================================================================
// EXPORT DEFAULT LOGGER
// =============================================================================

export default logger;