/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./frontend/**/*.html",
    "./frontend/assets/js/**/*.js",
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require("daisyui"),
  ],
  daisyui: {
    themes: ["light"],
    logs: false,
  },
}
