# Janua React Native SDK

Official React Native SDK for the Janua Identity Platform with full support for biometric authentication and secure storage.

## Installation

```bash
npm install @janua/react-native-sdk
# or
yarn add @janua/react-native-sdk

# iOS additional setup
cd ios && pod install
```

## Platform Setup

### iOS Setup

Add to your `Info.plist`:
```xml
<key>NSFaceIDUsageDescription</key>
<string>Authenticate with Face ID for secure access</string>
```

### Android Setup

Add to your `AndroidManifest.xml`:
```xml
<uses-permission android:name="android.permission.USE_BIOMETRIC" />
<uses-permission android:name="android.permission.USE_FINGERPRINT" />
```

## Quick Start

```javascript
import Janua from '@janua/react-native-sdk';

// Initialize the SDK
const janua = new Janua({
  baseURL: 'https://api.janua.dev',
  apiKey: 'your-api-key',
  enableBiometrics: true,
  secureStorage: true
});

// Sign in
const { user, session } = await janua.signIn({
  email: 'user@example.com',
  password: 'password'
});

// Enable biometric authentication
await janua.enableBiometricAuth();

// Sign in with biometrics next time
const { user } = await janua.signInWithBiometrics();
```

## Features

- 🔐 **Secure Authentication**: Email/password, OAuth, SSO
- 📱 **Biometric Support**: Face ID, Touch ID, Fingerprint
- 🔑 **Passkeys**: WebAuthn support for passwordless
- 💾 **Secure Storage**: Encrypted credential storage
- 🔄 **Auto Token Refresh**: Seamless session management
- 📡 **Offline Support**: Queue operations when offline
- 🎨 **UI Components**: Pre-built authentication screens

## API Reference

### Authentication

```javascript
// Sign up
const { user, session } = await janua.signUp({
  email: 'user@example.com',
  password: 'password',
  name: 'John Doe'
});

// Sign in
const { user, session } = await janua.signIn({
  email: 'user@example.com',
  password: 'password'
});

// Sign in with biometrics
const { user, session } = await janua.signInWithBiometrics();

// Sign in with social provider
const { user, session } = await janua.signInWithProvider('google');

// Sign out
await janua.signOut();
```

### Biometric Authentication

```javascript
// Check biometric availability
const isAvailable = await janua.isBiometricAvailable();

// Get biometric type
const type = await janua.getBiometricType(); // 'FaceID', 'TouchID', 'Fingerprint'

// Enable biometric authentication
await janua.enableBiometricAuth({
  title: 'Enable Biometric Login',
  subtitle: 'Use your fingerprint or face to sign in'
});

// Disable biometric authentication
await janua.disableBiometricAuth();
```

### User Management

```javascript
// Get current user
const user = await janua.getUser();

// Update user profile
await janua.updateUser({
  name: 'Jane Doe',
  avatar: 'https://example.com/avatar.jpg'
});

// Change password
await janua.changePassword({
  currentPassword: 'old-password',
  newPassword: 'new-password'
});

// Upload avatar
const avatarUrl = await janua.uploadAvatar(imageUri);
```

### Session Management

```javascript
// Get current session
const session = janua.getSession();

// List all sessions
const sessions = await janua.listSessions();

// Revoke a session
await janua.revokeSession(sessionId);

// Revoke all other sessions
await janua.revokeOtherSessions();
```

### Multi-Factor Authentication

```javascript
// Enable MFA
const { secret, qrCode, recoveryCodes } = await janua.enableMFA();

// Verify MFA code
await janua.verifyMFA('123456');

// Disable MFA
await janua.disableMFA('123456');
```

## UI Components

Pre-built authentication screens with customizable themes:

```javascript
import { SignInScreen, SignUpScreen, ProfileScreen } from '@janua/react-native-sdk/ui';

// Use pre-built sign in screen
<SignInScreen
  onSuccess={(user) => console.log('Signed in:', user)}
  onError={(error) => console.error(error)}
  theme={{
    primaryColor: '#007AFF',
    backgroundColor: '#FFFFFF',
    textColor: '#000000'
  }}
  enableBiometrics={true}
  enableSocialLogin={['google', 'apple', 'facebook']}
/>

// Use pre-built profile screen
<ProfileScreen
  user={currentUser}
  onSignOut={() => navigation.navigate('Login')}
  onUpdateProfile={(data) => janua.updateUser(data)}
/>
```

