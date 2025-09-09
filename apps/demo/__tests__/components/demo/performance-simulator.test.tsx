import React from 'react'
import { render, screen } from '@testing-library/react'
import { PerformanceSimulator } from '@/components/demo/performance-simulator'

// Mock framer-motion
jest.mock('framer-motion', () => ({
  motion: {
    div: (props) => {
      const { children, ...rest } = props;
      return React.createElement('div', rest, children);
    },
  },
}))

// Mock the useDemoFeatures hook
jest.mock('@/hooks/useEnvironment', () => ({
  useDemoFeatures: jest.fn(),
}))

// Mock @plinto/ui components
jest.mock('@plinto/ui', () => ({
  Card: (props) => React.createElement('div', { 'data-testid': 'card', ...props }, props.children),
  CardContent: (props) => React.createElement('div', { 'data-testid': 'card-content', ...props }, props.children),
  CardDescription: (props) => React.createElement('div', { 'data-testid': 'card-description', ...props }, props.children),
  CardHeader: (props) => React.createElement('div', { 'data-testid': 'card-header', ...props }, props.children),
  CardTitle: (props) => React.createElement('div', { 'data-testid': 'card-title', ...props }, props.children),
}))

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  Zap: (props) => React.createElement('span', { 'data-testid': 'zap-icon', ...props }),
  Globe: (props) => React.createElement('span', { 'data-testid': 'globe-icon', ...props }),
  Server: (props) => React.createElement('span', { 'data-testid': 'server-icon', ...props }),
  ArrowUp: (props) => React.createElement('span', { 'data-testid': 'arrow-up-icon', ...props }),
}))

const mockUseDemoFeatures = require('@/hooks/useEnvironment').useDemoFeatures

describe('PerformanceSimulator', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    jest.useFakeTimers()
  })

  afterEach(() => {
    jest.useRealTimers()
  })

  it('should not render when not in demo mode', () => {
    mockUseDemoFeatures.mockReturnValue({
      isDemo: false,
      performanceData: {
        edgeVerificationMs: 12,
        authFlowMs: 230,
        tokenGenerationMs: 45,
        globalLocations: 150
      }
    })

    const { container } = render(<PerformanceSimulator />)
    expect(container.firstChild).toBeNull()
  })

  it('should render performance monitor when in demo mode', () => {
    mockUseDemoFeatures.mockReturnValue({
      isDemo: true,
      performanceData: {
        edgeVerificationMs: 12,
        authFlowMs: 230,
        tokenGenerationMs: 45,
        globalLocations: 150
      }
    })

    render(<PerformanceSimulator />)

    expect(screen.getByTestId('zap-icon')).toBeInTheDocument()
    expect(screen.getByText('Performance Monitor')).toBeInTheDocument()
    expect(screen.getByText('Real-time performance metrics from global edge locations')).toBeInTheDocument()
  })

  it('should display performance metrics', () => {
    mockUseDemoFeatures.mockReturnValue({
      isDemo: true,
      performanceData: {
        edgeVerificationMs: 12,
        authFlowMs: 230,
        tokenGenerationMs: 45,
        globalLocations: 150
      }
    })

    render(<PerformanceSimulator />)

    expect(screen.getByText('Edge Verification')).toBeInTheDocument()
    expect(screen.getByText('Auth Flow')).toBeInTheDocument()
    expect(screen.getByText('Token Generation')).toBeInTheDocument()
    expect(screen.getByText('Global Locations')).toBeInTheDocument()

    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('230')).toBeInTheDocument()
    expect(screen.getByText('45')).toBeInTheDocument()
    expect(screen.getByText('150')).toBeInTheDocument()
  })

  it('should display metric descriptions', () => {
    mockUseDemoFeatures.mockReturnValue({
      isDemo: true,
      performanceData: {
        edgeVerificationMs: 12,
        authFlowMs: 230,
        tokenGenerationMs: 45,
        globalLocations: 150
      }
    })

    render(<PerformanceSimulator />)

    expect(screen.getByText('Token verification at edge locations')).toBeInTheDocument()
    expect(screen.getByText('Complete authentication process')).toBeInTheDocument()
    expect(screen.getByText('JWT token creation and signing')).toBeInTheDocument()
    expect(screen.getByText('Edge deployment locations')).toBeInTheDocument()
  })

  it('should display demo disclaimer', () => {
    mockUseDemoFeatures.mockReturnValue({
      isDemo: true,
      performanceData: {
        edgeVerificationMs: 12,
        authFlowMs: 230,
        tokenGenerationMs: 45,
        globalLocations: 150
      }
    })

    render(<PerformanceSimulator />)

    expect(screen.getByText('Demo Note:')).toBeInTheDocument()
    expect(screen.getByText(/These metrics are simulated for demonstration purposes/)).toBeInTheDocument()
    expect(screen.getByText(/Production performance may vary/)).toBeInTheDocument()
  })

  it('should update metrics over time', () => {
    mockUseDemoFeatures.mockReturnValue({
      isDemo: true,
      performanceData: {
        edgeVerificationMs: 12,
        authFlowMs: 230,
        tokenGenerationMs: 45,
        globalLocations: 150
      }
    })

    render(<PerformanceSimulator />)

    // Initial values
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('230')).toBeInTheDocument()

    // Advance timers to trigger metric updates
    jest.advanceTimersByTime(3000)

    // Values should still be present (they may have changed slightly due to randomization)
    expect(screen.getAllByText(/\d+/)).toHaveLength(12) // 4 metrics × 3 (value, unit, other text)
  })
})