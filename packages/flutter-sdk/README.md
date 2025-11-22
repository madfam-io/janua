# Janua Flutter SDK

Official Flutter SDK for the Janua Identity Platform with support for iOS, Android, and Web platforms.

## Installation

Add to your `pubspec.yaml`:

```yaml
dependencies:
  janua_flutter: ^1.0.0
```

Then run:
```bash
flutter pub get
```

## Platform Setup

### iOS Setup

Add to your `Info.plist`:
```xml
<key>NSFaceIDUsageDescription</key>
<string>Authenticate with Face ID for secure access</string>
```

Minimum iOS version: 12.0

### Android Setup

Add to your `AndroidManifest.xml`:
```xml
<uses-permission android:name="android.permission.USE_BIOMETRIC" />
<uses-permission android:name="android.permission.INTERNET" />
```

Minimum Android SDK: 23 (Android 6.0)

### Web Setup

Add to your `index.html`:
```html
<script src="https://cdn.janua.dev/js/janua-web.min.js"></script>
```

## Quick Start

```dart
import 'package:janua_flutter/janua_flutter.dart';

void main() async {
  // Initialize the SDK
  final janua = Janua(
    baseUrl: 'https://api.janua.dev',
    apiKey: 'your-api-key',
    enableBiometrics: true,
  );

  // Sign in
  final authResult = await janua.signIn(
    email: 'user@example.com',
    password: 'password',
  );

  print('Signed in as: ${authResult.user.email}');
}
```

## Features

- 🔐 **Multi-Platform Auth**: iOS, Android, Web support
- 📱 **Biometric Authentication**: Face ID, Touch ID, Fingerprint
- 🔑 **Passkeys**: WebAuthn for passwordless authentication
- 🎨 **Flutter Widgets**: Pre-built authentication UI
- 💾 **Secure Storage**: Platform-specific encrypted storage
- 🔄 **State Management**: Built-in BLoC pattern support
- 📡 **Real-time Updates**: WebSocket support for live data
- 🌐 **Internationalization**: Multi-language support

## API Reference

### Authentication

```dart
// Sign up
final authResult = await janua.signUp(
  email: 'user@example.com',
  password: 'SecurePassword123!',
  name: 'John Doe',
);

// Sign in
final authResult = await janua.signIn(
  email: 'user@example.com',
  password: 'password',
);

// Sign in with biometrics
final authResult = await janua.signInWithBiometrics();

// Sign in with OAuth
final authResult = await janua.signInWithProvider(
  OAuthProvider.google,
  scopes: ['email', 'profile'],
);

// Sign out
await janua.signOut();

// Listen to auth state changes
janua.authStateChanges.listen((user) {
  if (user != null) {
    print('User signed in: ${user.email}');
  } else {
    print('User signed out');
  }
});
```

### Biometric Authentication

```dart
// Check biometric availability
final isAvailable = await janua.isBiometricAvailable();

// Get available biometric types
final types = await janua.getAvailableBiometrics();
// Returns: [BiometricType.faceId, BiometricType.touchId]

// Enable biometric authentication
await janua.enableBiometricAuth(
  localizedReason: 'Authenticate to access your account',
);

// Authenticate with biometrics
final authenticated = await janua.authenticateWithBiometrics(
  localizedReason: 'Verify your identity',
  options: AuthenticationOptions(
    biometricOnly: true,
    stickyAuth: true,
  ),
);
```

### User Management

```dart
// Get current user
final user = janua.currentUser;

// Update user profile
await janua.updateProfile(
  name: 'Jane Doe',
  photoUrl: 'https://example.com/photo.jpg',
  metadata: {
    'timezone': 'America/New_York',
    'language': 'en',
  },
);

// Change password
await janua.changePassword(
  currentPassword: 'old-password',
  newPassword: 'new-password',
);

// Upload avatar
final File imageFile = File('path/to/image.jpg');
final avatarUrl = await janua.uploadAvatar(imageFile);
```

