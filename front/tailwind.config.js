/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // Color palette matching Material-UI defaults
      colors: {
        primary: {
          50: '#e3f2fd',
          100: '#bbdefb',
          200: '#90caf9',
          300: '#64b5f6',
          400: '#42a5f5',
          500: '#2196f3', // Main primary color
          600: '#1e88e5',
          700: '#1976d2',
          800: '#1565c0',
          900: '#0d47a1',
          main: '#1976d2',
          light: '#42a5f5',
          dark: '#1565c0',
        },
        secondary: {
          50: '#fce4ec',
          100: '#f8bbd9',
          200: '#f48fb1',
          300: '#f06292',
          400: '#ec407a',
          500: '#e91e63', // Main secondary color
          600: '#d81b60',
          700: '#c2185b',
          800: '#ad1457',
          900: '#880e4f',
          main: '#dc004e',
          light: '#ec407a',
          dark: '#c2185b',
        },
        error: {
          50: '#ffebee',
          100: '#ffcdd2',
          200: '#ef9a9a',
          300: '#e57373',
          400: '#ef5350',
          500: '#f44336', // Main error color
          600: '#e53935',
          700: '#d32f2f',
          800: '#c62828',
          900: '#b71c1c',
          main: '#d32f2f',
          light: '#ef5350',
          dark: '#c62828',
        },
        warning: {
          50: '#fff8e1',
          100: '#ffecb3',
          200: '#ffe082',
          300: '#ffd54f',
          400: '#ffca28',
          500: '#ffc107', // Main warning color
          600: '#ffb300',
          700: '#ffa000',
          800: '#ff8f00',
          900: '#ff6f00',
          main: '#ed6c02',
          light: '#ff9800',
          dark: '#e65100',
        },
        info: {
          50: '#e1f5fe',
          100: '#b3e5fc',
          200: '#81d4fa',
          300: '#4fc3f7',
          400: '#29b6f6',
          500: '#03a9f4', // Main info color
          600: '#039be5',
          700: '#0288d1',
          800: '#0277bd',
          900: '#01579b',
          main: '#0288d1',
          light: '#03a9f4',
          dark: '#01579b',
        },
        success: {
          50: '#e8f5e8',
          100: '#c8e6c9',
          200: '#a5d6a7',
          300: '#81c784',
          400: '#66bb6a',
          500: '#4caf50', // Main success color
          600: '#43a047',
          700: '#388e3c',
          800: '#2e7d32',
          900: '#1b5e20',
          main: '#2e7d32',
          light: '#4caf50',
          dark: '#1b5e20',
        },
        grey: {
          50: '#fafafa',
          100: '#f5f5f5',
          200: '#eeeeee',
          300: '#e0e0e0',
          400: '#bdbdbd',
          500: '#9e9e9e',
          600: '#757575',
          700: '#616161',
          800: '#424242',
          900: '#212121',
        },
        text: {
          primary: 'rgba(0, 0, 0, 0.87)',
          secondary: 'rgba(0, 0, 0, 0.6)',
          disabled: 'rgba(0, 0, 0, 0.38)',
        },
        divider: 'rgba(0, 0, 0, 0.12)',
        background: {
          default: '#ffffff',
          paper: '#ffffff',
        },
      },
      // Typography matching Material-UI
      fontFamily: {
        sans: ['"Roboto"', '"Helvetica"', '"Arial"', 'sans-serif'],
      },
      fontSize: {
        'h1': ['6rem', { lineHeight: '1.167', fontWeight: '300' }],
        'h2': ['3.75rem', { lineHeight: '1.2', fontWeight: '300' }],
        'h3': ['3rem', { lineHeight: '1.167', fontWeight: '400' }],
        'h4': ['2.125rem', { lineHeight: '1.235', fontWeight: '400' }],
        'h5': ['1.5rem', { lineHeight: '1.334', fontWeight: '400' }],
        'h6': ['1.25rem', { lineHeight: '1.6', fontWeight: '500' }],
        'subtitle1': ['1rem', { lineHeight: '1.75', fontWeight: '400' }],
        'subtitle2': ['0.875rem', { lineHeight: '1.57', fontWeight: '500' }],
        'body1': ['1rem', { lineHeight: '1.5', fontWeight: '400' }],
        'body2': ['0.875rem', { lineHeight: '1.43', fontWeight: '400' }],
        'button': ['0.875rem', { lineHeight: '1.75', fontWeight: '500', textTransform: 'uppercase' }],
        'caption': ['0.75rem', { lineHeight: '1.66', fontWeight: '400' }],
        'overline': ['0.75rem', { lineHeight: '2.66', fontWeight: '400', textTransform: 'uppercase' }],
      },
      // Spacing matching Material-UI (8px base unit)
      spacing: {
        '0.5': '4px',   // 0.5 * 8px
        '1': '8px',     // 1 * 8px
        '1.5': '12px',  // 1.5 * 8px
        '2': '16px',    // 2 * 8px
        '2.5': '20px',  // 2.5 * 8px
        '3': '24px',    // 3 * 8px
        '3.5': '28px',  // 3.5 * 8px
        '4': '32px',    // 4 * 8px
        '5': '40px',    // 5 * 8px
        '6': '48px',    // 6 * 8px
        '7': '56px',    // 7 * 8px
        '8': '64px',    // 8 * 8px
      },
      // Border radius matching Material-UI
      borderRadius: {
        'sm': '4px',
        'DEFAULT': '4px',
        'md': '6px',
        'lg': '8px',
        'xl': '12px',
        '2xl': '16px',
      },
      // Elevation shadows matching Material-UI
      boxShadow: {
        'elevation-1': '0px 2px 1px -1px rgba(0,0,0,0.2), 0px 1px 1px 0px rgba(0,0,0,0.14), 0px 1px 3px 0px rgba(0,0,0,0.12)',
        'elevation-2': '0px 3px 1px -2px rgba(0,0,0,0.2), 0px 2px 2px 0px rgba(0,0,0,0.14), 0px 1px 5px 0px rgba(0,0,0,0.12)',
        'elevation-3': '0px 3px 3px -2px rgba(0,0,0,0.2), 0px 3px 4px 0px rgba(0,0,0,0.14), 0px 1px 8px 0px rgba(0,0,0,0.12)',
        'elevation-4': '0px 2px 4px -1px rgba(0,0,0,0.2), 0px 4px 5px 0px rgba(0,0,0,0.14), 0px 1px 10px 0px rgba(0,0,0,0.12)',
        'elevation-6': '0px 3px 5px -1px rgba(0,0,0,0.2), 0px 6px 10px 0px rgba(0,0,0,0.14), 0px 1px 18px 0px rgba(0,0,0,0.12)',
        'elevation-8': '0px 5px 5px -3px rgba(0,0,0,0.2), 0px 8px 10px 1px rgba(0,0,0,0.14), 0px 3px 14px 2px rgba(0,0,0,0.12)',
        'elevation-12': '0px 7px 8px -4px rgba(0,0,0,0.2), 0px 12px 17px 2px rgba(0,0,0,0.14), 0px 5px 22px 4px rgba(0,0,0,0.12)',
        'elevation-16': '0px 8px 10px -5px rgba(0,0,0,0.2), 0px 16px 24px 2px rgba(0,0,0,0.14), 0px 6px 30px 5px rgba(0,0,0,0.12)',
        'elevation-24': '0px 11px 15px -7px rgba(0,0,0,0.2), 0px 24px 38px 3px rgba(0,0,0,0.14), 0px 9px 46px 8px rgba(0,0,0,0.12)',
      },
      // Transition durations matching Material-UI
      transitionDuration: {
        'shortest': '150ms',
        'shorter': '200ms',
        'short': '250ms',
        'standard': '300ms',
        'complex': '375ms',
        'entering-screen': '225ms',
        'leaving-screen': '195ms',
      },
      // Z-index values matching Material-UI
      zIndex: {
        'mobileStepper': '1000',
        'fab': '1050',
        'speedDial': '1050',
        'appBar': '1100',
        'drawer': '1200',
        'modal': '1300',
        'snackbar': '1400',
        'tooltip': '1500',
      },
    },
  },
  plugins: [],
  // Important: Enable preflight for migration but keep it disabled initially
  corePlugins: {
    preflight: false,
  },
}