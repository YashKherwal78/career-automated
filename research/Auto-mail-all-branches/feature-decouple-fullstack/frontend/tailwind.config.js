/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        geo: {
          void:    '#06080d',
          obsidian:'#0a0e17',
          gunmetal:'#111827',
          slate:   '#1a2035',
          steel:   '#2a3450',
          teal:    '#14b8a6',
          cyan:    '#06b6d4',
          amber:   '#f59e0b',
          ember:   '#ef4444',
          lime:    '#84cc16',
          text:    '#e5e7eb',
          muted:   '#6b7280',
          dim:     '#374151',
        }
      },
      fontFamily: {
        mono:    ['"JetBrains Mono"', 'Fira Code', 'monospace'],
        display: ['"DM Sans"', 'system-ui', 'sans-serif'],
        body:    ['"DM Sans"', 'system-ui', 'sans-serif'],
      },
      animation: {
        'fade-in':      'fadeIn 0.5s ease-out both',
        'slide-up':     'slideUp 0.6s ease-out both',
        'slide-right':  'slideRight 0.6s ease-out both',
        'hex-rotate':   'hexRotate 20s linear infinite',
        'pulse-glow':   'pulseGlow 3s ease-in-out infinite',
        'tessellate':   'tessellate 15s linear infinite',
        'crystallize':  'crystallize 0.4s ease-out both',
        'counter-spin': 'counterSpin 25s linear infinite',
        'float':        'float 6s ease-in-out infinite',
        'dash':         'dash 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%':   { opacity: '0', transform: 'translateY(24px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideRight: {
          '0%':   { opacity: '0', transform: 'translateX(-24px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        hexRotate: {
          '0%':   { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        counterSpin: {
          '0%':   { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(-360deg)' },
        },
        pulseGlow: {
          '0%, 100%': { opacity: '0.4' },
          '50%':      { opacity: '1' },
        },
        tessellate: {
          '0%':   { backgroundPosition: '0 0' },
          '100%': { backgroundPosition: '60px 104px' },
        },
        crystallize: {
          '0%':   { opacity: '0', transform: 'scale(0.95) rotate(-1deg)' },
          '100%': { opacity: '1', transform: 'scale(1) rotate(0deg)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%':      { transform: 'translateY(-12px)' },
        },
        dash: {
          '0%':   { strokeDashoffset: '300' },
          '50%':  { strokeDashoffset: '0' },
          '100%': { strokeDashoffset: '-300' },
        },
      },
      backgroundImage: {
        'geo-grid': `url("data:image/svg+xml,%3Csvg width='60' height='104' viewBox='0 0 60 104' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' stroke='%2314b8a6' stroke-width='0.3' opacity='0.12'%3E%3Cpath d='M30 0L60 17.32V52L30 69.28 0 52V17.32z'/%3E%3Cpath d='M30 34.64L60 51.96V86.6L30 103.92 0 86.6V51.96z'/%3E%3C/g%3E%3C/svg%3E")`,
      },
    },
  },
  plugins: [],
}
