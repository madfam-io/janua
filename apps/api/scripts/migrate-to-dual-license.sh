#!/bin/bash

# Migration script to set up dual-license structure
# This creates a public SDK repository while keeping enterprise features private

set -e

echo "🚀 Starting dual-license migration for Janua"
echo "============================================"

# Configuration
PRIVATE_REPO="janua"
PUBLIC_REPO="janua-sdks"
CURRENT_DIR=$(pwd)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Step 1: Create public SDKs repository structure
echo ""
echo "Step 1: Creating public SDK repository structure"
echo "-------------------------------------------------"

if [ -d "../$PUBLIC_REPO" ]; then
    print_warning "Public repo directory already exists. Skipping creation."
else
    mkdir -p ../$PUBLIC_REPO
    cd ../$PUBLIC_REPO

    # Initialize git repo
    git init

    # Create directory structure
    mkdir -p typescript react vue python go flutter

    print_status "Created public repository structure"
    cd $CURRENT_DIR
fi

# Step 2: Copy SDK packages (without enterprise code)
echo ""
echo "Step 2: Copying SDK packages to public repository"
echo "-------------------------------------------------"

# TypeScript SDK
echo "Copying TypeScript SDK..."
cp -r packages/typescript-sdk/* ../$PUBLIC_REPO/typescript/
# Remove enterprise directory from public version
rm -rf ../$PUBLIC_REPO/typescript/src/enterprise

# React SDK
echo "Copying React SDK..."
cp -r packages/react/* ../$PUBLIC_REPO/react/

# Vue SDK
echo "Copying Vue SDK..."
cp -r packages/vue-sdk/* ../$PUBLIC_REPO/vue/

# Python SDK
echo "Copying Python SDK..."
cp -r packages/python-sdk/* ../$PUBLIC_REPO/python/
# Remove enterprise module from public version
rm -f ../$PUBLIC_REPO/python/janua/enterprise.py

# Go SDK
echo "Copying Go SDK..."
cp -r packages/go-sdk/* ../$PUBLIC_REPO/go/

# Flutter SDK
echo "Copying Flutter SDK..."
cp -r packages/flutter-sdk/* ../$PUBLIC_REPO/flutter/

print_status "SDKs copied to public repository"

# Step 3: Create open-source versions of clients
echo ""
echo "Step 3: Creating open-source versions of SDK clients"
echo "-----------------------------------------------------"

# Create open-source TypeScript client
cat > ../$PUBLIC_REPO/typescript/src/client.ts << 'EOF'
/**
 * Main Janua SDK client (Open Source Version)
 */

import type {
  JanuaConfig,
  SdkEventMap,
  SdkEventType,
  SdkEventHandler,
  User,
  TokenResponse
} from './types';
import { HttpClient, AxiosHttpClient, createHttpClient } from './http-client';
import { TokenManager, EnvUtils, EventEmitter } from './utils';
import { ConfigurationError } from './errors';
import { Auth } from './auth';
import { Users } from './users';
import { Organizations } from './organizations';
import { Webhooks } from './webhooks';
import { Admin } from './admin';

/**
 * Main Janua SDK client class (Community Edition)
 *
 * For enterprise features, see https://janua.dev/pricing
 */
export class JanuaClient extends EventEmitter<SdkEventMap> {
  private config: Required<JanuaConfig>;
  private tokenManager: TokenManager;
  private httpClient: HttpClient;

  // Module instances
  public readonly auth: Auth;
  public readonly users: Users;
  public readonly organizations: Organizations;
  public readonly webhooks: Webhooks;
  public readonly admin: Admin;

  constructor(config: Partial<JanuaConfig> = {}) {
    super();

    // Validate and merge configuration
    this.config = this.validateAndMergeConfig(config);

    // Initialize token manager
    this.tokenManager = this.createTokenManager();

    // Initialize HTTP client
    this.httpClient = this.createHttpClient();

    // Initialize modules
    this.auth = new Auth(
      this.httpClient,
      this.tokenManager,
      () => this.emit('auth:signIn', {}),
      () => this.emit('auth:signOut', {})
    );
    this.users = new Users(this.httpClient);
    this.organizations = new Organizations(this.httpClient);
    this.webhooks = new Webhooks(this.httpClient);
    this.admin = new Admin(this.httpClient);

    // Set up event forwarding
    this.setupEventForwarding();

    // Auto-refresh tokens if enabled
    if (this.config.autoRefreshTokens) {
      this.setupAutoTokenRefresh();
    }
  }

  // ... rest of the open-source client methods ...

  /**
   * Check if enterprise features are available
   * @returns Always returns false in open-source version
   */
  isEnterprise(): boolean {
    return false;
  }

  /**
   * Get information about upgrading to enterprise
   */
  getEnterpriseInfo(): string {
    return `
      This is the open-source Community Edition of Janua SDK.

      For enterprise features including:
      - Single Sign-On (SAML/OIDC)
      - Audit Logs
      - Custom Roles
      - White Labeling
      - Compliance Reports
      - On-premise deployment

      Visit https://janua.dev/pricing or contact sales@janua.dev
    `;
  }
}
EOF

