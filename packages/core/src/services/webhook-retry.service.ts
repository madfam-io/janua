/**
 * Webhook Retry and Dead Letter Queue Service
 * Manages webhook delivery with exponential backoff, retries, and DLQ
 */

import { EventEmitter } from 'events';
import crypto from 'crypto';
import axios, { AxiosError, AxiosRequestConfig } from 'axios';

export interface WebhookPayload {
  id: string;
  webhook_id: string;
  organization_id: string;
  url: string;
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  headers: Record<string, string>;
  body: any;
  event_type: string;
  event_id: string;
  timestamp: Date;
  signature?: string;
  metadata?: Record<string, any>;
}

export interface WebhookAttempt {
  id: string;
  payload_id: string;
  attempt_number: number;
  status: 'pending' | 'success' | 'failed' | 'timeout' | 'dlq';
  status_code?: number;
  response_body?: any;
  error_message?: string;
  latency_ms?: number;
  attempted_at: Date;
  next_retry_at?: Date;
}

export interface WebhookDelivery {
  id: string;
  payload: WebhookPayload;
  attempts: WebhookAttempt[];
  status: 'pending' | 'delivered' | 'failed' | 'dlq';
  created_at: Date;
  delivered_at?: Date;
  failed_at?: Date;
  dlq_at?: Date;
  dlq_reason?: string;
}

export interface DeadLetterEntry {
  id: string;
  delivery_id: string;
  payload: WebhookPayload;
  attempts: WebhookAttempt[];
  reason: string;
  error_summary: string;
  entered_dlq_at: Date;
  expires_at: Date;
  can_retry: boolean;
  retry_count: number;
  metadata?: Record<string, any>;
}

export interface RetryConfig {
  max_attempts: number;
  initial_delay_ms: number;
  max_delay_ms: number;
  multiplier: number;
  jitter: boolean;
  timeout_ms: number;
  retry_on_status: number[];
  dlq_after_attempts: number;
  dlq_ttl_days: number;
}

export interface CircuitBreakerConfig {
  failure_threshold: number;
  success_threshold: number;
  timeout_ms: number;
  monitoring_period_ms: number;
  half_open_max_attempts: number;
}

export interface WebhookMetrics {
  total_deliveries: number;
  successful_deliveries: number;
  failed_deliveries: number;
  dlq_entries: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  success_rate: number;
  retry_rate: number;
}

class CircuitBreaker {
  private state: 'closed' | 'open' | 'half-open' = 'closed';
  private failures: number = 0;
  private successes: number = 0;
  private lastFailureTime?: Date;
  private halfOpenAttempts: number = 0;

  constructor(private config: CircuitBreakerConfig) {}

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.state === 'open') {
      if (this.shouldAttemptReset()) {
        this.state = 'half-open';
        this.halfOpenAttempts = 0;
      } else {
        throw new Error('Circuit breaker is open');
      }
    }

    if (this.state === 'half-open' && this.halfOpenAttempts >= this.config.half_open_max_attempts) {
      throw new Error('Circuit breaker is half-open, max attempts reached');
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private onSuccess(): void {
    this.failures = 0;
    
    if (this.state === 'half-open') {
      this.successes++;
      if (this.successes >= this.config.success_threshold) {
        this.state = 'closed';
        this.successes = 0;
        this.halfOpenAttempts = 0;
      }
    }
  }

  private onFailure(): void {
    this.failures++;
    this.lastFailureTime = new Date();

    if (this.state === 'half-open') {
      this.state = 'open';
      this.successes = 0;
      this.halfOpenAttempts++;
    } else if (this.failures >= this.config.failure_threshold) {
      this.state = 'open';
    }
  }

  private shouldAttemptReset(): boolean {
    return (
      this.lastFailureTime &&
      Date.now() - this.lastFailureTime.getTime() >= this.config.timeout_ms
    );
  }

  getState(): string {
    return this.state;
  }
}

export class WebhookRetryService extends EventEmitter {
  private deliveries: Map<string, WebhookDelivery> = new Map();
  private deadLetterQueue: Map<string, DeadLetterEntry> = new Map();
  private retryQueue: Array<{ delivery_id: string; execute_at: Date }> = [];
  private circuitBreakers: Map<string, CircuitBreaker> = new Map();
  private metrics: Map<string, number[]> = new Map(); // For latency tracking
  private processingInterval?: NodeJS.Timeout;

  constructor(
    private readonly config: {
      retry?: Partial<RetryConfig>;
      circuit_breaker?: Partial<CircuitBreakerConfig>;
      batch_size?: number;
      process_interval_ms?: number;
      enable_signature?: boolean;
      signature_header?: string;
      signature_secret?: string;
    } = {}
  ) {
    super();
    this.startProcessing();
  }