### Session Management

```dart
// Get current session
final session = janua.currentSession;

// List all sessions
final sessions = await janua.listSessions();

// Revoke a session
await janua.revokeSession(sessionId);

// Listen to session events
janua.sessionEvents.listen((event) {
  switch (event.type) {
    case SessionEventType.created:
      print('New session created');
      break;
    case SessionEventType.revoked:
      print('Session revoked');
      break;
    case SessionEventType.expired:
      print('Session expired');
      break;
  }
});
```

## Flutter Widgets

Pre-built authentication widgets with Material Design and Cupertino support:

```dart
import 'package:janua_flutter/widgets.dart';

// Sign in widget
JanuaSignInWidget(
  onSuccess: (user) {
    Navigator.pushReplacementNamed(context, '/home');
  },
  onError: (error) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(error.message)),
    );
  },
  theme: JanuaTheme(
    primaryColor: Colors.blue,
    backgroundColor: Colors.white,
    errorColor: Colors.red,
  ),
  enableBiometrics: true,
  enableSocialLogin: [
    SocialProvider.google,
    SocialProvider.apple,
    SocialProvider.facebook,
  ],
)

// Sign up widget
JanuaSignUpWidget(
  onSuccess: (user) {
    Navigator.pushReplacementNamed(context, '/onboarding');
  },
  passwordRequirements: PasswordRequirements(
    minLength: 8,
    requireUppercase: true,
    requireNumbers: true,
    requireSpecialChars: true,
  ),
)

// Profile widget
JanuaProfileWidget(
  user: currentUser,
  onSignOut: () {
    Navigator.pushReplacementNamed(context, '/login');
  },
  onUpdateProfile: (updates) async {
    await janua.updateProfile(updates);
  },
  enableAvatarUpload: true,
  enableMFA: true,
)

// Auth guard widget
JanuaAuthGuard(
  child: HomeScreen(),
  fallback: SignInScreen(),
  loadingWidget: CircularProgressIndicator(),
)
```

## State Management

Built-in BLoC pattern support for state management:

```dart
// Auth BLoC
class AuthBloc extends Bloc<AuthEvent, AuthState> {
  final Janua janua;
  
  AuthBloc({required this.janua}) : super(AuthInitial()) {
    on<SignInRequested>(_onSignInRequested);
    on<SignOutRequested>(_onSignOutRequested);
    
    // Listen to auth state changes
    janua.authStateChanges.listen((user) {
      add(AuthStateChanged(user));
    });
  }
  
  Future<void> _onSignInRequested(
    SignInRequested event,
    Emitter<AuthState> emit,
  ) async {
    emit(AuthLoading());
    try {
      final result = await janua.signIn(
        email: event.email,
        password: event.password,
      );
      emit(AuthSuccess(result.user));
    } catch (e) {
      emit(AuthFailure(e.toString()));
    }
  }
}

// Using with BlocProvider
BlocProvider(
  create: (context) => AuthBloc(janua: janua),
  child: MyApp(),
)
```

## Secure Storage

Platform-specific encrypted storage implementation:

```dart
// Store sensitive data
await janua.secureStorage.write(
  key: 'api_token',
  value: 'secret-token',
);

// Read sensitive data
final token = await janua.secureStorage.read(key: 'api_token');

// Delete sensitive data
await janua.secureStorage.delete(key: 'api_token');

// Clear all secure storage
await janua.secureStorage.deleteAll();

// Check if key exists
final hasToken = await janua.secureStorage.containsKey(key: 'api_token');
```

## WebSocket Support

Real-time updates and live data synchronization:

```dart
// Connect to WebSocket
await janua.connectWebSocket();

// Listen to real-time events
janua.on('user.updated', (data) {
  print('User updated: $data');
});

janua.on('session.created', (data) {
  print('New session: $data');
});

janua.on('security.alert', (data) {
  showSecurityAlert(data);
});

// Send WebSocket message
janua.send('message', {
  'type': 'ping',
  'timestamp': DateTime.now().toIso8601String(),
});

// Disconnect WebSocket
await janua.disconnectWebSocket();
```

