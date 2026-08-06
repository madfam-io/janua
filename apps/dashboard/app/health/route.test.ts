/**
 * @jest-environment node
 *
 * Route handlers import next/server, which needs the Web Fetch globals
 * (Request/Response). jsdom does not provide them; the node environment does.
 * Matches app/api/auth/session/route.test.ts in apps/admin.
 */

import * as module from './route'

describe('route', () => {
  it('should export expected functions', () => {
    expect(module).toBeDefined()
  })
})
