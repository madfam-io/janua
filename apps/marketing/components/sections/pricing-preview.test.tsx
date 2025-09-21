import React from 'react'
import { render, screen } from '@testing-library/react'
import { PricingPreview } from './pricing-preview'

describe('PricingPreview', () => {
  it('should render without crashing', () => {
    render(<PricingPreview />)
    expect(screen.getByText('Scale with confidence,')).toBeInTheDocument()
  })
})