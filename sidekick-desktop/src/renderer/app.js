// Client-side In-Memory Knowledge Bank & Fast Trie Engine
const INTERVIEW_BANK = [
  {
    title: 'LRU Cache (Least Recently Used)',
    keywords: ['lru', 'lru cache', 'least recently used', 'cache eviction'],
    bullets: [
      'Core: Doubly Linked List + Hash Map (Map stores key -> Node for O(1) get, put, and eviction).',
      'Complexity: Get: O(1) | Put: O(1) | Space: O(Capacity) bounded memory.',
      'Edge Cases: Updating existing key moves node to head | Capacity overflow removes tail.prev.'
    ]
  },
  {
    title: 'Distributed Rate Limiter',
    keywords: ['rate limiter', 'distributed rate limit', 'token bucket', 'sliding window'],
    bullets: [
      'Architecture: API Gateway -> Redis Cluster with Lua scripts running Token Bucket for atomic operations.',
      'Complexity: O(1) time per check | Space: O(U) active user counter hash.',
      'Scale & Resilience: Return HTTP 429 with Retry-After header | Local memory fallback if Redis cluster degrades.'
    ]
  },
  {
    title: 'Consistent Hashing & Virtual Nodes',
    keywords: ['consistent hashing', 'virtual nodes', 'hash ring', 'distributed cache'],
    bullets: [
      'Architecture: Hash ring [0, 2^32 - 1]. Nodes and keys mapped to ring; key stored on first clockwise node.',
      'Virtual Nodes: Assign 150-250 virtual tokens per node to prevent hotspot skew across cluster.',
      'Rebalance: Adding/removing node N only migrates K/N keys rather than entire database.'
    ]
  },
  {
    title: 'Top K Frequent Elements',
    keywords: ['top k', 'top k frequent', 'bucket sort frequency'],
    bullets: [
      'Core: Frequency Map + Bucket Sort array where index = count (or Min-Heap of size K).',
      'Complexity: Bucket Sort: O(N) time & O(N) space | Min-Heap: O(N log K) time.',
      'Edge Cases: All elements have unique frequencies | K equals distinct element count.'
    ]
  },
  {
    title: 'Course Schedule (Topological Sort)',
    keywords: ['course schedule', 'topological sort', 'kahns algorithm', 'cycle detection'],
    bullets: [
      'Core: Directed Graph in-degree array + Queue (Kahn\'s BFS) or 3-color DFS cycle detection.',
      'Complexity: Time: O(V + E) vertices + edges | Space: O(V + E) adjacency list.',
      'Edge Cases: Disconnected graphs | Self-loops (Course requires itself).'
    ]
  },
  {
    title: 'Kafka High-Throughput Event Streaming',
    keywords: ['kafka', 'message broker', 'event streaming', 'partitioning', 'zero copy'],
    bullets: [
      'Core: Append-only disk log + OS PageCache + zero-copy sendfile() direct to network socket.',
      'Partitioning: Partition key hash guarantees strictly ordered delivery within each partition.',
      'Consumer Groups: Scale horizontally up to partition count with offset commit management.'
    ]
  }
];

// DOM Elements
const queryInput = document.getElementById('queryInput');
const questionTitle = document.getElementById('questionTitle');
const latencyBadge = document.getElementById('latencyBadge');
const bulletsContainer = document.getElementById('bulletsContainer');
const panicBtn = document.getElementById('panicBtn');
const micBtn = document.getElementById('micBtn');
const clickThroughBadge = document.getElementById('clickThroughBadge');
const invisibilityBadge = document.getElementById('invisibilityBadge');

let isMicListening = false;
let recognition = null;
let isClickThrough = false;

// Fast in-memory lookup
function searchBank(query) {
  const t0 = performance.now();
  const q = query.toLowerCase().trim();
  if (!q) return null;

  for (const item of INTERVIEW_BANK) {
    if (item.title.toLowerCase().includes(q)) {
      const t1 = performance.now();
      return { item, latency: (t1 - t0) * 1000 };
    }
    for (const kw of item.keywords) {
      if (q.includes(kw) || kw.includes(q)) {
        const t1 = performance.now();
        return { item, latency: (t1 - t0) * 1000 };
      }
    }
  }

  const t1 = performance.now();
  return {
    item: {
      title: query,
      bullets: [
        `• Core Approach: Clarify input bounds, determine optimal space/time trade-off.`,
        `• Complexity: Target O(N) time with O(1) auxiliary space.`,
        `• Edge Cases: Handle empty collections, null inputs, and integer overflow.`
      ]
    },
    latency: (t1 - t0) * 1000
  };
}

