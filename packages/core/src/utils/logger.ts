/**
 * Production-safe logging utility
 * 
 * Replaces console.* calls with environment-aware logging that can be
 * controlled and disabled in production builds.
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error'

interface LogContext {
  [key: string]: any
}

class ProductionLogger {
  private context: string
  private isDevelopment: boolean
  
  constructor(context: string) {
    this.context = context
    this.isDevelopment = process.env.NODE_ENV === 'development' || process.env.NODE_ENV === 'test'
  }
  
  /**
   * Log debug message (development only)
   */
  debug(message: string, data?: LogContext): void {
    if (this.isDevelopment) {
      console.debug(`[${this.context}] ${message}`, data || '')
    }
  }
  
  /**
   * Log info message
   */
  info(message: string, data?: LogContext): void {
    if (this.isDevelopment || process.env.NEXT_PUBLIC_ENABLE_LOGGING === 'true') {
      console.info(`[${this.context}] ${message}`, data || '')
    }
  }
  
  /**
   * Log warning message
   */
  warn(message: string, data?: LogContext): void {
    console.warn(`[${this.context}] ${message}`, data || '')
  }
  
  /**
   * Log error message
   */
  error(message: string, error?: Error | LogContext): void {
    console.error(`[${this.context}] ${message}`, error || '')
  }
}

/**
 * Create a production-safe logger instance
 * 
 * @example
 * ```ts
 * import { createLogger } from '@/utils/logger'
 * 
 * const logger = createLogger('MyComponent')
 * logger.debug('Debug message') // Only in development
 * logger.info('Info message')   // Development or when enabled
 * logger.error('Error', err)    // Always logged
 * ```
 */
export function createLogger(context: string): ProductionLogger {
  return new ProductionLogger(context)
}

/**
 * Default logger instance
 */
export const logger = new ProductionLogger('app')
