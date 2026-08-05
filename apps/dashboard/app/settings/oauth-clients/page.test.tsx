import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import OAuthClientsPage from './page'
import { listOAuthClients } from '@/lib/api'

/**
 * Regression guard: a failed list request must never be presented as an empty
 * registry.
 *
 * On 2026-08-05 this page rendered "No OAuth clients yet — create your first
 * OAuth client" with a Create button, while the Janua instance actually held
 * 51 registered clients and the list request had merely errored. The offered
 * next action was Create, so acting on the screen honestly would have minted a
 * duplicate of an already-registered client. The registry still shows 13
 * clients named "Voxa" and 3 named "tulana*", consistent with that having
 * happened before.
 *
 * "I could not read the list" and "I read the list and it was empty" must stay
 * distinguishable on screen.
 */

jest.mock('@/lib/api', () => ({
  listOAuthClients: jest.fn(),
  createOAuthClient: jest.fn(),
  updateOAuthClient: jest.fn(),
  deleteOAuthClient: jest.fn(),
  rotateOAuthClientSecret: jest.fn(),
  getOAuthClientSecretStatus: jest.fn(),
}))

const mockList = listOAuthClients as jest.MockedFunction<typeof listOAuthClients>

describe('OAuthClientsPage — error is not emptiness', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('does not invite the operator to create a client when the list fails to load', async () => {
    mockList.mockRejectedValue(new Error('Request failed with status code 500'))

    render(<OAuthClientsPage />)

    await waitFor(() => {
      expect(screen.getByText('Could not load OAuth clients')).toBeInTheDocument()
    })

    // The dangerous copy and its call to action must be absent.
    expect(screen.queryByText('No OAuth clients yet')).not.toBeInTheDocument()
    expect(
      screen.queryByText(
        'Create your first OAuth client to enable third-party integrations.',
      ),
    ).not.toBeInTheDocument()
  })

  it('still shows the empty state when the list genuinely returns zero clients', async () => {
    mockList.mockResolvedValue({ clients: [], total: 0, page: 1, per_page: 20 } as never)

    render(<OAuthClientsPage />)

    await waitFor(() => {
      expect(screen.getByText('No OAuth clients yet')).toBeInTheDocument()
    })

    expect(
      screen.queryByText('Could not load OAuth clients'),
    ).not.toBeInTheDocument()
  })
})
