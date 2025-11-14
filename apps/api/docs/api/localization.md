# Localization & Internationalization (i18n)

## Overview

Plinto API provides comprehensive internationalization (i18n) and localization (l10n) support, enabling applications to deliver content in multiple languages with proper formatting and cultural adaptations.

## Features

- **Multi-language Support**: Manage translations for any number of locales
- **Translation Management**: Create, update, and approve translations
- **RTL Language Support**: Built-in right-to-left language detection
- **Translation Progress Tracking**: Monitor completion status per locale
- **Key Organization**: Categorize translations for better management
- **Approval Workflow**: Review and approve translations before deployment

## Data Model

### Locale

Represents a supported language/region combination (e.g., "en-US", "es-ES").

```python
{
  "id": "uuid",
  "code": "en-US",           # ISO 639-1 language + ISO 3166-1 country
  "name": "English (US)",
  "native_name": "English (United States)",
  "is_active": true,
  "is_rtl": false,           # Right-to-left language flag
  "translation_progress": 100,  # Percentage of translated keys
  "created_at": "2025-01-14T00:00:00Z",
  "updated_at": "2025-01-14T00:00:00Z"
}
```

### Translation Key

Defines a translatable string with its default (fallback) value.

```python
{
  "id": "uuid",
  "key": "auth.login.submit",  # Hierarchical dot notation
  "default_value": "Sign In",  # English fallback
  "description": "Submit button text on login form",
  "category": "auth",          # Optional grouping
  "created_at": "2025-01-14T00:00:00Z",
  "updated_at": "2025-01-14T00:00:00Z"
}
```

### Translation

Provides the translated value for a specific key in a specific locale.

```python
{
  "id": "uuid",
  "translation_key_id": "uuid",
  "locale_id": "uuid",
  "value": "Iniciar Sesión",  # Spanish translation
  "is_approved": true,
  "approved_by": "uuid",
  "approved_at": "2025-01-14T00:00:00Z",
  "created_at": "2025-01-14T00:00:00Z",
  "updated_at": "2025-01-14T00:00:00Z"
}
```

## API Endpoints

### List Locales

Get all available locales, optionally filtered by active status.

```http
GET /api/v1/localization/locales?is_active=true
```

**Response:**
```json
[
  {
    "code": "en-US",
    "name": "English (US)",
    "native_name": "English (United States)",
    "is_active": true,
    "is_rtl": false,
    "translation_progress": 100
  },
  {
    "code": "es-ES",
    "name": "Spanish (Spain)",
    "native_name": "Español (España)",
    "is_active": true,
    "is_rtl": false,
    "translation_progress": 85
  }
]
```

### Create/Update Translation

Create or update a translation for a specific key and locale.

```http
POST /api/v1/localization/translations
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "key": "auth.login.submit",
  "locale_code": "es-ES",
  "value": "Iniciar Sesión"
}
```

**Response:**
```json
{
  "message": "Translation saved successfully"
}
```

### Get Translations for Locale

Retrieve all translations for a specific locale.

```http
GET /api/v1/localization/translations/es-ES
```

**Response:**
```json
{
  "auth.login.submit": "Iniciar Sesión",
  "auth.login.email": "Correo Electrónico",
  "auth.login.password": "Contraseña",
  "dashboard.welcome": "Bienvenido"
}
```

## Usage Examples

### Frontend Integration

#### React Example

```typescript
import { useEffect, useState } from 'react';
import { PlintoClient } from '@plinto/react-sdk';

function App() {
  const [translations, setTranslations] = useState({});
  const [locale, setLocale] = useState('en-US');

  const plinto = new PlintoClient({
    baseURL: 'https://api.plinto.dev',
    apiKey: process.env.PLINTO_API_KEY
  });

  useEffect(() => {
    // Load translations for current locale
    plinto.localization.getTranslations(locale)
      .then(data => setTranslations(data));
  }, [locale]);

  const t = (key: string) => translations[key] || key;

  return (
    <div>
      <h1>{t('dashboard.welcome')}</h1>
      <button>{t('auth.login.submit')}</button>
    </div>
  );
}
```

#### Vue Example

