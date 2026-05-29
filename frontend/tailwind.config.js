/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        mono: ["'JetBrains Mono'", "Fira Code", "Consolas", "monospace"],
      },
      colors: {
        dna: {
          a: "#ef4444",   // Adenine  – red
          t: "#3b82f6",   // Thymine  – blue
          g: "#22c55e",   // Guanine  – green
          c: "#f59e0b",   // Cytosine – amber
        },
        impact: {
          silent:    "#16a34a",
          missense:  "#dc2626",
          nonsense:  "#1e293b",
          stop_lost: "#d97706",
          start_lost:"#0284c7",
          frameshift:"#6b7280",
          inframe:   "#9ca3af",
        },
      },
    },
  },
  plugins: [],
};