print_status "Created open-source TypeScript client"

# Create open-source Python client
cat > ../$PUBLIC_REPO/python/janua/client.py << 'EOF'
"""
Main Janua SDK client (Open Source Version)
"""

import os
from typing import Optional
from urllib.parse import urljoin

from .http_client import HTTPClient
from .auth import AuthModule
from .users import UsersModule
from .organizations import OrganizationsModule
from .webhooks import WebhooksModule
from .admin import AdminModule
from .exceptions import ConfigurationError


class JanuaClient:
    """
    Main Janua SDK client (Community Edition)

    For enterprise features, see https://janua.dev/pricing
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """Initialize Janua client"""
        # Get base URL from parameter or environment
        self.base_url = base_url or os.getenv("JANUA_BASE_URL")
        if not self.base_url:
            raise ConfigurationError(
                "Base URL is required. Provide it as a parameter or set JANUA_BASE_URL environment variable."
            )

        # Initialize modules
        self.auth = AuthModule(self.http)
        self.users = UsersModule(self.http)
        self.organizations = OrganizationsModule(self.http)
        self.webhooks = WebhooksModule(self.http)
        self.admin = AdminModule(self.http)

    def is_enterprise(self) -> bool:
        """Check if enterprise features are available"""
        return False

    def get_enterprise_info(self) -> str:
        """Get information about upgrading to enterprise"""
        return """
        This is the open-source Community Edition of Janua SDK.

        For enterprise features including:
        - Single Sign-On (SAML/OIDC)
        - Audit Logs
        - Custom Roles
        - White Labeling
        - Compliance Reports
        - On-premise deployment

        Visit https://janua.dev/pricing or contact sales@janua.dev
        """
EOF

print_status "Created open-source Python client"

# Step 4: Update package.json files for public packages
echo ""
echo "Step 4: Updating package.json files for public packages"
echo "-------------------------------------------------------"

# Update TypeScript SDK package.json
cat > ../$PUBLIC_REPO/typescript/package.json << 'EOF'
{
  "name": "@janua/sdk",
  "version": "1.0.0",
  "description": "Official Janua SDK for JavaScript/TypeScript (Community Edition)",
  "main": "dist/index.js",
  "module": "dist/index.esm.js",
  "types": "dist/index.d.ts",
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "https://github.com/madfam-io/janua-sdks.git",
    "directory": "typescript"
  },
  "keywords": [
    "janua",
    "authentication",
    "auth",
    "sdk",
    "typescript",
    "javascript",
    "opensource"
  ],
  "author": "Janua Team",
  "bugs": {
    "url": "https://github.com/madfam-io/janua-sdks/issues"
  },
  "homepage": "https://janua.dev",
  "publishConfig": {
    "access": "public"
  }
}
EOF

print_status "Updated package.json files"

# Step 5: Create LICENSE files
echo ""
echo "Step 5: Creating LICENSE files"
echo "------------------------------"

# AGPL-3.0 License for all components
cat > ../$PUBLIC_REPO/LICENSE << 'EOF'
                    GNU AFFERO GENERAL PUBLIC LICENSE
                       Version 3, 19 November 2007

 Copyright (C) 2025 Innovaciones MADFAM SAS de CV

Copyright (c) 2025 Janua

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF

# Copy LICENSE to each SDK
for sdk in typescript react vue python go flutter; do
    cp ../$PUBLIC_REPO/LICENSE ../$PUBLIC_REPO/$sdk/LICENSE
done

print_status "Created LICENSE files"

# Step 6: Create README for public repository
echo ""
echo "Step 6: Creating README for public repository"
echo "---------------------------------------------"

cat > ../$PUBLIC_REPO/README.md << 'EOF'
# Janua SDKs - Open Source Authentication Platform

Official SDKs for integrating with Janua authentication platform.

## 🎯 Available SDKs

- **TypeScript/JavaScript** - Full-featured SDK for Node.js and browsers
- **React** - React hooks and components for authentication
- **Vue** - Vue 3 composables and components
- **Python** - Async Python SDK for backend integration
- **Go** - Go client library
- **Flutter** - Dart/Flutter SDK for mobile apps

## 🚀 Quick Start

### TypeScript/JavaScript
```bash
npm install @janua/sdk
```

```typescript
import { JanuaClient } from '@janua/sdk';

const client = new JanuaClient({
  baseURL: 'https://api.janua.dev'
});

// Sign in
const { user, tokens } = await client.auth.signIn({
  email: 'user@example.com',
  password: 'password'
});
```

### React
```bash
npm install @janua/react
```

```jsx
import { JanuaProvider, useAuth } from '@janua/react';

function App() {
  return (
    <JanuaProvider baseURL="https://api.janua.dev">
      <YourApp />
    </JanuaProvider>
  );
}

function YourApp() {
  const { signIn, user, isAuthenticated } = useAuth();
  // Use authentication
}
```

### Python
```bash
pip install janua
```

```python
from janua import JanuaClient

async with JanuaClient(base_url="https://api.janua.dev") as client:
    # Sign in
    response = await client.auth.sign_in(
        email="user@example.com",
        password="password"
    )
```

## 📦 Features (Community Edition)

✅ **Core Authentication**
- Email/password authentication
- Social login (Google, GitHub, etc.)
- Magic links
- Multi-factor authentication (TOTP)

✅ **User Management**
- User registration and profiles
- Password reset
- Email verification
- Session management

✅ **Organizations**
- Basic multi-tenancy
- Team invitations
- Member management

✅ **Developer Tools**
- RESTful API
- Webhooks
- Comprehensive SDKs
- TypeScript support

## 🏢 Enterprise Features

For additional features, consider [Janua Enterprise](https://janua.dev/pricing):

- **Single Sign-On (SSO)** - SAML 2.0, OpenID Connect
- **Advanced Security** - Audit logs, compliance reports
- **Custom Roles** - Fine-grained permissions
- **White Labeling** - Custom branding
- **On-Premise Deployment** - Self-hosted options
- **Premium Support** - 24/7 support, SLA

## 📖 Documentation

Full documentation available at [https://docs.janua.dev](https://docs.janua.dev)

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for details.

## 📄 License

AGPL-3.0 License - see [LICENSE](./LICENSE) for details.

## 💬 Support

- **Documentation**: [https://docs.janua.dev](https://docs.janua.dev)
- **Community Forum**: [https://community.janua.dev](https://community.janua.dev)
- **GitHub Issues**: [https://github.com/madfam-io/janua-sdks/issues](https://github.com/madfam-io/janua-sdks/issues)
- **Enterprise Support**: [sales@janua.dev](mailto:sales@janua.dev)
EOF

print_status "Created README for public repository"

# Step 7: Create .gitignore for public repo
echo ""
echo "Step 7: Setting up git configuration"
echo "------------------------------------"

cat > ../$PUBLIC_REPO/.gitignore << 'EOF'
# Dependencies
node_modules/
*.pyc
__pycache__/
.venv/
venv/
dist/
build/
*.egg-info/

# IDE
.vscode/
.idea/
*.swp
*.swo
.DS_Store

# Environment
.env
.env.local
.env.*.local

# Logs
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Testing
coverage/
.coverage
htmlcov/
.pytest_cache/
*.cover

# Build outputs
*.tsbuildinfo
*.d.ts.map
EOF

print_status "Created .gitignore"

# Step 8: Initialize git and create first commit
echo ""
echo "Step 8: Initializing git repository"
echo "-----------------------------------"

cd ../$PUBLIC_REPO

if [ ! -d ".git" ]; then
    git init
    git add .
    git commit -m "Initial commit: Open source Janua SDKs"
    print_status "Git repository initialized"
else
    print_warning "Git repository already initialized"
fi

cd $CURRENT_DIR

# Step 9: Create enterprise package structure (private)
echo ""
echo "Step 9: Creating enterprise package structure"
echo "---------------------------------------------"

mkdir -p packages/enterprise-extensions

cat > packages/enterprise-extensions/package.json << 'EOF'
{
  "name": "@janua/enterprise",
  "version": "1.0.0",
  "private": true,
  "description": "Enterprise extensions for Janua SDK",
  "license": "Commercial",
  "author": "Janua Team",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "dependencies": {
    "@janua/sdk": "^1.0.0"
  }
}
EOF

print_status "Created enterprise package structure"

# Step 10: Summary
echo ""
echo "========================================"
echo "✨ Migration Complete!"
echo "========================================"
echo ""
echo "📁 Repository Structure:"
echo "  • Private repo (current): Contains full platform + enterprise features"
echo "  • Public repo (../$PUBLIC_REPO): Contains open-source SDKs only"
echo ""
echo "📝 Next Steps:"
echo "  1. Review the public repository at ../$PUBLIC_REPO"
echo "  2. Create GitHub repository: https://github.com/new"
echo "  3. Push public SDKs:"
echo "     cd ../$PUBLIC_REPO"
echo "     git remote add origin git@github.com:madfam-io/janua-sdks.git"
echo "     git push -u origin main"
echo ""
echo "  4. Publish packages:"
echo "     • npm: npm publish (in each JS package)"
echo "     • PyPI: python -m twine upload dist/*"
echo "     • Go: git tag and push"
echo ""
echo "  5. Keep enterprise features in private repo only"
echo ""
echo "🔐 Security Notes:"
echo "  • Never push enterprise code to public repo"
echo "  • Keep license validation server-side"
echo "  • Use environment variables for sensitive config"
echo ""
print_status "Migration script completed successfully!"
