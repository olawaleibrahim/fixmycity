/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        pothole: "#f97316",
        flooding: "#3b82f6",
        trash: "#84cc16",
        infrastructure: "#a855f7",
        graffiti: "#ec4899",
        housing: "#ef4444",
      },
    },
  },
  plugins: [],
};
