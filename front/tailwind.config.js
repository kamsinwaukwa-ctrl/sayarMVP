/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
  // Important: Ensure Tailwind doesn't conflict with Material-UI
  corePlugins: {
    preflight: false,
  },
}