/**
 * Centralized Design System
 *
 * Single source of truth for all design tokens, component styles, and utility classes.
 * This file ensures consistency across the frontend and enables easy updates to the design.
 */

// ─────────────────────────────────────────────────────────────
// Color Palette
// ─────────────────────────────────────────────────────────────

export const colors = {
  // Base colors
  background: '#0b1121',
  surface: '#161f33',
  surfaceSoft: '#1e293b',
  surfaceHover: '#1f2d42',
  border: '#2a354b',
  borderLight: '#3a4a5f',

  // Text colors
  text: '#f8fafc',
  textHeading: '#ffffff',
  textMuted: '#94a3b8',
  textSoft: '#cbd5e1',

  // Semantic colors
  primary: '#3b82f6',
  primaryHover: '#2563eb',
  primaryActive: '#1d4ed8',

  secondary: '#8b5cf6',
  secondaryHover: '#7c3aed',
  secondaryActive: '#6d28d9',

  success: '#10b981',
  successHover: '#059669',
  successActive: '#047857',

  warning: '#f59e0b',
  warningHover: '#d97706',
  warningActive: '#b45309',

  danger: '#ef4444',
  dangerHover: '#dc2626',
  dangerActive: '#b91c1c',

  info: '#0ea5e9',
  infoHover: '#0284c7',
  infoActive: '#0369a1',

  // Utility colors
  transparent: 'transparent',
  white: '#ffffff',
  black: '#000000',
} as const;

// ─────────────────────────────────────────────────────────────
// Typography
// ─────────────────────────────────────────────────────────────

export const typography = {
  fontFamily: {
    base: "'Inter', system-ui, -apple-system, sans-serif",
    mono: "'Fira Code', 'Courier New', monospace",
  },
  fontSize: {
    xs: '12px',
    sm: '13px',
    md: '15px',
    lg: '18px',
    xl: '20px',
    '2xl': '24px',
    '3xl': '28px',
    '4xl': '32px',
  },
  fontWeight: {
    light: 300,
    regular: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
  lineHeight: {
    tight: 1.2,
    normal: 1.5,
    relaxed: 1.75,
    loose: 2,
  },
} as const;

// ─────────────────────────────────────────────────────────────
// Spacing
// ─────────────────────────────────────────────────────────────

export const spacing = {
  xxs: '4px',
  xs: '8px',
  sm: '12px',
  md: '16px',
  lg: '24px',
  xl: '32px',
  '2xl': '40px',
  '3xl': '48px',
} as const;

// ─────────────────────────────────────────────────────────────
// Border Radius
// ─────────────────────────────────────────────────────────────

export const borderRadius = {
  none: '0',
  sm: '6px',
  md: '10px',
  lg: '16px',
  xl: '20px',
  full: '9999px',
} as const;

// ─────────────────────────────────────────────────────────────
// Shadows
// ─────────────────────────────────────────────────────────────

export const shadows = {
  none: 'none',
  sm: '0 1px 2px rgba(2, 6, 23, 0.6)',
  md: '0 4px 6px rgba(2, 6, 23, 0.7)',
  lg: '0 10px 15px rgba(2, 6, 23, 0.8)',
  xl: '0 20px 25px rgba(2, 6, 23, 0.9)',
  glow: '0 0 20px 4px rgba(59, 130, 246, 0.28)',
} as const;

// ─────────────────────────────────────────────────────────────
// Motion / Animations
// ─────────────────────────────────────────────────────────────

export const motion = {
  duration: {
    fast: '150ms',
    medium: '260ms',
    slow: '420ms',
    slower: '600ms',
  },
  easing: {
    easeInOutQuad: 'cubic-bezier(0.45, 0.05, 0.55, 0.95)',
    easeOutCubic: 'cubic-bezier(0.16, 1, 0.3, 1)',
    easeInOutCubic: 'cubic-bezier(0.645, 0.045, 0.355, 1)',
  },
} as const;

// ─────────────────────────────────────────────────────────────
// Layout
// ─────────────────────────────────────────────────────────────

export const layout = {
  maxContentWidth: '1200px',
  sidebarWidth: '260px',
  rightbarWidth: '340px',
  headerHeight: '60px',
  footerHeight: '40px',
} as const;

// ─────────────────────────────────────────────────────────────
// Breakpoints
// ─────────────────────────────────────────────────────────────

export const breakpoints = {
  xs: '320px',
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const;

// ─────────────────────────────────────────────────────────────
// Component Styles
// ─────────────────────────────────────────────────────────────

export const components = {
  button: {
    primary: {
      background: colors.primary,
      backgroundHover: colors.primaryHover,
      backgroundActive: colors.primaryActive,
      text: colors.white,
      border: colors.primary,
    },
    secondary: {
      background: colors.secondary,
      backgroundHover: colors.secondaryHover,
      backgroundActive: colors.secondaryActive,
      text: colors.white,
      border: colors.secondary,
    },
    ghost: {
      background: 'transparent',
      backgroundHover: colors.surface,
      text: colors.text,
      border: colors.border,
    },
  },
  input: {
    background: colors.surface,
    backgroundFocus: colors.surfaceHover,
    border: colors.border,
    borderFocus: colors.primary,
    text: colors.text,
    placeholder: colors.textMuted,
  },
  card: {
    background: colors.surface,
    border: colors.border,
    borderHover: colors.borderLight,
  },
  panel: {
    background: colors.surface,
    backgroundSoft: colors.surfaceSoft,
    border: colors.border,
  },
  badge: {
    success: {
      background: `${colors.success}20`,
      text: colors.success,
      border: colors.success,
    },
    warning: {
      background: `${colors.warning}20`,
      text: colors.warning,
      border: colors.warning,
    },
    danger: {
      background: `${colors.danger}20`,
      text: colors.danger,
      border: colors.danger,
    },
    info: {
      background: `${colors.info}20`,
      text: colors.info,
      border: colors.info,
    },
  },
  table: {
    headerBackground: colors.surfaceSoft,
    headerText: colors.textMuted,
    rowBorder: 'rgba(42, 53, 75, 0.5)',
    rowHover: 'rgba(59, 130, 246, 0.05)',
  },
} as const;

// ─────────────────────────────────────────────────────────────
// Z-Index Scale
// ─────────────────────────────────────────────────────────────

export const zIndex = {
  hide: -1,
  auto: 'auto',
  base: 0,
  dropdown: 100,
  sticky: 200,
  fixed: 300,
  header: 400,
  overlay: 500,
  modal: 600,
  popover: 700,
  tooltip: 800,
} as const;

// ─────────────────────────────────────────────────────────────
// Export all as a single object for convenience
// ─────────────────────────────────────────────────────────────

export const designSystem = {
  colors,
  typography,
  spacing,
  borderRadius,
  shadows,
  motion,
  layout,
  breakpoints,
  components,
  zIndex,
} as const;

export default designSystem;
