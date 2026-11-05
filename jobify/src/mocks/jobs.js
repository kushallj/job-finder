// DEMO DATA: fictional companies and listings, not verified live jobs.
const ROWS = `Senior Frontend Engineer|Tessellate|Bengaluru, India|5–8 years|₹38L–₹52L|react,typescript,css|94|Hybrid|Full-time
Staff Backend Engineer|Quarry Cloud|Remote, India|8+ years|₹65L–₹85L|go,postgres,kafka|91|Remote|Full-time
Full Stack Engineer|Kavach Security|Hyderabad, India|3–4 years|₹30L–₹40L|typescript,node,react|89|Hybrid|Full-time
Machine Learning Engineer, Retrieval|Kestrel AI|Bengaluru, India|5–7 years|₹45L–₹60L|python,pytorch,faiss|88|Onsite|Full-time
Platform Engineer|Vidyut Labs|Pune, India|5–7 years|₹38L–₹52L|kubernetes,terraform,aws|86|Hybrid|Full-time
Frontend Intern|Tessellate|Bengaluru, India|Internship (6 months)|₹35K / month|react,typescript,html|85|Hybrid|Internship
Senior Product Engineer|Aarna Health|Pune, India|5–8 years|₹42L–₹55L|typescript,next,postgres|84|Hybrid|Full-time
Backend Intern|Quarry Cloud|Remote, India|Internship (6 months)|₹45K / month|go,postgres,docker|83|Remote|Internship
Backend Engineer, Payments|Willow Payments|Mumbai, India|3–5 years|₹28L–₹38L|java,spring,mysql|83|Hybrid|Full-time
Machine Learning Intern|Prayog AI|Bengaluru, India|Internship (6 months)|₹60K / month|python,pytorch,sql|82|Onsite|Internship
Senior Data Engineer|Mosaic Retail|Gurugram, India|5–8 years|₹45L–₹58L|sql,spark,airflow|82|Hybrid|Full-time
Frontend Engineer, Design Systems|Meridian Retail|Mumbai, India|3–5 years|₹26L–₹34L|react,typescript,storybook|81|Hybrid|Full-time
Site Reliability Engineer|Neelam Systems|Chennai, India|5–8 years|₹40L–₹52L|linux,kubernetes,prometheus|80|Onsite|Full-time
Software Engineering Intern|Vidyut Labs|Pune, India|Internship (6 months)|₹40K / month|react,typescript,node|79|Hybrid|Internship
Software Engineer I|Willow Payments|Mumbai, India|1–2 years|₹12L–₹18L|java,postgres,rest|79|Hybrid|Full-time
Security Engineer, Detection|Ironvale Security|Remote, India|5–7 years|₹32L–₹45L|python,linux,siem|78|Remote|Full-time
Junior Frontend Developer|Aarna Health|Pune, India|0–1 years|₹4.5L–₹7L|react,javascript,css|77|Hybrid|Full-time
Associate Software Engineer|Kestrel AI|Bengaluru, India|0–2 years|₹8L–₹12L|python,sql,flask|76|Onsite|Full-time
Mobile Engineer, Android|Vidyut Labs|Pune, India|3–5 years|₹24L–₹32L|kotlin,java,compose|76|Hybrid|Full-time
Software Engineer I|Kavach Security|Hyderabad, India|1–2 years|₹10L–₹16L|typescript,node,sql|75|Hybrid|Full-time
DevOps Engineer|Neelam Systems|Chennai, India|3–5 years|₹22L–₹30L|aws,terraform,docker|74|Hybrid|Full-time
Data Analyst|Mosaic Retail|Gurugram, India|1–3 years|₹9L–₹15L|sql,python,tableau|74|Onsite|Full-time
Product Designer|Meridian Retail|Mumbai, India|3–5 years|₹20L–₹30L|figma,prototyping,research|73|Hybrid|Full-time
Senior Software Engineer, Infrastructure|Harbor Systems|San Francisco, USA|6+ years|$180K–$230K|rust,go,kubernetes|72|Hybrid|Full-time
Full Stack Engineer|Lumen Works|Remote, USA|3–5 years|$140K–$175K|typescript,react,postgres|72|Remote|Full-time
Frontend Engineer|Foxglove Studio|London, UK|3–5 years|£65K–£85K|react,typescript,graphql|71|Hybrid|Full-time
Backend Engineer|Brightside Labs|London, UK|4–6 years|£75K–£95K|python,django,postgres|70|Hybrid|Full-time
Data Scientist|Orchard Analytics|New York, USA|3–5 years|$150K–$190K|python,sql,xgboost|70|Onsite|Full-time
ML Platform Engineer|Harbor Systems|Remote, USA|5–7 years|$170K–$210K|python,kubernetes,ray|69|Remote|Full-time
Software Engineering Intern|Lumen Works|Remote, USA|Internship (3 months)|$5K / month|react,node,sql|69|Remote|Internship
QA Automation Engineer|Kavach Security|Hyderabad, India|3–5 years|₹16L–₹24L|playwright,typescript,ci|68|Hybrid|Full-time
Engineering Manager|Tessellate|Bengaluru, India|9+ years|₹70L–₹95L|leadership,architecture,hiring|67|Hybrid|Full-time
Technical Writer|Quarry Cloud|Remote, India|2–4 years|₹14L–₹20L|docs,api,markdown|66|Remote|Full-time
iOS Engineer|Foxglove Studio|London, UK|3–5 years|£70K–£90K|swift,swiftui,xcode|66|Hybrid|Full-time
Cloud Engineer|Ironvale Security|Gurugram, India|3–5 years|₹24L–₹34L|azure,terraform,python|65|Hybrid|Full-time
Growth Engineer|Aarna Health|Remote, India|2–4 years|₹16L–₹24L|typescript,sql,analytics|64|Remote|Full-time
Data Engineering Intern|Mosaic Retail|Gurugram, India|Internship (6 months)|₹30K / month|sql,python,airflow|63|Hybrid|Internship
Solutions Engineer|Brightside Labs|London, UK|3–5 years|£60K–£80K|apis,sql,communication|62|Hybrid|Full-time
Rust Engineer|Harbor Systems|Remote, USA|4–6 years|$160K–$200K|rust,wasm,linux|61|Remote|Full-time
Embedded Software Engineer|Vidyut Labs|Pune, India|3–6 years|₹22L–₹32L|c++,rtos,linux|60|Onsite|Full-time
Analytics Engineer|Orchard Analytics|New York, USA|3–5 years|$140K–$170K|dbt,sql,python|60|Hybrid|Full-time
Design Engineer|Foxglove Studio|London, UK|2–4 years|£60K–£80K|react,css,motion|59|Hybrid|Full-time
Customer Success Engineer|Lumen Works|Remote, USA|2–4 years|$100K–$130K|apis,support,sql|58|Remote|Full-time`;

