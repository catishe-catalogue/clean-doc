import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: "var(--color-paper)",
        "paper-2": "var(--color-paper-2)",
        "paper-3": "var(--color-paper-3)",
        ink: "var(--color-ink)",
        "ink-2": "var(--color-ink-2)",
        muted: "var(--color-muted)",
        rule: "var(--color-rule)",
        "rule-2": "var(--color-rule-2)",
        accent: "var(--color-accent)",
        "accent-ink": "var(--color-accent-ink)",
        "accent-2": "var(--color-accent-2)",
        focus: "var(--color-focus)",
        cotton: "var(--color-cotton)",
        desk: "var(--color-desk)",
        print: "var(--color-print)",
        board: "var(--color-board)",
        "board-type": "var(--color-board-type)",
        paid: "var(--color-paid)",
        error: "var(--color-error)",
        success: "var(--color-success)",
      },
      fontFamily: {
        sans: ["var(--font-display)", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
        display: ["var(--font-display)", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["var(--font-outlier)", "ui-monospace", "monospace"],
      },
      borderRadius: {
        card: "var(--radius-card)",
        input: "var(--radius-input)",
        stock: "var(--radius-stock)",
        pill: "var(--radius-pill)",
      },
      boxShadow: {
        card: "var(--shadow-card)",
        stock: "var(--cast-stock)",
        "stock-lift": "var(--cast-stock-lift)",
      },
    },
  },
  plugins: [],
};
export default config;
