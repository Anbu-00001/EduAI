import type { Config } from 'tailwindcss'
import forms from '@tailwindcss/forms'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // EduPredict design system — matches current dark theme
        bg:       '#030712',
        card:     '#0f172a',
        'card-2': '#1e293b',
        border:   '#1e293b',
        'border-2':'#334155',
        // Risk tier colours
        green:    { DEFAULT: '#10b981', dim: '#064e3b', text: '#34d399' },
        amber:    { DEFAULT: '#f59e0b', dim: '#78350f', text: '#fbbf24' },
        rose:     { DEFAULT: '#f43f5e', dim: '#4c0519', text: '#fb7185' },
        // Accent
        blue:     { DEFAULT: '#3b82f6', dim: '#1e3a5f', text: '#60a5fa' },
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'gauge-fill': 'gaugeFill 1.2s ease-out forwards',
        'slide-up':   'slideUp 0.4s ease-out',
        'fade-in':    'fadeIn 0.3s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        gaugeFill: {
          from: { strokeDashoffset: '283' },
          to:   { strokeDashoffset: 'var(--target-offset)' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(12px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          from: { opacity: '0' },
          to:   { opacity: '1' },
        },
      },
    },
  },
  plugins: [forms],
} satisfies Config
