/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Dark neon theme colors
        dark: {
          50: '#f0f0f5',
          100: '#e0e0eb',
          200: '#c2c2d6',
          300: '#9999b3',
          400: '#70708f',
          500: '#52526b',
          600: '#3d3d52',
          700: '#2a2a3d',
          800: '#1a1a2e',
          900: '#0f0f1a',
          950: '#0a0a12',
        },
        neon: {
          cyan: '#00ffff',
          pink: '#ff00ff',
          green: '#00ff88',
          blue: '#00aaff',
          purple: '#aa00ff',
          orange: '#ff8800',
        },
        primary: {
          50: '#f0fdfa',
          100: '#ccfbf1',
          200: '#99f6e4',
          300: '#5eead4',
          400: '#2dd4bf',
          500: '#14b8a6',
          600: '#0d9488',
          700: '#0f766e',
          800: '#115e59',
          900: '#134e4a',
          950: '#042f2e',
        },
      },
      boxShadow: {
        'neon-cyan': '0 0 20px rgba(0, 255, 255, 0.5)',
        'neon-pink': '0 0 20px rgba(255, 0, 255, 0.5)',
        'neon-green': '0 0 20px rgba(0, 255, 136, 0.5)',
        'neon-blue': '0 0 20px rgba(0, 170, 255, 0.5)',
      },
      animation: {
        'pulse-neon': 'pulse-neon 2s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        'pulse-neon': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
        'glow': {
          '0%': { boxShadow: '0 0 5px rgba(0, 255, 255, 0.3)' },
          '100%': { boxShadow: '0 0 20px rgba(0, 255, 255, 0.6)' },
        },
      },
    },
  },
  plugins: [],
};
