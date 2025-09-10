import React from 'react'
import { render, screen } from '@testing-library/react'
import { use-cases } from './use-cases'

describe('use-cases', () => {
  it('should render without crashing', () => {
    render(<use-cases />)
    expect(screen.getByTestId('use-cases')).toBeInTheDocument()
  })
})
