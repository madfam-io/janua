'use client';

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import {
  FeatureFlagKey,
  EvaluationContext,
  IFeatureFlagService,
  EvaluationResult,
} from './types';
import { featureFlagService } from './service';

/**
 * Feature flag context
 */
interface FeatureFlagContextValue {
  service: IFeatureFlagService;
  context: EvaluationContext;
  isEnabled: (key: FeatureFlagKey) => boolean;
  evaluate: (key: FeatureFlagKey) => EvaluationResult | null;
  loading: boolean;
}

const FeatureFlagContext = createContext<FeatureFlagContextValue | undefined>(undefined);

/**
 * Feature flag provider props
 */
interface FeatureFlagProviderProps {
  children: ReactNode;
  service?: IFeatureFlagService;
  context?: EvaluationContext;
}

/**
 * Feature flag provider component
 */
export function FeatureFlagProvider({
  children,
  service = featureFlagService,
  context = {},
}: FeatureFlagProviderProps) {
  const [evaluations, setEvaluations] = useState<Map<FeatureFlagKey, EvaluationResult>>(new Map());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadFlags = async () => {
      setLoading(true);
      try {
        const flags = await service.getAllFlags();
        const results = new Map<FeatureFlagKey, EvaluationResult>();

        for (const flag of flags) {
          const result = await service.evaluate(flag.key, context);
          results.set(flag.key, result);
        }

        setEvaluations(results);
      } catch (error) {
        console.error('Failed to load feature flags:', error);
      } finally {
        setLoading(false);
      }
    };

    loadFlags();
  }, [service, context]);

  const isEnabled = (key: FeatureFlagKey): boolean => {
    const result = evaluations.get(key);
    return result?.enabled || false;
  };

  const evaluate = (key: FeatureFlagKey): EvaluationResult | null => {
    return evaluations.get(key) || null;
  };

  return (
    <FeatureFlagContext.Provider
      value={{
        service,
        context,
        isEnabled,
        evaluate,
        loading,
      }}
    >
      {children}
    </FeatureFlagContext.Provider>
  );
}

/**
 * Hook to access feature flag context
 */
export function useFeatureFlags(): FeatureFlagContextValue {
  const context = useContext(FeatureFlagContext);
  if (!context) {
    throw new Error('useFeatureFlags must be used within FeatureFlagProvider');
  }
  return context;
}

/**
 * Hook to check if a feature is enabled
 */
export function useFeatureFlag(key: FeatureFlagKey): boolean {
  const { isEnabled } = useFeatureFlags();
  return isEnabled(key);
}

/**
 * Hook to get feature flag evaluation result
 */
export function useFeatureFlagEvaluation(key: FeatureFlagKey): EvaluationResult | null {
  const { evaluate } = useFeatureFlags();
  return evaluate(key);
}

/**
 * Component to conditionally render based on feature flag
 */
interface FeatureProps {
  name: FeatureFlagKey;
  children: ReactNode;
  fallback?: ReactNode;
}

export function Feature({ name, children, fallback = null }: FeatureProps) {
  const enabled = useFeatureFlag(name);
  return <>{enabled ? children : fallback}</>;
}

/**
 * Higher-order component to wrap component with feature flag check
 */
export function withFeatureFlag<P extends object>(
  Component: React.ComponentType<P>,
  featureKey: FeatureFlagKey,
  FallbackComponent?: React.ComponentType<P>
) {
  return function FeatureFlaggedComponent(props: P) {
    const enabled = useFeatureFlag(featureKey);

    if (!enabled) {
      return FallbackComponent ? <FallbackComponent {...props} /> : null;
    }

    return <Component {...props} />;
  };
}
