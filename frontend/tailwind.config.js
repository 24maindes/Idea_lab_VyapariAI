/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#0F4C5C",
        secondary: "#2A7F8E",
        accent: "#E9785B",
        bg: "#F7F8F5",
        card: "#FFFFFF",
        ink: "#243238",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      borderRadius: {
        DEFAULT: "10px",
        card: "12px",
        control: "8px",
      },
      boxShadow: {
        subtle: "0 1px 2px rgba(15, 76, 92, 0.06)",
        card: "0 1px 3px rgba(15, 76, 92, 0.08)",
      },
    },
  },
  plugins: [],
};
