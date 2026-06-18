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
              "on-error": "#ffffff",
              "on-primary-container": "#f8f7ff",
              "tertiary-fixed-dim": "#adc6ff",
              "error-container": "#ffdad6",
              "tertiary": "#0056b9",
              "on-tertiary-fixed": "#001a42",
              "surface": "#f9f9ff",
              "on-tertiary": "#ffffff",
              "surface-bright": "#f9f9ff",
              "surface-container-lowest": "#ffffff",
              "on-surface": "#151c27",
              "background": "#f9f9ff",
              "primary-fixed-dim": "#b3c5ff",
              "primary-fixed": "#dae1ff",
              "tertiary-container": "#1c6ee1",
              "outline-variant": "#c2c6d8",
              "error": "#ba1a1a",
              "inverse-surface": "#2a313d",
              "surface-tint": "#0054d6",
              "inverse-on-surface": "#ebf1ff",
              "on-primary": "#ffffff",
              "surface-container": "#e7eefe",
              "primary-container": "#0066ff",
              "surface-dim": "#d3daea",
              "outline": "#727687",
              "on-secondary-container": "#007165",
              "on-tertiary-fixed-variant": "#004395",
              "primary": "#0050cb",
              "surface-variant": "#dce2f3",
              "on-tertiary-container": "#f8f8ff",
              "on-secondary-fixed-variant": "#005047",
              "secondary-fixed-dim": "#3cddc7",
              "on-secondary-fixed": "#00201c",
              "inverse-primary": "#b3c5ff",
              "surface-container-highest": "#dce2f3",
              "secondary-fixed": "#62fae3",
              "on-primary-fixed-variant": "#003fa4",
              "secondary-container": "#62fae3",
              "on-background": "#151c27",
              "on-error-container": "#93000a",
              "surface-container-high": "#e2e8f8",
              "on-primary-fixed": "#001849",
              "on-secondary": "#ffffff",
              "surface-container-low": "#f0f3ff",
              "tertiary-fixed": "#d8e2ff",
              "secondary": "#006b5f",
              "on-surface-variant": "#424656",
              // Urgency Colors
              emergency: '#E63946',
              urgent: '#F4A261',
              soon: '#E9C46A',
              routine: '#2A9D8F',
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
