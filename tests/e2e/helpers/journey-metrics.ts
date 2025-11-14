/**
 * Journey Performance Metrics Tracker
 * 
 * Tracks timing, checkpoints, and performance metrics for user journeys.
 * Validates that user experience meets documented performance expectations.
 */

export interface JourneyCheckpoint {
  name: string;
  timestamp: number;
  elapsedMs: number;
  metadata?: Record<string, any>;
}

export interface JourneyMetrics {
  journeyName: string;
  startTime: number;
  endTime?: number;
  totalTime?: number;
  checkpoints: JourneyCheckpoint[];
  success: boolean;
  errorMessage?: string;
}

/**
 * Journey Metrics Tracker
 */
export class JourneyMetricsTracker {
  private journeyName: string = '';
  private startTime: number = 0;
  private checkpoints: JourneyCheckpoint[] = [];
  private metadata: Record<string, any> = {};

  /**
   * Start tracking a new journey
   */
  startJourney(journeyName: string, metadata?: Record<string, any>): void {
    this.journeyName = journeyName;
    this.startTime = Date.now();
    this.checkpoints = [];
    this.metadata = metadata || {};
    
    console.log(`📍 Journey started: ${journeyName}`);
    if (metadata) {
      console.log(`   Metadata:`, metadata);
    }
  }

  /**
   * Record a checkpoint in the journey
   */
  checkpoint(name: string, metadata?: Record<string, any>): void {
    const now = Date.now();
    const elapsed = now - this.startTime;
    
    const checkpoint: JourneyCheckpoint = {
      name,
      timestamp: now,
      elapsedMs: elapsed,
      metadata
    };
    
    this.checkpoints.push(checkpoint);
    
    console.log(`✓ Checkpoint "${name}" reached in ${elapsed}ms`);
    if (metadata) {
      console.log(`   Metadata:`, metadata);
    }
  }

  /**
   * End the journey
   */
  endJourney(success: boolean, errorMessage?: string): JourneyMetrics {
    const endTime = Date.now();
    const totalTime = endTime - this.startTime;
    
    const status = success ? '✅' : '❌';
    console.log(`${status} Journey "${this.journeyName}" completed in ${totalTime}ms`);
    
    if (!success && errorMessage) {
      console.error(`   Error: ${errorMessage}`);
    }
    
    console.log(`   Checkpoints:`, this.checkpoints.map(c => `${c.name} (${c.elapsedMs}ms)`).join(' → '));
    
    return {
      journeyName: this.journeyName,
      startTime: this.startTime,
      endTime,
      totalTime,
      checkpoints: this.checkpoints,
      success,
      errorMessage
    };
  }

  /**
   * Get total elapsed time
   */
  totalTime(): number {
    return Date.now() - this.startTime;
  }

  /**
   * Get time between two checkpoints
   */
  timeBetween(checkpoint1: string, checkpoint2: string): number {
    const cp1 = this.checkpoints.find(c => c.name === checkpoint1);
    const cp2 = this.checkpoints.find(c => c.name === checkpoint2);
    
    if (!cp1 || !cp2) {
      throw new Error(`Checkpoint not found: ${!cp1 ? checkpoint1 : checkpoint2}`);
    }
    
    return cp2.elapsedMs - cp1.elapsedMs;
  }

  /**
   * Get checkpoint by name
   */
  getCheckpoint(name: string): JourneyCheckpoint | undefined {
    return this.checkpoints.find(c => c.name === name);
  }

  /**
   * Check if journey meets performance target
   */
  meetsTarget(targetMs: number): boolean {
    return this.totalTime() <= targetMs;
  }

  /**
   * Get performance summary
   */
  getSummary(): string {
    const total = this.totalTime();
    const checkpointSummary = this.checkpoints
      .map(c => `  - ${c.name}: ${c.elapsedMs}ms`)
      .join('\n');
    
    return `Journey: ${this.journeyName}\nTotal Time: ${total}ms\nCheckpoints:\n${checkpointSummary}`;
  }
}

/**
 * Journey Performance Expectations
 * Define expected performance for each journey stage
 */
export class PerformanceExpectations {
  private static readonly EXPECTATIONS = {
    // Developer Integrator Journey
    'developer-signup': {
      total: 30000, // 30 seconds max
      checkpoints: {
        'page-load': 3000,
        'form-fill': 5000,
        'verification': 10000,
        'dashboard-ready': 30000
      }
    },
    'sdk-integration': {
      total: 300000, // 5 minutes max (documented as "5-minute integration")
      checkpoints: {
        'npm-install': 60000,
        'code-setup': 120000,
        'first-auth': 180000,
        'integration-complete': 300000
      }
    },

    // End User Journey
    'end-user-signup': {
      total: 30000, // 30 seconds max
      checkpoints: {
        'page-load': 2000,
        'form-submit': 5000,
        'verification-sent': 10000,
        'account-active': 30000
      }
    },
    'end-user-login': {
      total: 5000, // 5 seconds max
      checkpoints: {
        'page-load': 2000,
        'credentials-entered': 3000,
        'authenticated': 5000
      }
    },
    'mfa-setup': {
      total: 60000, // 1 minute max
      checkpoints: {
        'security-page-load': 3000,
        'qr-code-shown': 5000,
        'code-verified': 30000,
        'mfa-enabled': 60000
      }
    },

    // Security Admin Journey
    'security-audit-log-view': {
      total: 10000, // 10 seconds max
      checkpoints: {
        'page-load': 3000,
        'logs-fetched': 7000,
        'logs-displayed': 10000
      }
    },
    'sso-configuration': {
      total: 120000, // 2 minutes max
      checkpoints: {
        'config-page-load': 3000,
        'form-filled': 60000,
        'config-saved': 90000,
        'sso-tested': 120000
      }
    },

    // Business Decision Maker Journey
    'pricing-evaluation': {
      total: 60000, // 1 minute max
      checkpoints: {
        'pricing-page-load': 3000,
        'calculator-used': 30000,
        'comparison-viewed': 60000
      }
    },
    'trial-signup': {
      total: 60000, // 1 minute max
      checkpoints: {
        'signup-page-load': 3000,
        'form-completed': 30000,
        'account-created': 45000,
        'dashboard-ready': 60000
      }
    }
  };

