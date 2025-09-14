import React from 'react'
import { render, screen } from '@testing-library/react'
import { FeaturesGrid } from './features'

describe('FeaturesGrid', () => {
  it('should render without crashing', () => {
    render(<FeaturesGrid />)
    expect(screen.getByText('Edge-Fast Verification')).toBeInTheDocument()
  })

  it('should render performance features', () => {
    render(<FeaturesGrid />)
    expect(screen.getByText('Sub-30ms')).toBeInTheDocument()
    expect(screen.getByText('Global edge network')).toBeInTheDocument()
  })
})
