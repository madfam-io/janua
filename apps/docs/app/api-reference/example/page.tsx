'use client';

import React from 'react';
import { ApiEndpoint } from '@/components/ApiReference/ApiEndpoint';
import { ApiPlayground } from '@/components/ApiReference/ApiPlayground';
import { VersionSelector } from '@/components/VersionSelector/VersionSelector';
import { FeedbackWidget, InlineFeedback } from '@/components/Feedback/FeedbackWidget';
import { EditOnGitHub, Contributors, LastUpdated } from '@/components/GitHubLink/EditOnGitHub';
import { AlgoliaSearch } from '@/components/Search/AlgoliaSearch';

export default function ApiReferencePage() {
  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      {/* Page Header with Version Selector and GitHub Links */}
      <div className="border-b pb-4 space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">API Reference</h1>
          <VersionSelector />
        </div>

        <div className="flex items-center justify-between">
          <p className="text-muted-foreground">
            Complete API documentation with interactive playground
          </p>
          <EditOnGitHub
            filePath="apps/docs/app/api-reference/example/page.tsx"
            variant="link"
            showHistory
          />
        </div>

        {/* Search Bar */}
        <AlgoliaSearch className="w-full" />
      </div>

      {/* Authentication Endpoint */}
      <section className="space-y-6">
        <h2 className="text-2xl font-semibold">Authentication</h2>

        <ApiEndpoint
          method="POST"
          path="/api/auth/login"
          title="User Login"
          description="Authenticate a user and receive access tokens"
          authenticated={false}
          parameters={{
            body: [
              {
                name: 'email',
                type: 'string',
                required: true,
                description: 'User email address',
                example: 'user@example.com'
              },
              {
                name: 'password',
                type: 'string',
                required: true,
                description: 'User password',
                example: 'SecurePassword123!'
              },
              {
                name: 'remember',
                type: 'boolean',
                required: false,
                description: 'Keep user logged in for 30 days',
                example: true
              }
            ]
          }}
          responses={[
            {
              status: 200,
              description: 'Successful authentication',
              example: {
                user: {
                  id: 'usr_123',
                  email: 'user@example.com',
                  name: 'John Doe'
                },
                tokens: {
                  access: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                  refresh: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
                }
              }
            },
            {
              status: 401,
              description: 'Invalid credentials',
              example: {
                error: 'INVALID_CREDENTIALS',
                message: 'The email or password provided is incorrect'
              }
            }
          ]}
          examples={[
            {
              title: 'Basic Login',
              language: 'javascript',
              code: `const response = await fetch('https://api.plinto.dev/api/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'SecurePassword123!'
  })
});

const data = await response.json();
console.log(data.tokens.access);`
            },
            {
              title: 'With Remember Me',
              language: 'python',
              code: `import requests

response = requests.post(
    'https://api.plinto.dev/api/auth/login',
    json={
        'email': 'user@example.com',
        'password': 'SecurePassword123!',
        'remember': True
    }
)

data = response.json()
print(data['tokens']['access'])`
            }
          ]}
        />
      </section>

      {/* User Management Endpoints */}
      <section className="space-y-6">
        <h2 className="text-2xl font-semibold">User Management</h2>

        <ApiEndpoint
          method="GET"
          path="/api/users/{userId}"
          title="Get User Details"
          description="Retrieve detailed information about a specific user"
          authenticated={true}
          parameters={{
            path: [
              {
                name: 'userId',
                type: 'string',
                required: true,
                description: 'Unique user identifier',
                example: 'usr_123'
              }
            ],
            query: [
              {
                name: 'include',
                type: 'string',
                required: false,
                description: 'Comma-separated list of related data to include',
                example: 'profile,settings'
              }
            ]
          }}
          responses={[
            {
              status: 200,
              description: 'User details retrieved successfully',
              example: {
                id: 'usr_123',
                email: 'user@example.com',
                name: 'John Doe',
                createdAt: '2024-01-15T10:00:00Z',
                profile: {
                  bio: 'Software developer',
                  location: 'San Francisco, CA'
                }
              }
            },
            {
              status: 404,
              description: 'User not found',
              example: {
                error: 'USER_NOT_FOUND',
                message: 'No user found with the specified ID'
              }
            }
          ]}
        />

        {/* Try It Playground */}
        <div className="mt-8">
          <h3 className="text-lg font-semibold mb-4">Try It Out</h3>
          <ApiPlayground
            method="GET"
            path="/api/users/{userId}"
            parameters={{
              path: [
                {
                  name: 'userId',
                  type: 'string',
                  required: true,
                  description: 'User ID',
                  example: 'usr_123'
                }
              ],
              query: [
                {
                  name: 'include',
                  type: 'string',
                  description: 'Include related data',
                  example: 'profile,settings'
                }
              ]
            }}
            headers={{
              'Authorization': 'Bearer YOUR_ACCESS_TOKEN'
            }}
          />
        </div>
      </section>

      {/* Page Footer with Metadata */}
      <div className="border-t pt-6 space-y-4">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <LastUpdated filePath="apps/docs/app/api-reference/example/page.tsx" />
          <Contributors filePath="apps/docs/app/api-reference/example/page.tsx" />
        </div>

        {/* Inline Feedback */}
        <InlineFeedback pageId="api-reference-example" />
      </div>

      {/* Floating Feedback Widget */}
      <FeedbackWidget pageId="api-reference-example" />
    </div>
  );
}