/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        'agent-claude':  '#D97706',
        'agent-openai':  '#10A37F',
        'agent-gemini':  '#4285F4',
        'agent-falai':   '#FF6B6B',
        'agent-human':   '#8B5CF6',
        'agent-ralph':   '#EC4899',
      },
    },
  },
  plugins: [],
}
