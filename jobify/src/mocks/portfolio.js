// DEMO DATA: placeholder portfolio.
export const PORTFOLIO = {
  status: "draft",
  username: "",
  identity: {
    fullName: "Alex Demo",
    firstName: "Alex",
    jobTitle: "Senior Software Engineer",
    tagline: "I build data-heavy interfaces that stay fast",
    bio: "Eight years across fintech and developer tooling, mostly on the parts of the stack where rendering performance and correctness meet. I like small teams, written decisions, and benchmarks that run in CI.",
    introLabels: "Senior engineer focused on web performance, Currently building retrieval tooling",
    skills: ["typescript", "react", "python", "postgres", "docker", "vite"],
  },
  contact: { email: "alex@demo.jobify.example", website: "https://example.com/alex", calendar: "", resume: "https://example.com/resume.pdf" },
  projects: [
    { id: "p1", title: "Gridline", subtitle: "https://example.com/gridline", description: "Virtualised data grid handling 1M rows." },
    { id: "p2", title: "Benchbot", subtitle: "https://example.com/benchbot", description: "CI benchmark runner with regression alerts." },
    { id: "p3", title: "Pocketbook", subtitle: "https://example.com/pocketbook", description: "Offline-first expense tracker." },
  ],
  experience: [
    { id: "e1", title: "Senior Engineer", subtitle: "Fintech Co (demo) · 2022 – Present", description: "Led the dashboard platform team." },
    { id: "e2", title: "Engineer", subtitle: "DevTools Inc (demo) · 2019 – 2022", description: "Built the CLI and web console." },
    { id: "e3", title: "Intern", subtitle: "Startup (demo) · 2018", description: "Shipped the onboarding flow." },
  ],
  education: [{ id: "ed1", title: "B.Tech Computer Science", subtitle: "Demo University · 2014 – 2018", description: "" }],
  hacks: [],
  research: [],
  socials: { github: "", linkedin: "", x: "" },
  custom: [],
  sources: { resume: "2026-10-29", github: null },
};
