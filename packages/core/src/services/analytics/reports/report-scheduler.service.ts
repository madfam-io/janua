/**
 * Report Scheduler Service
 * Handles scheduled report execution and delivery
 * Extracted from AnalyticsReportingService
 */

import { EventEmitter } from 'events';
import {
  Report,
  ReportSchedule
} from '../core/types';

export interface ReportExecutor {
  executeReportForExport(reportId: string, format: ReportSchedule['format']): Promise<any>;
}

export interface ScheduledJob {
  reportId: string;
  schedule: ReportSchedule;
  nextRun: Date;
  lastRun?: Date;
  enabled: boolean;
}

export class ReportSchedulerService extends EventEmitter {
  private scheduledJobs: Map<string, ScheduledJob> = new Map();
  private schedulerTimer?: NodeJS.Timeout;

  constructor(
    private readonly reportExecutor: ReportExecutor,
    private readonly checkInterval: number = 60000 // Check every minute
  ) {
    super();
    this.startScheduler();
  }

  /**
   * Schedule a report
   */
  scheduleReport(report: Report): void {
    if (!report.schedule) {
      throw new Error('Report has no schedule configuration');
    }

    const job: ScheduledJob = {
      reportId: report.id,
      schedule: report.schedule,
      nextRun: this.calculateNextRun(report.schedule),
      enabled: true
    };

    this.scheduledJobs.set(report.id, job);

    this.emit('report:scheduled', {
      reportId: report.id,
      nextRun: job.nextRun
    });
  }

  /**
   * Unschedule a report
   */
  unscheduleReport(reportId: string): boolean {
    const job = this.scheduledJobs.get(reportId);
    if (!job) {
      return false;
    }

    this.scheduledJobs.delete(reportId);

    this.emit('report:unscheduled', { reportId });

    return true;
  }

  /**
   * Enable/disable scheduled job
   */
  setJobEnabled(reportId: string, enabled: boolean): boolean {
    const job = this.scheduledJobs.get(reportId);
    if (!job) {
      return false;
    }

    job.enabled = enabled;

    this.emit('report:schedule_updated', {
      reportId,
      enabled
    });

    return true;
  }

  /**
   * Get scheduled job
   */
  getScheduledJob(reportId: string): ScheduledJob | null {
    return this.scheduledJobs.get(reportId) || null;
  }

  /**
   * List all scheduled jobs
   */
  listScheduledJobs(filter?: { enabled?: boolean }): ScheduledJob[] {
    let jobs = Array.from(this.scheduledJobs.values());

    if (filter?.enabled !== undefined) {
      jobs = jobs.filter(j => j.enabled === filter.enabled);
    }

    return jobs.sort((a, b) => a.nextRun.getTime() - b.nextRun.getTime());
  }

  /**
   * Update schedule for a report
   */
  updateSchedule(reportId: string, schedule: ReportSchedule): boolean {
    const job = this.scheduledJobs.get(reportId);
    if (!job) {
      return false;
    }

    job.schedule = schedule;
    job.nextRun = this.calculateNextRun(schedule);

    this.emit('report:schedule_updated', {
      reportId,
      nextRun: job.nextRun
    });

    return true;
  }

  /**
   * Manually trigger a scheduled report
   */
  async triggerReport(reportId: string): Promise<void> {
    const job = this.scheduledJobs.get(reportId);
    if (!job) {
      throw new Error(`No scheduled job found for report ${reportId}`);
    }

    await this.executeScheduledReport(job);
  }

  /**
   * Private: Start the scheduler
   */
  private startScheduler(): void {
    this.schedulerTimer = setInterval(async () => {
      await this.checkAndExecuteJobs();
    }, this.checkInterval);

    this.emit('scheduler:started', { checkInterval: this.checkInterval });
  }

  /**
   * Private: Check and execute due jobs
   */
  private async checkAndExecuteJobs(): Promise<void> {
    const now = new Date();
    const dueJobs = Array.from(this.scheduledJobs.values()).filter(
      job => job.enabled && job.nextRun <= now
    );

    if (dueJobs.length === 0) {
      return;
    }

    this.emit('scheduler:checking', {
      totalJobs: this.scheduledJobs.size,
      dueJobs: dueJobs.length
    });

    for (const job of dueJobs) {
      try {
        await this.executeScheduledReport(job);
      } catch (error) {
        this.emit('report:execution_failed', {
          reportId: job.reportId,
          error
        });
      }
    }
  }