  /**
   * Send a webhook with retry logic
   */
  async sendWebhook(payload: WebhookPayload): Promise<WebhookDelivery> {
    const delivery: WebhookDelivery = {
      id: crypto.randomUUID(),
      payload,
      attempts: [],
      status: 'pending',
      created_at: new Date()
    };

    this.deliveries.set(delivery.id, delivery);

    // Execute first attempt immediately
    await this.executeDelivery(delivery);

    return delivery;
  }

  /**
   * Bulk send webhooks
   */
  async sendBulkWebhooks(payloads: WebhookPayload[]): Promise<WebhookDelivery[]> {
    const deliveries: WebhookDelivery[] = [];

    // Process in batches to avoid overwhelming the system
    const batchSize = this.config.batch_size || 10;
    
    for (let i = 0; i < payloads.length; i += batchSize) {
      const batch = payloads.slice(i, i + batchSize);
      const batchDeliveries = await Promise.all(
        batch.map(payload => this.sendWebhook(payload))
      );
      deliveries.push(...batchDeliveries);
    }

    return deliveries;
  }

  /**
   * Execute webhook delivery
   */
  private async executeDelivery(delivery: WebhookDelivery): Promise<void> {
    const retryConfig = this.getRetryConfig();
    const attemptNumber = delivery.attempts.length + 1;

    if (attemptNumber > retryConfig.max_attempts) {
      await this.moveToDeadLetterQueue(delivery, 'Max retries exceeded');
      return;
    }

    const attempt: WebhookAttempt = {
      id: crypto.randomUUID(),
      payload_id: delivery.payload.id,
      attempt_number: attemptNumber,
      status: 'pending',
      attempted_at: new Date()
    };

    delivery.attempts.push(attempt);

    try {
      // Get or create circuit breaker for this URL
      const breaker = this.getCircuitBreaker(delivery.payload.url);

      // Execute with circuit breaker
      const startTime = Date.now();
      const response = await breaker.execute(() => this.makeHttpRequest(delivery.payload));
      const latency = Date.now() - startTime;

      // Record success
      attempt.status = 'success';
      attempt.status_code = response.status;
      attempt.response_body = response.data;
      attempt.latency_ms = latency;

      delivery.status = 'delivered';
      delivery.delivered_at = new Date();

      this.recordLatency(delivery.payload.url, latency);
      this.emit('webhook:delivered', { delivery_id: delivery.id, attempt_number: attemptNumber });

    } catch (error: any) {
      // Handle failure
      attempt.status = 'failed';
      
      if (error.response) {
        attempt.status_code = error.response.status;
        attempt.response_body = error.response.data;
        attempt.error_message = error.response.statusText;
      } else if (error.code === 'ECONNABORTED') {
        attempt.status = 'timeout';
        attempt.error_message = 'Request timeout';
      } else {
        attempt.error_message = error.message;
      }

      // Check if we should retry
      if (this.shouldRetry(attempt, retryConfig)) {
        const delay = this.calculateDelay(attemptNumber, retryConfig);
        attempt.next_retry_at = new Date(Date.now() + delay);
        
        this.scheduleRetry(delivery.id, attempt.next_retry_at);
        
        this.emit('webhook:retry-scheduled', {
          delivery_id: delivery.id,
          attempt_number: attemptNumber,
          next_retry_at: attempt.next_retry_at
        });
      } else {
        // Move to DLQ if retries exhausted or non-retryable error
        const reason = attemptNumber >= retryConfig.dlq_after_attempts
          ? 'DLQ threshold reached'
          : 'Non-retryable error';
        
        await this.moveToDeadLetterQueue(delivery, reason);
      }
    }
  }

  /**
   * Make HTTP request
   */
  private async makeHttpRequest(payload: WebhookPayload): Promise<any> {
    const retryConfig = this.getRetryConfig();

    // Prepare headers
    const headers = { ...payload.headers };

    // Add signature if configured
    if (this.config.enable_signature && this.config.signature_secret) {
      const signature = this.generateSignature(payload);
      headers[this.config.signature_header || 'X-Webhook-Signature'] = signature;
    }

    // Add standard webhook headers
    headers['X-Webhook-ID'] = payload.id;
    headers['X-Webhook-Event'] = payload.event_type;
    headers['X-Webhook-Timestamp'] = payload.timestamp.toISOString();

    const axiosConfig: AxiosRequestConfig = {
      method: payload.method,
      url: payload.url,
      headers,
      data: payload.body,
      timeout: retryConfig.timeout_ms,
      validateStatus: (status) => status < 500 // Don't throw on 4xx
    };

    return await axios(axiosConfig);
  }

