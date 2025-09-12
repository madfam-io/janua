import React from 'react'
import { render, screen } from '@testing-library/react'
import AdminPage from './page'

describe('AdminPage', () => {
  it('should render without crashing', () => {
    render(<AdminPage />)
    expect(screen.getByText('Plinto Superadmin')).toBeInTheDocument()
    expect(screen.getByText('Platform Overview')).toBeInTheDocument()
  })
})
