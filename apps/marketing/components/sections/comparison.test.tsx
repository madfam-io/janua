import React from 'react'
import { render, screen } from '@testing-library/react'
import { comparison } from './comparison'

describe('comparison', () => {
  it('should render without crashing', () => {
    render(<comparison />)
    expect(screen.getByTestId('comparison')).toBeInTheDocument()
  })
})
