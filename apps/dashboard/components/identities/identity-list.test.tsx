import React from 'react'
import { render, screen } from '@testing-library/react'
import { identity-list } from './identity-list'

describe('identity-list', () => {
  it('should render without crashing', () => {
    render(<identity-list />)
    expect(screen.getByTestId('identity-list')).toBeInTheDocument()
  })
})
