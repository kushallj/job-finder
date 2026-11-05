// DEMO DATA: fictional applications used to show the tracker. Not read from any inbox.
export const STAGES = [
  { id: "applied", label: "Applied", dot: "#2685E8" },
  { id: "interview", label: "Interview", dot: "#EBAA20" },
  { id: "offer", label: "Offer", dot: "#13A875" },
  { id: "rejected", label: "Rejected", dot: "#DC4C5C" },
  { id: "ghosted", label: "Ghosted", dot: "#707070" },
];

const COMPANIES = ["Tessellate", "Quarry Cloud", "Kavach Security", "Kestrel AI", "Vidyut Labs", "Willow Payments", "Aarna Health", "Mosaic Retail", "Meridian Retail", "Neelam Systems"];
const ROLES = ["Frontend Engineer", "Backend Engineer", "Platform Engineer", "Data Engineer", "ML Engineer", "Full Stack Engineer", "SRE", "Product Engineer"];
const SUBJECTS = {
  applied: ["We received your application", "Application confirmation", "Thanks for applying"],
  interview: ["Interview invitation", "Next steps for your application", "Scheduling your technical round"],
  offer: ["Your offer from", "Offer letter attached"],
  rejected: ["Update on your application", "We went with another candidate", "Regarding your application"],
  ghosted: ["Application received"],
};
const DIST = ["applied", "applied", "applied", "applied", "applied", "applied", "applied", "applied", "interview", "interview", "interview", "interview", "offer", "offer", "rejected", "rejected", "rejected", "rejected", "ghosted", "ghosted"];
const slug = (s) => s.toLowerCase().replace(/[^a-z]/g, "");

export const APPLICATIONS = Array.from({ length: 30 }, (_, i) => {
  const stage = DIST[i % DIST.length];
  const company = COMPANIES[i % COMPANIES.length];
  const subj = SUBJECTS[stage][i % SUBJECTS[stage].length];
  return {
    id: `app_${i + 1}`,
    company,
    position: ROLES[(i * 3) % ROLES.length],
    stage,
    subject: stage === "offer" && subj.endsWith("from") ? `${subj} ${company}` : subj,
    sender: `talent@${slug(company)}.example`,
    date: new Date(Date.UTC(2026, 9, 31 - i, 14, 0)).toISOString(),
    messages: (i % 3) + 1,
    notes: i % 4 === 0 ? "Followed up with recruiter." : "",
    events: stage === "interview" ? [{ id: `ev_${i}`, title: "Technical round", at: "2026-11-05T10:30" }] : [],
    offer: stage === "offer" ? { salary: "₹38L", deadline: "2026-11-15" } : null,
    source: "demo",
  };
});
