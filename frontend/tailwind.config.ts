import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: ["class", '[data-theme="dark"]'],
  theme: {
    // Mobile-first, matching docs/FRONTEND.md §4: base = <=470px, xs = the
    // 471-780px tier, sm = 781-1140px (rail + detail), lg = >=1141px (full).
    screens: {
      xs: "471px",
      sm: "781px",
      lg: "1141px",
    },
    extend: {
      colors: {
        page: "var(--page)",
        surface: "var(--surface)",
        raised: "var(--raised)",
        sunk: "var(--sunk)",
        ink: "var(--ink)",
        muted: "var(--muted)",
        faint: "var(--faint)",
        rule: "var(--rule)",
        "rule-strong": "var(--rule-strong)",
        oxide: "var(--oxide)",
        ochre: "var(--ochre)",
        moss: "var(--moss)",
        "internal-bg": "var(--internal-bg)",
        "sel-bg": "var(--sel-bg)",
      },
      fontFamily: {
        sans: ["var(--font-poppins)", "sans-serif"],
      },
      borderRadius: {
        DEFAULT: "0px",
      },
    },
  },
  plugins: [],
};
export default config;
