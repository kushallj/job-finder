"""
question_bank_syncer.py — Ingests and synchronizes real-world interview question banks
from Google Sheets, CSVs, and remote spreadsheets into the AI Interviewer and Ghost Copilot engines.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger("question_bank_syncer")

DEFAULT_GOOGLE_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/1uJ8zyFyubiq_H50SxLXZ0HM0bviyOQ6m41ySlQhd0D8/export?format=csv"
)

# Standardized category mapping
CATEGORY_MAP = {
    "javascript": "JavaScript & Core Web",
    "node.js": "Node.js & Backend Architecture",
    "nodejs": "Node.js & Backend Architecture",
    "react": "React.js & Frontend State",
    "react.js": "React.js & Frontend State",
    "next.js": "Next.js & Full-Stack SSR",
    "nextjs": "Next.js & Full-Stack SSR",
    "typescript": "TypeScript & Type Safety",
    "html/css": "HTML5, CSS3 & Responsive UI",
    "mongodb": "MongoDB & NoSQL Data Modeling",
    "sql": "SQL, PostgreSQL & Relational DBs",
    "database": "Database Architecture & Storage",
    "architecture": "Distributed System Architecture",
    "aws": "AWS Cloud & Serverless Infrastructure",
    "devops": "DevOps, CI/CD & Containers",
    "dsa": "Algorithms & Problem Solving",
    "scenario base": "Behavioral, Leadership & Scenarios",
    "other": "General Software Engineering",
}


class QuestionBankSyncer:
    """Synchronizes, parses, and ingests question banks into Trie, RAG, and AI Interviewer."""

    def __init__(self, bank_json_path: Optional[str] = None):
        if not bank_json_path:
            bank_json_path = os.path.join(
                os.path.dirname(__file__), "..", "sidekick", "knowledge", "interview_bank.json"
            )
        self.bank_json_path = os.path.abspath(bank_json_path)

    async def fetch_sheet_csv(self, url: str = DEFAULT_GOOGLE_SHEET_URL) -> str:
        """Downloads CSV data from a published or shareable Google Sheet URL."""
        csv_url = url
        if "docs.google.com/spreadsheets" in url and "/export" not in url:
            # Extract sheet ID
            match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
            if match:
                sheet_id = match.group(1)
                csv_url = f"https://docs.google.com/spreadsheets/d/sheet_id/export?format=csv".replace("sheet_id", sheet_id)

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(csv_url)
            resp.raise_for_status()
            return resp.text

    def parse_csv_rows(self, csv_content: str) -> List[Dict[str, Any]]:
        """Parses CSV rows into clean question definitions."""
        rows = []
        reader = csv.reader(io.StringIO(csv_content))
        header = None

        for line in reader:
            if not line or not any(line):
                continue
            if header is None:
                header = [h.strip().lower() for h in line]
                continue

            q_text = line[0].strip() if len(line) > 0 else ""
            tech = line[1].strip() if len(line) > 1 else "General"
            simple_exp = line[2].strip() if len(line) > 2 else ""

            if not q_text or len(q_text) < 3 or q_text in ["0", "Question"]:
                continue

            # Clean tech category
            cat_key = tech.lower().strip()
            category = CATEGORY_MAP.get(cat_key, tech.title() or "Technical Concept")

            # Extract keywords for Radix Trie and BM25 index
            keywords = self._extract_keywords(q_text, tech)

            # Synthesize 3 concise, glanceable teleprompter bullets
            bullets = self._synthesize_bullets(q_text, category, simple_exp)

            rows.append({
                "id": re.sub(r"[^a-zA-Z0-9_]+", "_", q_text[:40].lower()).strip("_"),
                "title": q_text,
                "keywords": keywords,
                "category": category,
                "technology": tech,
                "bullets": bullets,
                "simple_explanation": simple_exp,
            })

        return rows

    def _extract_keywords(self, question: str, tech: str) -> List[str]:
        """Generates search keywords and synonyms for instant Trie matching."""
        clean = re.sub(r"[^\w\s]", " ", question.lower())
        words = [w for w in clean.split() if len(w) > 2]
        
        keywords = [question.lower()]
        # Add tech keyword
        if tech.lower() not in keywords:
            keywords.append(tech.lower())
        
        # Add 2-word and 3-word n-grams
        for i in range(len(words) - 1):
            keywords.append(f"{words[i]} {words[i+1]}")
        for i in range(len(words) - 2):
            keywords.append(f"{words[i]} {words[i+1]} {words[i+2]}")

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for kw in keywords:
            if kw not in seen and len(kw) > 2:
                seen.add(kw)
                deduped.append(kw)
        return deduped[:8]

    def _synthesize_bullets(self, question: str, category: str, simple_exp: str) -> List[str]:
        """Creates 3 high-impact glanceable bullets for teleprompter display."""
        if simple_exp and len(simple_exp) > 20:
            # If a human explanation was provided in the sheet, format into 3 bullet points
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", simple_exp) if s.strip()]
            if len(sentences) >= 3:
                return sentences[:3]
            elif len(sentences) == 2:
                return [sentences[0], sentences[1], f"Key Takeaway: Best practice approach in modern {category} architectures."]
            else:
                return [sentences[0], f"Architecture & Implementation: Standard pattern used in {category} applications.", "Trade-off / Optimization: Benchmark latency and handle boundary conditions."]

        # Smart domain-aware bullet synthesis based on keywords
        q_lower = question.lower()
        if "closure" in q_lower:
            return [
                "Definition: Function bundled with its lexical environment, allowing access to outer scope variables even after execution.",
                "Use Cases: Data privacy/encapsulation (module pattern), memoization caches, and function currying/partial application.",
                "Caution: Beware of memory leaks if closures retain unnecessary large object references in long-lived event listeners."
            ]
        elif "event loop" in q_lower:
            return [
                "Mechanism: Single-threaded coordinator continuously moving ready callbacks from microtask/macrotask queues to call stack.",
                "Priority Order: Call Stack -> process.nextTick() -> Promise Microtasks -> Timer Macrotasks (setTimeout) -> I/O Polling -> setImmediate.",
                "Optimization: Never block the event loop with CPU-heavy loops; offload compute to Worker Threads or Child Processes."
            ]
        elif "hoisting" in q_lower:
            return [
                "Mechanism: JavaScript engine's memory creation phase moves variable and function declarations to the top of their scope.",
                "var vs let/const: `var` is initialized with `undefined`; `let` and `const` are hoisted into Temporal Dead Zone (TDZ) and throw ReferenceError.",
                "Function Hoisting: Function declarations are fully hoisted; function expressions / arrow functions act according to their variable declaration."
            ]
        elif "promise" in q_lower or "async" in q_lower:
            return [
                "Pattern: Asynchronous control flow returning Pending, Fulfilled, or Rejected states.",
                "Combinators: `Promise.all` (fast-fail) vs `Promise.allSettled` (waits for all outcomes) vs `Promise.race` (first finished).",
                "Best Practice: Always handle errors with try/catch in async-await to prevent unhandled promise rejections."
            ]
        elif "kafka" in q_lower:
            return [
                "Architecture: Distributed commit log with topics partitioned across brokers for horizontal scalability and sequential disk I/O.",
                "Consumer Groups: Parallel consumption partitioned by key hash; offset commits provide At-Least-Once or Exactly-Once semantics.",
                "Microservice Role: Decouples async service communication, buffers traffic spikes, and powers event-driven CQRS architectures."
            ]
        elif "sharding" in q_lower or "partition" in q_lower:
            return [
                "Strategy: Horizontal database partitioning across multiple nodes using Hash-based, Range-based, or Directory Shard Keys.",
                "Routing: Stateless Shard Proxy (e.g. Vitess, Citus) calculates target shard hash to eliminate monolithic single-point bottlenecks.",
                "Trade-offs: Beware of cross-shard joins and distributed transactions; co-locate related entities on same shard."
            ]
        elif "lambda" in q_lower or "serverless" in q_lower:
            return [
                "Architecture: Ephemeral, stateless compute executing in microVMs (AWS Firecracker) triggered by events (API GW, SQS, S3).",
                "Cold Starts: Mitigate via Provisioned Concurrency, small deployment packages, and connection pooling outside handler scope.",
                "Best Practice: Keep functions single-purpose, manage DB connections with RDS Proxy, and set execution timeouts."
            ]
        elif "jwt" in q_lower or "token" in q_lower or "auth" in q_lower:
            return [
                "Structure: Base64-encoded Header (alg), Payload (claims), and Signature verified with HMAC-SHA256 or RSA public/private key.",
                "Storage & Security: Store access tokens in memory / secure HttpOnly cookies with SameSite=Strict to mitigate XSS and CSRF.",
                "Refresh Flow: Short-lived Access Token (15m) + Long-lived Refresh Token stored securely with token rotation and revocation list."
            ]
        elif "index" in q_lower:
            return [
                "Structure: B-Tree / LSM-Tree data structures pointing to row pointers to turn O(N) full table scans into O(log N) searches.",
                "Compound Indexes: Follow the Leftmost Prefix Rule (e.g., index on [tenant_id, created_at] accelerates queries filtering by tenant).",
                "Trade-off: Speeds up SELECT reads but introduces write amplification on INSERT/UPDATE operations."
            ]
        elif "useeffect" in q_lower or "usememo" in q_lower or "usecallback" in q_lower or "hook" in q_lower:
            return [
                "useMemo vs useCallback: `useMemo` caches the calculated return value; `useCallback` caches the function instance itself.",
                "Dependency Array: Must declare all referenced variables to avoid stale closures; empty array runs once on mount.",
                "Performance: Avoid premature optimization; use for expensive computations, referential equality in props, or subscriptions."
            ]
        elif "ssr" in q_lower or "next" in q_lower:
            return [
                "Rendering Strategies: SSR (Server-Side Rendering on demand) vs SSG (Static Site Generation at build) vs ISR (Incremental Static Regeneration).",
                "Benefits: Optimal SEO crawlability, fast First Contentful Paint (FCP), and direct access to server-side credentials/DBs.",
                "App Router: React Server Components (RSC) stream HTML zero-bundle-size by default, hydrating interactive client components as needed."
            ]
        elif "flex" in q_lower or "grid" in q_lower or "css" in q_lower:
            return [
                "Flexbox vs Grid: Flexbox is 1-dimensional (row OR column content flow); CSS Grid is 2-dimensional (rows AND columns layout system).",
                "Responsive Design: Use `grid-template-columns: repeat(auto-fit, minmax(280px, 1fr))` for fluid layouts without media queries.",
                "Performance: Prefer CSS transforms/opacity over top/left/width for 60fps GPU-accelerated animations."
            ]

        # General High-Impact Technical Response Template
        return [
            f"Core Concept: Address fundamental architectural mechanism for '{question[:55]}'.",
            f"Implementation & Complexity: Discuss time/space trade-offs, standard patterns in {category}, and production edge cases.",
            "Production Considerations: Highlight monitoring, error handling, backward compatibility, and graceful degradation."
        ]

    def sync_to_knowledge_bank(self, questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merges parsed questions into the main knowledge bank and updates Trie & RAG structures."""
        # Read existing bank if present
        existing_data: Dict[str, Any] = {"version": "2.2.0"}
        if os.path.exists(self.bank_json_path):
            try:
                with open(self.bank_json_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except Exception as e:
                logger.warning(f"Could not parse existing bank: {e}")

        # Group into structured categories
        dsa_list = existing_data.get("dsa_patterns", [])
        system_design_list = existing_data.get("system_design_archetypes", [])
        behavioral_list = existing_data.get("behavioral_star_matrix", [])
        custom_sheet_questions = []

        seen_titles = {item.get("title", "").lower() for item in (dsa_list + system_design_list + behavioral_list)}

        for q in questions:
            title_clean = q["title"].strip()
            if title_clean.lower() in seen_titles:
                continue

            item = {
                "id": q["id"],
                "keywords": q["keywords"],
                "title": q["title"],
                "category": q["category"],
                "technology": q.get("technology", "Technical"),
                "bullets": q["bullets"],
            }
            custom_sheet_questions.append(item)
            seen_titles.add(title_clean.lower())

        existing_data["sheet_question_bank"] = custom_sheet_questions
        existing_data["version"] = "2.2.0"

        # Save to disk
        os.makedirs(os.path.dirname(self.bank_json_path), exist_ok=True)
        with open(self.bank_json_path, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=2)

        # Also write a backup to data/
        data_backup_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "interview_question_bank.json")
        try:
            os.makedirs(os.path.dirname(data_backup_path), exist_ok=True)
            with open(data_backup_path, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=2)
        except Exception:
            pass

        total_questions = len(dsa_list) + len(system_design_list) + len(behavioral_list) + len(custom_sheet_questions)
        logger.info(f"✅ Ingested {len(custom_sheet_questions)} sheet questions. Total knowledge bank: {total_questions} questions.")

        return {
            "status": "success",
            "ingested_from_sheet": len(custom_sheet_questions),
            "total_questions": total_questions,
            "bank_path": self.bank_json_path,
        }

    async def run_sync_pipeline(self, sheet_url: str = DEFAULT_GOOGLE_SHEET_URL) -> Dict[str, Any]:
        """Full end-to-end pipeline: fetch -> parse -> ingest -> reload in-memory engines."""
        csv_text = await self.fetch_sheet_csv(sheet_url)
        questions = self.parse_csv_rows(csv_text)
        result = self.sync_to_knowledge_bank(questions)

        # Dynamically reload in-memory Sidekick engines if loaded
        try:
            from src.sidekick.api.sidekick_router import trie_engine, rag_engine
            trie_engine.load_from_json(self.bank_json_path)
            rag_engine.load_bank(self.bank_json_path)
            result["trie_keys_indexed"] = trie_engine.total_indexed_keys
            result["rag_documents_indexed"] = len(rag_engine.documents)
        except Exception as e:
            logger.warning(f"In-memory engine live reload skipped or failed: {e}")

        return result


question_bank_syncer = QuestionBankSyncer()