  /**
   * Generate webhook signature
   */
  private generateSignature(payload: WebhookPayload): string {
    if (!this.config.signature_secret) {
      throw new Error('Signature secret not configured');
    }

    const timestamp = Math.floor(payload.timestamp.getTime() / 1000);
    const message = `${timestamp}.${JSON.stringify(payload.body)}`;
    
    const hmac = crypto.createHmac('sha256', this.config.signature_secret);
    hmac.update(message);
    
    return `t=${timestamp},v1=${hmac.digest('hex')}`;
  }

  /**
   * Verify webhook signature (for receivers)
   */
  verifySignature(signature: string, body: any, secret: string): boolean {
    const parts = signature.split(',');
    const timestamp = parts[0]?.replace('t=', '');
    const hash = parts[1]?.replace('v1=', '');

    if (!timestamp || !hash) return false;

    // Check timestamp is within 5 minutes
    const currentTime = Math.floor(Date.now() / 1000);
    if (Math.abs(currentTime - parseInt(timestamp)) > 300) {
      return false;
    }

    // Verify signature
    const message = `${timestamp}.${JSON.stringify(body)}`;
    const expectedHash = crypto.createHmac('sha256', secret)
      .update(message)
      .digest('hex');

    return crypto.timingSafeEqual(
      Buffer.from(hash),
      Buffer.from(expectedHash)
    );
  }

  /**
   * Move delivery to Dead Letter Queue
   */
  private async moveToDeadLetterQueue(
    delivery: WebhookDelivery,
    reason: string
  ): Promise<void> {
    delivery.status = 'dlq';
    delivery.dlq_at = new Date();
    delivery.dlq_reason = reason;

    const retryConfig = this.getRetryConfig();
    
    const dlqEntry: DeadLetterEntry = {
      id: crypto.randomUUID(),
      delivery_id: delivery.id,
      payload: delivery.payload,
      attempts: delivery.attempts,
      reason,
      error_summary: this.summarizeErrors(delivery.attempts),
      entered_dlq_at: new Date(),
      expires_at: new Date(Date.now() + retryConfig.dlq_ttl_days * 86400000),
      can_retry: true,
      retry_count: 0
    };

    this.deadLetterQueue.set(dlqEntry.id, dlqEntry);

    this.emit('webhook:dlq', {
      delivery_id: delivery.id,
      dlq_id: dlqEntry.id,
      reason
    });
  }

  /**
   * Retry delivery from DLQ
   */
  async retryFromDLQ(dlq_id: string): Promise<WebhookDelivery | null> {
    const dlqEntry = this.deadLetterQueue.get(dlq_id);
    
    if (!dlqEntry) {
      throw new Error('DLQ entry not found');
    }

    if (!dlqEntry.can_retry) {
      throw new Error('DLQ entry cannot be retried');
    }

    // Create new delivery from DLQ entry
    const delivery: WebhookDelivery = {
      id: crypto.randomUUID(),
      payload: dlqEntry.payload,
      attempts: [],
      status: 'pending',
      created_at: new Date()
    };

    this.deliveries.set(delivery.id, delivery);
    
    // Update DLQ entry
    dlqEntry.retry_count++;
    if (dlqEntry.retry_count >= 3) {
      dlqEntry.can_retry = false;
    }

    // Execute delivery
    await this.executeDelivery(delivery);

    // Remove from DLQ if successful
    if (delivery.status === 'delivered') {
      this.deadLetterQueue.delete(dlq_id);
    }

    return delivery;
  }

  /**
   * Bulk retry from DLQ
   */
  async bulkRetryFromDLQ(
    filter?: (entry: DeadLetterEntry) => boolean
  ): Promise<{ successful: number; failed: number }> {
    const entries = Array.from(this.deadLetterQueue.values());
    const toRetry = filter ? entries.filter(filter) : entries;

    let successful = 0;
    let failed = 0;

    for (const entry of toRetry) {
      if (!entry.can_retry) continue;

      try {
        const delivery = await this.retryFromDLQ(entry.id);
        if (delivery?.status === 'delivered') {
          successful++;
        } else {
          failed++;
        }
      } catch {
        failed++;
      }
    }

    return { successful, failed };
  }

