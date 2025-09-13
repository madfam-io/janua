# React Native SDK Quickstart

Build secure mobile authentication with Plinto's React Native SDK supporting biometric authentication, secure storage, and native performance.

## Installation

```bash
npm install @plinto/react-native
# or
yarn add @plinto/react-native

# iOS specific
cd ios && pod install
```

### Required Dependencies
```bash
npm install @react-native-async-storage/async-storage
npm install react-native-keychain
npm install react-native-url-polyfill
```

## Basic Setup

```javascript
import PlintoClient from '@plinto/react-native';

// Initialize the client
const plinto = new PlintoClient({
  baseURL: 'https://api.plinto.dev',
  tenantId: 'YOUR_TENANT_ID',
  clientId: 'YOUR_CLIENT_ID',
  redirectUri: 'yourapp://auth/callback'
});
```

## Quick Examples

### Sign Up
```javascript
try {
  const response = await plinto.auth.signUp({
    email: 'user@example.com',
    password: 'SecurePassword123!',
    firstName: 'John',
    lastName: 'Doe'
  });
  
  console.log('Welcome,', response.user.first_name);
  // Tokens are securely stored
} catch (error) {
  Alert.alert('Error', error.message);
}
```

### Sign In
```javascript
try {
  const response = await plinto.auth.signIn({
    email: 'user@example.com',
    password: 'SecurePassword123!'
  });
  
  console.log('Welcome back,', response.user.first_name);
} catch (error) {
  Alert.alert('Error', error.message);
}
```

### Biometric Authentication

#### Enable Biometric
```javascript
import * as Keychain from 'react-native-keychain';

// Check biometric support
const biometryType = await Keychain.getSupportedBiometryType();
if (biometryType) {
  try {
    await plinto.auth.enableBiometric();
    Alert.alert('Success', `${biometryType} authentication enabled!`);
  } catch (error) {
    Alert.alert('Error', error.message);
  }
} else {
  Alert.alert('Not Supported', 'Biometric authentication not available');
}
```

#### Sign In with Biometric
```javascript
try {
  const response = await plinto.auth.signInWithBiometric();
  console.log('Signed in with biometric:', response.user.email);
} catch (error) {
  Alert.alert('Authentication Failed', error.message);
}
```

## Deep Linking for OAuth

### iOS Configuration (Info.plist)
```xml
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleURLSchemes</key>
    <array>
      <string>yourapp</string>
    </array>
  </dict>
</array>
```

### Android Configuration (AndroidManifest.xml)
```xml
<intent-filter>
  <action android:name="android.intent.action.VIEW" />
  <category android:name="android.intent.category.DEFAULT" />
  <category android:name="android.intent.category.BROWSABLE" />
  <data android:scheme="yourapp" android:host="auth" />
</intent-filter>
```

### Handle OAuth Flow
```javascript
import { Linking } from 'react-native';

// Setup deep linking
useEffect(() => {
  const handleDeepLink = ({ url }) => {
    if (url.includes('auth/callback')) {
      const params = new URLSearchParams(url.split('?')[1]);
      const code = params.get('code');
      const state = params.get('state');
      
      if (code && state) {
        handleOAuthCallback(code, state);
      }
    }
  };
  
  // Listen for incoming links
  const subscription = Linking.addEventListener('url', handleDeepLink);
  
  // Check if app was opened with a link
  Linking.getInitialURL().then(url => {
    if (url) handleDeepLink({ url });
  });
  
  return () => subscription.remove();
}, []);

// Initiate social login
const handleSocialLogin = async (provider) => {
  try {
    const authUrl = await plinto.auth.signInWithProvider(provider);
    await Linking.openURL(authUrl);
  } catch (error) {
    Alert.alert('Error', error.message);
  }
};

// Handle OAuth callback
const handleOAuthCallback = async (code, state) => {
  try {
    const response = await plinto.auth.handleOAuthCallback(code, state);
    console.log('OAuth success:', response.user.email);
  } catch (error) {
    Alert.alert('OAuth Error', error.message);
  }
};
```