## Internationalization

Multi-language support with easy localization:

```dart
// Set locale
await janua.setLocale(Locale('es', 'ES'));

// Get available locales
final locales = janua.supportedLocales;

// Use localized strings
Text(janua.t('auth.sign_in')); // "Sign In" or "Iniciar Sesión"

// Add custom translations
janua.addTranslations('fr', {
  'auth.sign_in': 'Se connecter',
  'auth.sign_up': "S'inscrire",
});
```

## Error Handling

```dart
try {
  await janua.signIn(email: email, password: password);
} on JanuaAuthException catch (e) {
  switch (e.code) {
    case 'invalid-credentials':
      showError('Invalid email or password');
      break;
    case 'user-disabled':
      showError('This account has been disabled');
      break;
    case 'too-many-requests':
      showError('Too many attempts. Please try again later');
      break;
    default:
      showError(e.message);
  }
} on JanuaNetworkException catch (e) {
  showError('Network error. Please check your connection');
} catch (e) {
  showError('An unexpected error occurred');
}
```

## Platform-Specific Features

### iOS Specific
```dart
if (Platform.isIOS) {
  // Sign in with Apple
  final result = await janua.signInWithApple(
    scopes: [AppleIDAuthorizationScopes.email, AppleIDAuthorizationScopes.fullName],
  );
}
```

### Android Specific
```dart
if (Platform.isAndroid) {
  // Configure Android-specific biometric settings
  await janua.configureBiometric(
    androidAuthStrings: AndroidAuthMessages(
      biometricHint: 'Verify identity',
      biometricNotRecognized: 'Not recognized. Try again.',
      biometricSuccess: 'Success',
      cancelButton: 'Cancel',
      deviceCredentialsRequiredTitle: 'Device credentials required',
      deviceCredentialsSetupDescription: 'Please set up device credentials',
      goToSettingsButton: 'Go to settings',
      goToSettingsDescription: 'Device credentials not set up',
      signInTitle: 'Authentication required',
    ),
  );
}
```

### Web Specific
```dart
if (kIsWeb) {
  // Configure WebAuthn for web platform
  await janua.configureWebAuthn(
    rpName: 'Janua Demo',
    rpId: 'janua.dev',
    userVerification: 'preferred',
  );
}
```

## Testing

```dart
// Use mock client for testing
final mockJanua = MockJanua();

when(mockJanua.signIn(any, any)).thenAnswer(
  (_) async => AuthResult(
    user: User(id: '123', email: 'test@example.com'),
    session: Session(token: 'mock-token'),
  ),
);

// Widget testing
testWidgets('Sign in button test', (WidgetTester tester) async {
  await tester.pumpWidget(
    MaterialApp(
      home: JanuaSignInWidget(
        janua: mockJanua,
        onSuccess: (user) {},
      ),
    ),
  );
  
  await tester.tap(find.text('Sign In'));
  await tester.pump();
  
  verify(mockJanua.signIn(any, any)).called(1);
});
```

## Examples

Complete example applications:

- [Basic Authentication](./example/lib/basic_auth.dart)
- [Biometric Login](./example/lib/biometric_auth.dart)
- [Social Login](./example/lib/social_login.dart)
- [Custom UI Theme](./example/lib/custom_theme.dart)
- [State Management](./example/lib/state_management.dart)

## Migration Guide

Migrating from other auth solutions:

- [From Firebase Auth](./docs/migration/firebase.md)
- [From Auth0](./docs/migration/auth0.md)
- [From Supabase Auth](./docs/migration/supabase.md)

## Contributing

We welcome contributions! Please see our [Contributing Guide](../../CONTRIBUTING.md).

## License

AGPL-3.0 License - see [LICENSE](../../LICENSE) for details.