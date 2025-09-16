import Redis from 'ioredis';
import { config } from '@/config';

// =============================================================================
// REDIS CLIENT CONFIGURATION
// =============================================================================

const globalForRedis = globalThis as unknown as {
  redis: Redis | undefined;
};

export const redis =
  globalForRedis.redis ??
  new Redis({
    host: config.redis.host,
    port: config.redis.port,
    password: config.redis.password,
    db: config.redis.db,
    keyPrefix: config.redis.keyPrefix,
    maxRetriesPerRequest: 3,
    retryDelayOnFailover: 100,
    enableReadyCheck: true,
    lazyConnect: true,
    keepAlive: 30000,
    family: 4,
    connectTimeout: 10000,
    commandTimeout: 5000,
  });

if (config.env !== 'production') {
  globalForRedis.redis = redis;
}

// =============================================================================
// REDIS CONNECTION MANAGEMENT
// =============================================================================

export async function connectRedis(): Promise<void> {
  try {
    await redis.connect();
    console.log('📦 Redis connected successfully');

    // Test Redis connection
    await redis.ping();
    console.log('✅ Redis connectivity verified');
  } catch (error) {
    console.error('❌ Failed to connect to Redis:', error);
    // Don't exit process for Redis failures - app can work without cache
  }
}

export async function disconnectRedis(): Promise<void> {
  try {
    await redis.disconnect();
    console.log('📦 Redis disconnected successfully');
  } catch (error) {
    console.error('❌ Failed to disconnect from Redis:', error);
  }
}

// =============================================================================
// REDIS HEALTH CHECK
// =============================================================================

