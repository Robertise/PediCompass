/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      "colors": {
        "on-error": "var(--color-on-error)",
        "on-primary-container": "var(--color-on-primary-container)",
        "tertiary-fixed-dim": "var(--color-tertiary-fixed-dim)",
        "error-container": "var(--color-error-container)",
        "tertiary": "var(--color-tertiary)",
        "on-tertiary-fixed": "var(--color-on-tertiary-fixed)",
        "surface": "var(--color-surface)",
        "on-tertiary": "var(--color-on-tertiary)",
        "surface-bright": "var(--color-surface-bright)",
        "surface-container-lowest": "var(--color-surface-container-lowest)",
        "on-surface": "var(--color-on-surface)",
        "background": "var(--color-background)",
        "primary-fixed-dim": "var(--color-primary-fixed-dim)",
        "primary-fixed": "var(--color-primary-fixed)",
        "tertiary-container": "var(--color-tertiary-container)",
        "outline-variant": "var(--color-outline-variant)",
        "error": "var(--color-error)",
        "inverse-surface": "var(--color-inverse-surface)",
        "surface-tint": "var(--color-surface-tint)",
        "inverse-on-surface": "var(--color-inverse-on-surface)",
        "on-primary": "var(--color-on-primary)",
        "surface-container": "var(--color-surface-container)",
        "primary-container": "var(--color-primary-container)",
        "surface-dim": "var(--color-surface-dim)",
        "outline": "var(--color-outline)",
        "on-secondary-container": "var(--color-on-secondary-container)",
        "on-tertiary-fixed-variant": "var(--color-on-tertiary-fixed-variant)",
        "primary": "var(--color-primary)",
        "surface-variant": "var(--color-surface-variant)",
        "on-tertiary-container": "var(--color-on-tertiary-container)",
        "on-secondary-fixed-variant": "var(--color-on-secondary-fixed-variant)",
        "secondary-fixed-dim": "var(--color-secondary-fixed-dim)",
        "on-secondary-fixed": "var(--color-on-secondary-fixed)",
        "inverse-primary": "var(--color-inverse-primary)",
        "surface-container-highest": "var(--color-surface-container-highest)",
        "secondary-fixed": "var(--color-secondary-fixed)",
        "on-primary-fixed-variant": "var(--color-on-primary-fixed-variant)",
        "secondary-container": "var(--color-secondary-container)",
        "on-background": "var(--color-on-background)",
        "on-error-container": "var(--color-on-error-container)",
        "surface-container-high": "var(--color-surface-container-high)",
        "on-primary-fixed": "var(--color-on-primary-fixed)",
        "on-secondary": "var(--color-on-secondary)",
        "surface-container-low": "var(--color-surface-container-low)",
        "tertiary-fixed": "var(--color-tertiary-fixed)",
        "secondary": "var(--color-secondary)",
        "on-surface-variant": "var(--color-on-surface-variant)",
        // Urgency Colors
        emergency: 'var(--color-emergency)',
        urgent: 'var(--color-urgent)',
        soon: 'var(--color-soon)',
        routine: 'var(--color-routine)',
      },
      "borderRadius": {
              "DEFAULT": "0.25rem",
              "lg": "0.5rem",
              "xl": "0.75rem",
              "2xl": "1rem",
              "full": "9999px"
      },
      "spacing": {
              "xl": "64px",
              "margin-desktop": "120px",
              "base": "8px",
              "md": "24px",
              "xs": "4px",
              "sm": "12px",
              "lg": "40px",
              "margin-mobile": "20px",
              "gutter": "16px"
      },
      "fontFamily": {
              "manrope": ["Manrope"],
              "headline-sm": ["Geist"],
              "label-md": ["Inter"],
              "body-sm": ["Inter"],
              "headline-lg-mobile": ["Geist"],
              "headline-md": ["Geist"],
              "body-lg": ["Inter"],
              "body-md": ["Inter"],
              "headline-lg": ["Geist"],
              "label-sm": ["Inter"]
      },
      "fontSize": {
              "headline-sm": ["20px", {"lineHeight": "28px", "fontWeight": "600"}],
              "label-md": ["14px", {"lineHeight": "16px", "letterSpacing": "0.01em", "fontWeight": "600"}],
              "body-sm": ["14px", {"lineHeight": "20px", "fontWeight": "400"}],
              "headline-lg-mobile": ["26px", {"lineHeight": "32px", "letterSpacing": "-0.02em", "fontWeight": "700"}],
              "headline-md": ["24px", {"lineHeight": "32px", "fontWeight": "600"}],
              "body-lg": ["18px", {"lineHeight": "28px", "fontWeight": "400"}],
              "body-md": ["16px", {"lineHeight": "24px", "fontWeight": "400"}],
              "headline-lg": ["32px", {"lineHeight": "40px", "letterSpacing": "-0.02em", "fontWeight": "700"}],
              "label-sm": ["12px", {"lineHeight": "14px", "fontWeight": "500"}]
      },
      animation: {
        'pulse-emergency': 'pulse-emergency 2s infinite',
      },
      keyframes: {
        'pulse-emergency': {
          '0%': { boxShadow: '0 0 0 0 rgba(230, 57, 70, 0.4)' },
          '70%': { boxShadow: '0 0 0 10px rgba(230, 57, 70, 0)' },
          '100%': { boxShadow: '0 0 0 0 rgba(230, 57, 70, 0)' },
        }
      }
    }
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/container-queries'),
  ]
}
