/**
 * Forecaster Service
 * Handles metric forecasting and prediction
 * Extracted from AnalyticsReportingService
 */

import { EventEmitter } from 'events';
import {
  TimeSeriesData
} from '../core/types';

export interface MetricDataSource {
  getMetricHistory(metricName: string, dimensions?: Record<string, string>): Promise<TimeSeriesData[]>;
}

export class ForecasterService extends EventEmitter {
  constructor(private readonly metricSource: MetricDataSource) {
    super();
  }

  /**
   * Forecast a metric using linear regression
   */
  async forecastMetric(
    metricName: string,
    periods: number,
    periodType: 'hour' | 'day' | 'week' | 'month',
    dimensions?: Record<string, string>
  ): Promise<TimeSeriesData[]> {
    const startTime = Date.now();

    const historicalData = await this.metricSource.getMetricHistory(metricName, dimensions);

    if (historicalData.length < 2) {
      throw new Error('Insufficient historical data for forecasting');
    }

    // Perform linear regression
    const forecast = this.performLinearRegression(historicalData, periods, periodType);

    const executionTime = Date.now() - startTime;

    this.emit('forecast:generated', {
      metric: metricName,
      periods,
      historicalPoints: historicalData.length,
      forecastPoints: forecast.length,
      executionTimeMs: executionTime
    });

    return forecast;
  }

  /**
   * Get trend direction for a metric
   */
  async getTrend(
    metricName: string,
    dimensions?: Record<string, string>
  ): Promise<{
    direction: 'increasing' | 'decreasing' | 'stable';
    slope: number;
    confidence: number;
  }> {
    const historicalData = await this.metricSource.getMetricHistory(metricName, dimensions);

    if (historicalData.length < 2) {
      return {
        direction: 'stable',
        slope: 0,
        confidence: 0
      };
    }

    const { slope, rSquared } = this.calculateLinearRegression(historicalData);

    let direction: 'increasing' | 'decreasing' | 'stable' = 'stable';
    if (Math.abs(slope) > 0.01) {
      direction = slope > 0 ? 'increasing' : 'decreasing';
    }

    return {
      direction,
      slope,
      confidence: rSquared
    };
  }

  /**
   * Forecast with confidence intervals
   */
  async forecastWithConfidence(
    metricName: string,
    periods: number,
    periodType: 'hour' | 'day' | 'week' | 'month',
    confidenceLevel: number = 0.95
  ): Promise<Array<{
    timestamp: Date;
    predicted: number;
    lower: number;
    upper: number;
  }>> {
    const historicalData = await this.metricSource.getMetricHistory(metricName);

    if (historicalData.length < 2) {
      throw new Error('Insufficient historical data for forecasting');
    }

    const forecast = this.performLinearRegression(historicalData, periods, periodType);
    const { standardError } = this.calculateRegressionError(historicalData);

    // Calculate confidence intervals (simplified - using standard error)
    const zScore = confidenceLevel === 0.95 ? 1.96 : 2.58; // 95% or 99%
    const marginOfError = zScore * standardError;

    return forecast.map(point => ({
      timestamp: point.timestamp,
      predicted: point.value,
      lower: Math.max(0, point.value - marginOfError),
      upper: point.value + marginOfError
    }));
  }

  /**
   * Private: Perform linear regression
   */
  private performLinearRegression(
    data: TimeSeriesData[],
    periods: number,
    periodType: string
  ): TimeSeriesData[] {
    if (data.length === 0) {
      return [];
    }

    const { slope, intercept } = this.calculateLinearRegression(data);

    const forecast: TimeSeriesData[] = [];
    const lastDate = data[data.length - 1].timestamp;

    for (let i = 1; i <= periods; i++) {
      const forecastDate = this.addPeriods(lastDate, i, periodType);
      const x = data.length + i;
      const predictedValue = slope * x + intercept;

      forecast.push({
        metric: data[0].metric,
        timestamp: forecastDate,
        value: Math.max(0, predictedValue), // Don't predict negative values
        dimensions: data[0].dimensions
      });
    }

    return forecast;
  }

  /**
   * Private: Calculate linear regression parameters
   */
  private calculateLinearRegression(data: TimeSeriesData[]): {
    slope: number;
    intercept: number;
    rSquared: number;
  } {
    const n = data.length;
    const values = data.map((d, i) => ({ x: i, y: d.value }));

    // Calculate means
    const meanX = values.reduce((sum, p) => sum + p.x, 0) / n;
    const meanY = values.reduce((sum, p) => sum + p.y, 0) / n;

    // Calculate slope and intercept
    let numerator = 0;
    let denominator = 0;

    for (const point of values) {
      numerator += (point.x - meanX) * (point.y - meanY);
      denominator += Math.pow(point.x - meanX, 2);
    }

    const slope = denominator === 0 ? 0 : numerator / denominator;
    const intercept = meanY - slope * meanX;

    // Calculate R-squared
    let ssRes = 0;
    let ssTot = 0;

    for (const point of values) {
      const predicted = slope * point.x + intercept;
      ssRes += Math.pow(point.y - predicted, 2);
      ssTot += Math.pow(point.y - meanY, 2);
    }

    const rSquared = ssTot === 0 ? 0 : 1 - (ssRes / ssTot);

    return { slope, intercept, rSquared };
  }

  /**
   * Private: Calculate regression error
   */
  private calculateRegressionError(data: TimeSeriesData[]): {
    standardError: number;
    meanAbsoluteError: number;
  } {
    const { slope, intercept } = this.calculateLinearRegression(data);
    const errors: number[] = [];

    for (let i = 0; i < data.length; i++) {
      const predicted = slope * i + intercept;
      const error = data[i].value - predicted;
      errors.push(error);
    }

    const meanError = errors.reduce((sum, e) => sum + Math.abs(e), 0) / errors.length;
    const variance = errors.reduce((sum, e) => sum + Math.pow(e, 2), 0) / errors.length;
    const standardError = Math.sqrt(variance);

    return {
      standardError,
      meanAbsoluteError: meanError
    };
  }

  /**
   * Private: Add periods to a date
   */
  private addPeriods(date: Date, periods: number, periodType: string): Date {
    const result = new Date(date);

    switch (periodType) {
      case 'hour':
        result.setHours(result.getHours() + periods);
        break;
      case 'day':
        result.setDate(result.getDate() + periods);
        break;
      case 'week':
        result.setDate(result.getDate() + periods * 7);
        break;
      case 'month':
        result.setMonth(result.getMonth() + periods);
        break;
    }

    return result;
  }

  /**
   * Cleanup
   */
  destroy(): void {
    this.removeAllListeners();
  }
}
