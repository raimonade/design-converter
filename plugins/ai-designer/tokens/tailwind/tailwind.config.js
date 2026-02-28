/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        background: 'var(--semantic-colors-background)',
        foreground: 'var(--semantic-colors-foreground)',
        primary: {
          DEFAULT: 'var(--semantic-colors-primary)',
          hover: 'var(--semantic-colors-primary-hover)',
          foreground: 'var(--semantic-colors-primary-foreground)',
        },
        secondary: {
          DEFAULT: 'var(--semantic-colors-secondary)',
          foreground: 'var(--semantic-colors-secondary-foreground)',
        },
        muted: {
          DEFAULT: 'var(--semantic-colors-muted)',
          foreground: 'var(--semantic-colors-muted-foreground)',
        },
        accent: {
          DEFAULT: 'var(--semantic-colors-accent)',
          foreground: 'var(--semantic-colors-accent-foreground)',
        },
        destructive: {
          DEFAULT: 'var(--semantic-colors-destructive)',
          foreground: 'var(--semantic-colors-destructive-foreground)',
        },
        success: {
          DEFAULT: 'var(--semantic-colors-success)',
          foreground: 'var(--semantic-colors-success-foreground)',
        },
        warning: {
          DEFAULT: 'var(--semantic-colors-warning)',
          foreground: 'var(--semantic-colors-warning-foreground)',
        },
        border: 'var(--semantic-colors-border)',
        input: {
          DEFAULT: 'var(--semantic-colors-input-background)',
          placeholder: 'var(--semantic-colors-input-placeholder)',
          border: 'var(--semantic-colors-input-border)',
        },
        ring: 'var(--semantic-colors-ring)',
        card: {
          DEFAULT: 'var(--semantic-colors-card)',
          foreground: 'var(--semantic-colors-card-foreground)',
        },
        popover: {
          DEFAULT: 'var(--semantic-colors-popover)',
          foreground: 'var(--semantic-colors-popover-foreground)',
        },
      },
      spacing: {
        'semantic-xs': 'var(--semantic-padding-xs)',
        'semantic-sm': 'var(--semantic-padding-sm)',
        'semantic-md': 'var(--semantic-padding-md)',
        'semantic-lg': 'var(--semantic-padding-lg)',
        'semantic-xl': 'var(--semantic-padding-xl)',
      },
      borderRadius: {
        'semantic-sm': 'var(--semantic-radius-sm)',
        'semantic-md': 'var(--semantic-radius-md)',
        'semantic-lg': 'var(--semantic-radius-lg)',
        'semantic-full': 'var(--semantic-radius-full)',
      },
      fontSize: {
        'semantic-xs': 'var(--semantic-fontSize-xs)',
        'semantic-sm': 'var(--semantic-fontSize-sm)',
        'semantic-base': 'var(--semantic-fontSize-base)',
        'semantic-lg': 'var(--semantic-fontSize-lg)',
        'semantic-xl': 'var(--semantic-fontSize-xl)',
      },
      fontFamily: {
        body: 'var(--semantic-fontFamily-body)',
        heading: 'var(--semantic-fontFamily-heading)',
        code: 'var(--semantic-fontFamily-code)',
      },
      fontWeight: {
        'semantic-regular': 'var(--semantic-weight-regular)',
        'semantic-medium': 'var(--semantic-weight-medium)',
        'semantic-semibold': 'var(--semantic-weight-semibold)',
        'semantic-bold': 'var(--semantic-weight-bold)',
      },
      lineHeight: {
        'semantic-tight': 'var(--semantic-lineHeight-tight)',
        'semantic-normal': 'var(--semantic-lineHeight-normal)',
        'semantic-relaxed': 'var(--semantic-lineHeight-relaxed)',
      },
      letterSpacing: {
        'semantic-tight': 'var(--semantic-letterSpacing-tight)',
        'semantic-normal': 'var(--semantic-letterSpacing-normal)',
        'semantic-wide': 'var(--semantic-letterSpacing-wide)',
      },
    },
  },
  plugins: [],
};
