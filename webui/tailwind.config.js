/** @type {import('tailwindcss').Config} */

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    container: {
      center: true,
    },
    extend: {
      colors: {
        // 深夜紫蓝 — 主背景
        midnight: {
          DEFAULT: "#1B1633",
          50: "#3A3361",
          100: "#332E57",
          200: "#2C284D",
          300: "#252243",
          400: "#1F1C39",
          500: "#1B1633",
          600: "#15112A",
          700: "#0F0C21",
          800: "#0A0818",
          900: "#050410",
        },
        // 月光青 — 强调色 / 文字高亮
        moonlight: {
          DEFAULT: "#8EE6E0",
          50: "#F0FCFB",
          100: "#D9F8F5",
          200: "#B3F0EB",
          300: "#8EE6E0",
          400: "#6DDCD5",
          500: "#4FBFB9",
          600: "#3A9994",
          700: "#2C736F",
          800: "#1F4D4A",
          900: "#122625",
        },
        // 樱粉 — 对话气泡 / 提示
        sakura: {
          DEFAULT: "#FFB7C5",
          50: "#FFF5F7",
          100: "#FFE4EA",
          200: "#FFD0DA",
          300: "#FFB7C5",
          400: "#FF94A6",
          500: "#FF6B82",
          600: "#E04A63",
          700: "#B8384E",
          800: "#8A2939",
          900: "#5C1B26",
        },
        // 星辰紫 — 次强调
        stardust: {
          DEFAULT: "#A78BFA",
          400: "#A78BFA",
          500: "#8B5CF6",
        },
      },
      fontFamily: {
        display: ['"Zen Maru Gothic"', '"Noto Sans SC"', "system-ui", "sans-serif"],
        body: ['"Noto Sans SC"', "system-ui", "sans-serif"],
      },
      animation: {
        "pulse-soft": "pulse-soft 2.4s ease-in-out infinite",
        "breathe": "breathe 3.2s ease-in-out infinite",
        "float-up": "float-up 0.4s ease-out",
        "shimmer": "shimmer 2s linear infinite",
        "ring-expand": "ring-expand 1.6s ease-out infinite",
      },
      keyframes: {
        "pulse-soft": {
          "0%, 100%": { opacity: "0.7", transform: "scale(1)" },
          "50%": { opacity: "1", transform: "scale(1.05)" },
        },
        "breathe": {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-4px)" },
        },
        "float-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "shimmer": {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "ring-expand": {
          "0%": { transform: "scale(1)", opacity: "0.6" },
          "100%": { transform: "scale(2.2)", opacity: "0" },
        },
      },
    },
  },
  plugins: [],
};
