/**
 * Logger utility for Janua SDK
 *
 * Only logs in development mode to avoid spamming production logs
 * and prevent potential sensitive data leakage.
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LoggerConfig {
  enabled: boolean;
  level: LogLevel;
  prefix: string;
}

class SDKLogger {
  private config: LoggerConfig;

  constructor(config?: Partial<LoggerConfig>) {
    this.config = {
      enabled: process.env.NODE_ENV === 'development',
      level: 'info',
      prefix: '[Janua SDK]',
      ...config,
    };
  }

  debug(message: string, ...args: unknown[]): void {
    if (this.config.enabled && this.shouldLog('debug')) {
      console.debug(this.config.prefix, message, ...args);
    }
  }

  info(message: string, ...args: unknown[]): void {
    if (this.config.enabled && this.shouldLog('info')) {
      console.info(this.config.prefix, message, ...args);
    }
  }

  warn(message: string, ...args: unknown[]): void {
    if (this.shouldLog('warn')) {
      console.warn(this.config.prefix, message, ...args);
    }
  }

  error(message: string, ...args: unknown[]): void {
    if (this.shouldLog('error')) {
      console.error(this.config.prefix, message, ...args);
    }
  }

  private shouldLog(level: LogLevel): boolean {
    const levels: LogLevel[] = ['debug', 'info', 'warn', 'error'];
    const currentLevelIndex = levels.indexOf(this.config.level);
    const messageLevelIndex = levels.indexOf(level);
    return messageLevelIndex >= currentLevelIndex;
  }
}

// Export singleton instance
export const logger = new SDKLogger();

// Export class for custom configurations
export { SDKLogger };