  /**
   * Get DLQ entries
   */
  getDLQEntries(
    filters?: {
      organization_id?: string;
      event_type?: string;
      can_retry?: boolean;
      since?: Date;
    }
  ): DeadLetterEntry[] {
    let entries = Array.from(this.deadLetterQueue.values());

    if (filters) {
      if (filters.organization_id) {
        entries = entries.filter(e => e.payload.organization_id === filters.organization_id);
      }
      if (filters.event_type) {
        entries = entries.filter(e => e.payload.event_type === filters.event_type);
      }
      if (filters.can_retry !== undefined) {
        entries = entries.filter(e => e.can_retry === filters.can_retry);
      }
      if (filters.since) {
        entries = entries.filter(e => e.entered_dlq_at >= filters.since);
      }
    }

    return entries.sort((a, b) => b.entered_dlq_at.getTime() - a.entered_dlq_at.getTime());
  }

  /**
   * Purge expired DLQ entries
   */
  purgeExpiredDLQEntries(): number {
    const now = new Date();
    let purged = 0;

    for (const [id, entry] of this.deadLetterQueue) {
      if (entry.expires_at < now) {
        this.deadLetterQueue.delete(id);
        purged++;
      }
    }

    if (purged > 0) {
      this.emit('dlq:purged', { count: purged });
    }

    return purged;
  }

  /**
   * Get delivery status
   */
  getDelivery(delivery_id: string): WebhookDelivery | null {
    return this.deliveries.get(delivery_id) || null;
  }

  /**
   * Get metrics
   */
  getMetrics(): WebhookMetrics {
    const deliveries = Array.from(this.deliveries.values());
    
    const metrics: WebhookMetrics = {
      total_deliveries: deliveries.length,
      successful_deliveries: deliveries.filter(d => d.status === 'delivered').length,
      failed_deliveries: deliveries.filter(d => d.status === 'failed').length,
      dlq_entries: this.deadLetterQueue.size,
      avg_latency_ms: 0,
      p95_latency_ms: 0,
      p99_latency_ms: 0,
      success_rate: 0,
      retry_rate: 0
    };

    // Calculate latency metrics
    const allLatencies: number[] = [];
    for (const latencies of this.metrics.values()) {
      allLatencies.push(...latencies);
    }

    if (allLatencies.length > 0) {
      allLatencies.sort((a, b) => a - b);
      metrics.avg_latency_ms = allLatencies.reduce((a, b) => a + b, 0) / allLatencies.length;
      metrics.p95_latency_ms = allLatencies[Math.floor(allLatencies.length * 0.95)] || 0;
      metrics.p99_latency_ms = allLatencies[Math.floor(allLatencies.length * 0.99)] || 0;
    }

    // Calculate rates
    if (metrics.total_deliveries > 0) {
      metrics.success_rate = metrics.successful_deliveries / metrics.total_deliveries;
      
      const retriedDeliveries = deliveries.filter(d => d.attempts.length > 1).length;
      metrics.retry_rate = retriedDeliveries / metrics.total_deliveries;
    }

    return metrics;
  }

  /**
   * Get metrics by organization
   */
  getOrganizationMetrics(organization_id: string): WebhookMetrics {
    const deliveries = Array.from(this.deliveries.values())
      .filter(d => d.payload.organization_id === organization_id);

    // Similar calculation as getMetrics but filtered by organization
    return this.calculateMetrics(deliveries);
  }

  /**
   * Private: Calculate metrics for a set of deliveries
   */
  private calculateMetrics(deliveries: WebhookDelivery[]): WebhookMetrics {
    const metrics: WebhookMetrics = {
      total_deliveries: deliveries.length,
      successful_deliveries: deliveries.filter(d => d.status === 'delivered').length,
      failed_deliveries: deliveries.filter(d => d.status === 'failed').length,
      dlq_entries: 0, // Count from DLQ
      avg_latency_ms: 0,
      p95_latency_ms: 0,
      p99_latency_ms: 0,
      success_rate: 0,
      retry_rate: 0
    };

    // Count DLQ entries for these deliveries
    for (const entry of this.deadLetterQueue.values()) {
      if (deliveries.some(d => d.id === entry.delivery_id)) {
        metrics.dlq_entries++;
      }
    }

    // Calculate latencies
    const latencies: number[] = [];
    for (const delivery of deliveries) {
      for (const attempt of delivery.attempts) {
        if (attempt.latency_ms) {
          latencies.push(attempt.latency_ms);
        }
      }
    }

    if (latencies.length > 0) {
      latencies.sort((a, b) => a - b);
      metrics.avg_latency_ms = latencies.reduce((a, b) => a + b, 0) / latencies.length;
      metrics.p95_latency_ms = latencies[Math.floor(latencies.length * 0.95)] || 0;
      metrics.p99_latency_ms = latencies[Math.floor(latencies.length * 0.99)] || 0;
    }

    // Calculate rates
    if (metrics.total_deliveries > 0) {
      metrics.success_rate = metrics.successful_deliveries / metrics.total_deliveries;
      
      const retriedDeliveries = deliveries.filter(d => d.attempts.length > 1).length;
      metrics.retry_rate = retriedDeliveries / metrics.total_deliveries;
    }

    return metrics;
  }

