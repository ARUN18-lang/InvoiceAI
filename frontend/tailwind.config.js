/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#0a0a0a",
        surface: "#121212",
        raised: "#1a1a1a",
        /* Dark-only hairlines — no light/white outlines on black UI */
        line: "#0c0c0c",
        "line-strong": "#141414",
        muted: "#a3a3a3",
        "muted-dim": "#737373",
        accent: "#2563eb",
        "accent-hover": "#1d4ed8",
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
      borderRadius: {
        lg: "10px",
        xl: "12px",
      },
      boxShadow: {
        /* Subtle depth only — no light ring */
        card: "0 1px 0 rgba(0,0,0,0.75)",
      },
    },
  },
  plugins: [],
};