export async function checkRedisHealth(): Promise<{
  healthy: boolean;
  latency: number;
  error?: string;
}> {
  const start = Date.now();

  try {
    await redis.ping();
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
// CACHE HELPERS
// =============================================================================

export class CacheService {
  private defaultTTL = 300; // 5 minutes

  async get<T>(key: string): Promise<T | null> {
    try {
      const value = await redis.get(key);
      return value ? JSON.parse(value) : null;
    } catch (error) {
      console.error('Cache get error:', error);
      return null;
    }
  }

  async set<T>(key: string, value: T, ttlSeconds?: number): Promise<boolean> {
    try {
      const ttl = ttlSeconds || this.defaultTTL;
      await redis.setex(key, ttl, JSON.stringify(value));
      return true;
    } catch (error) {
      console.error('Cache set error:', error);
      return false;
    }
  }

  async del(key: string): Promise<boolean> {
    try {
      await redis.del(key);
      return true;
    } catch (error) {
      console.error('Cache delete error:', error);
      return false;
    }
  }

  async exists(key: string): Promise<boolean> {
    try {
      const result = await redis.exists(key);
      return result === 1;
    } catch (error) {
      console.error('Cache exists error:', error);
      return false;
    }
  }

  async increment(key: string, amount: number = 1): Promise<number> {
    try {
      return await redis.incrby(key, amount);
    } catch (error) {
      console.error('Cache increment error:', error);
      return 0;
    }
  }

  async expire(key: string, ttlSeconds: number): Promise<boolean> {
    try {
      await redis.expire(key, ttlSeconds);
      return true;
    } catch (error) {
      console.error('Cache expire error:', error);
      return false;
    }
  }

  async mget<T>(keys: string[]): Promise<(T | null)[]> {
    try {
      const values = await redis.mget(keys);
      return values.map(value => value ? JSON.parse(value) : null);
    } catch (error) {
      console.error('Cache mget error:', error);
      return keys.map(() => null);
    }
  }

  async mset<T>(keyValuePairs: Array<{ key: string; value: T; ttl?: number }>): Promise<boolean> {
    try {
      const pipeline = redis.pipeline();

      for (const { key, value, ttl } of keyValuePairs) {
        const ttlToUse = ttl || this.defaultTTL;
        pipeline.setex(key, ttlToUse, JSON.stringify(value));
      }

      await pipeline.exec();
      return true;
    } catch (error) {
      console.error('Cache mset error:', error);
      return false;
    }
  }

  async clearPattern(pattern: string): Promise<number> {
    try {
      const keys = await redis.keys(pattern);
      if (keys.length === 0) return 0;

      await redis.del(keys);
      return keys.length;
    } catch (error) {
      console.error('Cache clear pattern error:', error);
      return 0;
    }
  }
}

export const cache = new CacheService();

// =============================================================================
// SESSION STORAGE
// =============================================================================

export class SessionService {
  private keyPrefix = 'session:';
  private defaultTTL = 86400; // 24 hours

  async createSession(sessionId: string, data: any, ttlSeconds?: number): Promise<boolean> {
    const key = `${this.keyPrefix}${sessionId}`;
    const ttl = ttlSeconds || this.defaultTTL;

    try {
      await redis.setex(key, ttl, JSON.stringify(data));
      return true;
    } catch (error) {
      console.error('Session create error:', error);
      return false;
    }
  }

  async getSession(sessionId: string): Promise<any | null> {
    const key = `${this.keyPrefix}${sessionId}`;

    try {
      const value = await redis.get(key);
      return value ? JSON.parse(value) : null;
    } catch (error) {
      console.error('Session get error:', error);
      return null;
    }
  }

  async updateSession(sessionId: string, data: any, ttlSeconds?: number): Promise<boolean> {
    const key = `${this.keyPrefix}${sessionId}`;

    try {
      const existing = await this.getSession(sessionId);
      if (!existing) return false;

      const updated = { ...existing, ...data };
      const ttl = ttlSeconds || this.defaultTTL;

      await redis.setex(key, ttl, JSON.stringify(updated));
      return true;
    } catch (error) {
      console.error('Session update error:', error);
      return false;
    }
  }

  async destroySession(sessionId: string): Promise<boolean> {
    const key = `${this.keyPrefix}${sessionId}`;

    try {
      await redis.del(key);
      return true;
    } catch (error) {
      console.error('Session destroy error:', error);
      return false;
    }
  }

  async extendSession(sessionId: string, ttlSeconds?: number): Promise<boolean> {
    const key = `${this.keyPrefix}${sessionId}`;
    const ttl = ttlSeconds || this.defaultTTL;

    try {
      await redis.expire(key, ttl);
      return true;
    } catch (error) {
      console.error('Session extend error:', error);
      return false;
    }
  }

  async getUserSessions(userId: string): Promise<string[]> {
    const pattern = `${this.keyPrefix}*`;

    try {
      const keys = await redis.keys(pattern);
      const sessions: string[] = [];

      for (const key of keys) {
        const value = await redis.get(key);
        if (value) {
          const data = JSON.parse(value);
          if (data.userId === userId) {
            sessions.push(key.replace(this.keyPrefix, ''));
          }
        }
      }

      return sessions;
    } catch (error) {
      console.error('Get user sessions error:', error);
      return [];
    }
  }

  async destroyUserSessions(userId: string): Promise<number> {
    try {
      const sessions = await this.getUserSessions(userId);
      const keys = sessions.map(sessionId => `${this.keyPrefix}${sessionId}`);

      if (keys.length === 0) return 0;

      await redis.del(keys);
      return keys.length;
    } catch (error) {
      console.error('Destroy user sessions error:', error);
      return 0;
    }
  }
}

export const sessionStore = new SessionService();

// =============================================================================
// RATE LIMITING
// =============================================================================

export class RateLimitService {
  private keyPrefix = 'ratelimit:';

  async checkRateLimit(
    identifier: string,
    windowMs: number,
    maxRequests: number
  ): Promise<{
    allowed: boolean;
    remaining: number;
    resetTime: number;
    totalHits: number;
  }> {
    const key = `${this.keyPrefix}${identifier}`;
    const now = Date.now();
    const windowStart = now - windowMs;

    try {
      // Use Redis sorted set to track requests within window
      const pipeline = redis.pipeline();

      // Remove old requests outside the window
      pipeline.zremrangebyscore(key, '-inf', windowStart);

      // Add current request
      pipeline.zadd(key, now, `${now}-${Math.random()}`);

      // Count requests in current window
      pipeline.zcard(key);

      // Set expiration
      pipeline.expire(key, Math.ceil(windowMs / 1000));

      const results = await pipeline.exec();

      if (!results || results.some(([err]) => err)) {
        throw new Error('Rate limit pipeline failed');
      }

      const totalHits = results[2]?.[1] as number || 0;
      const remaining = Math.max(0, maxRequests - totalHits);
      const allowed = totalHits <= maxRequests;
      const resetTime = now + windowMs;

      return {
        allowed,
        remaining,
        resetTime,
        totalHits,
      };
    } catch (error) {
      console.error('Rate limit check error:', error);
      // On error, allow the request (fail open)
      return {
        allowed: true,
        remaining: maxRequests - 1,
        resetTime: now + windowMs,
        totalHits: 1,
      };
    }
  }

  async resetRateLimit(identifier: string): Promise<boolean> {
    const key = `${this.keyPrefix}${identifier}`;

    try {
      await redis.del(key);
      return true;
    } catch (error) {
      console.error('Rate limit reset error:', error);
      return false;
    }
  }
}

export const rateLimiter = new RateLimitService();

// =============================================================================
// BACKGROUND JOBS QUEUE
// =============================================================================

export class JobQueue {
  private queueName = 'jobs';

  async addJob(jobData: {
    type: string;
    payload: any;
    priority?: number;
    delay?: number;
    maxAttempts?: number;
  }): Promise<string> {
    const jobId = `job:${Date.now()}:${Math.random().toString(36).substr(2, 9)}`;
    const priority = jobData.priority || 0;
    const delay = jobData.delay || 0;
    const scheduleTime = Date.now() + delay;

    const job = {
      id: jobId,
      type: jobData.type,
      payload: jobData.payload,
      priority,
      attempts: 0,
      maxAttempts: jobData.maxAttempts || 3,
      createdAt: Date.now(),
      scheduledAt: scheduleTime,
    };

    try {
      // Add to scheduled jobs sorted set
      await redis.zadd(`${this.queueName}:scheduled`, scheduleTime, JSON.stringify(job));
      return jobId;
    } catch (error) {
      console.error('Add job error:', error);
      throw error;
    }
  }

  async getNextJob(): Promise<any | null> {
    try {
      const now = Date.now();

      // Get jobs that are ready to run
      const jobs = await redis.zrangebyscore(
        `${this.queueName}:scheduled`,
        '-inf',
        now,
        'LIMIT',
        0,
        1
      );

      if (jobs.length === 0) return null;

      const jobData = JSON.parse(jobs[0]);

      // Remove from scheduled and add to processing
      const pipeline = redis.pipeline();
      pipeline.zrem(`${this.queueName}:scheduled`, jobs[0]);
      pipeline.setex(`${this.queueName}:processing:${jobData.id}`, 300, jobs[0]); // 5 min timeout

      await pipeline.exec();

      return jobData;
    } catch (error) {
      console.error('Get next job error:', error);
      return null;
    }
  }

  async completeJob(jobId: string): Promise<boolean> {
    try {
      await redis.del(`${this.queueName}:processing:${jobId}`);
      return true;
    } catch (error) {
      console.error('Complete job error:', error);
      return false;
    }
  }

  async failJob(jobId: string, error: string): Promise<boolean> {
    try {
      const jobKey = `${this.queueName}:processing:${jobId}`;
      const jobData = await redis.get(jobKey);

      if (jobData) {
        const job = JSON.parse(jobData);
        job.attempts++;
        job.lastError = error;
        job.lastAttemptAt = Date.now();

        // Remove from processing
        await redis.del(jobKey);

        // Retry if under max attempts
        if (job.attempts < job.maxAttempts) {
          const delay = Math.pow(2, job.attempts) * 1000; // Exponential backoff
          const scheduleTime = Date.now() + delay;

          await redis.zadd(`${this.queueName}:scheduled`, scheduleTime, JSON.stringify(job));
        } else {
          // Move to failed queue
          await redis.lpush(`${this.queueName}:failed`, JSON.stringify(job));
        }
      }

      return true;
    } catch (error) {
      console.error('Fail job error:', error);
      return false;
    }
  }

  async getQueueStats(): Promise<{
    scheduled: number;
    processing: number;
    failed: number;
  }> {
    try {
      const [scheduled, processingKeys, failed] = await Promise.all([
        redis.zcard(`${this.queueName}:scheduled`),
        redis.keys(`${this.queueName}:processing:*`),
        redis.llen(`${this.queueName}:failed`),
      ]);

      return {
        scheduled,
        processing: processingKeys.length,
        failed,
      };
    } catch (error) {
      console.error('Get queue stats error:', error);
      return { scheduled: 0, processing: 0, failed: 0 };
    }
  }
}

export const jobQueue = new JobQueue();

// =============================================================================
// REDIS EVENT HANDLERS
// =============================================================================

redis.on('connect', () => {
  console.log('📦 Redis connection established');
});

redis.on('ready', () => {
  console.log('✅ Redis ready for commands');
});

redis.on('error', (error) => {
  console.error('❌ Redis error:', error);
});

redis.on('close', () => {
  console.log('📦 Redis connection closed');
});

redis.on('reconnecting', () => {
  console.log('🔄 Redis reconnecting...');
});

// =============================================================================
// EXPORT DEFAULT
// =============================================================================

export default redis;