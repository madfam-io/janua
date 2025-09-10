import React from 'react'
import { render, screen } from '@testing-library/react'
import { pricing } from './pricing'

describe('pricing', () => {
  it('should render without crashing', () => {
    render(<pricing />)
    expect(screen.getByTestId('pricing')).toBeInTheDocument()
  })
})
