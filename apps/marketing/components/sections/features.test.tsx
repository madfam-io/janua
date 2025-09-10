import React from 'react'
import { render, screen } from '@testing-library/react'
import { features } from './features'

describe('features', () => {
  it('should render without crashing', () => {
    render(<features />)
    expect(screen.getByTestId('features')).toBeInTheDocument()
  })
})