  /**
   * Private: Get retry configuration
   */
  private getRetryConfig(): RetryConfig {
    return {
      max_attempts: 5,
      initial_delay_ms: 1000,
      max_delay_ms: 60000,
      multiplier: 2,
      jitter: true,
      timeout_ms: 30000,
      retry_on_status: [429, 500, 502, 503, 504],
      dlq_after_attempts: 3,
      dlq_ttl_days: 30,
      ...this.config.retry
    };
  }

  /**
   * Private: Get circuit breaker for URL
   */
  private getCircuitBreaker(url: string): CircuitBreaker {
    const host = new URL(url).host;
    
    if (!this.circuitBreakers.has(host)) {
      const config: CircuitBreakerConfig = {
        failure_threshold: 5,
        success_threshold: 3,
        timeout_ms: 60000,
        monitoring_period_ms: 300000,
        half_open_max_attempts: 3,
        ...this.config.circuit_breaker
      };
      
      this.circuitBreakers.set(host, new CircuitBreaker(config));
    }

    return this.circuitBreakers.get(host)!;
  }

  /**
   * Private: Should retry attempt
   */
  private shouldRetry(attempt: WebhookAttempt, config: RetryConfig): boolean {
    if (attempt.status === 'timeout') return true;
    if (attempt.status_code && config.retry_on_status.includes(attempt.status_code)) return true;
    if (attempt.status_code && attempt.status_code >= 500) return true;
    return false;
  }

  /**
   * Private: Calculate retry delay
   */
  private calculateDelay(attemptNumber: number, config: RetryConfig): number {
    let delay = config.initial_delay_ms * Math.pow(config.multiplier, attemptNumber - 1);
    
    // Apply max delay cap
    delay = Math.min(delay, config.max_delay_ms);

    // Add jitter
    if (config.jitter) {
      delay = delay * (0.5 + Math.random() * 0.5);
    }

    return Math.floor(delay);
  }

  /**
   * Private: Schedule retry
   */
  private scheduleRetry(delivery_id: string, execute_at: Date): void {
    this.retryQueue.push({ delivery_id, execute_at });
    this.retryQueue.sort((a, b) => a.execute_at.getTime() - b.execute_at.getTime());
  }

  /**
   * Private: Process retry queue
   */
  private async processRetryQueue(): Promise<void> {
    const now = new Date();
    
    while (this.retryQueue.length > 0 && this.retryQueue[0].execute_at <= now) {
      const item = this.retryQueue.shift()!;
      const delivery = this.deliveries.get(item.delivery_id);
      
      if (delivery && delivery.status === 'pending') {
        await this.executeDelivery(delivery);
      }
    }
  }

  /**
   * Private: Record latency
   */
  private recordLatency(url: string, latency: number): void {
    const host = new URL(url).host;
    
    if (!this.metrics.has(host)) {
      this.metrics.set(host, []);
    }

    const latencies = this.metrics.get(host)!;
    latencies.push(latency);

    // Keep only last 1000 measurements
    if (latencies.length > 1000) {
      latencies.shift();
    }
  }

  /**
   * Private: Summarize errors
   */
  private summarizeErrors(attempts: WebhookAttempt[]): string {
    const errors = attempts
      .filter(a => a.status === 'failed')
      .map(a => a.error_message || `HTTP ${a.status_code}`)
      .filter((e, i, arr) => arr.indexOf(e) === i); // Unique

    return errors.join(', ');
  }

  /**
   * Private: Start processing
   */
  private startProcessing(): void {
    const interval = this.config.process_interval_ms || 5000;
    
    this.processingInterval = setInterval(async () => {
      await this.processRetryQueue();
      
      // Purge expired DLQ entries periodically
      if (Math.random() < 0.01) { // 1% chance each interval
        this.purgeExpiredDLQEntries();
      }
    }, interval);
  }

  /**
   * Stop processing
   */
  stop(): void {
    if (this.processingInterval) {
      clearInterval(this.processingInterval);
      this.processingInterval = undefined;
    }
  }
}

// Export factory function
export function createWebhookRetryService(config?: any): WebhookRetryService {
  return new WebhookRetryService(config);
}