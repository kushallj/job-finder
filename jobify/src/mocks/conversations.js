// DEMO DATA: scripted conversations. No AI provider is called.
const t = (d) => new Date(Date.UTC(2026, 9, 31 - d, 9, 0)).toISOString();
const TOPICS = [
  ["Founders who fit my profile", "Here are five demo founders whose companies match a TypeScript and React background: Lattice Pay, Northbeam Labs, Saffron Labs, Halcyon AI and Ridgeline. Each is marked as hiring in the demo directory."],
  ["Remote intern roles", "Three demo founders list remote or intern roles: Pebble Learning, Cinder and Orbit Notes."],
  ["Outreach angle for fintech", "Lead with a concrete project: describe a payments or data-heavy UI you shipped, then offer one specific improvement for their product."],
  ["Cold email to Lattice Pay", "Draft: Hi Asha, I build data-heavy interfaces in React and TypeScript and noticed Lattice Pay is hiring. Could I send a short note on how I would approach your dashboard?"],
  ["Resume bullet rewrite", "Try: Cut dashboard render time 40% by virtualising tables and moving filtering off the main thread."],
  ["Interview prep: system design", "Practise: design a rate limiter, a notification service and a feed. Time-box each to 40 minutes."],
  ["Salary negotiation", "Anchor on the range, cite market data and negotiate the whole package, not only base."],
  ["Portfolio feedback", "Lead with three projects, add outcomes to each, and put contact links above the fold."],
  ["Follow-up after interview", "Send a short thank-you within 24 hours that references one specific topic from the conversation."],
  ["Weekly job-search plan", "Mon: shortlist 10 roles. Tue to Thu: tailor and apply to 5. Fri: follow up and review the tracker."],
];

export const CONVERSATIONS = TOPICS.map(([title, reply], i) => ({
  id: `conv_${i + 1}`,
  title,
  mode: i % 2 ? "ask" : "agent",
  updatedAt: t(i),
  messages: [
    { id: `m_${i}_u`, role: "user", content: title, at: t(i) },
    { id: `m_${i}_a`, role: "assistant", content: reply, at: t(i), demo: true },
  ],
}));
