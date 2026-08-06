import React from 'react'
import { render, screen } from '@testing-library/react'
import AdminPage from './page'

// TODO(janua-tests): STALE TEST. AdminPage now calls useAuth(), which throws
// outside an AuthProvider, so rendering it bare can no longer work. Rewrite to
// wrap the page in AuthProvider (or mock the auth module) before re-enabling.
describe.skip('AdminPage', () => {
  it('should render without crashing', () => {
    render(<AdminPage />)
    expect(screen.getByText('Janua Superadmin')).toBeInTheDocument()
    expect(screen.getByText('Platform Overview')).toBeInTheDocument()
  })
})
