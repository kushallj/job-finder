# React Frontend Architecture Plan

## 1. Information Gathered

### Backend API Structure (FastAPI)
- **Base URL**: `http://localhost:8000`
- **Authentication**: None (development mode)
- **CORS**: Enabled for all origins

### Key API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/api/health` | Detailed health with subsystem status |
| POST | `/run-query` | Full pipeline: fetch → store → AI process |
| POST | `/api/contacts/search` | Search contacts by company |
| POST | `/api/outreach/send` | Send outreach email |
| POST | `/api/outreach/followup` | Send follow-up email |
| GET | `/api/jobs/pending-outreach` | Get jobs pending outreach |
| GET | `/api/stats` | Get outreach statistics |

### Database Models
- **Job**: id, job_id, title, company, location, description, url, source, posted_date, fetched_at
- **Application**: id, job_id, match_score, skills_matched, skills_missing, resume_version, cover_letter, status
- **Contact**: id, name, title, email, company, department, confidence_score, source
- **OutreachRecord**: id, contact_id, job_id, subject, body, status, sent_at, replied_at, follow_up_count

---

## 2. Frontend Architecture Design

### Technology Stack
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **State Management**: React Query (server state) + Zustand (client state)
- **Routing**: React Router v6
- **UI Framework**: Material UI (MUI) v5
- **HTTP Client**: Axios
- **Form Handling**: React Hook Form + Zod validation

### Project Structure (Clean Architecture)
```
src/
├── api/                    # API layer (Axios instances, API calls)
│   ├── axios.ts           # Base axios configuration
│   ├── endpoints/         # API endpoint functions
│   │   ├── jobs.ts
│   │   ├── contacts.ts
│   │   ├── outreach.ts
│   │   └── stats.ts
│   └── types/             # API response types
│
├── components/            # Reusable UI components
│   ├── common/           # Generic components (Button, Card, Input)
│   ├── layout/           # Layout components (Sidebar, Header)
│   └── features/         # Feature-specific components
│       ├── jobs/
│       ├── contacts/
│       ├── outreach/
│       └── stats/
│
├── features/             # Feature-based modules (/domain-driven)
│   ├── jobs/            # Job listing, details, search
│   ├── contacts/        # Contact management
│   ├── outreach/        # Email outreach campaigns
│   ├── stats/           # Dashboard statistics
│   └── settings/        # App settings
│
├── hooks/               # Custom React hooks
│   ├── useJobs.ts
│   ├── useContacts.ts
│   ├── useOutreach.ts
│   └── useStats.ts
│
├── pages/               # Route pages
│   ├── Dashboard.tsx
│   ├── Jobs.tsx
│   ├── JobDetails.tsx
│   ├── Contacts.tsx
│   ├── Outreach.tsx
│   ├── Stats.tsx
│   └── Settings.tsx
│
├── stores/              # Zustand stores
│   ├── useAuthStore.ts
│   ├── useUIStore.ts
│   └── useFilterStore.ts
│
├── theme/               # MUI theme configuration
│   └── index.ts
│
├── utils/               # Utility functions
│   ├── formatters.ts
│   └── validators.ts
│
├── App.tsx
└── main.tsx
```

### Design Principles Applied

1. **SOLID Principles**:
   - **S**: Single Responsibility - Each component/hook has one purpose
   - **O**: Open/Closed - Components extendable via props/children
   - **L**: Liskov Substitution - Interface-based component hierarchies
   - **I**: Interface Segregation - Focused hooks and types
   - **D**: Dependency Inversion - API layer abstracted from components

2. **Clean Architecture Layers**:
   - **UI Layer**: React components, pages
   - **Business Logic**: Custom hooks, Zustand stores
   - **Data Layer**: API calls, React Query cache

3. **Feature-Based Organization**:
   - Each feature (jobs, contacts, outreach) is self-contained
   - Easy to add/remove features
   - Colocated related code

---

## 3. Implementation Plan

### Phase 1: Project Setup
- [ ] Initialize Vite + React + TypeScript project
- [ ] Install dependencies (MUI, React Query, Zustand, React Router, Axios)
- [ ] Configure MUI theme (custom colors matching job finder brand)
- [ ] Set up project folder structure

### Phase 2: API Layer
- [ ] Create Axios base instance with interceptors
- [ ] Implement API endpoint functions
- [ ] Create TypeScript interfaces for all data models
- [ ] Set up React Query provider and query client

### Phase 3: Layout & Navigation
- [ ] Create app shell with sidebar navigation
- [ ] Implement responsive header with actions
- [ ] Set up React Router with protected routes
- [ ] Add loading skeletons and error boundaries

### Phase 4: Core Features
- [ ] **Dashboard**: Stats overview, recent activity, quick actions
- [ ] **Jobs**: List view with filters, search, job details modal
- [ ] **Contacts**: Contact list, company filtering, contact details
- [   ] **Outreach**: Campaign management, email composition, send跟踪
- [ ] **Stats**: Charts, metrics, export functionality

### Phase 5: Polish & Performance
- [ ] Add loading states and error handling
- [ ] Implement optimistic updates
- [ ] Add caching strategies
- [ ] Performance optimization (memo, code splitting)

---

## 4. Key UI/UX Features

### Dashboard
- Summary cards (total jobs, contacts, outreach attempts, success rate)
- Recent activity feed
- Quick action buttons (Fetch Jobs, Run Outreach, View Stats)
- Mini charts for trends

### Jobs Page
- Search bar with instant filtering
- Filter chips (source, date, match score)
- Sortable table/grid view
- Job details drawer with match score visualization
- One-click outreach action

### Contacts Page
- Searchable contact list
- Company grouping
- Confidence score indicators
- Email copy functionality

### Outreach Page
- Campaign creation wizard
- Email template editor
- Preview mode
- Send/dry-run toggle
- Delivery tracking

### Stats Page
- Key metrics cards
- Bar/line charts for trends
- Status breakdown pie chart
- Export to CSV/Excel

---

## 5. API Integration Details

### Job Query Flow
```
User enters query → POST /run-query → 
Loading state → Fetch jobs → AI processing →
Update UI with new jobs + match scores
```

### Outreach Flow
```
Select job → Choose contact → Compose email →
POST /api/outreach/send → Track status →
Update outreach records
```

---

## 6. Follow-up Steps

1. **User confirms plan** → Proceed with Phase 1 (project setup)
2. **Install dependencies** → Create folder structure
3. **Implement API layer** → Build all endpoints
4. **Create layout** → Navigation, header, routing
5. **Build features** → Page by page implementation
6. **Test integration** → Verify backend connectivity

---

## Dependencies to Install
```json
{
  "dependencies": {
    "@emotion/react": "^11.x",
    "@emotion/styled": "^11.x",
    "@mui/material": "^5.x",
    "@mui/icons-material": "^5.x",
    "@tanstack/react-query": "^5.x",
    "zustand": "^4.x",
    "react-router-dom": "^6.x",
    "axios": "^1.x",
    "react-hook-form": "^7.x",
    "zod": "^3.x",
    "@hookform/resolvers": "^3.x",
    "recharts": "^2.x",
    "date-fns": "^3.x"
  }
}
```