## Secure Storage

Encrypted storage for sensitive data:

```javascript
import { SecureStorage } from '@janua/react-native-sdk';

// Store encrypted data
await SecureStorage.setItem('api_key', 'secret-key');

// Retrieve encrypted data
const apiKey = await SecureStorage.getItem('api_key');

// Remove item
await SecureStorage.removeItem('api_key');

// Clear all secure storage
await SecureStorage.clear();
```

## Offline Support

Queue operations when offline and sync when connected:

```javascript
// Enable offline mode
janua.enableOfflineMode({
  syncOnReconnect: true,
  maxQueueSize: 100,
  persistQueue: true
});

// Operations are automatically queued when offline
await janua.updateUser({ name: 'Jane' }); // Queued if offline

// Listen for sync events
janua.on('sync:start', () => console.log('Syncing...'));
janua.on('sync:complete', () => console.log('Sync complete'));
janua.on('sync:error', (error) => console.error('Sync failed:', error));
```

## Deep Linking

Handle authentication callbacks from external providers:

```javascript
import { Linking } from 'react-native';

// Configure deep linking
janua.configureDeepLinking({
  scheme: 'janua',
  universalLinks: ['https://app.janua.dev']
});

// Handle deep links
Linking.addEventListener('url', (event) => {
  janua.handleDeepLink(event.url);
});

// In your app.json
{
  "expo": {
    "scheme": "janua",
    "ios": {
      "associatedDomains": ["applinks:app.janua.dev"]
    }
  }
}
```

## Push Notifications

Security alerts and authentication notifications:

```javascript
// Register for push notifications
const token = await janua.registerPushNotifications();

// Handle push notifications
janua.on('notification', (notification) => {
  if (notification.type === 'security_alert') {
    // Handle security alert
  }
});

// Update push token
await janua.updatePushToken(newToken);
```

## Error Handling

```javascript
try {
  await janua.signIn({ email, password });
} catch (error) {
  if (error.code === 'invalid_credentials') {
    // Handle invalid credentials
  } else if (error.code === 'account_locked') {
    // Handle locked account
  } else if (error.code === 'network_error') {
    // Handle network error
  }
}
```

## Security Best Practices

1. **Always use biometric authentication when available**
2. **Store sensitive data in SecureStorage only**
3. **Implement certificate pinning for API calls**
4. **Use short session durations with refresh tokens**
5. **Clear sensitive data on app background**
6. **Implement jailbreak/root detection**

## Examples

See the [examples](./examples) directory for complete working examples:

- [Basic Authentication](./examples/BasicAuth)
- [Biometric Login](./examples/BiometricAuth)
- [Social Login](./examples/SocialLogin)
- [Custom UI](./examples/CustomUI)

## Migration from v1

If upgrading from v1, see our [migration guide](./MIGRATION.md).

## Contributing

We welcome contributions! Please see our [Contributing Guide](../../CONTRIBUTING.md).

## Related Documentation

- [SDK Selection Guide](/docs/sdks/CHOOSE_YOUR_SDK.md) - Compare all Janua SDKs
- [Error Handling Guide](/docs/guides/ERROR_HANDLING_GUIDE.md) - Error codes and handling patterns
- [Rate Limiting](/docs/api/RATE_LIMITING.md) - API rate limits and best practices
- [API Reference](/apps/api/docs/api/endpoints-reference.md) - Complete API documentation
- [Architecture Overview](/docs/architecture/INDEX.md) - System architecture and ADRs
- [Flutter SDK](/packages/flutter-sdk/README.md) - Alternative mobile SDK
- [React SDK](/packages/react-sdk/README.md) - React web SDK

## License

AGPL-3.0 License - see [LICENSE](../../LICENSE) for details.