import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    container: { center: true, padding: "1rem" },
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui"],
        display: ["var(--font-display)", "ui-serif", "Georgia"],
      },
      colors: {
        canvas: "#FBF7F1",
        ink: { DEFAULT: "#1F1A17", soft: "#4A433E", muted: "#7A716A" },
        line: "#ECE4D9",
        mit: { 50: "#FFF1F1", 100: "#FFE1E1", 200: "#FFC7C7", 400: "#F87171", 500: "#E5484D", 600: "#CE2C31", 700: "#A61E24" },
        student: { 50: "#EEF5FF", 100: "#DCEAFF", 200: "#B9D5FF", 400: "#5B9BFA", 500: "#2F7CF6", 600: "#1D64DB", 700: "#174FAF" },
        cs: { 50: "#F4F0FF", 100: "#E9E1FF", 500: "#8B5CF6", 600: "#7342E8", 700: "#5B2FC4" },
        phys: { 50: "#FFF8EB", 100: "#FFEDC7", 500: "#F59E0B", 600: "#D97F06", 700: "#B45F09" },
        bio: { 50: "#ECFDF5", 100: "#D1FAE5", 500: "#10B981", 600: "#059669", 700: "#047857" },
      },
      borderRadius: { "4xl": "2rem" },
      boxShadow: {
        soft: "0 1px 2px rgba(31,26,23,.04), 0 8px 24px -12px rgba(31,26,23,.12)",
        lift: "0 2px 4px rgba(31,26,23,.05), 0 18px 40px -18px rgba(31,26,23,.25)",
      },
      keyframes: {
        "fade-up": { from: { opacity: "0", transform: "translateY(8px)" }, to: { opacity: "1", transform: "none" } },
        float: { "0%,100%": { transform: "translateY(0)" }, "50%": { transform: "translateY(-6px)" } },
      },
      animation: { "fade-up": "fade-up .45s ease-out both", float: "float 6s ease-in-out infinite" },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
export default config;
