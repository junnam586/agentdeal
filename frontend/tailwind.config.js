/** @type {import('tailwindcss').Config} */
// "The Broadsheet" — a living financial newspaper. Warm newsprint, ink serif
// headlines, ruled ledger lines, tabular figures. All tokens derive from this.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F2EDE3", // warm newsprint base
        paper2: "#EBE4D5", // raised panel / pull-quote ground
        paper3: "#E3DBC8", // deepest inset
        ink: "#19150F", // primary ink (warm near-black)
        inksoft: "#4C463A", // secondary ink
        buyer: "#1C5566", // petrol blue — buyer pulls price down
        seller: "#9C3B2A", // oxblood — sellers hold price up
        seal: "#136A4A", // emerald stamp — the settled deal (used sparingly)
        trust: "#3A357E", // indigo — the verified-identity layer only
        rule: "#D6CEBE", // hairline rules
        muted: "#8B8170", // metadata, datelines, captions
      },
      fontFamily: {
        display: ['"Fraunces"', "Georgia", "serif"],
        body: ['"Newsreader"', "Georgia", "serif"],
        mono: ['"Spline Sans Mono"', "ui-monospace", "monospace"],
      },
      fontSize: {
        masthead: ["clamp(2.75rem, 7vw, 6rem)", { lineHeight: "0.92", letterSpacing: "-0.02em" }],
        headline: ["clamp(2rem, 5vw, 4rem)", { lineHeight: "0.95", letterSpacing: "-0.015em" }],
        "settle-price": ["clamp(2.5rem, 6vw, 4.25rem)", { lineHeight: "1", letterSpacing: "-0.02em" }],
      },
      letterSpacing: {
        news: "0.18em", // smallcaps datelines / kickers
      },
      boxShadow: {
        stamp: "0 0 0 2px rgba(19,106,74,0.55), 0 1px 0 rgba(19,106,74,0.25)",
        lift: "0 18px 40px -28px rgba(25,21,15,0.45)",
      },
      keyframes: {
        "ink-in": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "ink-in": "ink-in 0.5s cubic-bezier(0.2,0.7,0.2,1) both",
      },
    },
  },
  plugins: [],
};
