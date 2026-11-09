/**
 * Centralized Site Content & Copy for Jobify
 * Adheres to Aarivi information architecture and section requirements.
 */

export const SUPPORT_EMAIL = "support@jobify.app";

export const SITE_CONTENT = {
  brand: {
    name: "Jobify",
    tagline: "Job Search & Application Management",
    navCta: "Get Started",
    navSignIn: "Sign In",
  },

  hero: {
    eyebrow: "YOUR JOB SEARCH, ALL IN ONE PLACE",
    headline: "Your job search, all in one place.",
    subheadline: "Discover opportunities. Track applications. Move your career forward.",
    description:
      "Find relevant opportunities, organize every application, and manage your job search from one focused workspace.",
    primaryCta: {
      label: "Get Started",
      href: "/signup",
    },
    secondaryCta: {
      label: "Watch Demo",
      href: "/demo/chat",
    },
    // Illustrative demo application records for realistic dashboard preview
    demoApplications: [
      {
        id: "app-1",
        title: "Frontend Developer",
        company: "Acme Corp",
        companyInitials: "AC",
        companyBg: "#1E293B",
        location: "San Francisco, CA (Remote)",
        type: "Full-time",
        status: "Interview",
        statusVariant: "warning", // status warning color #D99A22
        appliedDate: "Oct 24",
        matchScore: "96%",
      },
      {
        id: "app-2",
        title: "Product Designer",
        company: "Linear Design",
        companyInitials: "LN",
        companyBg: "#5E6AD2",
        location: "New York, NY (Remote)",
        type: "Full-time",
        status: "Offer",
        statusVariant: "success", // status success color #238636
        appliedDate: "Oct 21",
        matchScore: "94%",
      },
      {
        id: "app-3",
        title: "Full Stack Developer",
        company: "Example Labs",
        companyInitials: "EL",
        companyBg: "#0F766E",
        location: "Austin, TX (Hybrid)",
        type: "Full-time",
        status: "Applied",
        statusVariant: "info",
        appliedDate: "Oct 28",
        matchScore: "89%",
      },
      {
        id: "app-4",
        title: "UI/UX Designer",
        company: "Studio North",
        companyInitials: "SN",
        companyBg: "#C026D3",
        location: "London, UK (Remote)",
        type: "Contract",
        status: "Review",
        statusVariant: "neutral",
        appliedDate: "Oct 29",
        matchScore: "92%",
      },
      {
        id: "app-5",
        title: "Data Analyst",
        company: "Example Analytics",
        companyInitials: "EA",
        companyBg: "#EA580C",
        location: "Chicago, IL (On-site)",
        type: "Full-time",
        status: "Applied",
        statusVariant: "info",
        appliedDate: "Oct 27",
        matchScore: "86%",
      },
    ],
    supportingCompanies: [
      { name: "Acme Corp", label: "Acme" },
      { name: "Linear", label: "Linear" },
      { name: "Stripe", label: "Stripe" },
      { name: "Figma", label: "Figma" },
      { name: "Notion", label: "Notion" },
      { name: "Vercel", label: "Vercel" },
    ],
  },

  categories: {
    eyebrow: "EXPLORE OPPORTUNITIES",
    heading: "Find every kind of role in one place.",
    description:
      "Discover opportunities across different industries, experience levels, and career paths.",
    chips: [
      { id: "ai", label: "AI Engineer", icon: "Bot", count: "340+ roles" },
      { id: "frontend", label: "Frontend Developer", icon: "Code", count: "820+ roles" },
      { id: "backend", label: "Backend Developer", icon: "Server", count: "750+ roles" },
      { id: "fullstack", label: "Full Stack Developer", icon: "Layers", count: "910+ roles" },
      { id: "product-designer", label: "Product Designer", icon: "Figma", count: "430+ roles" },
      { id: "ui-ux", label: "UI/UX Designer", icon: "Layout", count: "390+ roles" },
      { id: "data-analyst", label: "Data Analyst", icon: "BarChart3", count: "510+ roles" },
      { id: "data-scientist", label: "Data Scientist", icon: "Binary", count: "420+ roles" },
      { id: "devops", label: "DevOps Engineer", icon: "Cpu", count: "380+ roles" },
      { id: "mobile", label: "Mobile Developer", icon: "Smartphone", count: "310+ roles" },
      { id: "marketing", label: "Marketing", icon: "Megaphone", count: "290+ roles" },
      { id: "qa", label: "QA Engineer", icon: "CheckSquare", count: "240+ roles" },
      { id: "internships", label: "Internships", icon: "GraduationCap", count: "650+ roles" },
      { id: "remote", label: "Remote Jobs", icon: "Globe", count: "1,200+ roles" },
    ],
  },

  howItWorks: {
    eyebrow: "HOW IT WORKS",
    heading: "Find opportunities, stay organized, and get hired.",
    description: "One focused workspace for the important parts of your job search.",
    steps: [
      {
        id: "search",
        num: "01",
        label: "SEARCH",
        title: "Find relevant opportunities.",
        description:
          "Explore opportunities that align with your skills, interests, and career goals with clear filters.",
      },
      {
        id: "track",
        num: "02",
        label: "TRACK",
        title: "Manage every application.",
        description:
          "Keep track of applications, deadlines, interviews, and your progress in one organized workspace.",
      },
      {
        id: "prepare",
        num: "03",
        label: "PREPARE",
        title: "Get your applications ready.",
        description:
          "Keep your resume, profile, and application materials organized so you can apply with confidence.",
      },
      {
        id: "organize",
        num: "04",
        label: "STAY ORGANIZED",
        title: "Keep your job search moving.",
        description:
          "Stay on top of your next steps, upcoming interviews, and important follow-ups without spreadsheet chaos.",
      },
    ],
  },

  everythingYouNeed: {
    eyebrow: "ALSO INCLUDED",
    heading: "Everything you need to find opportunities and get hired.",
    description: "Bring your job search essentials together in one simple workspace.",
    cards: [
      {
        id: "card-1",
        eyebrow: "APPLICATION TRACKING",
        title: "Never lose track of an application.",
        description:
          "Organize the companies you've applied to and monitor each application's progress from submission to offer.",
        badge: "Status Pipeline",
      },
      {
        id: "card-2",
        eyebrow: "SMART JOB DISCOVERY",
        title: "Find roles that match your goals.",
        description:
          "Explore opportunities using relevant search filters, remote preferences, and curated job categories.",
        badge: "Keyword Filters",
      },
      {
        id: "card-3",
        eyebrow: "RESUME MANAGEMENT",
        title: "Get your resume ready.",
        description:
          "Keep your career profile and tailored application materials organized so you are always interview-ready.",
        badge: "Profile Kit",
      },
      {
        id: "card-4",
        eyebrow: "ORGANIZED FOLLOW-UPS",
        title: "Stay ready for what's next.",
        description:
          "Keep deadlines, interview dates, and next steps visible throughout your job search without manual reminders.",
        badge: "Milestones",
      },
    ],
  },

  pricing: {
    eyebrow: "SIMPLE PRICING",
    heading: "Choose the right plan for your job search.",
    description: "Start with the essentials and choose more support as your needs grow.",
    monthlyYearlyDiscount: "Save 20% on Annual",
    plans: [
      {
        id: "free",
        name: "Free",
        badge: "STARTER",
        description: "Everything you need to kickstart your organized job search.",
        monthlyPrice: 0,
        yearlyPrice: 0,
        period: "forever",
        ctaLabel: "Get Started Free",
        ctaHref: "/signup",
        isPopular: false,
        features: [
          "Job discovery & smart filters",
          "Basic application tracking (up to 15 active jobs)",
          "Single resume profile storage",
          "Application status updates",
          "Web browser access",
        ],
      },
      {
        id: "pro",
        name: "Pro",
        badge: "RECOMMENDED",
        description: "Unlimited tracking and preparation tools for active job seekers.",
        monthlyPrice: 9,
        yearlyPrice: 7, // $7/mo billed annually
        period: "per month",
        ctaLabel: "Start Pro Plan",
        ctaHref: "/signup?plan=pro",
        isPopular: true,
        features: [
          "Unlimited saved jobs & applications",
          "Advanced interview calendar & reminders",
          "Multiple resume & cover letter versions",
          "Application timeline & notes history",
          "Priority customer support",
          "Export applications to CSV",
        ],
      },
    ],
    disclaimer:
      "Prices shown are illustrative for the preview version. Free tier available upon signup.",
  },

  testimonials: {
    eyebrow: "CUSTOMER REVIEWS",
    heading: "What customers are saying.",
    description: "Real experiences from people using Jobify.",
    disclaimer: "Illustrative feedback from early preview community testers.",
    items: [
      {
        id: "t-1",
        quote:
          "Jobify replaced my messy spreadsheet within ten minutes. Seeing all my applications and interview stages in one clear view reduced my anxiety immensely.",
        name: "Alex Morgan",
        role: "Frontend Engineer",
        org: "Recent University Graduate",
        avatarInitials: "AM",
      },
      {
        id: "t-2",
        quote:
          "Applying to 40+ internship roles while studying was exhausting until I started using Jobify. The follow-up reminders made sure I never missed a recruiter call.",
        name: "Sarah Chen",
        role: "Product Design Student",
        org: "Internship Candidate",
        avatarInitials: "SC",
      },
      {
        id: "t-3",
        quote:
          "Simple, fast, and completely free of clutter. I could easily monitor which companies reached out for interviews and which ones were pending.",
        name: "David Kim",
        role: "Data Analyst",
        org: "Early Career Professional",
        avatarInitials: "DK",
      },
    ],
  },

  faq: {
    eyebrow: "FAQ",
    heading: "Frequently asked questions.",
    description: "Everything you need to know about using Jobify.",
    items: [
      {
        q: "What is Jobify?",
        a: "Jobify is a focused job-search and application management platform designed to help job seekers discover roles, track application statuses, organize resume materials, and prepare for interviews from a single workspace.",
      },
      {
        q: "How does Jobify help with my job search?",
        a: "Instead of juggling scattered spreadsheets, email threads, and multiple job boards, Jobify brings your search into one structured dashboard where you can see application progress, set reminders, and maintain candidate profiles.",
      },
      {
        q: "Can I track multiple job applications?",
        a: "Yes. You can track every application across customizable stages such as Saved, Applied, Interview, Offer, and Archived, along with interview dates, notes, and contact contacts.",
      },
      {
        q: "How can I find suitable opportunities?",
        a: "Jobify provides curated role categories, experience level tags, and remote filters to quickly discover roles that match your background and career goals.",
      },
      {
        q: "Is Jobify suitable for fresh graduates?",
        a: "Yes. Fresh graduates and career changers use Jobify to organize their high-volume initial application process and stay prepared for recruiter follow-ups.",
      },
      {
        q: "Can I use Jobify for internships?",
        a: "Yes. Jobify includes dedicated internship tracking filters and milestone checklists specifically tailored for seasonal recruiting cycles.",
      },
      {
        q: "Does Jobify offer a free plan?",
        a: "Yes. Jobify offers a permanent Free tier that includes core job discovery, basic application tracking, and profile storage.",
      },
      {
        q: "How can I contact support?",
        a: "You can reach out directly using the contact form below or email our support desk at support@jobify.app.",
      },
    ],
  },

  contact: {
    eyebrow: "GET IN TOUCH",
    heading: "Get in touch.",
    description:
      "Have a question or need help with your job search? Send us a message and our team will get back to you.",
    details: [
      { label: "Email Support", value: "support@jobify.app" },
      { label: "Response Time", value: "Within 24 business hours" },
      { label: "Location", value: "San Francisco, CA & Global Remote" },
    ],
  },

  finalCta: {
    heading: "Ready to start applying?",
    description:
      "Bring your job search into one place and take the next step in your career.",
    buttonLabel: "Get Started",
    buttonHref: "/signup",
  },

  footer: {
    wordmark: "Jobify",
    description:
      "A simpler way to discover opportunities, track applications, and manage your job search.",
    copyright: `© ${new Date().getFullYear()} Jobify. All rights reserved.`,
    linkGroups: [
      {
        title: "PRODUCT",
        links: [
          { label: "Features", href: "#how-it-works" },
          { label: "Job Categories", href: "#categories" },
          { label: "Pricing", href: "#pricing" },
          { label: "FAQ", href: "#faq" },
        ],
      },
      {
        title: "COMPANY",
        links: [
          { label: "About", href: "/about" },
          { label: "Contact", href: "#contact" },
          { label: "Blog", href: "/blog" },
        ],
      },
      {
        title: "ACCOUNT",
        links: [
          { label: "Sign In", href: "/signin" },
          { label: "Get Started", href: "/signup" },
        ],
      },
      {
        title: "LEGAL",
        links: [
          { label: "Privacy Policy", href: "/terms" },
          { label: "Terms of Service", href: "/terms" },
        ],
      },
    ],
  },
};
