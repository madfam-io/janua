/**
 * Plinto Unified Design System
 * Shared across all applications: marketing, dashboard, admin, docs
 */

export const colors = {
  // Brand Colors
  brand: {
    50: '#eff6ff',
    100: '#dbeafe',
    200: '#bfdbfe',
    300: '#93c5fd',
    400: '#60a5fa',
    500: '#3b82f6',  // Primary brand blue
    600: '#2563eb',
    700: '#1d4ed8',
    800: '#1e40af',
    900: '#1e3a8a',
    950: '#172554',
  },

  // Semantic Colors
  gray: {
    50: '#f9fafb',
    100: '#f3f4f6',
    200: '#e5e7eb',
    300: '#d1d5db',
    400: '#9ca3af',
    500: '#6b7280',
    600: '#4b5563',
    700: '#374151',
    800: '#1f2937',
    900: '#111827',
    950: '#030712',
  },

  success: {
    50: '#f0fdf4',
    500: '#22c55e',
    600: '#16a34a',
    700: '#15803d',
  },

  warning: {
    50: '#fefce8',
    500: '#eab308',
    600: '#ca8a04',
    700: '#a16207',
  },

  error: {
    50: '#fef2f2',
    500: '#ef4444',
    600: '#dc2626',
    700: '#b91c1c',
  },
}

export const theme = {
  colors: {
    // Primary Palette
    primary: colors.brand[500],
    primaryDark: colors.brand[600],
    primaryLight: colors.brand[400],
    primaryForeground: '#ffffff',

    // Backgrounds
    background: '#ffffff',
    backgroundSecondary: colors.gray[50],
    foreground: colors.gray[900],
    
    // Dark mode
    backgroundDark: colors.gray[950],
    backgroundSecondaryDark: colors.gray[900],
    foregroundDark: colors.gray[50],

    // Components
    card: '#ffffff',
    cardForeground: colors.gray[900],
    border: colors.gray[200],
    input: colors.gray[200],
    ring: colors.brand[500],
    
    // Semantic
    muted: colors.gray[500],
    mutedForeground: colors.gray[600],
    accent: colors.brand[100],
    accentForeground: colors.brand[900],
    
    destructive: colors.error[500],
    destructiveForeground: '#ffffff',
    
    success: colors.success[500],
    warning: colors.warning[500],
  },

  fonts: {
    sans: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    mono: 'JetBrains Mono, Menlo, Monaco, Consolas, "Courier New", monospace',
  },

  spacing: {
    xs: '0.5rem',    // 8px
    sm: '1rem',      // 16px
    md: '1.5rem',    // 24px
    lg: '2rem',      // 32px
    xl: '3rem',      // 48px
    '2xl': '4rem',   // 64px
    '3xl': '6rem',   // 96px
  },

  radius: {
    none: '0',
    sm: '0.25rem',   // 4px
    md: '0.375rem',  // 6px
    lg: '0.5rem',    // 8px
    xl: '0.75rem',   // 12px
    '2xl': '1rem',   // 16px
    full: '9999px',
  },

  shadows: {
    sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.1)',
    xl: '0 20px 25px -5px rgb(0 0 0 / 0.1)',
    '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    inner: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
  },

  transitions: {
    fast: '150ms ease-in-out',
    base: '250ms ease-in-out',
    slow: '350ms ease-in-out',
  },

  breakpoints: {
    sm: '640px',
    md: '768px',
    lg: '1024px',
    xl: '1280px',
    '2xl': '1536px',
  },
}

// CSS Variables for runtime theming
export const cssVariables = `
  :root {
    --color-primary: ${theme.colors.primary};
    --color-primary-dark: ${theme.colors.primaryDark};
    --color-primary-light: ${theme.colors.primaryLight};
    --color-background: ${theme.colors.background};
    --color-foreground: ${theme.colors.foreground};
    --color-card: ${theme.colors.card};
    --color-border: ${theme.colors.border};
    --color-muted: ${theme.colors.muted};
    --color-success: ${theme.colors.success};
    --color-warning: ${theme.colors.warning};
    --color-destructive: ${theme.colors.destructive};
    
    --font-sans: ${theme.fonts.sans};
    --font-mono: ${theme.fonts.mono};
    
    --radius-sm: ${theme.radius.sm};
    --radius-md: ${theme.radius.md};
    --radius-lg: ${theme.radius.lg};
    --radius-xl: ${theme.radius.xl};
    
    --shadow-sm: ${theme.shadows.sm};
    --shadow-md: ${theme.shadows.md};
    --shadow-lg: ${theme.shadows.lg};
  }
  
  .dark {
    --color-background: ${theme.colors.backgroundDark};
    --color-foreground: ${theme.colors.foregroundDark};
    --color-card: ${colors.gray[900]};
    --color-border: ${colors.gray[800]};
  }
`

export default theme