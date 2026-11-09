// DEMO DATA: fictional startups and founders. No real people or contact details.
const ROWS = `Lattice Pay|latticepay.example|Bengaluru, India|India|Fintech|Payments infrastructure for small businesses.|1|Asha Menon:Founder/CEO;Rohan Iyer:Co-founder/CTO
Northbeam Labs|northbeam.example|San Francisco, USA|USA|Developer Tools|Observability for distributed systems.|1|Dana Whitfield:Founder/CEO
Kiln Health|kilnhealth.example|Pune, India|India|Healthtech|Clinic scheduling and records for tier-2 cities.|0|Imran Qureshi:Founder
Fernhill|fernhill.example|London, UK|UK|Climate|Carbon accounting for mid-size manufacturers.|1|Priya Nair:Founder/CEO;Tom Hargreaves:Co-founder
Okapi Logistics|okapi.example|Lagos, Nigeria|Nigeria|Logistics|Last-mile delivery routing across West Africa.|0|Chidi Eze:Founder/CEO
Sprig|sprig.example|Mumbai, India|India|Consumer|Meal planning that learns your pantry.|1|Neha Kulkarni:Founder
Halcyon AI|halcyon.example|New York, USA|USA|AI|Workflow agents for finance operations.|1|Marcus Bell:Founder/CEO;Lena Park:Founder/CTO
Tarn|tarn.example|Hyderabad, India|India|SaaS|Contract management for procurement teams.|0|Vikram Rao:Founder/CEO
Basil and Co|basilco.example|Bogotá, Colombia|Colombia|Consumer|Neighbourhood grocery delivery.|0|Camila Ortega:Founder;Diego Salas:Founder
Quill Systems|quill.example|Gurugram, India|India|HR Tech|Applicant tracking with structured interviews.|1|Sana Ahmed:Founder/CEO
Marlin|marlin.example|Singapore|Singapore|Fintech|Cross-border treasury for SMEs.|0|Wei Tan:Founder/CEO
Ridgeline|ridgeline.example|Chennai, India|India|Infrastructure|Edge compute for retail stores.|1|Karthik Subramanian:Founder/CTO
Pebble Learning|pebble.example|Remote|India|Edtech|Project-based coding courses.|1|Anjali Desai:Founder
Wren|wren.example|Berlin, Germany|Germany|Design Tools|Handoff tooling for product teams.|0|Jonas Keller:Founder/CEO
Copper Mile|coppermile.example|Austin, USA|USA|Mobility|Fleet charging software.|1|Alicia Moreno:Founder/CEO;Ben Ortiz:Co-founder
Saffron Labs|saffron.example|Bengaluru, India|India|AI|Speech models for Indian languages.|1|Meera Pillai:Founder/CEO
Atlas Grain|atlasgrain.example|Nairobi, Kenya|Kenya|Agritech|Crop storage financing for cooperatives.|0|Wanjiru Kamau:Founder
Orbit Notes|orbitnotes.example|Toronto, Canada|Canada|Productivity|Meeting notes that link to your tasks.|1|Sam Whitaker:Founder
Delta Forge|deltaforge.example|Mumbai, India|India|B2B|Procurement marketplace for metal fabrication.|0|Rahul Shetty:Founder/CEO
Cinder|cinder.example|Remote|USA|Security|Secrets management for small teams.|1|Noor Haddad:Founder/CEO;Eli Brandt:Founder
Juniper Bank|juniperbank.example|London, UK|UK|Fintech|Business accounts for freelancers.|0|Grace Okafor:Founder/CEO
Mosaic Farms|mosaicfarms.example|Pune, India|India|Agritech|Produce sourcing for restaurants.|0|Siddharth Joshi:Founder`;

const COLORS = ["#141414", "#2563EB", "#059669", "#DC2626", "#7C3AED", "#D97706", "#DB2777", "#0891B2"];
const initials = (n) => n.split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();

export const COMPANIES = ROWS.split("\n").map((row, i) => {
  const [name, site, location, country, industry, description, hiring, founders] = row.split("|");
  return {
    id: `co_${i + 1}`,
    name,
    website: `https://${site}`,
    location,
    country,
    industry,
    description,
    hiring: hiring === "1",
    color: COLORS[i % COLORS.length],
    founders: founders.split(";").map((f, j) => {
      const [fname, role] = f.split(":");
      return {
        id: `f_${i + 1}_${j}`,
        name: fname,
        initials: initials(fname),
        role,
        linkedin: "https://www.linkedin.com/",
        x: j === 0 ? "https://x.com/" : null,
      };
    }),
  };
});

export const FOUNDER_COUNTRIES = [...new Set(COMPANIES.map((c) => c.country))].sort();
export const FOUNDER_INDUSTRIES = [...new Set(COMPANIES.map((c) => c.industry))].sort();
export const UNLOCK_COST = 5;
