'use client'

import { useEffect, useState } from 'react'
import { getEnvironment, isDemo, isProduction, getFeature, DEMO_CREDENTIALS, DEMO_PERFORMANCE_METRICS } from '@/lib/config'
import type { Environment } from '@/lib/config'

export function useEnvironment() {
  const [environment, setEnvironment] = useState<Environment | null>(null)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setEnvironment(getEnvironment())
    setMounted(true)
  }, [])

  if (!mounted || !environment) {
    return {
      environment: null,
      isDemo: false,
      isProduction: true,
      features: {} as Environment['features'],
      demoConfig: null,
      demoCredentials: DEMO_CREDENTIALS,
      performanceMetrics: DEMO_PERFORMANCE_METRICS,
      mounted: false
    }
  }

  return {
    environment,
    isDemo: isDemo(),
    isProduction: isProduction(),
    features: environment.features,
    demoConfig: environment.demo || null,
    demoCredentials: DEMO_CREDENTIALS,
    performanceMetrics: DEMO_PERFORMANCE_METRICS,
    mounted: true,
    
    // Helper methods
    showDemoNotice: () => environment.features.showDemoNotice,
    allowRealSignups: () => environment.features.realSignups,
    processRealPayments: () => environment.features.realBilling,
    sendRealEmails: () => environment.features.realEmails,
    retainUserData: () => environment.features.dataRetention,
    shouldAutoSignIn: () => environment.features.autoSignIn,
    hasDemoCredentials: () => environment.features.demoCredentials,
  }
}

// Demo-specific hooks
export function useDemoFeatures() {
  const { isDemo, demoConfig, performanceMetrics } = useEnvironment()
  
  const [performanceData, setPerformanceData] = useState(performanceMetrics)
  
  const simulatePerformance = (operation: 'auth' | 'verification' | 'generation') => {
    const metrics = {
      auth: performanceMetrics.authFlowMs,
      verification: performanceMetrics.edgeVerificationMs,
      generation: performanceMetrics.tokenGenerationMs,
    }
    
    return new Promise(resolve => {
      const delay = metrics[operation] + Math.random() * 10 // Add some jitter
      setTimeout(resolve, delay)
    })
  }
  
  const generateSampleUsers = () => {
    return [
      { name: 'Alice Developer', email: 'alice@demo.com', role: 'admin' },
      { name: 'Bob Designer', email: 'bob@demo.com', role: 'member' },
      { name: 'Carol Product', email: 'carol@demo.com', role: 'viewer' },
    ]
  }
  
  const resetDemoData = async () => {
    if (!isDemo) return false
    
    // Simulate reset operation
    await new Promise(resolve => setTimeout(resolve, 1000))
    return true
  }
  
  return {
    isDemo,
    demoConfig,
    performanceData,
    simulatePerformance,
    generateSampleUsers,
    resetDemoData,
    shouldShowInteractiveTutorial: () => demoConfig?.interactiveTutorial || false,
    shouldSimulatePerformance: () => demoConfig?.performanceSimulation || false,
  }
}

// Environment-aware API client configuration
export function useApiConfig() {
  const { environment, mounted } = useEnvironment()
  
  if (!mounted || !environment) {
    return {
      apiUrl: 'http://localhost:4000',
      timeout: 5000,
      retries: 3
    }
  }
  
  return {
    apiUrl: environment.apiUrl,
    timeout: environment.name === 'demo' ? 2000 : 5000, // Faster timeouts for demo
    retries: environment.name === 'demo' ? 1 : 3,       // Fewer retries for demo
  }
}