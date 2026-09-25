/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        obsidian: {
          950: '#04060a',
          900: '#070a12',
          850: '#0b101c',
          800: '#101728',
          700: '#18233c',
          600: '#223254',
        },
        profit: {
          light: '#34d399',
          DEFAULT: '#10b981',
          dark: '#059669',
          glow: 'rgba(16, 185, 129, 0.25)'
        },
        loss: {
          light: '#fb7185',
          DEFAULT: '#f43f5e',
          dark: '#e11d48',
          glow: 'rgba(244, 63, 94, 0.25)'
        },
        cyber: {
          cyan: '#00f2fe',
          blue: '#4facfe',
          purple: '#8b5cf6',
          gold: '#f59e0b'
        }
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Courier New', 'monospace'],
      },
      animation: {
        'pulse-subtle': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow-pulse': 'glowPulse 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glowPulse: {
          '0%': { boxShadow: '0 0 5px rgba(0, 242, 254, 0.2)' },
          '100%': { boxShadow: '0 0 18px rgba(0, 242, 254, 0.6)' },
        }
      }
    },
  },
  plugins: [],
};