  /**
   * Get performance expectations for a journey
   */
  static getExpectations(journeyName: string) {
    return this.EXPECTATIONS[journeyName as keyof typeof this.EXPECTATIONS];
  }

  /**
   * Validate journey performance against expectations
   */
  static validate(metrics: JourneyMetrics): {
    passedTotal: boolean;
    passedCheckpoints: Map<string, boolean>;
    report: string;
  } {
    const expectations = this.getExpectations(metrics.journeyName);
    
    if (!expectations) {
      return {
        passedTotal: true,
        passedCheckpoints: new Map(),
        report: `No performance expectations defined for journey: ${metrics.journeyName}`
      };
    }

    // Validate total time
    const passedTotal = (metrics.totalTime || 0) <= expectations.total;
    
    // Validate checkpoints
    const passedCheckpoints = new Map<string, boolean>();
    
    for (const checkpoint of metrics.checkpoints) {
      const expectedTime = expectations.checkpoints[checkpoint.name as keyof typeof expectations.checkpoints];
      
      if (expectedTime) {
        const passed = checkpoint.elapsedMs <= expectedTime;
        passedCheckpoints.set(checkpoint.name, passed);
      }
    }

    // Generate report
    const totalStatus = passedTotal ? '✅' : '❌';
    const totalReport = `${totalStatus} Total time: ${metrics.totalTime}ms (expected: ${expectations.total}ms)`;
    
    const checkpointReports = Array.from(passedCheckpoints.entries()).map(([name, passed]) => {
      const checkpoint = metrics.checkpoints.find(c => c.name === name);
      const expected = expectations.checkpoints[name as keyof typeof expectations.checkpoints];
      const status = passed ? '✅' : '❌';
      return `${status} ${name}: ${checkpoint?.elapsedMs}ms (expected: ${expected}ms)`;
    });

    const report = [totalReport, ...checkpointReports].join('\n');
    
    return {
      passedTotal,
      passedCheckpoints,
      report
    };
  }
}

/**
 * Metrics Aggregator
 * Collect and analyze metrics across multiple test runs
 */
export class MetricsAggregator {
  private metrics: JourneyMetrics[] = [];

  /**
   * Add journey metrics
   */
  add(metrics: JourneyMetrics): void {
    this.metrics.push(metrics);
  }

  /**
   * Get average time for a journey
   */
  getAverageTime(journeyName: string): number {
    const journeyMetrics = this.metrics.filter(m => m.journeyName === journeyName);
    
    if (journeyMetrics.length === 0) return 0;
    
    const total = journeyMetrics.reduce((sum, m) => sum + (m.totalTime || 0), 0);
    return total / journeyMetrics.length;
  }

  /**
   * Get success rate for a journey
   */
  getSuccessRate(journeyName: string): number {
    const journeyMetrics = this.metrics.filter(m => m.journeyName === journeyName);
    
    if (journeyMetrics.length === 0) return 0;
    
    const successful = journeyMetrics.filter(m => m.success).length;
    return (successful / journeyMetrics.length) * 100;
  }

  /**
   * Get p95 latency for a checkpoint
   */
  getP95Checkpoint(journeyName: string, checkpointName: string): number {
    const journeyMetrics = this.metrics.filter(m => m.journeyName === journeyName);
    
    const checkpointTimes = journeyMetrics
      .map(m => m.checkpoints.find(c => c.name === checkpointName)?.elapsedMs)
      .filter((t): t is number => t !== undefined)
      .sort((a, b) => a - b);
    
    if (checkpointTimes.length === 0) return 0;
    
    const p95Index = Math.floor(checkpointTimes.length * 0.95);
    return checkpointTimes[p95Index];
  }

  /**
   * Generate comprehensive report
   */
  generateReport(): string {
    const uniqueJourneys = [...new Set(this.metrics.map(m => m.journeyName))];
    
    const reports = uniqueJourneys.map(journey => {
      const avgTime = this.getAverageTime(journey);
      const successRate = this.getSuccessRate(journey);
      
      return `Journey: ${journey}\n` +
             `  Average Time: ${avgTime.toFixed(0)}ms\n` +
             `  Success Rate: ${successRate.toFixed(1)}%`;
    });

    return reports.join('\n\n');
  }

  /**
   * Export metrics to JSON
   */
  exportJSON(): string {
    return JSON.stringify(this.metrics, null, 2);
  }

  /**
   * Clear all metrics
   */
  clear(): void {
    this.metrics = [];
  }
}
