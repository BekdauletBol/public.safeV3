/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          900: '#0a0e1a',
          800: '#0f1624',
          700: '#141d2f',
          600: '#1a2540',
          500: '#1e2d4f',
        },
        accent: {
          cyan: '#00d4ff',
          green: '#00ff9d',
          red: '#ff3d6b',
          amber: '#ffb830',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        display: ['Syne', 'sans-serif'],
        body: ['DM Sans', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
