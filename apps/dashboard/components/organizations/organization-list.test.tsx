import React from 'react'
import { render, screen } from '@testing-library/react'
import { OrganizationList } from './organization-list'

// TODO(janua-tests): STALE TEST. The component renders (a loading spinner at
// assert time), but asserts a data-testid="organization-list" it does not set.
// Scaffold stub, not real coverage. Needs a real assertion, awaited.
describe.skip('OrganizationList', () => {
  it('should render without crashing', () => {
    render(<OrganizationList />)
    expect(screen.getByTestId('organization-list')).toBeInTheDocument()
  })
})
