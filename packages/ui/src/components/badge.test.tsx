import React from 'react'
import { render, screen } from '@testing-library/react'
import { badge } from './badge'

describe('badge', () => {
  it('should render without crashing', () => {
    render(<badge />)
    expect(screen.getByTestId('badge')).toBeInTheDocument()
  })
})
