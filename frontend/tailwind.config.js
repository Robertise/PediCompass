/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bgDeep: '#0D1B2A',
        bgSurface: '#152538',
        bgCard: '#1A2E42',
        teal: {
          400: '#00B4D8',
          500: '#0096C7',
        },
        emergency: '#E63946',
        urgent: '#F4A261',
        soon: '#E9C46A',
        routine: '#2A9D8F',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
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
    },
  },
  plugins: [],
}
