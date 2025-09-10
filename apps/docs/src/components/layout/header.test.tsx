import React from 'react'
import { render, screen } from '@testing-library/react'
import { header } from './header'

describe('header', () => {
  it('should render without crashing', () => {
    render(<header />)
    expect(screen.getByTestId('header')).toBeInTheDocument()
  })
})
