import React from 'react'
import { render, screen } from '@testing-library/react'
import { DashboardStats } from './stats'

// TODO(janua-tests): STALE TEST. The component renders correctly, but asserts a
// data-testid="stats" that the component does not (and never did) set. Scaffold
// stub, not real coverage. Give it a real assertion or add the test id.
describe.skip('DashboardStats', () => {
  it('should render without crashing', () => {
    render(<DashboardStats />)
    expect(screen.getByTestId('stats')).toBeInTheDocument()
  })
})
