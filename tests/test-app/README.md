# Test Application

Simple application using Plinto SDK for validating user journey tests.

## Purpose

This test app simulates a real application integrating Plinto authentication.
It validates that:
- SDK integration works as documented
- Authentication flows complete successfully
- User experience matches expectations
- Performance meets requirements

## Structure

```
tests/test-app/
├── src/
│   ├── app.ts           # Express server
│   ├── routes/          # Application routes
│   │   ├── auth.ts      # Authentication routes
│   │   ├── profile.ts   # User profile routes
│   │   └── security.ts  # Security settings routes
│   ├── views/           # HTML templates
│   │   ├── index.html   # Landing page
│   │   ├── login.html   # Login page
│   │   ├── signup.html  # Signup page
│   │   └── dashboard.html # User dashboard
│   └── public/          # Static assets
│       ├── css/
│       └── js/
├── Dockerfile           # Container image
├── package.json         # Dependencies
└── README.md           # This file
```

## Running Locally

```bash
# Install dependencies
cd tests/test-app
npm install

# Set environment variables
export PLINTO_API_URL=http://localhost:8000
export PLINTO_API_KEY=your-test-api-key

# Run test app
npm start

# Visit http://localhost:3001
```

## Running in Docker

```bash
# From project root
docker-compose -f docker-compose.test.yml up test-app

# Visit http://localhost:3001
```

## Test Scenarios

### Signup Flow
1. Navigate to `/signup`
2. Fill email, password, name
3. Submit form
4. Verify email (simulated in test environment)
5. Redirect to dashboard

### Login Flow
1. Navigate to `/login`
2. Fill email, password
3. Submit form
4. Redirect to dashboard

### MFA Setup
1. Navigate to `/security`
2. Enable MFA
3. Scan QR code
4. Enter TOTP code
5. Save backup codes

### Profile Management
1. Navigate to `/profile`
2. Update name/email
3. Change password
4. View active sessions

## Test Data

Test accounts are automatically created:
- `test-user@example.com` / `TestPass123!`
- `test-admin@example.com` / `AdminPass123!`
- `test-developer@example.com` / `DevPass123!`
