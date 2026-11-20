tailwind.config = {
  theme: {
    extend: {
      colors: {
        // deep green brand scale (from the VERA logo) — named "navy" for continuity
        navy: {
          50: "#edf4f0",
          100: "#d4e6dc",
          600: "#2d5a45",
          700: "#214636",
          800: "#173629",
          900: "#0f261c",
          950: "#091a13",
        },
        cream: {
          50: "#fbf9f4",
          100: "#f6f1e8",
          200: "#ece3d4",
          300: "#ddd0bb",
        },
        copper: {
          100: "#f4e2d2",
          400: "#d2884f",
          500: "#c06a38",
          600: "#a4572a",
        },
      },
      fontFamily: {
        sans: ["Plus Jakarta Sans", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        serif: ["Lora", "Georgia", "Cambria", "Times New Roman", "serif"],
      },
    },
  },
};
