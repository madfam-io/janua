# Flutter SDK Complete Guide

## Overview

The **@plinto/flutter** SDK provides a comprehensive Flutter package for integrating Plinto authentication across iOS, Android, and Web platforms. Built with native performance in mind, it offers biometric authentication, secure storage, real-time updates, and pre-built widgets following Material Design and Cupertino patterns.

## Table of Contents

1. [Installation & Setup](#installation--setup)
2. [Platform Configuration](#platform-configuration)
3. [Core Authentication](#core-authentication)
4. [Biometric Authentication](#biometric-authentication)
5. [Pre-built Widgets](#pre-built-widgets)
6. [State Management](#state-management)
7. [Secure Storage](#secure-storage)
8. [Real-time Features](#real-time-features)
9. [Platform-Specific Implementation](#platform-specific-implementation)
10. [Testing Strategies](#testing-strategies)
11. [Migration & Integration](#migration--integration)
12. [Troubleshooting](#troubleshooting)

## Installation & Setup

### Package Installation

```yaml
# pubspec.yaml
dependencies:
  plinto_flutter: ^1.0.0

  # Required for biometric authentication
  local_auth: ^2.1.6

  # Required for secure storage
  flutter_secure_storage: ^9.0.0

  # Optional: For advanced state management
  flutter_bloc: ^8.1.3

  # Optional: For network requests
  dio: ^5.3.2
```

```bash
flutter pub get
```

### Basic Initialization

```dart
// main.dart
import 'package:flutter/material.dart';
import 'package:plinto_flutter/plinto_flutter.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize Plinto SDK
  final plinto = await Plinto.initialize(
    config: PlintoConfig(
      baseUrl: 'https://api.plinto.dev',
      apiKey: 'your-api-key',
      organizationSlug: 'your-org-slug',
      environment: Environment.production,
      enableBiometrics: true,
      enableSecureStorage: true,
      enableRealTimeUpdates: true,
    ),
  );

  runApp(MyApp(plinto: plinto));
}

class MyApp extends StatelessWidget {
  final Plinto plinto;

  const MyApp({Key? key, required this.plinto}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return PlintoProvider(
      plinto: plinto,
      child: MaterialApp(
        title: 'Plinto Flutter Demo',
        theme: ThemeData(
          primarySwatch: Colors.blue,
          useMaterial3: true,
        ),
        home: const AuthWrapper(),
      ),
    );
  }
}
```

### Configuration Options

```dart
// config/plinto_config.dart
class PlintoConfigurationManager {
  static PlintoConfig getConfig() {
    const environment = String.fromEnvironment('ENVIRONMENT', defaultValue: 'development');

    switch (environment) {
      case 'production':
        return PlintoConfig(
          baseUrl: 'https://api.plinto.dev',
          apiKey: const String.fromEnvironment('PLINTO_API_KEY'),
          organizationSlug: const String.fromEnvironment('PLINTO_ORG_SLUG'),
          environment: Environment.production,
          enableBiometrics: true,
          enableSecureStorage: true,
          enableRealTimeUpdates: true,
          timeout: const Duration(seconds: 30),
          retryAttempts: 3,
          logLevel: LogLevel.warning,
        );

      case 'staging':
        return PlintoConfig(
          baseUrl: 'https://staging-api.plinto.dev',
          apiKey: const String.fromEnvironment('PLINTO_STAGING_API_KEY'),
          organizationSlug: 'staging-org',
          environment: Environment.staging,
          enableBiometrics: true,
          enableSecureStorage: true,
          enableRealTimeUpdates: true,
          logLevel: LogLevel.info,
        );

      default: // development
        return PlintoConfig(
          baseUrl: 'http://localhost:8000',
          apiKey: 'dev-api-key',
          organizationSlug: 'dev-org',
          environment: Environment.development,
          enableBiometrics: false, // Disable for simulator
          enableSecureStorage: true,
          enableRealTimeUpdates: false,
          logLevel: LogLevel.debug,
        );
    }
  }
}
```

## Platform Configuration

### iOS Configuration

```xml
<!-- ios/Runner/Info.plist -->
<key>NSFaceIDUsageDescription</key>
<string>Authenticate with Face ID for secure access to your account</string>

<key>NSBiometricAuthenticationUsageDescription</key>
<string>Use biometric authentication for quick and secure access</string>

<!-- For camera access (if avatar upload is enabled) -->
<key>NSCameraUsageDescription</key>
<string>Take photos for your profile avatar</string>

<!-- For photo library access -->
<key>NSPhotoLibraryUsageDescription</key>
<string>Select photos for your profile avatar</string>

<!-- Deep linking support -->
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleURLName</key>
    <string>plinto.auth</string>
    <key>CFBundleURLSchemes</key>
    <array>
      <string>your-app-scheme</string>
    </array>
  </dict>
</array>
```

```swift
// ios/Runner/AppDelegate.swift
import UIKit
import Flutter
import LocalAuthentication

@UIApplicationMain
@objc class AppDelegate: FlutterAppDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    GeneratedPluginRegistrant.register(with: self)

    // Configure biometric authentication
    let context = LAContext()
    var error: NSError?

    if context.canEvaluatePolicy(.biometryAny, error: &error) {
      // Biometric authentication is available
      print("Biometric authentication available")
    }

    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  // Handle deep links
  override func application(
    _ app: UIApplication,
    open url: URL,
    options: [UIApplication.OpenURLOptionsKey : Any] = [:]
  ) -> Bool {
    return super.application(app, open: url, options: options)
  }
}
```

### Android Configuration

```xml
<!-- android/app/src/main/AndroidManifest.xml -->
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <!-- Biometric permissions -->
    <uses-permission android:name="android.permission.USE_BIOMETRIC" />
    <uses-permission android:name="android.permission.USE_FINGERPRINT" />

    <!-- Network permissions -->
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

    <!-- Camera permissions (if avatar upload is enabled) -->
    <uses-permission android:name="android.permission.CAMERA" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />

    <application
        android:label="Plinto Flutter App"
        android:name="${applicationName}"
        android:icon="@mipmap/ic_launcher">

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:launchMode="singleTop"
            android:theme="@style/LaunchTheme"
            android:configChanges="orientation|keyboardHidden|keyboard|screenSize|smallestScreenSize|locale|layoutDirection|fontScale|screenLayout|density|uiMode"
            android:hardwareAccelerated="true"
            android:windowSoftInputMode="adjustResize">

            <meta-data
              android:name="io.flutter.embedding.android.NormalTheme"
              android:resource="@style/NormalTheme"
              />

            <intent-filter android:autoVerify="true">
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>

            <!-- Deep linking support -->
            <intent-filter android:autoVerify="true">
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="your-app-scheme" />
            </intent-filter>
        </activity>

        <meta-data
            android:name="flutterEmbedding"
            android:value="2" />
    </application>
</manifest>
```

```kotlin
// android/app/src/main/kotlin/MainActivity.kt
package com.yourcompany.yourapp

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugins.GeneratedPluginRegistrant
import androidx.biometric.BiometricManager

class MainActivity: FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        GeneratedPluginRegistrant.registerWith(flutterEngine)

        // Check biometric availability
        val biometricManager = BiometricManager.from(this)
        when (biometricManager.canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_WEAK)) {
            BiometricManager.BIOMETRIC_SUCCESS -> {
                // Biometric authentication is available
            }
            BiometricManager.BIOMETRIC_ERROR_NO_HARDWARE -> {
                // No biometric features available
            }
            BiometricManager.BIOMETRIC_ERROR_HW_UNAVAILABLE -> {
                // Biometric features are unavailable
            }
            BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED -> {
                // No biometric credentials enrolled
            }
        }
    }
}
```

### Web Configuration

```html
<!-- web/index.html -->
<!DOCTYPE html>
<html>
<head>
  <base href="$FLUTTER_BASE_HREF">
  <meta charset="UTF-8">
  <meta content="IE=Edge" http-equiv="X-UA-Compatible">
  <meta name="description" content="Plinto Flutter Web App">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black">
  <meta name="apple-mobile-web-app-title" content="Plinto App">
  <link rel="apple-touch-icon" href="icons/Icon-192.png">
  <link rel="icon" type="image/png" href="favicon.png"/>
  <title>Plinto App</title>
  <link rel="manifest" href="manifest.json">

  <!-- Plinto Web SDK -->
  <script src="https://cdn.plinto.dev/js/plinto-web.min.js"></script>
</head>
<body>
  <script>
    window.addEventListener('load', function(ev) {
      // Initialize Plinto Web SDK
      window.PlintoWeb = new PlintoWebSDK({
        apiKey: 'your-web-api-key',
        baseUrl: 'https://api.plinto.dev'
      });

      // Download main.dart.js
      _flutter.loader.loadEntrypoint({
        serviceWorker: {
          serviceWorkerVersion: serviceWorkerVersion,
        }
      }).then(function(engineInitializer) {
        return engineInitializer.initializeEngine();
      }).then(function(appRunner) {
        return appRunner.runApp();
      });
    });
  </script>
</body>
</html>
```

## Core Authentication

### Authentication Service

```dart
// services/auth_service.dart
import 'package:plinto_flutter/plinto_flutter.dart';

class AuthService {
  final Plinto _plinto;

  AuthService(this._plinto);

  // Stream of authentication state changes
  Stream<User?> get authStateChanges => _plinto.authStateChanges;

  // Current user
  User? get currentUser => _plinto.currentUser;

  // Sign up with email and password
  Future<AuthResult> signUp({
    required String email,
    required String password,
    String? firstName,
    String? lastName,
    Map<String, dynamic>? metadata,
  }) async {
    try {
      final result = await _plinto.signUp(
        email: email,
        password: password,
        name: firstName != null && lastName != null
            ? '$firstName $lastName'
            : null,
        metadata: metadata,
      );

      // Send email verification
      await _plinto.sendEmailVerification();

      return result;
    } on PlintoException catch (e) {
      throw AuthServiceException.fromPlintoException(e);
    }
  }

  // Sign in with email and password
  Future<AuthResult> signIn({
    required String email,
    required String password,
    bool rememberMe = false,
  }) async {
    try {
      final result = await _plinto.signIn(
        email: email,
        password: password,
      );

      if (rememberMe) {
        await _plinto.secureStorage.write(
          key: 'remember_user',
          value: email,
        );
      }

      return result;
    } on PlintoException catch (e) {
      throw AuthServiceException.fromPlintoException(e);
    }
  }

  // Sign in with biometrics
  Future<AuthResult> signInWithBiometrics({
    String? localizedReason,
  }) async {
    try {
      // Check if biometrics are available
      if (!await _plinto.isBiometricAvailable()) {
        throw const AuthServiceException(
          code: 'biometric-unavailable',
          message: 'Biometric authentication is not available',
        );
      }

      return await _plinto.signInWithBiometrics(
        localizedReason: localizedReason ?? 'Authenticate to access your account',
      );
    } on PlintoException catch (e) {
      throw AuthServiceException.fromPlintoException(e);
    }
  }

  // Sign in with OAuth provider
  Future<AuthResult> signInWithProvider({
    required OAuthProvider provider,
    List<String>? scopes,
  }) async {
    try {
      return await _plinto.signInWithProvider(
        provider,
        scopes: scopes,
      );
    } on PlintoException catch (e) {
      throw AuthServiceException.fromPlintoException(e);
    }
  }

  // Send magic link
  Future<void> sendMagicLink({
    required String email,
    String? redirectUrl,
  }) async {
    try {
      await _plinto.sendMagicLink(
        email: email,
        redirectUrl: redirectUrl,
      );
    } on PlintoException catch (e) {
      throw AuthServiceException.fromPlintoException(e);
    }
  }

  // Verify magic link
  Future<AuthResult> verifyMagicLink(String token) async {
    try {
      return await _plinto.verifyMagicLink(token);
    } on PlintoException catch (e) {
      throw AuthServiceException.fromPlintoException(e);
    }
  }

  // Password reset
  Future<void> sendPasswordReset(String email) async {
    try {
      await _plinto.sendPasswordReset(email);
    } on PlintoException catch (e) {
      throw AuthServiceException.fromPlintoException(e);
    }
  }

  // Change password
  Future<void> changePassword({
    required String currentPassword,
    required String newPassword,
  }) async {
    try {
      await _plinto.changePassword(
        currentPassword: currentPassword,
        newPassword: newPassword,
      );
    } on PlintoException catch (e) {
      throw AuthServiceException.fromPlintoException(e);
    }
  }

  // Sign out
  Future<void> signOut() async {
    try {
      await _plinto.signOut();

      // Clear remember me data
      await _plinto.secureStorage.delete(key: 'remember_user');
    } on PlintoException catch (e) {
      throw AuthServiceException.fromPlintoException(e);
    }
  }

  // Update user profile
  Future<User> updateProfile({
    String? name,
    String? photoUrl,
    Map<String, dynamic>? metadata,
  }) async {
    try {
      return await _plinto.updateProfile(
        name: name,
        photoUrl: photoUrl,
        metadata: metadata,
      );
    } on PlintoException catch (e) {
      throw AuthServiceException.fromPlintoException(e);
    }
  }

  // Upload avatar
  Future<String> uploadAvatar(File imageFile) async {
    try {
      return await _plinto.uploadAvatar(imageFile);
    } on PlintoException catch (e) {
      throw AuthServiceException.fromPlintoException(e);
    }
  }
}

// Custom exception class
class AuthServiceException implements Exception {
  final String code;
  final String message;

  const AuthServiceException({
    required this.code,
    required this.message,
  });

  factory AuthServiceException.fromPlintoException(PlintoException e) {
    return AuthServiceException(
      code: e.code,
      message: e.message,
    );
  }

  @override
  String toString() => 'AuthServiceException: $message ($code)';
}
```

## Biometric Authentication

### Biometric Setup and Management

```dart
// services/biometric_service.dart
import 'package:local_auth/local_auth.dart';
import 'package:plinto_flutter/plinto_flutter.dart';

class BiometricService {
  final Plinto _plinto;
  final LocalAuthentication _localAuth = LocalAuthentication();

  BiometricService(this._plinto);

  // Check if biometric authentication is available
  Future<bool> isBiometricAvailable() async {
    try {
      final isAvailable = await _localAuth.canCheckBiometrics;
      final isDeviceSupported = await _localAuth.isDeviceSupported();
      return isAvailable && isDeviceSupported;
    } catch (e) {
      return false;
    }
  }

  // Get available biometric types
  Future<List<BiometricType>> getAvailableBiometrics() async {
    try {
      return await _localAuth.getAvailableBiometrics();
    } catch (e) {
      return [];
    }
  }

  // Enable biometric authentication for the user
  Future<void> enableBiometricAuth({
    required String localizedReason,
    String? password,
  }) async {
    // First, verify current password if required
    if (password != null) {
      final user = _plinto.currentUser;
      if (user?.email == null) {
        throw const BiometricServiceException(
          code: 'no-user',
          message: 'No authenticated user found',
        );
      }

      // Verify password by attempting sign in
      try {
        await _plinto.signIn(
          email: user!.email!,
          password: password,
        );
      } catch (e) {
        throw const BiometricServiceException(
          code: 'invalid-password',
          message: 'Invalid password provided',
        );
      }
    }

    // Authenticate with biometrics to ensure it works
    final didAuthenticate = await _localAuth.authenticate(
      localizedReason: localizedReason,
      options: const AuthenticationOptions(
        biometricOnly: true,
        stickyAuth: true,
      ),
    );

    if (!didAuthenticate) {
      throw const BiometricServiceException(
        code: 'authentication-failed',
        message: 'Biometric authentication failed',
      );
    }

    // Enable biometric authentication in Plinto
    await _plinto.enableBiometricAuth(localizedReason: localizedReason);
  }

  // Disable biometric authentication
  Future<void> disableBiometricAuth({
    String? password,
  }) async {
    if (password != null) {
      // Verify password before disabling
      final user = _plinto.currentUser;
      if (user?.email != null) {
        await _plinto.signIn(
          email: user!.email!,
          password: password,
        );
      }
    }

    await _plinto.disableBiometricAuth();
  }

  // Authenticate with biometrics
  Future<bool> authenticateWithBiometrics({
    required String localizedReason,
    bool biometricOnly = true,
    bool stickyAuth = true,
  }) async {
    try {
      return await _localAuth.authenticate(
        localizedReason: localizedReason,
        options: AuthenticationOptions(
          biometricOnly: biometricOnly,
          stickyAuth: stickyAuth,
        ),
      );
    } catch (e) {
      return false;
    }
  }

  // Check if biometric authentication is enabled for current user
  Future<bool> isBiometricEnabled() async {
    return await _plinto.isBiometricEnabled();
  }

  // Get biometric capability description
  Future<String> getBiometricCapabilityDescription() async {
    final biometrics = await getAvailableBiometrics();

    if (biometrics.contains(BiometricType.face)) {
      return 'Face ID';
    } else if (biometrics.contains(BiometricType.fingerprint)) {
      return 'Fingerprint';
    } else if (biometrics.contains(BiometricType.iris)) {
      return 'Iris';
    } else if (biometrics.contains(BiometricType.strong) ||
               biometrics.contains(BiometricType.weak)) {
      return 'Biometric Authentication';
    } else {
      return 'Device Authentication';
    }
  }
}

class BiometricServiceException implements Exception {
  final String code;
  final String message;

  const BiometricServiceException({
    required this.code,
    required this.message,
  });

  @override
  String toString() => 'BiometricServiceException: $message ($code)';
}
```

### Biometric Authentication Widget

```dart
// widgets/biometric_auth_widget.dart
class BiometricAuthWidget extends StatefulWidget {
  final VoidCallback? onSuccess;
  final Function(String)? onError;
  final String? localizedReason;
  final bool showFallback;

  const BiometricAuthWidget({
    Key? key,
    this.onSuccess,
    this.onError,
    this.localizedReason,
    this.showFallback = true,
  }) : super(key: key);

  @override
  State<BiometricAuthWidget> createState() => _BiometricAuthWidgetState();
}

class _BiometricAuthWidgetState extends State<BiometricAuthWidget>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  late Animation<double> _pulseAnimation;

  bool _isAuthenticating = false;
  String? _biometricType;

  @override
  void initState() {
    super.initState();
    _setupAnimation();
    _detectBiometricType();
  }

  void _setupAnimation() {
    _animationController = AnimationController(
      duration: const Duration(seconds: 2),
      vsync: this,
    );

    _pulseAnimation = Tween<double>(
      begin: 0.8,
      end: 1.2,
    ).animate(CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeInOut,
    ));

    _animationController.repeat(reverse: true);
  }

  Future<void> _detectBiometricType() async {
    final biometricService = context.read<BiometricService>();
    final description = await biometricService.getBiometricCapabilityDescription();

    if (mounted) {
      setState(() {
        _biometricType = description;
      });
    }
  }

  Future<void> _authenticate() async {
    if (_isAuthenticating) return;

    setState(() {
      _isAuthenticating = true;
    });

    try {
      final authService = context.read<AuthService>();

      await authService.signInWithBiometrics(
        localizedReason: widget.localizedReason ??
            'Authenticate to access your account',
      );

      widget.onSuccess?.call();
    } catch (e) {
      widget.onError?.call(e.toString());
    } finally {
      if (mounted) {
        setState(() {
          _isAuthenticating = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        // Biometric icon with pulse animation
        AnimatedBuilder(
          animation: _pulseAnimation,
          builder: (context, child) {
            return Transform.scale(
              scale: _isAuthenticating ? _pulseAnimation.value : 1.0,
              child: Container(
                width: 120,
                height: 120,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: Theme.of(context).primaryColor.withOpacity(0.1),
                  border: Border.all(
                    color: Theme.of(context).primaryColor,
                    width: 2,
                  ),
                ),
                child: Icon(
                  _getBiometricIcon(),
                  size: 60,
                  color: Theme.of(context).primaryColor,
                ),
              ),
            );
          },
        ),

        const SizedBox(height: 24),

        // Biometric type text
        Text(
          _biometricType ?? 'Biometric Authentication',
          style: Theme.of(context).textTheme.headlineSmall,
          textAlign: TextAlign.center,
        ),

        const SizedBox(height: 8),

        Text(
          _isAuthenticating
              ? 'Authenticating...'
              : 'Touch the sensor to continue',
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: Theme.of(context).textTheme.bodySmall?.color,
          ),
          textAlign: TextAlign.center,
        ),

        const SizedBox(height: 32),

        // Authenticate button
        SizedBox(
          width: double.infinity,
          child: ElevatedButton.icon(
            onPressed: _isAuthenticating ? null : _authenticate,
            icon: Icon(
              _isAuthenticating
                  ? Icons.hourglass_empty
                  : Icons.fingerprint,
            ),
            label: Text(
              _isAuthenticating
                  ? 'Authenticating...'
                  : 'Authenticate',
            ),
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 16),
            ),
          ),
        ),

        // Fallback options
        if (widget.showFallback) ...[
          const SizedBox(height: 16),
          TextButton(
            onPressed: () {
              // Navigate to password login
              Navigator.of(context).pushReplacement(
                MaterialPageRoute(
                  builder: (context) => const LoginScreen(),
                ),
              );
            },
            child: const Text('Use password instead'),
          ),
        ],
      ],
    );
  }

  IconData _getBiometricIcon() {
    switch (_biometricType) {
      case 'Face ID':
        return Icons.face;
      case 'Fingerprint':
        return Icons.fingerprint;
      case 'Iris':
        return Icons.visibility;
      default:
        return Icons.security;
    }
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }
}
```

## Pre-built Widgets

### Complete Authentication Flow Widget

```dart
// widgets/auth_flow_widget.dart
class AuthFlowWidget extends StatefulWidget {
  final Function(User)? onAuthSuccess;
  final Function(String)? onAuthError;
  final PlintoTheme? theme;
  final bool enableBiometrics;
  final bool enableSocialLogin;
  final List<SocialProvider> socialProviders;

  const AuthFlowWidget({
    Key? key,
    this.onAuthSuccess,
    this.onAuthError,
    this.theme,
    this.enableBiometrics = true,
    this.enableSocialLogin = true,
    this.socialProviders = const [
      SocialProvider.google,
      SocialProvider.apple,
      SocialProvider.facebook,
    ],
  }) : super(key: key);

  @override
  State<AuthFlowWidget> createState() => _AuthFlowWidgetState();
}

class _AuthFlowWidgetState extends State<AuthFlowWidget>
    with TickerProviderStateMixin {
  late TabController _tabController;
  bool _isLoading = false;
  String? _errorMessage;

  final _loginFormKey = GlobalKey<FormState>();
  final _signUpFormKey = GlobalKey<FormState>();

  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  final _firstNameController = TextEditingController();
  final _lastNameController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _checkRememberedUser();
  }

  Future<void> _checkRememberedUser() async {
    final authService = context.read<AuthService>();
    final plinto = context.read<Plinto>();

    final rememberedEmail = await plinto.secureStorage.read(key: 'remember_user');
    if (rememberedEmail != null) {
      _emailController.text = rememberedEmail;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = widget.theme ?? PlintoTheme.defaultTheme();

    return Theme(
      data: Theme.of(context).copyWith(
        primaryColor: theme.primaryColor,
        colorScheme: Theme.of(context).colorScheme.copyWith(
          primary: theme.primaryColor,
          error: theme.errorColor,
        ),
      ),
      child: Container(
        decoration: BoxDecoration(
          gradient: theme.backgroundGradient,
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              children: [
                // Logo and title
                _buildHeader(theme),

                const SizedBox(height: 32),

                // Biometric authentication (if available and enabled)
                if (widget.enableBiometrics)
                  FutureBuilder<bool>(
                    future: context.read<BiometricService>().isBiometricAvailable(),
                    builder: (context, snapshot) {
                      if (snapshot.data == true) {
                        return Column(
                          children: [
                            BiometricQuickAuthButton(
                              onSuccess: () => widget.onAuthSuccess?.call(
                                context.read<AuthService>().currentUser!,
                              ),
                              onError: (error) => _handleError(error),
                            ),
                            const SizedBox(height: 24),
                            _buildDivider(),
                            const SizedBox(height: 24),
                          ],
                        );
                      }
                      return const SizedBox.shrink();
                    },
                  ),

                // Tab bar
                _buildTabBar(theme),

                const SizedBox(height: 24),

                // Auth forms
                Expanded(
                  child: TabBarView(
                    controller: _tabController,
                    children: [
                      _buildLoginForm(theme),
                      _buildSignUpForm(theme),
                    ],
                  ),
                ),

                // Social login options
                if (widget.enableSocialLogin) ...[
                  const SizedBox(height: 24),
                  _buildDivider(),
                  const SizedBox(height: 24),
                  _buildSocialLoginButtons(theme),
                ],

                // Error message
                if (_errorMessage != null) ...[
                  const SizedBox(height: 16),
                  _buildErrorMessage(theme),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(PlintoTheme theme) {
    return Column(
      children: [
        Container(
          width: 80,
          height: 80,
          decoration: BoxDecoration(
            color: theme.primaryColor,
            borderRadius: BorderRadius.circular(20),
          ),
          child: const Icon(
            Icons.security,
            color: Colors.white,
            size: 40,
          ),
        ),
        const SizedBox(height: 16),
        Text(
          'Welcome to Plinto',
          style: TextStyle(
            fontSize: 28,
            fontWeight: FontWeight.bold,
            color: theme.onBackgroundColor,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Secure authentication for your app',
          style: TextStyle(
            fontSize: 16,
            color: theme.onBackgroundColor.withOpacity(0.7),
          ),
        ),
      ],
    );
  }

  Widget _buildTabBar(PlintoTheme theme) {
    return Container(
      decoration: BoxDecoration(
        color: theme.surfaceColor,
        borderRadius: BorderRadius.circular(8),
      ),
      child: TabBar(
        controller: _tabController,
        indicator: BoxDecoration(
          color: theme.primaryColor,
          borderRadius: BorderRadius.circular(8),
        ),
        labelColor: Colors.white,
        unselectedLabelColor: theme.onSurfaceColor,
        tabs: const [
          Tab(text: 'Sign In'),
          Tab(text: 'Sign Up'),
        ],
      ),
    );
  }

  Widget _buildLoginForm(PlintoTheme theme) {
    return Form(
      key: _loginFormKey,
      child: Column(
        children: [
          _buildEmailField(theme),
          const SizedBox(height: 16),
          _buildPasswordField(theme),
          const SizedBox(height: 8),
          _buildForgotPasswordButton(theme),
          const SizedBox(height: 24),
          _buildLoginButton(theme),
          const SizedBox(height: 16),
          _buildMagicLinkButton(theme),
        ],
      ),
    );
  }

  Widget _buildSignUpForm(PlintoTheme theme) {
    return Form(
      key: _signUpFormKey,
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: _buildFirstNameField(theme),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildLastNameField(theme),
              ),
            ],
          ),
          const SizedBox(height: 16),
          _buildEmailField(theme),
          const SizedBox(height: 16),
          _buildPasswordField(theme),
          const SizedBox(height: 16),
          _buildConfirmPasswordField(theme),
          const SizedBox(height: 24),
          _buildSignUpButton(theme),
        ],
      ),
    );
  }

  Widget _buildEmailField(PlintoTheme theme) {
    return TextFormField(
      controller: _emailController,
      keyboardType: TextInputType.emailAddress,
      decoration: InputDecoration(
        labelText: 'Email',
        prefixIcon: const Icon(Icons.email),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
        ),
      ),
      validator: (value) {
        if (value == null || value.isEmpty) {
          return 'Please enter your email';
        }
        if (!RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$').hasMatch(value)) {
          return 'Please enter a valid email';
        }
        return null;
      },
    );
  }

  Widget _buildPasswordField(PlintoTheme theme) {
    return TextFormField(
      controller: _passwordController,
      obscureText: true,
      decoration: InputDecoration(
        labelText: 'Password',
        prefixIcon: const Icon(Icons.lock),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
        ),
      ),
      validator: (value) {
        if (value == null || value.isEmpty) {
          return 'Please enter your password';
        }
        if (_tabController.index == 1 && value.length < 8) {
          return 'Password must be at least 8 characters';
        }
        return null;
      },
    );
  }

  // Additional form field builders...

  Widget _buildLoginButton(PlintoTheme theme) {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: _isLoading ? null : _handleLogin,
        style: ElevatedButton.styleFrom(
          backgroundColor: theme.primaryColor,
          padding: const EdgeInsets.symmetric(vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
        ),
        child: _isLoading
            ? const SizedBox(
                height: 20,
                width: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                ),
              )
            : const Text(
                'Sign In',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
      ),
    );
  }

  Future<void> _handleLogin() async {
    if (!_loginFormKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final authService = context.read<AuthService>();
      final result = await authService.signIn(
        email: _emailController.text.trim(),
        password: _passwordController.text,
        rememberMe: true,
      );

      widget.onAuthSuccess?.call(result.user);
    } catch (e) {
      _handleError(e.toString());
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  // Additional methods for sign up, social login, etc...

  void _handleError(String error) {
    setState(() {
      _errorMessage = error;
    });
    widget.onAuthError?.call(error);
  }

  @override
  void dispose() {
    _tabController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    _firstNameController.dispose();
    _lastNameController.dispose();
    super.dispose();
  }
}

// Theme configuration
class PlintoTheme {
  final Color primaryColor;
  final Color backgroundColor;
  final Color surfaceColor;
  final Color onBackgroundColor;
  final Color onSurfaceColor;
  final Color errorColor;
  final Gradient? backgroundGradient;

  const PlintoTheme({
    required this.primaryColor,
    required this.backgroundColor,
    required this.surfaceColor,
    required this.onBackgroundColor,
    required this.onSurfaceColor,
    required this.errorColor,
    this.backgroundGradient,
  });

  factory PlintoTheme.defaultTheme() {
    return PlintoTheme(
      primaryColor: const Color(0xFF2196F3),
      backgroundColor: Colors.white,
      surfaceColor: const Color(0xFFF5F5F5),
      onBackgroundColor: Colors.black87,
      onSurfaceColor: Colors.black54,
      errorColor: const Color(0xFFE53E3E),
      backgroundGradient: const LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [
          Color(0xFFF8F9FA),
          Color(0xFFE9ECEF),
        ],
      ),
    );
  }
}
```

## State Management

### BLoC Implementation

```dart
// bloc/auth_bloc.dart
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';

// Events
abstract class AuthEvent extends Equatable {
  const AuthEvent();

  @override
  List<Object?> get props => [];
}

class AuthCheckRequested extends AuthEvent {}

class AuthSignInRequested extends AuthEvent {
  final String email;
  final String password;
  final bool rememberMe;

  const AuthSignInRequested({
    required this.email,
    required this.password,
    this.rememberMe = false,
  });

  @override
  List<Object?> get props => [email, password, rememberMe];
}

class AuthSignUpRequested extends AuthEvent {
  final String email;
  final String password;
  final String? firstName;
  final String? lastName;

  const AuthSignUpRequested({
    required this.email,
    required this.password,
    this.firstName,
    this.lastName,
  });

  @override
  List<Object?> get props => [email, password, firstName, lastName];
}

class AuthSignOutRequested extends AuthEvent {}

class AuthBiometricSignInRequested extends AuthEvent {
  final String localizedReason;

  const AuthBiometricSignInRequested({
    required this.localizedReason,
  });

  @override
  List<Object?> get props => [localizedReason];
}

class AuthSocialSignInRequested extends AuthEvent {
  final SocialProvider provider;
  final List<String>? scopes;

  const AuthSocialSignInRequested({
    required this.provider,
    this.scopes,
  });

  @override
  List<Object?> get props => [provider, scopes];
}

class AuthStateChanged extends AuthEvent {
  final User? user;

  const AuthStateChanged(this.user);

  @override
  List<Object?> get props => [user];
}

// States
abstract class AuthState extends Equatable {
  const AuthState();

  @override
  List<Object?> get props => [];
}

class AuthInitial extends AuthState {}

class AuthLoading extends AuthState {}

class AuthAuthenticated extends AuthState {
  final User user;

  const AuthAuthenticated(this.user);

  @override
  List<Object?> get props => [user];
}

class AuthUnauthenticated extends AuthState {}

class AuthError extends AuthState {
  final String message;
  final String? code;

  const AuthError({
    required this.message,
    this.code,
  });

  @override
  List<Object?> get props => [message, code];
}

// BLoC
class AuthBloc extends Bloc<AuthEvent, AuthState> {
  final AuthService _authService;
  final BiometricService _biometricService;
  late StreamSubscription<User?> _authStateSubscription;

  AuthBloc({
    required AuthService authService,
    required BiometricService biometricService,
  }) : _authService = authService,
       _biometricService = biometricService,
       super(AuthInitial()) {

    on<AuthCheckRequested>(_onAuthCheckRequested);
    on<AuthSignInRequested>(_onAuthSignInRequested);
    on<AuthSignUpRequested>(_onAuthSignUpRequested);
    on<AuthSignOutRequested>(_onAuthSignOutRequested);
    on<AuthBiometricSignInRequested>(_onAuthBiometricSignInRequested);
    on<AuthSocialSignInRequested>(_onAuthSocialSignInRequested);
    on<AuthStateChanged>(_onAuthStateChanged);

    // Listen to auth state changes
    _authStateSubscription = _authService.authStateChanges.listen(
      (user) => add(AuthStateChanged(user)),
    );
  }

  Future<void> _onAuthCheckRequested(
    AuthCheckRequested event,
    Emitter<AuthState> emit,
  ) async {
    emit(AuthLoading());

    final user = _authService.currentUser;
    if (user != null) {
      emit(AuthAuthenticated(user));
    } else {
      emit(AuthUnauthenticated());
    }
  }

  Future<void> _onAuthSignInRequested(
    AuthSignInRequested event,
    Emitter<AuthState> emit,
  ) async {
    emit(AuthLoading());

    try {
      final result = await _authService.signIn(
        email: event.email,
        password: event.password,
        rememberMe: event.rememberMe,
      );

      emit(AuthAuthenticated(result.user));
    } on AuthServiceException catch (e) {
      emit(AuthError(message: e.message, code: e.code));
    } catch (e) {
      emit(AuthError(message: 'An unexpected error occurred'));
    }
  }

  Future<void> _onAuthSignUpRequested(
    AuthSignUpRequested event,
    Emitter<AuthState> emit,
  ) async {
    emit(AuthLoading());

    try {
      final result = await _authService.signUp(
        email: event.email,
        password: event.password,
        firstName: event.firstName,
        lastName: event.lastName,
      );

      emit(AuthAuthenticated(result.user));
    } on AuthServiceException catch (e) {
      emit(AuthError(message: e.message, code: e.code));
    } catch (e) {
      emit(AuthError(message: 'An unexpected error occurred'));
    }
  }

  Future<void> _onAuthSignOutRequested(
    AuthSignOutRequested event,
    Emitter<AuthState> emit,
  ) async {
    try {
      await _authService.signOut();
      emit(AuthUnauthenticated());
    } catch (e) {
      emit(AuthError(message: 'Sign out failed'));
    }
  }

  Future<void> _onAuthBiometricSignInRequested(
    AuthBiometricSignInRequested event,
    Emitter<AuthState> emit,
  ) async {
    emit(AuthLoading());

    try {
      final result = await _authService.signInWithBiometrics(
        localizedReason: event.localizedReason,
      );

      emit(AuthAuthenticated(result.user));
    } on AuthServiceException catch (e) {
      emit(AuthError(message: e.message, code: e.code));
    } catch (e) {
      emit(AuthError(message: 'Biometric authentication failed'));
    }
  }

  Future<void> _onAuthSocialSignInRequested(
    AuthSocialSignInRequested event,
    Emitter<AuthState> emit,
  ) async {
    emit(AuthLoading());

    try {
      final result = await _authService.signInWithProvider(
        provider: event.provider,
        scopes: event.scopes,
      );

      emit(AuthAuthenticated(result.user));
    } on AuthServiceException catch (e) {
      emit(AuthError(message: e.message, code: e.code));
    } catch (e) {
      emit(AuthError(message: 'Social sign in failed'));
    }
  }

  void _onAuthStateChanged(
    AuthStateChanged event,
    Emitter<AuthState> emit,
  ) {
    if (event.user != null) {
      emit(AuthAuthenticated(event.user!));
    } else {
      emit(AuthUnauthenticated());
    }
  }

  @override
  Future<void> close() {
    _authStateSubscription.cancel();
    return super.close();
  }
}
```

### Provider Setup

```dart
// main.dart - Updated with providers
void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final plinto = await Plinto.initialize(
    config: PlintoConfigurationManager.getConfig(),
  );

  runApp(MyApp(plinto: plinto));
}

class MyApp extends StatelessWidget {
  final Plinto plinto;

  const MyApp({Key? key, required this.plinto}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MultiRepositoryProvider(
      providers: [
        RepositoryProvider<Plinto>.value(value: plinto),
        RepositoryProvider<AuthService>(
          create: (context) => AuthService(context.read<Plinto>()),
        ),
        RepositoryProvider<BiometricService>(
          create: (context) => BiometricService(context.read<Plinto>()),
        ),
      ],
      child: MultiBlocProvider(
        providers: [
          BlocProvider<AuthBloc>(
            create: (context) => AuthBloc(
              authService: context.read<AuthService>(),
              biometricService: context.read<BiometricService>(),
            )..add(AuthCheckRequested()),
          ),
        ],
        child: MaterialApp(
          title: 'Plinto Flutter Demo',
          theme: ThemeData(
            primarySwatch: Colors.blue,
            useMaterial3: true,
          ),
          home: const AuthWrapper(),
          routes: {
            '/login': (context) => const LoginScreen(),
            '/signup': (context) => const SignUpScreen(),
            '/home': (context) => const HomeScreen(),
            '/profile': (context) => const ProfileScreen(),
          },
        ),
      ),
    );
  }
}

// Auth wrapper to handle navigation based on auth state
class AuthWrapper extends StatelessWidget {
  const AuthWrapper({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return BlocListener<AuthBloc, AuthState>(
      listener: (context, state) {
        if (state is AuthError) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(state.message),
              backgroundColor: Colors.red,
            ),
          );
        }
      },
      child: BlocBuilder<AuthBloc, AuthState>(
        builder: (context, state) {
          switch (state.runtimeType) {
            case AuthLoading:
              return const Scaffold(
                body: Center(
                  child: CircularProgressIndicator(),
                ),
              );

            case AuthAuthenticated:
              return const HomeScreen();

            case AuthUnauthenticated:
            case AuthError:
              return const LoginScreen();

            default:
              return const SplashScreen();
          }
        },
      ),
    );
  }
}
```

## Secure Storage

### Secure Storage Service

```dart
// services/secure_storage_service.dart
class SecureStorageService {
  final Plinto _plinto;

  SecureStorageService(this._plinto);

  // Store sensitive data
  Future<void> storeSecurely({
    required String key,
    required String value,
    Map<String, String>? metadata,
  }) async {
    try {
      await _plinto.secureStorage.write(
        key: key,
        value: value,
        aOptions: const AndroidOptions(
          encryptedSharedPreferences: true,
          sharedPreferencesName: 'plinto_secure_prefs',
          preferencesKeyPrefix: 'plinto_',
        ),
        iOptions: const IOSOptions(
          groupId: 'group.com.yourcompany.yourapp.plinto',
          accountName: 'plinto_account',
          accessibility: IOSAccessibility.first_unlock_this_device,
        ),
        webOptions: const WebOptions(
          dbName: 'plinto_secure_db',
          publicKey: 'plinto_public_key',
        ),
      );

      // Store metadata if provided
      if (metadata != null) {
        await _storeMetadata(key, metadata);
      }
    } catch (e) {
      throw SecureStorageException(
        message: 'Failed to store data securely: $e',
      );
    }
  }

  // Retrieve sensitive data
  Future<String?> retrieveSecurely(String key) async {
    try {
      return await _plinto.secureStorage.read(
        key: key,
        aOptions: const AndroidOptions(
          encryptedSharedPreferences: true,
          sharedPreferencesName: 'plinto_secure_prefs',
          preferencesKeyPrefix: 'plinto_',
        ),
        iOptions: const IOSOptions(
          groupId: 'group.com.yourcompany.yourapp.plinto',
          accountName: 'plinto_account',
        ),
        webOptions: const WebOptions(
          dbName: 'plinto_secure_db',
          publicKey: 'plinto_public_key',
        ),
      );
    } catch (e) {
      throw SecureStorageException(
        message: 'Failed to retrieve data securely: $e',
      );
    }
  }

  // Store user preferences securely
  Future<void> storeUserPreferences(Map<String, dynamic> preferences) async {
    final preferencesJson = jsonEncode(preferences);
    await storeSecurely(
      key: 'user_preferences',
      value: preferencesJson,
      metadata: {
        'type': 'preferences',
        'lastUpdated': DateTime.now().toIso8601String(),
      },
    );
  }

  // Retrieve user preferences
  Future<Map<String, dynamic>?> retrieveUserPreferences() async {
    final preferencesJson = await retrieveSecurely('user_preferences');
    if (preferencesJson != null) {
      return jsonDecode(preferencesJson) as Map<String, dynamic>;
    }
    return null;
  }

  // Store authentication tokens
  Future<void> storeAuthTokens({
    required String accessToken,
    required String refreshToken,
    DateTime? expiresAt,
  }) async {
    final tokenData = {
      'accessToken': accessToken,
      'refreshToken': refreshToken,
      'expiresAt': expiresAt?.toIso8601String(),
      'storedAt': DateTime.now().toIso8601String(),
    };

    await storeSecurely(
      key: 'auth_tokens',
      value: jsonEncode(tokenData),
      metadata: {
        'type': 'auth_tokens',
        'sensitive': 'true',
      },
    );
  }

  // Retrieve authentication tokens
  Future<AuthTokens?> retrieveAuthTokens() async {
    final tokenJson = await retrieveSecurely('auth_tokens');
    if (tokenJson != null) {
      final tokenData = jsonDecode(tokenJson) as Map<String, dynamic>;
      return AuthTokens.fromJson(tokenData);
    }
    return null;
  }

  // Store biometric authentication data
  Future<void> storeBiometricData({
    required String userId,
    required bool isEnabled,
    required List<BiometricType> availableTypes,
  }) async {
    final biometricData = {
      'userId': userId,
      'isEnabled': isEnabled,
      'availableTypes': availableTypes.map((type) => type.toString()).toList(),
      'lastUpdated': DateTime.now().toIso8601String(),
    };

    await storeSecurely(
      key: 'biometric_data_$userId',
      value: jsonEncode(biometricData),
      metadata: {
        'type': 'biometric',
        'userId': userId,
      },
    );
  }

  // Check if data exists
  Future<bool> containsKey(String key) async {
    try {
      return await _plinto.secureStorage.containsKey(key: key);
    } catch (e) {
      return false;
    }
  }

  // Delete specific data
  Future<void> deleteSecurely(String key) async {
    try {
      await _plinto.secureStorage.delete(key: key);
      await _deleteMetadata(key);
    } catch (e) {
      throw SecureStorageException(
        message: 'Failed to delete data securely: $e',
      );
    }
  }

  // Clear all secure storage
  Future<void> clearAllSecureData() async {
    try {
      await _plinto.secureStorage.deleteAll();
    } catch (e) {
      throw SecureStorageException(
        message: 'Failed to clear secure storage: $e',
      );
    }
  }

  // Get all keys
  Future<Set<String>> getAllKeys() async {
    try {
      return await _plinto.secureStorage.readAll().then(
        (data) => data.keys.toSet(),
      );
    } catch (e) {
      return <String>{};
    }
  }

  // Private method to store metadata
  Future<void> _storeMetadata(String key, Map<String, String> metadata) async {
    final metadataKey = '${key}_metadata';
    await _plinto.secureStorage.write(
      key: metadataKey,
      value: jsonEncode(metadata),
    );
  }

  // Private method to delete metadata
  Future<void> _deleteMetadata(String key) async {
    final metadataKey = '${key}_metadata';
    try {
      await _plinto.secureStorage.delete(key: metadataKey);
    } catch (e) {
      // Ignore metadata deletion errors
    }
  }
}

// Auth tokens model
class AuthTokens {
  final String accessToken;
  final String refreshToken;
  final DateTime? expiresAt;
  final DateTime storedAt;

  AuthTokens({
    required this.accessToken,
    required this.refreshToken,
    this.expiresAt,
    required this.storedAt,
  });

  factory AuthTokens.fromJson(Map<String, dynamic> json) {
    return AuthTokens(
      accessToken: json['accessToken'] as String,
      refreshToken: json['refreshToken'] as String,
      expiresAt: json['expiresAt'] != null
          ? DateTime.parse(json['expiresAt'] as String)
          : null,
      storedAt: DateTime.parse(json['storedAt'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'accessToken': accessToken,
      'refreshToken': refreshToken,
      'expiresAt': expiresAt?.toIso8601String(),
      'storedAt': storedAt.toIso8601String(),
    };
  }

  bool get isExpired {
    if (expiresAt == null) return false;
    return DateTime.now().isAfter(expiresAt!);
  }
}

// Exception class
class SecureStorageException implements Exception {
  final String message;

  SecureStorageException({required this.message});

  @override
  String toString() => 'SecureStorageException: $message';
}
```

## Real-time Features

### WebSocket Service

```dart
// services/websocket_service.dart
class WebSocketService {
  final Plinto _plinto;
  WebSocketChannel? _channel;
  final Map<String, List<Function(dynamic)>> _eventListeners = {};
  Timer? _heartbeatTimer;
  bool _isConnected = false;

  WebSocketService(this._plinto);

  // Connect to WebSocket
  Future<void> connect() async {
    try {
      final wsUrl = await _plinto.getWebSocketUrl();
      final accessToken = await _plinto.getAccessToken();

      _channel = WebSocketChannel.connect(
        Uri.parse('$wsUrl?token=$accessToken'),
      );

      // Listen to messages
      _channel!.stream.listen(
        _handleMessage,
        onError: _handleError,
        onDone: _handleDisconnection,
      );

      _isConnected = true;
      _startHeartbeat();

      // Emit connection event
      _emitEvent('connection', {'status': 'connected'});

    } catch (e) {
      throw WebSocketException('Failed to connect: $e');
    }
  }

  // Disconnect from WebSocket
  Future<void> disconnect() async {
    _isConnected = false;
    _heartbeatTimer?.cancel();
    await _channel?.sink.close();
    _channel = null;

    _emitEvent('connection', {'status': 'disconnected'});
  }

  // Send message
  void send(String event, Map<String, dynamic> data) {
    if (!_isConnected || _channel == null) {
      throw WebSocketException('Not connected to WebSocket');
    }

    final message = jsonEncode({
      'event': event,
      'data': data,
      'timestamp': DateTime.now().toIso8601String(),
    });

    _channel!.sink.add(message);
  }

  // Listen to events
  void on(String event, Function(dynamic) callback) {
    if (!_eventListeners.containsKey(event)) {
      _eventListeners[event] = [];
    }
    _eventListeners[event]!.add(callback);
  }

  // Remove event listener
  void off(String event, Function(dynamic) callback) {
    if (_eventListeners.containsKey(event)) {
      _eventListeners[event]!.remove(callback);
    }
  }

  // Listen to user events
  void listenToUserEvents() {
    on('user.updated', (data) {
      _plinto.handleUserUpdate(data);
    });

    on('user.session.created', (data) {
      _plinto.handleNewSession(data);
    });

    on('user.session.revoked', (data) {
      _plinto.handleRevokedSession(data);
    });

    on('security.alert', (data) {
      _plinto.handleSecurityAlert(data);
    });
  }

  // Listen to organization events
  void listenToOrganizationEvents() {
    on('organization.updated', (data) {
      _plinto.handleOrganizationUpdate(data);
    });

    on('organization.member.added', (data) {
      _plinto.handleMemberAdded(data);
    });

    on('organization.member.removed', (data) {
      _plinto.handleMemberRemoved(data);
    });
  }

  // Handle incoming messages
  void _handleMessage(dynamic message) {
    try {
      final data = jsonDecode(message as String);
      final event = data['event'] as String;
      final eventData = data['data'];

      _emitEvent(event, eventData);
    } catch (e) {
      print('Error handling WebSocket message: $e');
    }
  }

  // Handle errors
  void _handleError(dynamic error) {
    print('WebSocket error: $error');
    _emitEvent('error', {'error': error.toString()});
  }

  // Handle disconnection
  void _handleDisconnection() {
    _isConnected = false;
    _heartbeatTimer?.cancel();
    _emitEvent('connection', {'status': 'disconnected'});

    // Attempt to reconnect after a delay
    Timer(const Duration(seconds: 5), () {
      if (!_isConnected) {
        connect();
      }
    });
  }

  // Emit event to listeners
  void _emitEvent(String event, dynamic data) {
    if (_eventListeners.containsKey(event)) {
      for (final callback in _eventListeners[event]!) {
        try {
          callback(data);
        } catch (e) {
          print('Error in event callback: $e');
        }
      }
    }
  }

  // Start heartbeat to keep connection alive
  void _startHeartbeat() {
    _heartbeatTimer = Timer.periodic(
      const Duration(seconds: 30),
      (timer) {
        if (_isConnected) {
          send('ping', {'timestamp': DateTime.now().toIso8601String()});
        }
      },
    );
  }

  bool get isConnected => _isConnected;
}

class WebSocketException implements Exception {
  final String message;

  WebSocketException(this.message);

  @override
  String toString() => 'WebSocketException: $message';
}
```

## Platform-Specific Implementation

### iOS Native Integration

```swift
// ios/Classes/PlintoPlugin.swift
import Flutter
import UIKit
import LocalAuthentication
import Security

public class PlintoPlugin: NSObject, FlutterPlugin {
    public static func register(with registrar: FlutterPluginRegistrar) {
        let channel = FlutterMethodChannel(name: "plinto_flutter", binaryMessenger: registrar.messenger())
        let instance = PlintoPlugin()
        registrar.addMethodCallDelegate(instance, channel: channel)
    }

    public func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
        switch call.method {
        case "authenticateWithBiometrics":
            authenticateWithBiometrics(call: call, result: result)
        case "isBiometricAvailable":
            isBiometricAvailable(result: result)
        case "getAvailableBiometrics":
            getAvailableBiometrics(result: result)
        case "storeInKeychain":
            storeInKeychain(call: call, result: result)
        case "retrieveFromKeychain":
            retrieveFromKeychain(call: call, result: result)
        default:
            result(FlutterMethodNotImplemented)
        }
    }

    private func authenticateWithBiometrics(call: FlutterMethodCall, result: @escaping FlutterResult) {
        guard let args = call.arguments as? [String: Any],
              let localizedReason = args["localizedReason"] as? String else {
            result(FlutterError(code: "INVALID_ARGUMENTS", message: "Invalid arguments", details: nil))
            return
        }

        let context = LAContext()
        var error: NSError?

        guard context.canEvaluatePolicy(.biometryAny, error: &error) else {
            result(FlutterError(code: "BIOMETRIC_UNAVAILABLE", message: error?.localizedDescription, details: nil))
            return
        }

        context.evaluatePolicy(.biometryAny, localizedReason: localizedReason) { success, authError in
            DispatchQueue.main.async {
                if success {
                    result(true)
                } else {
                    result(FlutterError(code: "AUTHENTICATION_FAILED", message: authError?.localizedDescription, details: nil))
                }
            }
        }
    }

    private func isBiometricAvailable(result: @escaping FlutterResult) {
        let context = LAContext()
        var error: NSError?
        let isAvailable = context.canEvaluatePolicy(.biometryAny, error: &error)
        result(isAvailable)
    }

    private func getAvailableBiometrics(result: @escaping FlutterResult) {
        let context = LAContext()
        var biometrics: [String] = []

        if context.canEvaluatePolicy(.biometryAny, error: nil) {
            switch context.biometryType {
            case .faceID:
                biometrics.append("face")
            case .touchID:
                biometrics.append("fingerprint")
            default:
                biometrics.append("none")
            }
        }

        result(biometrics)
    }

    private func storeInKeychain(call: FlutterMethodCall, result: @escaping FlutterResult) {
        guard let args = call.arguments as? [String: Any],
              let key = args["key"] as? String,
              let value = args["value"] as? String else {
            result(FlutterError(code: "INVALID_ARGUMENTS", message: "Invalid arguments", details: nil))
            return
        }

        let data = value.data(using: .utf8)!

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        ]

        // Delete any existing item
        SecItemDelete(query as CFDictionary)

        // Add the new item
        let status = SecItemAdd(query as CFDictionary, nil)

        if status == errSecSuccess {
            result(nil)
        } else {
            result(FlutterError(code: "KEYCHAIN_ERROR", message: "Failed to store in keychain", details: nil))
        }
    }

    private func retrieveFromKeychain(call: FlutterMethodCall, result: @escaping FlutterResult) {
        guard let args = call.arguments as? [String: Any],
              let key = args["key"] as? String else {
            result(FlutterError(code: "INVALID_ARGUMENTS", message: "Invalid arguments", details: nil))
            return
        }

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var dataTypeRef: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &dataTypeRef)

        if status == errSecSuccess {
            if let data = dataTypeRef as? Data,
               let value = String(data: data, encoding: .utf8) {
                result(value)
            } else {
                result(nil)
            }
        } else if status == errSecItemNotFound {
            result(nil)
        } else {
            result(FlutterError(code: "KEYCHAIN_ERROR", message: "Failed to retrieve from keychain", details: nil))
        }
    }
}
```

### Android Native Integration

```kotlin
// android/src/main/kotlin/PlintoPlugin.kt
package com.plinto.flutter

import android.content.Context
import android.hardware.biometrics.BiometricManager
import android.os.Build
import androidx.annotation.NonNull
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.embedding.engine.plugins.activity.ActivityAware
import io.flutter.embedding.engine.plugins.activity.ActivityPluginBinding
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import io.flutter.plugin.common.MethodChannel.MethodCallHandler
import io.flutter.plugin.common.MethodChannel.Result
import java.util.concurrent.Executor

class PlintoPlugin: FlutterPlugin, MethodCallHandler, ActivityAware {
    private lateinit var channel: MethodChannel
    private lateinit var context: Context
    private var activity: FragmentActivity? = null

    override fun onAttachedToEngine(@NonNull flutterPluginBinding: FlutterPlugin.FlutterPluginBinding) {
        channel = MethodChannel(flutterPluginBinding.binaryMessenger, "plinto_flutter")
        channel.setMethodCallHandler(this)
        context = flutterPluginBinding.applicationContext
    }

    override fun onMethodCall(@NonNull call: MethodCall, @NonNull result: Result) {
        when (call.method) {
            "authenticateWithBiometrics" -> authenticateWithBiometrics(call, result)
            "isBiometricAvailable" -> isBiometricAvailable(result)
            "getAvailableBiometrics" -> getAvailableBiometrics(result)
            else -> result.notImplemented()
        }
    }

    private fun authenticateWithBiometrics(call: MethodCall, result: Result) {
        val localizedReason = call.argument<String>("localizedReason") ?: "Authenticate"
        val activity = this.activity

        if (activity == null) {
            result.error("NO_ACTIVITY", "No activity available", null)
            return
        }

        val executor: Executor = ContextCompat.getMainExecutor(context)
        val biometricPrompt = BiometricPrompt(activity, executor,
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    super.onAuthenticationError(errorCode, errString)
                    result.error("AUTHENTICATION_ERROR", errString.toString(), null)
                }

                override fun onAuthenticationSucceeded(authResult: BiometricPrompt.AuthenticationResult) {
                    super.onAuthenticationSucceeded(authResult)
                    result.success(true)
                }

                override fun onAuthenticationFailed() {
                    super.onAuthenticationFailed()
                    result.error("AUTHENTICATION_FAILED", "Authentication failed", null)
                }
            })

        val promptInfo = BiometricPrompt.PromptInfo.Builder()
            .setTitle("Biometric Authentication")
            .setSubtitle(localizedReason)
            .setNegativeButtonText("Cancel")
            .build()

        biometricPrompt.authenticate(promptInfo)
    }

    private fun isBiometricAvailable(result: Result) {
        val biometricManager = BiometricManager.from(context)
        val canAuthenticate = biometricManager.canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_WEAK)
        result.success(canAuthenticate == BiometricManager.BIOMETRIC_SUCCESS)
    }

    private fun getAvailableBiometrics(result: Result) {
        val biometrics = mutableListOf<String>()
        val biometricManager = BiometricManager.from(context)

        when (biometricManager.canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_WEAK)) {
            BiometricManager.BIOMETRIC_SUCCESS -> {
                // Check for specific biometric types if needed
                biometrics.add("fingerprint")
            }
            else -> {
                // No biometrics available
            }
        }

        result.success(biometrics)
    }

    override fun onDetachedFromEngine(@NonNull binding: FlutterPlugin.FlutterPluginBinding) {
        channel.setMethodCallHandler(null)
    }

    override fun onAttachedToActivity(binding: ActivityPluginBinding) {
        activity = binding.activity as? FragmentActivity
    }

    override fun onDetachedFromActivityForConfigChanges() {
        activity = null
    }

    override fun onReattachedToActivityForConfigChanges(binding: ActivityPluginBinding) {
        activity = binding.activity as? FragmentActivity
    }

    override fun onDetachedFromActivity() {
        activity = null
    }
}
```

## Testing Strategies

### Unit Testing

```dart
// test/services/auth_service_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';
import 'package:plinto_flutter/plinto_flutter.dart';

@GenerateMocks([Plinto])
import 'auth_service_test.mocks.dart';

void main() {
  group('AuthService', () {
    late AuthService authService;
    late MockPlinto mockPlinto;

    setUp(() {
      mockPlinto = MockPlinto();
      authService = AuthService(mockPlinto);
    });

    group('signIn', () {
      test('should sign in successfully with valid credentials', () async {
        // Arrange
        const email = 'test@example.com';
        const password = 'password123';
        final expectedResult = AuthResult(
          user: User(id: '123', email: email),
          session: Session(token: 'mock-token'),
        );

        when(mockPlinto.signIn(email: email, password: password))
            .thenAnswer((_) async => expectedResult);

        // Act
        final result = await authService.signIn(
          email: email,
          password: password,
        );

        // Assert
        expect(result, equals(expectedResult));
        verify(mockPlinto.signIn(email: email, password: password));
      });

      test('should throw AuthServiceException on invalid credentials', () async {
        // Arrange
        const email = 'test@example.com';
        const password = 'wrong-password';

        when(mockPlinto.signIn(email: email, password: password))
            .thenThrow(const PlintoAuthException(
              code: 'invalid-credentials',
              message: 'Invalid email or password',
            ));

        // Act & Assert
        expect(
          () => authService.signIn(email: email, password: password),
          throwsA(isA<AuthServiceException>()),
        );
      });
    });

    group('signUp', () {
      test('should sign up successfully with valid data', () async {
        // Arrange
        const email = 'test@example.com';
        const password = 'password123';
        const firstName = 'John';
        const lastName = 'Doe';

        final expectedResult = AuthResult(
          user: User(id: '123', email: email, name: '$firstName $lastName'),
          session: Session(token: 'mock-token'),
        );

        when(mockPlinto.signUp(
          email: email,
          password: password,
          name: '$firstName $lastName',
        )).thenAnswer((_) async => expectedResult);

        when(mockPlinto.sendEmailVerification())
            .thenAnswer((_) async => {});

        // Act
        final result = await authService.signUp(
          email: email,
          password: password,
          firstName: firstName,
          lastName: lastName,
        );

        // Assert
        expect(result, equals(expectedResult));
        verify(mockPlinto.signUp(
          email: email,
          password: password,
          name: '$firstName $lastName',
        ));
        verify(mockPlinto.sendEmailVerification());
      });
    });

    group('signInWithBiometrics', () {
      test('should sign in with biometrics when available', () async {
        // Arrange
        final expectedResult = AuthResult(
          user: User(id: '123', email: 'test@example.com'),
          session: Session(token: 'mock-token'),
        );

        when(mockPlinto.isBiometricAvailable())
            .thenAnswer((_) async => true);

        when(mockPlinto.signInWithBiometrics(
          localizedReason: anyNamed('localizedReason'),
        )).thenAnswer((_) async => expectedResult);

        // Act
        final result = await authService.signInWithBiometrics();

        // Assert
        expect(result, equals(expectedResult));
      });

      test('should throw exception when biometrics not available', () async {
        // Arrange
        when(mockPlinto.isBiometricAvailable())
            .thenAnswer((_) async => false);

        // Act & Assert
        expect(
          () => authService.signInWithBiometrics(),
          throwsA(isA<AuthServiceException>()),
        );
      });
    });
  });
}
```

### Widget Testing

```dart
// test/widgets/auth_flow_widget_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:provider/provider.dart';
import '../mocks.dart';

void main() {
  group('AuthFlowWidget', () {
    late MockAuthService mockAuthService;
    late MockBiometricService mockBiometricService;

    setUp(() {
      mockAuthService = MockAuthService();
      mockBiometricService = MockBiometricService();
    });

    Widget createWidget({
      Function(User)? onAuthSuccess,
      Function(String)? onAuthError,
    }) {
      return MaterialApp(
        home: MultiProvider(
          providers: [
            Provider<AuthService>.value(value: mockAuthService),
            Provider<BiometricService>.value(value: mockBiometricService),
          ],
          child: AuthFlowWidget(
            onAuthSuccess: onAuthSuccess,
            onAuthError: onAuthError,
          ),
        ),
      );
    }

    testWidgets('should display sign in form by default', (tester) async {
      // Arrange
      when(mockBiometricService.isBiometricAvailable())
          .thenAnswer((_) async => false);

      // Act
      await tester.pumpWidget(createWidget());
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Sign In'), findsOneWidget);
      expect(find.byType(TextFormField), findsNWidgets(2)); // Email and password
      expect(find.text('Sign Up'), findsOneWidget);
    });

    testWidgets('should show biometric button when available', (tester) async {
      // Arrange
      when(mockBiometricService.isBiometricAvailable())
          .thenAnswer((_) async => true);

      // Act
      await tester.pumpWidget(createWidget());
      await tester.pumpAndSettle();

      // Assert
      expect(find.byType(BiometricQuickAuthButton), findsOneWidget);
    });

    testWidgets('should switch to sign up tab when tapped', (tester) async {
      // Arrange
      when(mockBiometricService.isBiometricAvailable())
          .thenAnswer((_) async => false);

      // Act
      await tester.pumpWidget(createWidget());
      await tester.pumpAndSettle();
      await tester.tap(find.text('Sign Up'));
      await tester.pumpAndSettle();

      // Assert
      expect(find.byType(TextFormField), findsNWidgets(4)); // First name, last name, email, password, confirm password
    });

    testWidgets('should call onAuthSuccess when sign in succeeds', (tester) async {
      // Arrange
      User? successUser;
      final mockUser = User(id: '123', email: 'test@example.com');

      when(mockBiometricService.isBiometricAvailable())
          .thenAnswer((_) async => false);

      when(mockAuthService.signIn(
        email: anyNamed('email'),
        password: anyNamed('password'),
        rememberMe: anyNamed('rememberMe'),
      )).thenAnswer((_) async => AuthResult(
        user: mockUser,
        session: Session(token: 'mock-token'),
      ));

      // Act
      await tester.pumpWidget(createWidget(
        onAuthSuccess: (user) => successUser = user,
      ));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextFormField).first, 'test@example.com');
      await tester.enterText(find.byType(TextFormField).last, 'password123');
      await tester.tap(find.text('Sign In'));
      await tester.pumpAndSettle();

      // Assert
      expect(successUser, equals(mockUser));
    });

    testWidgets('should show error message when sign in fails', (tester) async {
      // Arrange
      String? errorMessage;

      when(mockBiometricService.isBiometricAvailable())
          .thenAnswer((_) async => false);

      when(mockAuthService.signIn(
        email: anyNamed('email'),
        password: anyNamed('password'),
        rememberMe: anyNamed('rememberMe'),
      )).thenThrow(const AuthServiceException(
        code: 'invalid-credentials',
        message: 'Invalid email or password',
      ));

      // Act
      await tester.pumpWidget(createWidget(
        onAuthError: (error) => errorMessage = error,
      ));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextFormField).first, 'test@example.com');
      await tester.enterText(find.byType(TextFormField).last, 'wrong-password');
      await tester.tap(find.text('Sign In'));
      await tester.pumpAndSettle();

      // Assert
      expect(errorMessage, contains('Invalid email or password'));
    });
  });
}
```

### Integration Testing

```dart
// integration_test/auth_flow_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:plinto_flutter_example/main.dart' as app;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('Authentication Flow Integration Tests', () {
    testWidgets('complete sign up and sign in flow', (tester) async {
      // Start the app
      app.main();
      await tester.pumpAndSettle();

      // Test sign up flow
      await tester.tap(find.text('Sign Up'));
      await tester.pumpAndSettle();

      // Fill sign up form
      await tester.enterText(find.byKey(const Key('firstName')), 'John');
      await tester.enterText(find.byKey(const Key('lastName')), 'Doe');
      await tester.enterText(find.byKey(const Key('email')), 'john.doe@example.com');
      await tester.enterText(find.byKey(const Key('password')), 'Password123!');
      await tester.enterText(find.byKey(const Key('confirmPassword')), 'Password123!');

      // Submit sign up
      await tester.tap(find.byKey(const Key('signUpButton')));
      await tester.pumpAndSettle(const Duration(seconds: 3));

      // Should navigate to home or email verification screen
      expect(find.byKey(const Key('homeScreen')), findsOneWidget);

      // Test sign out
      await tester.tap(find.byKey(const Key('signOutButton')));
      await tester.pumpAndSettle();

      // Should return to auth screen
      expect(find.text('Sign In'), findsOneWidget);

      // Test sign in flow
      await tester.enterText(find.byKey(const Key('email')), 'john.doe@example.com');
      await tester.enterText(find.byKey(const Key('password')), 'Password123!');
      await tester.tap(find.byKey(const Key('signInButton')));
      await tester.pumpAndSettle(const Duration(seconds: 3));

      // Should navigate back to home
      expect(find.byKey(const Key('homeScreen')), findsOneWidget);
    });

    testWidgets('biometric authentication flow', (tester) async {
      app.main();
      await tester.pumpAndSettle();

      // Look for biometric button
      final biometricButton = find.byKey(const Key('biometricButton'));

      if (await tester.tryPumpingElement(biometricButton)) {
        await tester.tap(biometricButton);
        await tester.pumpAndSettle();

        // The actual biometric prompt would appear here
        // In a real test, you might need to interact with the system dialog

        // For testing purposes, we assume success and check for home screen
        await tester.pumpAndSettle(const Duration(seconds: 5));
        expect(find.byKey(const Key('homeScreen')), findsOneWidget);
      }
    });

    testWidgets('social login flow', (tester) async {
      app.main();
      await tester.pumpAndSettle();

      // Test Google sign in
      final googleButton = find.byKey(const Key('googleSignInButton'));

      if (await tester.tryPumpingElement(googleButton)) {
        await tester.tap(googleButton);
        await tester.pumpAndSettle();

        // This would typically open a web view or redirect
        // The actual OAuth flow would happen outside the app
        // For testing, we simulate a successful return

        await tester.pumpAndSettle(const Duration(seconds: 10));
        // Check if we're authenticated (implementation dependent)
      }
    });
  });
}

extension TesterExtension on WidgetTester {
  Future<bool> tryPumpingElement(Finder finder) async {
    try {
      await pumpAndSettle();
      return any(finder);
    } catch (e) {
      return false;
    }
  }
}
```

## Migration & Integration

### Migration from Firebase Auth

```dart
// migration/firebase_migration.dart
class FirebaseToPlinto Migration {
  final FirebaseAuth _firebaseAuth;
  final AuthService _plintoAuth;

  FirebaseToPlintoMigration({
    required FirebaseAuth firebaseAuth,
    required AuthService plintoAuth,
  }) : _firebaseAuth = firebaseAuth,
       _plintoAuth = plintoAuth;

  // Migrate user data from Firebase to Plinto
  Future<void> migrateUser() async {
    final firebaseUser = _firebaseAuth.currentUser;
    if (firebaseUser == null) {
      throw MigrationException('No Firebase user found');
    }

    try {
      // Create corresponding Plinto account
      final result = await _plintoAuth.signUp(
        email: firebaseUser.email!,
        password: '', // Temporary password, user will reset
        firstName: firebaseUser.displayName?.split(' ').first,
        lastName: firebaseUser.displayName?.split(' ').skip(1).join(' '),
        metadata: {
          'migratedFrom': 'firebase',
          'firebaseUid': firebaseUser.uid,
          'migrationDate': DateTime.now().toIso8601String(),
        },
      );

      // Migrate user preferences
      await _migrateUserPreferences(firebaseUser, result.user);

      // Migrate custom claims/roles if any
      await _migrateCustomClaims(firebaseUser, result.user);

      print('User migration completed for ${firebaseUser.email}');
    } catch (e) {
      throw MigrationException('Failed to migrate user: $e');
    }
  }

  // Migrate authentication methods
  Future<void> migrateAuthMethods() async {
    final firebaseUser = _firebaseAuth.currentUser;
    if (firebaseUser == null) return;

    // Check for linked providers
    for (final providerData in firebaseUser.providerData) {
      switch (providerData.providerId) {
        case 'google.com':
          // Enable Google OAuth in Plinto
          break;
        case 'apple.com':
          // Enable Apple OAuth in Plinto
          break;
        case 'phone':
          // Enable phone authentication in Plinto
          break;
      }
    }
  }

  // Batch migrate multiple users (admin operation)
  Future<void> batchMigrateUsers(List<String> userIds) async {
    final results = <String, bool>{};

    for (final userId in userIds) {
      try {
        // This would require Firebase Admin SDK access
        await _migrateUserById(userId);
        results[userId] = true;
      } catch (e) {
        results[userId] = false;
        print('Failed to migrate user $userId: $e');
      }
    }

    // Generate migration report
    final successCount = results.values.where((success) => success).length;
    final failureCount = results.length - successCount;

    print('Migration completed: $successCount successful, $failureCount failed');
  }

  private Future<void> _migrateUserPreferences(
    User firebaseUser,
    User plintoUser,
  ) async {
    // Implementation would depend on how preferences were stored in Firebase
    // This is a simplified example

    final preferences = {
      'theme': 'light',
      'notifications': true,
      'language': 'en',
    };

    await _plintoAuth.updateProfile(
      metadata: {
        ...plintoUser.metadata ?? {},
        'preferences': preferences,
      },
    );
  }

  private Future<void> _migrateCustomClaims(
    User firebaseUser,
    User plintoUser,
  ) async {
    // Migrate Firebase custom claims to Plinto roles/permissions
    // This would require Firebase Admin SDK to read custom claims

    final customClaims = <String, dynamic>{
      // Read from Firebase Admin SDK
    };

    // Map Firebase claims to Plinto roles
    final roles = <String>[];
    if (customClaims['admin'] == true) {
      roles.add('admin');
    }
    if (customClaims['moderator'] == true) {
      roles.add('moderator');
    }

    // Update user roles in Plinto
    // This would require admin API access
  }
}

class MigrationException implements Exception {
  final String message;

  MigrationException(this.message);

  @override
  String toString() => 'MigrationException: $message';
}
```

### Integration with Existing Apps

```dart
// integration/existing_app_integration.dart
class ExistingAppIntegration {
  static Future<void> integrateWithExistingAuth({
    required String existingUserId,
    required String existingEmail,
    required Map<String, dynamic> existingUserData,
  }) async {
    try {
      // Create Plinto user account
      final plinto = Plinto.instance;

      // Check if user already exists in Plinto
      final existingUser = await plinto.findUserByEmail(existingEmail);
      if (existingUser != null) {
        throw IntegrationException('User already exists in Plinto');
      }

      // Create new Plinto user with existing data
      final result = await plinto.createUser(
        email: existingEmail,
        metadata: {
          'legacyUserId': existingUserId,
          'migrationDate': DateTime.now().toIso8601String(),
          'legacyData': existingUserData,
        },
      );

      // Set up user session
      await plinto.createSession(result.user.id);

      print('Integration completed for user: $existingEmail');
    } catch (e) {
      throw IntegrationException('Failed to integrate existing user: $e');
    }
  }

  // Integrate existing user sessions
  static Future<void> integrateExistingSessions({
    required String existingSessionToken,
    required DateTime expiresAt,
  }) async {
    final plinto = Plinto.instance;

    try {
      // Validate existing session token
      final isValid = await _validateExistingToken(existingSessionToken);
      if (!isValid) {
        throw IntegrationException('Invalid existing session token');
      }

      // Create equivalent Plinto session
      await plinto.createSessionFromLegacyToken(
        legacyToken: existingSessionToken,
        expiresAt: expiresAt,
      );

    } catch (e) {
      throw IntegrationException('Failed to integrate session: $e');
    }
  }

  // Sync user data between systems
  static Future<void> syncUserData({
    required String plintoUserId,
    required Map<String, dynamic> externalUserData,
  }) async {
    final plinto = Plinto.instance;

    try {
      // Update Plinto user with external data
      await plinto.updateUser(
        userId: plintoUserId,
        data: {
          'syncedData': externalUserData,
          'lastSyncAt': DateTime.now().toIso8601String(),
        },
      );

      // Set up periodic sync if needed
      Timer.periodic(const Duration(hours: 1), (timer) async {
        await _performPeriodicSync(plintoUserId);
      });

    } catch (e) {
      throw IntegrationException('Failed to sync user data: $e');
    }
  }

  private static Future<bool> _validateExistingToken(String token) async {
    // Implement validation logic for your existing token format
    // This would depend on your current authentication system
    return token.isNotEmpty && token.length > 10;
  }

  private static Future<void> _performPeriodicSync(String userId) async {
    // Implement periodic sync logic
    // This could involve calling your existing API to get updated user data
  }
}

class IntegrationException implements Exception {
  final String message;

  IntegrationException(this.message);

  @override
  String toString() => 'IntegrationException: $message';
}
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Biometric Authentication Not Working

```dart
// Debug biometric issues
class BiometricDiagnostics {
  static Future<Map<String, dynamic>> runDiagnostics() async {
    final results = <String, dynamic>{};

    try {
      // Check device capability
      final localAuth = LocalAuthentication();
      results['deviceSupported'] = await localAuth.isDeviceSupported();
      results['canCheckBiometrics'] = await localAuth.canCheckBiometrics();

      // Check available biometrics
      final availableBiometrics = await localAuth.getAvailableBiometrics();
      results['availableBiometrics'] = availableBiometrics.map((b) => b.toString()).toList();

      // Check permissions
      if (Platform.isAndroid) {
        results['androidVersion'] = await _getAndroidVersion();
      } else if (Platform.isIOS) {
        results['iOSVersion'] = await _getiOSVersion();
      }

      return results;
    } catch (e) {
      results['error'] = e.toString();
      return results;
    }
  }

  static Future<String> _getAndroidVersion() async {
    // Implementation to get Android version
    return 'Unknown';
  }

  static Future<String> _getiOSVersion() async {
    // Implementation to get iOS version
    return 'Unknown';
  }
}

// Usage
final diagnostics = await BiometricDiagnostics.runDiagnostics();
print('Biometric diagnostics: $diagnostics');
```

#### 2. Secure Storage Issues

```dart
// Debug secure storage
class SecureStorageDiagnostics {
  static Future<void> testSecureStorage() async {
    const testKey = 'test_key';
    const testValue = 'test_value';

    try {
      final plinto = Plinto.instance;

      // Test write
      await plinto.secureStorage.write(key: testKey, value: testValue);
      print('✓ Secure storage write successful');

      // Test read
      final retrievedValue = await plinto.secureStorage.read(key: testKey);
      if (retrievedValue == testValue) {
        print('✓ Secure storage read successful');
      } else {
        print('✗ Secure storage read failed: expected $testValue, got $retrievedValue');
      }

      // Test delete
      await plinto.secureStorage.delete(key: testKey);
      final afterDelete = await plinto.secureStorage.read(key: testKey);
      if (afterDelete == null) {
        print('✓ Secure storage delete successful');
      } else {
        print('✗ Secure storage delete failed: value still exists');
      }

    } catch (e) {
      print('✗ Secure storage error: $e');
    }
  }
}
```

#### 3. Network Connectivity Issues

```dart
// Debug network issues
class NetworkDiagnostics {
  static Future<Map<String, dynamic>> checkConnectivity() async {
    final results = <String, dynamic>{};

    try {
      // Check internet connectivity
      final connectivityResult = await Connectivity().checkConnectivity();
      results['connectivity'] = connectivityResult.toString();

      // Test API endpoint
      final apiUrl = 'https://api.plinto.dev/health';
      final response = await http.get(Uri.parse(apiUrl));
      results['apiStatus'] = response.statusCode;
      results['apiResponse'] = response.body;

      // Test WebSocket connection
      try {
        final wsChannel = WebSocketChannel.connect(
          Uri.parse('wss://api.plinto.dev/ws'),
        );
        await wsChannel.sink.close();
        results['websocketAvailable'] = true;
      } catch (e) {
        results['websocketAvailable'] = false;
        results['websocketError'] = e.toString();
      }

    } catch (e) {
      results['error'] = e.toString();
    }

    return results;
  }
}
```

#### 4. Platform-Specific Debug Tools

```dart
// Debug platform-specific issues
class PlatformDiagnostics {
  static Future<Map<String, dynamic>> getPlatformInfo() async {
    final info = <String, dynamic>{};

    // Basic platform info
    info['platform'] = Platform.operatingSystem;
    info['version'] = Platform.operatingSystemVersion;

    if (Platform.isAndroid) {
      // Android-specific diagnostics
      info['androidInfo'] = await _getAndroidInfo();
    } else if (Platform.isIOS) {
      // iOS-specific diagnostics
      info['iOSInfo'] = await _getiOSInfo();
    } else if (kIsWeb) {
      // Web-specific diagnostics
      info['webInfo'] = await _getWebInfo();
    }

    return info;
  }

  static Future<Map<String, dynamic>> _getAndroidInfo() async {
    final deviceInfo = DeviceInfoPlugin();
    final androidInfo = await deviceInfo.androidInfo;

    return {
      'version': androidInfo.version.release,
      'sdkInt': androidInfo.version.sdkInt,
      'manufacturer': androidInfo.manufacturer,
      'model': androidInfo.model,
      'supportedAbis': androidInfo.supportedAbis,
    };
  }

  static Future<Map<String, dynamic>> _getiOSInfo() async {
    final deviceInfo = DeviceInfoPlugin();
    final iosInfo = await deviceInfo.iosInfo;

    return {
      'version': iosInfo.systemVersion,
      'model': iosInfo.model,
      'name': iosInfo.name,
      'systemName': iosInfo.systemName,
    };
  }

  static Future<Map<String, dynamic>> _getWebInfo() async {
    final deviceInfo = DeviceInfoPlugin();
    final webInfo = await deviceInfo.webBrowserInfo;

    return {
      'browserName': webInfo.browserName.toString(),
      'userAgent': webInfo.userAgent,
      'vendor': webInfo.vendor,
    };
  }
}
```

### Performance Optimization

```dart
// Performance monitoring and optimization
class PerformanceOptimizer {
  static void optimizeForProduction() {
    // Reduce debug information in production
    if (kReleaseMode) {
      // Disable debug prints
      print = (Object? object) {};

      // Configure error reporting
      FlutterError.onError = (FlutterErrorDetails details) {
        // Send to crash reporting service
      };
    }
  }

  static Widget buildOptimizedAuthWidget() {
    return LayoutBuilder(
      builder: (context, constraints) {
        // Responsive design based on screen size
        if (constraints.maxWidth > 600) {
          return const DesktopAuthLayout();
        } else {
          return const MobileAuthLayout();
        }
      },
    );
  }

  static void preloadCriticalData() async {
    // Preload essential data for better UX
    final plinto = Plinto.instance;

    if (plinto.currentUser != null) {
      // Preload user organizations
      unawaited(plinto.organizations.getUserOrganizations());

      // Preload user preferences
      unawaited(plinto.secureStorage.read(key: 'user_preferences'));

      // Setup real-time connections
      unawaited(plinto.connectWebSocket());
    }
  }
}
```

---

## Summary

The **@plinto/flutter** SDK provides a comprehensive authentication solution for Flutter applications with:

- **Cross-Platform Support**: Native iOS, Android, and Web implementations
- **Biometric Authentication**: Face ID, Touch ID, Fingerprint with fallback options
- **Secure Storage**: Platform-specific encrypted storage with keychain/keystore integration
- **Real-time Features**: WebSocket support for live data synchronization
- **Pre-built Widgets**: Material Design and Cupertino-compatible authentication UI
- **State Management**: Built-in BLoC pattern support with reactive streams
- **Platform Integration**: Deep platform-specific integrations and optimizations
- **Migration Support**: Tools for migrating from other authentication systems

This guide covers everything from basic setup to advanced enterprise features, providing you with all the tools needed to implement robust authentication in your Flutter applications across all platforms.

For additional support and advanced configuration options, refer to the [Plinto documentation](https://docs.plinto.dev) or contact our support team.