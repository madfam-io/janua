import React from 'react'
import { render, screen } from '@testing-library/react'
import { organization-list } from './organization-list'

describe('organization-list', () => {
  it('should render without crashing', () => {
    render(<organization-list />)
    expect(screen.getByTestId('organization-list')).toBeInTheDocument()
  })
})
