/**
 * Widget Executor Service
 * Handles widget execution and data retrieval
 * Extracted from AnalyticsReportingService
 */

import { EventEmitter } from 'events';
import {
  ReportWidget,
  AnalyticsQuery,
  QueryResult,
  VisualizationConfig,
  MetricDefinition
} from '../core/types';

export interface QueryExecutor {
  execute(query: AnalyticsQuery): Promise<QueryResult>;
}

export interface MetricSource {
  getMetric(metricId: string): MetricDefinition | undefined;
}

export class WidgetExecutorService extends EventEmitter {
  constructor(
    private readonly queryExecutor: QueryExecutor,
    private readonly metricSource: MetricSource
  ) {
    super();
  }

  /**
   * Execute a single widget
   */
  async executeWidget(widget: ReportWidget): Promise<any> {
    const startTime = Date.now();

    try {
      const metric = this.metricSource.getMetric(widget.metric_id);
      if (!metric) {
        throw new Error(`Metric ${widget.metric_id} not found`);
      }

      // Build query from widget configuration
      const query: AnalyticsQuery = {
        metrics: [widget.metric_id],
        time_range: widget.time_range,
        filters: widget.filters
          ? Object.entries(widget.filters).map(([k, v]) => ({
              dimension: k,
              operator: 'equals' as const,
              value: v
            }))
          : undefined
      };

      // Execute query
      const result = await this.queryExecutor.execute(query);

      // Format for visualization
      const formatted = this.formatForVisualization(result.data, widget.visualization);

      const executionTimeMs = Date.now() - startTime;

      this.emit('widget:executed', {
        widgetId: widget.id,
        metricId: widget.metric_id,
        executionTimeMs,
        rowCount: result.data.length
      });

      return formatted;
    } catch (error) {
      const executionTimeMs = Date.now() - startTime;

      this.emit('widget:failed', {
        widgetId: widget.id,
        metricId: widget.metric_id,
        executionTimeMs,
        error
      });

      throw error;
    }
  }

  /**
   * Execute multiple widgets in parallel
   */
  async executeWidgets(widgets: ReportWidget[]): Promise<
    Array<{
      widgetId: string;
      data: any;
      error?: string;
    }>
  > {
    const results = await Promise.allSettled(
      widgets.map(widget => this.executeWidget(widget))
    );

    return results.map((result, index) => {
      if (result.status === 'fulfilled') {
        return {
          widgetId: widgets[index].id,
          data: result.value
        };
      } else {
        return {
          widgetId: widgets[index].id,
          data: null,
          error: result.reason instanceof Error ? result.reason.message : 'Unknown error'
        };
      }
    });
  }

  /**
   * Get widget data preview (limited rows)
   */
  async getWidgetPreview(widget: ReportWidget, limit: number = 10): Promise<any> {
    const metric = this.metricSource.getMetric(widget.metric_id);
    if (!metric) {
      throw new Error(`Metric ${widget.metric_id} not found`);
    }

    const query: AnalyticsQuery = {
      metrics: [widget.metric_id],
      time_range: widget.time_range,
      filters: widget.filters
        ? Object.entries(widget.filters).map(([k, v]) => ({
            dimension: k,
            operator: 'equals' as const,
            value: v
          }))
        : undefined,
      limit
    };

    const result = await this.queryExecutor.execute(query);

    return this.formatForVisualization(result.data, widget.visualization);
  }

  /**
   * Validate widget configuration
   */
  async validateWidget(widget: ReportWidget): Promise<{
    valid: boolean;
    errors: string[];
  }> {
    const errors: string[] = [];

    // Check metric exists
    const metric = this.metricSource.getMetric(widget.metric_id);
    if (!metric) {
      errors.push(`Metric ${widget.metric_id} not found`);
    }

    // Validate time range
    if (!widget.time_range) {
      errors.push('Time range is required');
    } else {
      if (widget.time_range.type === 'relative') {
        if (!widget.time_range.relative) {
          errors.push('Relative time range configuration is missing');
        }
      } else if (widget.time_range.type === 'absolute') {
        if (!widget.time_range.absolute) {
          errors.push('Absolute time range configuration is missing');
        } else {
          if (widget.time_range.absolute.start >= widget.time_range.absolute.end) {
            errors.push('Start date must be before end date');
          }
        }
      }
    }

    // Validate visualization config
    if (widget.type === 'chart' && !widget.visualization.chart_type) {
      errors.push('Chart type is required for chart widgets');
    }

    return {
      valid: errors.length === 0,
      errors
    };
  }

  /**
   * Private: Format data for visualization
   */
  private formatForVisualization(data: any[], config: VisualizationConfig): any {
    // Basic formatting - in production this would be more sophisticated
    if (!config.chart_type) {
      return data;
    }

    switch (config.chart_type) {
      case 'pie':
      case 'donut':
        // Format for pie/donut charts
        return this.formatForPieChart(data);

      case 'line':
      case 'area':
        // Format for time series charts
        return this.formatForTimeSeriesChart(data);

      case 'bar':
        // Format for bar charts
        return this.formatForBarChart(data);

      default:
        return data;
    }
  }

  /**
   * Private: Format for pie/donut charts
   */
  private formatForPieChart(data: any[]): any {
    return data.map(item => ({
      label: item.timestamp || item.dimension || 'Unknown',
      value: item.value || 0
    }));
  }

  /**
   * Private: Format for time series charts
   */
  private formatForTimeSeriesChart(data: any[]): any {
    return {
      labels: data.map(item => item.timestamp),
      datasets: [
        {
          data: data.map(item => item.value)
        }
      ]
    };
  }

  /**
   * Private: Format for bar charts
   */
  private formatForBarChart(data: any[]): any {
    return {
      labels: data.map(item => item.timestamp || item.dimension || 'Unknown'),
      values: data.map(item => item.value || 0)
    };
  }

  /**
   * Cleanup
   */
  destroy(): void {
    this.removeAllListeners();
  }
}
