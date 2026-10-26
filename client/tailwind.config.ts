import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        // Palette Kwa-Ba (charte « L'Afrique vous accueille »)
        primary: {
          // Deep "Trust" green: buttons, links, headers (9.8:1 with white)
          DEFAULT: '#0E4D47',
          50: '#EEF6F5',
          100: '#D3E8E5',
          200: '#A7D0CA',
          300: '#73B2A9',
          400: '#3E8D83',
          500: '#146B62',
          600: '#0B3F3A',
          700: '#093430',
          800: '#072A27',
          900: '#05201D',
        },
        dark: {
          DEFAULT: '#1F2937', // "Modernity": main text
          muted: '#475569',
        },
        light: {
          DEFAULT: '#F8F6F2', // "Simplicity" cream: backgrounds
          muted: '#F0ECE4',
        },
        secondary: {
          // Darkened "Energy" orange for action buttons (Pay, Book): 5:1 with white.
          // The brand's bright orange (#F59E0B) stays as `accent` (logo, stars, decorations).
          DEFAULT: '#B45309',
          600: '#92400E',
        },
        accent: '#F59E0B',
        muted: '#5F6B6C', // gris secondaire lisible (≥ 5:1)
        // gray-400 and 500 raised: help texts and hints readable on white and on cream (≥ 4.5:1)
        gray: { 400: '#667080', 500: '#667080' },
        // Semantic Colors
        success: '#10B981', // Emerald 500
        warning: '#F59E0B', // Amber 500
        danger: '#EF4444',  // Red 500
      },
      fontFamily: {
        // Fonts self-hosted by next/font (app/layout.tsx): no call to Google from the visitor
        heading: ["var(--font-montserrat)", "Montserrat", "Inter", "sans-serif"],
        body: ["var(--font-inter)", "Inter", "Roboto", "sans-serif"],
      },
      borderRadius: {
        card: "10px",
        'xl': '1rem',
        '2xl': '1.5rem',
        '3xl': '2rem',
      },
      boxShadow: {
        'soft': '0 4px 20px -2px rgba(0, 0, 0, 0.05)',
        'card': '0 10px 30px -5px rgba(0, 0, 0, 0.08)',
        'card-hover': '0 20px 40px -5px rgba(0, 0, 0, 0.12)',
        'button': '0 4px 14px 0 rgba(14, 77, 71, 0.35)', // halo vert Kwa-Ba
      },
    },
  },
  plugins: [],
};

export default config;
