import React from 'react'
import { render, screen } from '@testing-library/react'
import { layout as _layout } from './layout'

describe('layout', () => {
  it('should render without crashing', () => {
    render(<_layout />)
    expect(screen.getByTestId('layout')).toBeInTheDocument()
  })
})
