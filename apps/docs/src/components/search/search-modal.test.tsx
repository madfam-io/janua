import React from 'react'
import { render, screen } from '@testing-library/react'
import { search-modal } from './search-modal'

describe('search-modal', () => {
  it('should render without crashing', () => {
    render(<search-modal />)
    expect(screen.getByTestId('search-modal')).toBeInTheDocument()
  })
})
