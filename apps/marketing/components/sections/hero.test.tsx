import React from 'react'
import { render, screen } from '@testing-library/react'
import { hero } from './hero'

describe('hero', () => {
  it('should render without crashing', () => {
    render(<hero />)
    expect(screen.getByTestId('hero')).toBeInTheDocument()
  })
})