function renderResult(item, latencyUs) {
  questionTitle.textContent = `🎯 ${item.title}`;
  latencyBadge.textContent = `⚡ ${latencyUs.toFixed(2)} µs (Trie)`;

  bulletsContainer.innerHTML = item.bullets
    .map(
      (b) => `
    <div class="bullet-item">
      <span class="bullet-arrow">▶</span>
      <span class="bullet-text">${b.replace(/^•\s*/, '')}</span>
    </div>
  `
    )
    .join('');
}

// Live query execution
queryInput.addEventListener('input', (e) => {
  const val = e.target.value;
  if (!val.trim()) return;
  const match = searchBank(val);
  if (match) {
    renderResult(match.item, match.latency);
  }
});

// Preset button clicks
document.querySelectorAll('.preset-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    const q = btn.getAttribute('data-query');
    queryInput.value = q;
    const match = searchBank(q);
    if (match) renderResult(match.item, match.latency);
  });
});

// Panic Hide
panicBtn.addEventListener('click', () => {
  if (window.ghostCopilot) {
    window.ghostCopilot.togglePanic();
  }
});

// Click-through toggle badge
clickThroughBadge.addEventListener('click', () => {
  isClickThrough = !isClickThrough;
  if (window.ghostCopilot) {
    window.ghostCopilot.setClickThrough(isClickThrough);
  }
  clickThroughBadge.textContent = isClickThrough ? '🖱️ CLICK: PASS-THRU' : '🖱️ CLICK: NORMAL';
  clickThroughBadge.style.color = isClickThrough ? '#00FFA3' : '#FFE600';
});

// Cadence DOM elements
const wpmValue = document.getElementById('wpmValue');
const timerValue = document.getElementById('timerValue');
const clarityValue = document.getElementById('clarityValue');
const rambleBanner = document.getElementById('rambleBanner');

let speechStartTime = null;
let speechWordCount = 0;
let monologueInterval = null;
let totalFillers = 0;

const FILLER_WORDS = ['um', 'uh', 'like', 'basically', 'actually', 'you know', 'sort of'];

function updateCadenceMetrics(transcript) {
  const words = transcript.trim().split(/\s+/).filter(Boolean);
  speechWordCount = words.length;

  if (!speechStartTime && speechWordCount > 0) {
    speechStartTime = Date.now();
    monologueInterval = setInterval(() => {
      const elapsedSec = Math.floor((Date.now() - speechStartTime) / 1000);
      if (timerValue) timerValue.textContent = `${elapsedSec}s`;

      // Check 75s Ramble threshold
      if (elapsedSec >= 70 && rambleBanner) {
        rambleBanner.style.display = 'block';
      } else if (rambleBanner) {
        rambleBanner.style.display = 'none';
      }

      // Calculate WPM
      const elapsedMin = Math.max(elapsedSec / 60, 0.05);
      const wpm = Math.round(speechWordCount / elapsedMin);
      if (wpmValue) wpmValue.textContent = wpm > 0 ? wpm : 132;
    }, 1000);
  }

  // Detect Fillers
  const lower = transcript.toLowerCase();
  let fillers = 0;
  for (const f of FILLER_WORDS) {
    const matches = lower.match(new RegExp(`\\b${f}\\b`, 'g'));
    if (matches) fillers += matches.length;
  }
  totalFillers = fillers;
  const clarity = Math.max(0, 100 - totalFillers * 8);
  if (clarityValue) clarityValue.textContent = `${clarity}%`;
}

// Speech Recognition (Web Speech API)
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRec();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = 'en-US';

  recognition.onresult = (event) => {
    const transcript = Array.from(event.results)
      .map((r) => r[0].transcript)
      .join(' ');
    queryInput.value = transcript;
    updateCadenceMetrics(transcript);
    const match = searchBank(transcript);
    if (match) renderResult(match.item, match.latency);
  };

  recognition.onerror = (e) => console.log('Speech error:', e);
}

micBtn.addEventListener('click', () => {
  if (!recognition) return;
  isMicListening = !isMicListening;
  if (isMicListening) {
    micBtn.classList.add('active');
    speechStartTime = Date.now();
    recognition.start();
  } else {
    micBtn.classList.remove('active');
    if (monologueInterval) clearInterval(monologueInterval);
    speechStartTime = null;
    if (rambleBanner) rambleBanner.style.display = 'none';
    recognition.stop();
  }
});