const COLORS = ["#141414", "#2563EB", "#059669", "#DC2626", "#7C3AED", "#D97706", "#DB2777", "#0891B2"];
const hash = (s) => [...s].reduce((a, c) => a + c.charCodeAt(0), 0);

export const JOBS = ROWS.split("\n").map((row, i) => {
  const [title, company, location, experience, salary, skills, match, workMode, type] = row.split("|");
  const skillList = skills.split(",");
  return {
    id: `job_${i + 1}`,
    title,
    company,
    companyColor: COLORS[hash(company) % COLORS.length],
    location,
    country: location.split(", ").pop(),
    experience,
    salary,
    skills: skillList,
    match: Number(match),
    workMode,
    type,
    postedDaysAgo: ((i * 3) % 28) + 1,
    description: `${company} is hiring a ${title} to work with ${skillList.slice(0, 3).join(", ")}. You will own features end to end, collaborate with a small cross-functional team and ship to production regularly. This is a demo listing used to show the Jobify interface.`,
    responsibilities: [
      "Design, build and ship production features",
      "Collaborate with product and design",
      "Improve reliability and performance",
      "Review code and mentor teammates",
    ],
  };
});

export const JOB_FILTER_OPTIONS = {
  workModes: ["Remote", "Hybrid", "Onsite"],
  types: ["Full-time", "Internship"],
  countries: [...new Set(JOBS.map((j) => j.country))].sort(),
  skills: [...new Set(JOBS.flatMap((j) => j.skills))].sort(),
};
