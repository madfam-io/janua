/**
 * Dashboard Service
 * Handles dashboard CRUD operations
 * Extracted from AnalyticsReportingService
 */

import crypto from 'crypto';
import { EventEmitter } from 'events';
import {
  Dashboard,
  AccessControl
} from '../core/types';

export class DashboardService extends EventEmitter {
  private dashboards: Map<string, Dashboard> = new Map();

  constructor() {
    super();
  }

  /**
   * Create a new dashboard
   */
  async createDashboard(
    dashboard: Omit<Dashboard, 'id' | 'created_at' | 'updated_at'>
  ): Promise<Dashboard> {
    const fullDashboard: Dashboard = {
      ...dashboard,
      id: crypto.randomUUID(),
      created_at: new Date(),
      updated_at: new Date()
    };

    this.dashboards.set(fullDashboard.id, fullDashboard);

    this.emit('dashboard:created', fullDashboard);

    return fullDashboard;
  }

  /**
   * Get dashboard by ID
   */
  async getDashboard(dashboardId: string): Promise<Dashboard | null> {
    const dashboard = this.dashboards.get(dashboardId);
    return dashboard || null;
  }

  /**
   * List all dashboards
   */
  async listDashboards(filter?: {
    ownerId?: string;
    organizationId?: string;
  }): Promise<Dashboard[]> {
    let dashboards = Array.from(this.dashboards.values());

    if (filter?.ownerId) {
      dashboards = dashboards.filter(d => d.owner_id === filter.ownerId);
    }

    if (filter?.organizationId) {
      dashboards = dashboards.filter(d => d.organization_id === filter.organizationId);
    }

    // Sort by updated_at descending
    dashboards.sort((a, b) => b.updated_at.getTime() - a.updated_at.getTime());

    return dashboards;
  }

  /**
   * Update dashboard
   */
  async updateDashboard(
    dashboardId: string,
    updates: Partial<Omit<Dashboard, 'id' | 'created_at' | 'owner_id' | 'organization_id'>>
  ): Promise<Dashboard> {
    const dashboard = this.dashboards.get(dashboardId);
    if (!dashboard) {
      throw new Error(`Dashboard ${dashboardId} not found`);
    }

    const updatedDashboard: Dashboard = {
      ...dashboard,
      ...updates,
      id: dashboard.id,
      created_at: dashboard.created_at,
      owner_id: dashboard.owner_id,
      organization_id: dashboard.organization_id,
      updated_at: new Date()
    };

    this.dashboards.set(dashboardId, updatedDashboard);

    this.emit('dashboard:updated', {
      dashboardId,
      oldDashboard: dashboard,
      newDashboard: updatedDashboard
    });

    return updatedDashboard;
  }

  /**
   * Delete dashboard
   */
  async deleteDashboard(dashboardId: string): Promise<boolean> {
    const dashboard = this.dashboards.get(dashboardId);
    if (!dashboard) {
      return false;
    }

    this.dashboards.delete(dashboardId);

    this.emit('dashboard:deleted', { dashboardId, dashboard });

    return true;
  }

  /**
   * Check if user has access to dashboard
   */
  async checkAccess(
    dashboardId: string,
    userId: string,
    userRoles: string[] = []
  ): Promise<boolean> {
    const dashboard = this.dashboards.get(dashboardId);
    if (!dashboard) {
      return false;
    }

    // If no access control, default to owner only
    if (!dashboard.shared_with) {
      return dashboard.owner_id === userId;
    }

    const ac = dashboard.shared_with;

    // Public dashboards
    if (ac.visibility === 'public') {
      return true;
    }

    // Owner always has access
    if (dashboard.owner_id === userId) {
      return true;
    }

    // Check explicit users
    if (ac.users?.includes(userId)) {
      return true;
    }

    // Check roles
    if (ac.roles && userRoles.some(role => ac.roles!.includes(role))) {
      return true;
    }

    // Check teams (if user belongs to team)
    // In production, this would check team membership
    if (ac.teams) {
      // Simplified - would need team membership service
    }

    return false;
  }

  /**
   * Get dashboards accessible to user
   */
  async getAccessibleDashboards(
    userId: string,
    userRoles: string[] = []
  ): Promise<Dashboard[]> {
    const dashboards = Array.from(this.dashboards.values());
    const accessible: Dashboard[] = [];

    for (const dashboard of dashboards) {
      if (await this.checkAccess(dashboard.id, userId, userRoles)) {
        accessible.push(dashboard);
      }
    }

    return accessible;
  }

  /**
   * Clone dashboard
   */
  async cloneDashboard(
    dashboardId: string,
    userId: string,
    organizationId: string,
    newName?: string
  ): Promise<Dashboard> {
    const original = this.dashboards.get(dashboardId);
    if (!original) {
      throw new Error(`Dashboard ${dashboardId} not found`);
    }

    const cloned: Omit<Dashboard, 'id' | 'created_at' | 'updated_at'> = {
      ...original,
      name: newName || `${original.name} (Copy)`,
      owner_id: userId,
      organization_id: organizationId,
      shared_with: undefined // Cloned dashboards start private
    };

    const newDashboard = await this.createDashboard(cloned);

    this.emit('dashboard:cloned', {
      originalId: dashboardId,
      newId: newDashboard.id
    });

    return newDashboard;
  }

  /**
   * Share dashboard with users/roles/teams
   */
  async shareDashboard(
    dashboardId: string,
    accessControl: AccessControl
  ): Promise<Dashboard> {
    const dashboard = this.dashboards.get(dashboardId);
    if (!dashboard) {
      throw new Error(`Dashboard ${dashboardId} not found`);
    }

    return this.updateDashboard(dashboardId, {
      shared_with: accessControl
    });
  }

  /**
   * Get dashboard count
   */
  getDashboardCount(): number {
    return this.dashboards.size;
  }

  /**
   * Cleanup
   */
  destroy(): void {
    this.removeAllListeners();
  }
}
