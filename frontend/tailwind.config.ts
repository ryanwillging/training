import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Material Design 3 Color Palette
        primary: {
          DEFAULT: '#1976d2',
          light: '#42a5f5',
          dark: '#1565c0',
        },
        secondary: {
          DEFAULT: '#9c27b0',
          light: '#ba68c8',
          dark: '#7b1fa2',
        },
        surface: {
          DEFAULT: '#ffffff',
          variant: '#f5f5f5',
        },
        background: '#fafafa',
        outline: {
          DEFAULT: '#79747e',
          variant: '#e0e0e0',
        },
        success: {
          DEFAULT: '#2e7d32',
          light: '#4caf50',
        },
        warning: {
          DEFAULT: '#ed6c02',
          light: '#ff9800',
        },
        error: {
          DEFAULT: '#d32f2f',
          light: '#ef5350',
        },
        info: {
          DEFAULT: '#0288d1',
          light: '#03a9f4',
        },
        // Workout type colors
        swim: {
          DEFAULT: '#1976d2',
          dark: '#1565c0',
          test: '#0d47a1',
        },
        lift: {
          DEFAULT: '#388e3c',
          dark: '#2e7d32',
        },
        vo2: '#d32f2f',
      },
      fontFamily: {
        sans: ['Roboto', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Helvetica Neue', 'Arial', 'sans-serif'],
      },
      boxShadow: {
        'md-1': '0 1px 2px rgba(0,0,0,0.3), 0 1px 3px 1px rgba(0,0,0,0.15)',
        'md-2': '0 1px 2px rgba(0,0,0,0.3), 0 2px 6px 2px rgba(0,0,0,0.15)',
        'md-3': '0 4px 8px 3px rgba(0,0,0,0.15), 0 1px 3px rgba(0,0,0,0.3)',
      },
      borderRadius: {
        'xs': '4px',
        'md': '12px',
        'lg': '16px',
        'xl': '28px',
      },
    },
  },
  plugins: [],
};

export default config;
