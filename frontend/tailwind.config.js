/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bone: "#F4F2F0",
        ink: "#0C0A08",
        burgundy: { DEFAULT: "#7B1F4B", light: "#F1E4EA" },
      },
    },
  },
  plugins: [],
};