  /**
   * Private: Execute a scheduled report
   */
  private async executeScheduledReport(job: ScheduledJob): Promise<void> {
    const startTime = Date.now();

    try {
      // Execute report with export format
      const result = await this.reportExecutor.executeReportForExport(
        job.reportId,
        job.schedule.format
      );

      // Update job
      job.lastRun = new Date();
      job.nextRun = this.calculateNextRun(job.schedule, job.lastRun);

      // Emit success event with delivery info
      this.emit('report:executed_scheduled', {
        reportId: job.reportId,
        executionTimeMs: Date.now() - startTime,
        format: job.schedule.format,
        recipients: job.schedule.recipients,
        nextRun: job.nextRun
      });

      // In production, this would trigger actual delivery
      // e.g., email service, webhook, Slack notification
      this.emit('report:delivery_required', {
        reportId: job.reportId,
        result,
        format: job.schedule.format,
        recipients: job.schedule.recipients
      });
    } catch (error) {
      this.emit('report:execution_failed', {
        reportId: job.reportId,
        error,
        executionTimeMs: Date.now() - startTime
      });

      throw error;
    }
  }

  /**
   * Private: Calculate next run time
   */
  private calculateNextRun(schedule: ReportSchedule, from?: Date): Date {
    const base = from || new Date();
    const next = new Date(base);

    // Parse timezone (simplified - in production use proper timezone library)
    // For now, assume UTC or local time

    switch (schedule.frequency) {
      case 'hourly':
        next.setHours(next.getHours() + 1);
        next.setMinutes(0);
        next.setSeconds(0);
        next.setMilliseconds(0);
        break;

      case 'daily':
        if (schedule.time) {
          const [hours, minutes] = schedule.time.split(':').map(Number);
          next.setHours(hours, minutes, 0, 0);

          // If time has passed today, schedule for tomorrow
          if (next <= base) {
            next.setDate(next.getDate() + 1);
          }
        } else {
          next.setDate(next.getDate() + 1);
          next.setHours(0, 0, 0, 0);
        }
        break;

      case 'weekly':
        if (schedule.day_of_week !== undefined) {
          const targetDay = schedule.day_of_week;
          const currentDay = next.getDay();
          let daysUntilTarget = targetDay - currentDay;

          if (daysUntilTarget <= 0) {
            daysUntilTarget += 7;
          }

          next.setDate(next.getDate() + daysUntilTarget);

          if (schedule.time) {
            const [hours, minutes] = schedule.time.split(':').map(Number);
            next.setHours(hours, minutes, 0, 0);
          } else {
            next.setHours(0, 0, 0, 0);
          }
        }
        break;

      case 'monthly':
        if (schedule.day_of_month) {
          next.setDate(schedule.day_of_month);

          // If day has passed this month, move to next month
          if (next <= base) {
            next.setMonth(next.getMonth() + 1);
          }

          if (schedule.time) {
            const [hours, minutes] = schedule.time.split(':').map(Number);
            next.setHours(hours, minutes, 0, 0);
          } else {
            next.setHours(0, 0, 0, 0);
          }
        } else {
          // Default to first of next month
          next.setMonth(next.getMonth() + 1);
          next.setDate(1);
          next.setHours(0, 0, 0, 0);
        }
        break;
    }

    return next;
  }

  /**
   * Get scheduler statistics
   */
  getStats(): {
    totalJobs: number;
    enabledJobs: number;
    disabledJobs: number;
    nextJob?: { reportId: string; nextRun: Date };
  } {
    const jobs = Array.from(this.scheduledJobs.values());

    const enabled = jobs.filter(j => j.enabled);
    const nextJob = enabled.sort((a, b) => a.nextRun.getTime() - b.nextRun.getTime())[0];

    return {
      totalJobs: jobs.length,
      enabledJobs: enabled.length,
      disabledJobs: jobs.length - enabled.length,
      nextJob: nextJob
        ? { reportId: nextJob.reportId, nextRun: nextJob.nextRun }
        : undefined
    };
  }

  /**
   * Cleanup
   */
  destroy(): void {
    if (this.schedulerTimer) {
      clearInterval(this.schedulerTimer);
    }
    this.scheduledJobs.clear();
    this.removeAllListeners();
  }
}
