import React from 'react'
import { render, screen } from '@testing-library/react'
import { navigation } from './navigation'

describe('navigation', () => {
  it('should render without crashing', () => {
    render(<navigation />)
    expect(screen.getByTestId('navigation')).toBeInTheDocument()
  })
})
