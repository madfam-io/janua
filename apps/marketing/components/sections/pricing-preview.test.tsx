import React from 'react'
import { render, screen } from '@testing-library/react'
import { pricing-preview } from './pricing-preview'

describe('pricing-preview', () => {
  it('should render without crashing', () => {
    render(<pricing-preview />)
    expect(screen.getByTestId('pricing-preview')).toBeInTheDocument()
  })
})