## Secure Storage

Tokens are automatically stored securely using:
- **iOS**: Keychain Services with biometric protection
- **Android**: Android Keystore with hardware-backed encryption

```javascript
// Tokens are automatically managed, but you can access them if needed
const accessToken = await plinto.getAccessToken();

// Clear tokens on logout
await plinto.clearTokens();
```

## Multi-Factor Authentication

### Enable MFA
```javascript
try {
  const setup = await plinto.auth.enableMFA('totp');
  
  // Display QR code to user
  Alert.alert(
    'MFA Setup',
    `Scan this QR code with your authenticator app:\n${setup.qr_code}`,
    [
      {
        text: 'Save Recovery Codes',
        onPress: () => saveRecoveryCodes(setup.recovery_codes)
      }
    ]
  );
} catch (error) {
  Alert.alert('Error', error.message);
}
```

### Verify MFA
```javascript
const verifyMFA = async (code) => {
  try {
    await plinto.auth.verifyMFA(code, challengeId);
    Alert.alert('Success', 'MFA verified');
  } catch (error) {
    Alert.alert('Invalid Code', 'Please try again');
  }
};
```

## Session Management

### List Sessions
```javascript
const sessions = await plinto.sessions.listSessions();
sessions.forEach(session => {
  console.log(`Device: ${session.device}`);
  console.log(`Location: ${session.location}`);
  console.log(`Last active: ${session.last_active}`);
});
```

### Revoke Session
```javascript
await plinto.sessions.revokeSession(sessionId);
Alert.alert('Success', 'Session revoked');
```

## React Hooks

### useAuth Hook
```javascript
import { useState, useEffect, createContext, useContext } from 'react';
import PlintoClient from '@plinto/react-native';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  
  const plinto = new PlintoClient({
    baseURL: 'https://api.plinto.dev',
    tenantId: 'YOUR_TENANT_ID',
    clientId: 'YOUR_CLIENT_ID',
  });
  
  useEffect(() => {
    checkAuthStatus();
  }, []);
  
  const checkAuthStatus = async () => {
    try {
      const currentUser = await plinto.users.getCurrentUser();
      setUser(currentUser);
    } catch (error) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };
  
  const signIn = async (email, password) => {
    const response = await plinto.auth.signIn({ email, password });
    setUser(response.user);
    return response;
  };
  
  const signOut = async () => {
    await plinto.auth.signOut();
    setUser(null);
  };
  
  return (
    <AuthContext.Provider value={{
      user,
      loading,
      signIn,
      signOut,
      plinto
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
```

### Usage in Components
```javascript
function ProfileScreen() {
  const { user, signOut } = useAuth();
  
  if (!user) {
    return <LoginScreen />;
  }
  
  return (
    <View>
      <Text>Welcome, {user.first_name}!</Text>
      <Button title="Sign Out" onPress={signOut} />
    </View>
  );
}
```

## React Navigation Integration

### Auth Flow
```javascript
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';

const Stack = createStackNavigator();

function App() {
  const { user, loading } = useAuth();
  
  if (loading) {
    return <SplashScreen />;
  }
  
  return (
    <NavigationContainer>
      <Stack.Navigator>
        {user ? (
          <>
            <Stack.Screen name="Home" component={HomeScreen} />
            <Stack.Screen name="Profile" component={ProfileScreen} />
          </>
        ) : (
          <>
            <Stack.Screen name="Login" component={LoginScreen} />
            <Stack.Screen name="SignUp" component={SignUpScreen} />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
```

## Error Handling

```javascript
import { PlintoError } from '@plinto/react-native';

const handleError = (error) => {
  if (error.code === 'NETWORK_ERROR') {
    Alert.alert('Network Error', 'Please check your connection');
  } else if (error.code === 'INVALID_CREDENTIALS') {
    Alert.alert('Login Failed', 'Invalid email or password');
  } else if (error.code === 'SESSION_EXPIRED') {
    Alert.alert('Session Expired', 'Please sign in again');
    navigation.navigate('Login');
  } else {
    Alert.alert('Error', error.message);
  }
};
```

