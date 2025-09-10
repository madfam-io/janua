import React from 'react'
import { render, screen } from '@testing-library/react'
import { about } from './about'

describe('about', () => {
  it('should render without crashing', () => {
    render(<about />)
    expect(screen.getByTestId('about')).toBeInTheDocument()
  })
})
