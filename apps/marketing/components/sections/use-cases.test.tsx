import React from 'react'
import { render, screen } from '@testing-library/react'
import { UseCases } from './use-cases'

describe('UseCases', () => {
  it('should render without crashing', () => {
    render(<UseCases />)
    expect(screen.getByText('Built for every')).toBeInTheDocument()
  })
})