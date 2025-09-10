import React from 'react'
import { render, screen } from '@testing-library/react'
import { layout } from './layout'

describe('layout', () => {
  it('should render without crashing', () => {
    render(<layout />)
    expect(screen.getByTestId('layout')).toBeInTheDocument()
  })
})