## Upload Avatar

```javascript
import { launchImageLibrary } from 'react-native-image-picker';

const uploadAvatar = async () => {
  const result = await launchImageLibrary({
    mediaType: 'photo',
    quality: 0.7
  });
  
  if (!result.cancelled) {
    try {
      const response = await plinto.users.uploadAvatar(result.uri);
      Alert.alert('Success', 'Avatar updated');
    } catch (error) {
      Alert.alert('Error', error.message);
    }
  }
};
```

## Platform-Specific Code

```javascript
import { Platform } from 'react-native';

const BiometricButton = () => {
  const getBiometricLabel = () => {
    if (Platform.OS === 'ios') {
      return 'Use Face ID / Touch ID';
    }
    return 'Use Fingerprint';
  };
  
  return (
    <TouchableOpacity onPress={handleBiometricAuth}>
      <Text>{getBiometricLabel()}</Text>
    </TouchableOpacity>
  );
};
```

## Testing

### Detox E2E Tests
```javascript
describe('Authentication Flow', () => {
  beforeAll(async () => {
    await device.launchApp();
  });
  
  it('should sign in successfully', async () => {
    await element(by.id('email-input')).typeText('test@example.com');
    await element(by.id('password-input')).typeText('password');
    await element(by.id('sign-in-button')).tap();
    
    await expect(element(by.id('home-screen'))).toBeVisible();
  });
  
  it('should handle biometric auth', async () => {
    await element(by.id('biometric-button')).tap();
    // Simulator will auto-approve biometric
    await expect(element(by.id('home-screen'))).toBeVisible();
  });
});
```

### Jest Unit Tests
```javascript
import { renderHook, act } from '@testing-library/react-hooks';
import { useAuth } from '../hooks/useAuth';

jest.mock('@plinto/react-native');

describe('useAuth', () => {
  it('should sign in user', async () => {
    const { result } = renderHook(() => useAuth());
    
    await act(async () => {
      await result.current.signIn('test@example.com', 'password');
    });
    
    expect(result.current.user).toBeDefined();
    expect(result.current.user.email).toBe('test@example.com');
  });
});
```

## Performance Optimization

### Token Refresh
```javascript
// Automatic token refresh is handled internally
// But you can configure the interval
const plinto = new PlintoClient({
  baseURL: 'https://api.plinto.dev',
  tenantId: 'YOUR_TENANT_ID',
  clientId: 'YOUR_CLIENT_ID',
  tokenRefreshInterval: 45 * 60 * 1000, // 45 minutes
});
```

### Caching
```javascript
import AsyncStorage from '@react-native-async-storage/async-storage';

// Cache user data
const cacheUser = async (user) => {
  await AsyncStorage.setItem('cached_user', JSON.stringify(user));
};

// Load cached user on app start
const loadCachedUser = async () => {
  const cached = await AsyncStorage.getItem('cached_user');
  return cached ? JSON.parse(cached) : null;
};
```

## Troubleshooting

### Common Issues

1. **Keychain Access Issues (iOS)**
   ```bash
   # Reset keychain in simulator
   xcrun simctl keychain booted reset
   ```

2. **Deep Link Not Working (Android)**
   ```bash
   # Test deep link
   adb shell am start -W -a android.intent.action.VIEW -d "yourapp://auth/callback" com.yourapp
   ```

3. **Biometric Not Available**
   - Ensure device has biometric hardware
   - Check permissions in app settings
   - For simulator, enable Face ID/Touch ID in settings

## Next Steps

- [Full React Native API Reference](/docs/api/react-native)
- [Biometric Authentication Guide](/docs/guides/biometric)
- [Push Notifications Integration](/docs/guides/push-notifications)
- [Example App](https://github.com/plinto/react-native-example)

## Support

- 📖 [Documentation](https://docs.plinto.dev)
- 📱 [React Native Examples](https://github.com/plinto/react-native-examples)
- 💬 [Community Forum](https://community.plinto.dev)
- 📧 [Support](mailto:support@plinto.dev)