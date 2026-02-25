import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    fontFamily: {
      sans: ['"Plus Jakarta Sans"', "Inter", "system-ui", "sans-serif"],
    },
    extend: {
      colors: {
        primary: {
          DEFAULT: "#1E2A6E",
          dark: "#141D52",
          light: "#2D3A8C",
          50: "#EEF0F7",
          100: "#D0D4E8",
          200: "#A8AECF",
          300: "#7880B5",
          400: "#4E579B",
          500: "#1E2A6E",
          600: "#1A2561",
          700: "#141D52",
          800: "#0F1642",
          900: "#0A0F33",
        },
        accent: {
          DEFAULT: "#3B82F6",
          dark: "#2563EB",
          light: "#DBEAFE",
          50: "#EFF6FF",
        },
        surface: {
          DEFAULT: "#F8FAFC",
          card: "#FFFFFF",
        },
        text: {
          primary: "#0F172A",
          body: "#334155",
          muted: "#94A3B8",
          inverse: "#FFFFFF",
        },
        success: "#10B981",
        warning: "#F59E0B",
        danger: "#EF4444",
        info: "#3B82F6",
        border: {
          DEFAULT: "#E2E8F0",
          active: "#1E2A6E",
        },
      },
      fontSize: {
        display: ["56px", { lineHeight: "1.2", fontWeight: "700" }],
        h1: ["40px", { lineHeight: "1.2", fontWeight: "700" }],
        h2: ["28px", { lineHeight: "1.2", fontWeight: "600" }],
        h3: ["22px", { lineHeight: "1.2", fontWeight: "600" }],
        "body-lg": ["20px", { lineHeight: "1.5", fontWeight: "400" }],
        body: ["18px", { lineHeight: "1.5", fontWeight: "400" }],
        caption: ["14px", { lineHeight: "1.5", fontWeight: "500" }],
        button: ["18px", { lineHeight: "1.5", fontWeight: "600" }],
      },
      letterSpacing: {
        heading: "-0.02em",
      },
      borderRadius: {
        card: "20px",
        button: "16px",
        modal: "24px",
        input: "12px",
      },
      boxShadow: {
        card: "0 4px 24px rgba(30, 42, 110, 0.06), 0 1px 3px rgba(30, 42, 110, 0.04)",
        "card-hover":
          "0 8px 32px rgba(30, 42, 110, 0.12), 0 2px 4px rgba(30, 42, 110, 0.06)",
        modal: "0 24px 48px rgba(30, 42, 110, 0.18)",
        button: "0 2px 12px rgba(30, 42, 110, 0.25)",
        glow: "0 0 40px rgba(30, 42, 110, 0.15)",
        "glow-active": "0 0 60px rgba(30, 42, 110, 0.25)",
      },
      spacing: {
        "touch-sm": "44px",
        "touch-md": "56px",
        "touch-lg": "72px",
      },
      screens: {
        "kiosk-portrait": { raw: "(min-width: 1080px) and (min-height: 1920px)" },
        "kiosk-landscape": { raw: "(min-width: 1920px) and (min-height: 1080px)" },
      },
      keyframes: {
        breathing: {
          "0%, 100%": { transform: "scale(1)", opacity: "1" },
          "50%": { transform: "scale(1.03)", opacity: "0.9" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-20px)" },
        },
        "pulse-ring": {
          "0%": { transform: "scale(0.8)", opacity: "1" },
          "100%": { transform: "scale(2.5)", opacity: "0" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "gradient-shift": {
          "0%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
          "100%": { backgroundPosition: "0% 50%" },
        },
      },
      animation: {
        breathing: "breathing 3s ease-in-out infinite",
        float: "float 6s ease-in-out infinite",
        "pulse-ring": "pulse-ring 2s ease-out infinite",
        shimmer: "shimmer 1.5s ease-in-out infinite",
        "gradient-shift": "gradient-shift 20s ease infinite",
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
} satisfies Config;
