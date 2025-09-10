import React from 'react'
import { render, screen } from '@testing-library/react'
import { session-list } from './session-list'

describe('session-list', () => {
  it('should render without crashing', () => {
    render(<session-list />)
    expect(screen.getByTestId('session-list')).toBeInTheDocument()
  })
})
