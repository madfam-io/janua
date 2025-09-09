import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { DemoBanner } from '@/components/demo/demo-banner'

// Mock framer-motion
jest.mock('framer-motion', () => ({
  motion: {
    div: (props) => React.createElement('div', props, props.children),
  },
  AnimatePresence: (props) => props.children,
}))

// Mock the useEnvironment hook
jest.mock('@/hooks/useEnvironment', () => ({
  useEnvironment: jest.fn(),
}))

// Mock @plinto/ui components
jest.mock('@plinto/ui', () => ({
  Button: (props) => React.createElement('button', props, props.children),
}))

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  X: (props) => React.createElement('span', { ...props, 'data-testid': 'x-icon' }),
  Info: (props) => React.createElement('span', { ...props, 'data-testid': 'info-icon' }),
  ExternalLink: (props) => React.createElement('span', { ...props, 'data-testid': 'external-link-icon' }),
}))

const mockUseEnvironment = require('@/hooks/useEnvironment').useEnvironment

describe('DemoBanner', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('should not render when not mounted', () => {
    mockUseEnvironment.mockReturnValue({
      isDemo: true,
      showDemoNotice: () => true,
      mounted: false,
    })

    const { container } = render(<DemoBanner />)
    expect(container.firstChild).toBeNull()
  })

  it('should not render when not in demo mode', () => {
    mockUseEnvironment.mockReturnValue({
      isDemo: false,
      showDemoNotice: () => true,
      mounted: true,
    })

    const { container } = render(<DemoBanner />)
    expect(container.firstChild).toBeNull()
  })

  it('should not render when demo notice should not be shown', () => {
    mockUseEnvironment.mockReturnValue({
      isDemo: true,
      showDemoNotice: () => false,
      mounted: true,
    })

    const { container } = render(<DemoBanner />)
    expect(container.firstChild).toBeNull()
  })

  it('should render demo banner when conditions are met', () => {
    mockUseEnvironment.mockReturnValue({
      isDemo: true,
      showDemoNotice: () => true,
      mounted: true,
    })

    render(<DemoBanner />)

    expect(screen.getByTestId('info-icon')).toBeInTheDocument()
    expect(screen.getByText('Demo Environment')).toBeInTheDocument()
    expect(screen.getByText(/Experience Plinto's authentication platform/)).toBeInTheDocument()
    expect(screen.getByText('Try Production')).toBeInTheDocument()
    expect(screen.getByTestId('external-link-icon')).toBeInTheDocument()
    expect(screen.getByTestId('x-icon')).toBeInTheDocument()
  })

  it('should open contact page when Try Production button is clicked', () => {
    mockUseEnvironment.mockReturnValue({
      isDemo: true,
      showDemoNotice: () => true,
      mounted: true,
    })

    render(<DemoBanner />)

    const tryProductionButton = screen.getByText('Try Production')
    fireEvent.click(tryProductionButton)

    expect(global.open).toHaveBeenCalledWith('https://plinto.dev/contact', '_blank')
  })

  it('should dismiss banner when close button is clicked', () => {
    mockUseEnvironment.mockReturnValue({
      isDemo: true,
      showDemoNotice: () => true,
      mounted: true,
    })

    const { container } = render(<DemoBanner />)

    expect(container.firstChild).not.toBeNull()

    const closeButton = screen.getByTestId('x-icon').closest('button')
    fireEvent.click(closeButton)

    // After dismissal, component should not render
    expect(container.firstChild).toBeNull()
  })

  it('should maintain dismissed state after re-render', () => {
    mockUseEnvironment.mockReturnValue({
      isDemo: true,
      showDemoNotice: () => true,
      mounted: true,
    })

    const { rerender, container } = render(<DemoBanner />)

    // Initially should render
    expect(container.firstChild).not.toBeNull()

    // Dismiss the banner
    const closeButton = screen.getByTestId('x-icon').closest('button')
    fireEvent.click(closeButton)

    // Should be dismissed
    expect(container.firstChild).toBeNull()

    // Re-render and should still be dismissed
    rerender(<DemoBanner />)
    expect(container.firstChild).toBeNull()
  })
})