```vue
<template>
  <div>
    <h1>{{ t('dashboard.welcome') }}</h1>
    <button>{{ t('auth.login.submit') }}</button>
  </div>
</template>

<script>
import { PlintoClient } from '@plinto/vue-sdk';

export default {
  data() {
    return {
      translations: {},
      locale: 'en-US'
    };
  },
  mounted() {
    const plinto = new PlintoClient({
      baseURL: 'https://api.plinto.dev',
      apiKey: process.env.VUE_APP_PLINTO_API_KEY
    });

    plinto.localization.getTranslations(this.locale)
      .then(data => this.translations = data);
  },
  methods: {
    t(key) {
      return this.translations[key] || key;
    }
  }
};
</script>
```

### Backend Integration

#### Python Example

```python
from plinto import PlintoClient

client = PlintoClient(
    base_url="https://api.plinto.dev",
    api_key="your_api_key"
)

# Get all active locales
locales = client.localization.list_locales(is_active=True)

# Get translations for Spanish
translations = client.localization.get_translations("es-ES")

# Create/update translation (admin only)
client.localization.create_translation(
    key="notifications.new_message",
    locale_code="es-ES",
    value="Nuevo Mensaje"
)
```

## Translation Key Naming Convention

Use hierarchical dot notation for translation keys:

```
{domain}.{section}.{element}

Examples:
- auth.login.submit
- auth.signup.email_placeholder
- dashboard.sidebar.profile
- errors.validation.required_field
- notifications.email.welcome_subject
```

## RTL Language Support

For right-to-left languages (Arabic, Hebrew, etc.), the `is_rtl` flag is automatically set:

```json
{
  "code": "ar-SA",
  "name": "Arabic (Saudi Arabia)",
  "native_name": "العربية (المملكة العربية السعودية)",
  "is_rtl": true
}
```

Frontend applications can use this flag to adjust layout:

```typescript
const locale = await plinto.localization.getLocale('ar-SA');
document.dir = locale.is_rtl ? 'rtl' : 'ltr';
```

## Translation Approval Workflow

1. **Create Translation**: Translator submits new translation
2. **Review**: Translation appears with `is_approved: false`
3. **Approve**: Admin approves translation, setting `is_approved: true`
4. **Deploy**: Only approved translations served in production

```http
PUT /api/v1/localization/translations/{id}/approve
Authorization: Bearer {admin_token}
```

## Best Practices

### 1. Use Descriptive Keys
```
✅ Good: auth.login.submit_button
❌ Bad: btn1
```

### 2. Provide Context in Descriptions
```python
{
  "key": "dashboard.user_count",
  "default_value": "{count} users",
  "description": "Display total number of users. {count} is replaced with actual number."
}
```

### 3. Handle Pluralization
```python
{
  "messages.count.zero": "No messages",
  "messages.count.one": "1 message",
  "messages.count.many": "{count} messages"
}
```

### 4. Separate by Domain
Organize keys by application domain for easier management:
- `auth.*` - Authentication flows
- `dashboard.*` - Dashboard UI
- `errors.*` - Error messages
- `notifications.*` - Notification templates

## Migration Guide

### Adding Localization to Existing Application

1. **Identify Hardcoded Strings**
```bash
# Find hardcoded UI text
grep -r "\".*\"" src/components --include="*.jsx"
```

2. **Extract to Translation Keys**
```typescript
// Before
<button>Sign In</button>

// After
<button>{t('auth.login.submit')}</button>
```

3. **Load Initial Translations**
```typescript
useEffect(() => {
  plinto.localization.getTranslations(locale)
    .then(setTranslations);
}, [locale]);
```

4. **Add Locale Selector**
```typescript
<select onChange={(e) => setLocale(e.target.value)}>
  {locales.map(l => (
    <option key={l.code} value={l.code}>
      {l.native_name}
    </option>
  ))}
</select>
```

## Performance Considerations

- **Caching**: Translations are cached client-side
- **Bundle Size**: Only load translations for active locale
- **Fallback**: Always provide English (`en-US`) as fallback
- **Lazy Loading**: Load translations on demand for large applications

## Security

- **Admin-Only**: Creating/updating translations requires admin privileges
- **Validation**: Translation keys are validated against regex pattern
- **Sanitization**: Values are sanitized to prevent XSS attacks
- **Audit**: All translation changes are logged in audit system

## Related Documentation

- [API Reference](/docs/api/README.md)
- [SDKs Documentation](/docs/development/sdks.md)
- [Architecture Overview](/docs/architecture/README.md)
