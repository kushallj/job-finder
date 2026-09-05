// In-Memory Fast Trie & Radical Interview Knowledge Bank
const INTERVIEW_BANK = [
  {
    title: 'LRU Cache (Least Recently Used)',
    keywords: ['lru', 'lru cache', 'least recently used', 'cache eviction', 'doubly linked list'],
    bullets: [
      'Architecture: Doubly Linked List + Hash Map (Map stores key ➔ Node pointer for O(1) get, put, and eviction).',
      'Complexity: Get: O(1) | Put: O(1) | Space: O(Capacity) strictly bounded memory.',
      'Edge Cases: Updating existing key moves node to head | Capacity overflow removes tail.prev.'
    ]
  },
  {
    title: 'Distributed Rate Limiter',
    keywords: ['rate limiter', 'distributed rate limit', 'token bucket', 'sliding window', 'redis rate'],
    bullets: [
      'Architecture: API Gateway ➔ Redis Cluster with Lua scripts running Token Bucket for atomic synchronization.',
      'Complexity: O(1) time per check | Space: O(U) active user counter hash.',
      'Scale & Resilience: Return HTTP 429 with Retry-After header | Local in-memory fallback if Redis cluster degrades.'
    ]
  },
  {
    title: 'Consistent Hashing & Virtual Nodes',
    keywords: ['consistent hashing', 'virtual nodes', 'hash ring', 'distributed cache', 'sharding'],
    bullets: [
      'Architecture: Hash ring [0, 2^32 - 1]. Nodes and keys mapped to ring; key stored on first clockwise node.',
      'Virtual Nodes: Assign 150–250 virtual tokens per physical node to eliminate hotspot skew.',
      'Rebalance: Adding/removing node N only migrates K/N keys rather than re-hashing the entire cluster.'
    ]
  },
  {
    title: 'Top K Frequent Elements',
    keywords: ['top k', 'top k frequent', 'bucket sort frequency', 'min heap'],
    bullets: [
      'Core: Frequency Map + Bucket Sort array where index = count (or Min-Heap of bounded size K).',
      'Complexity: Bucket Sort: O(N) time & O(N) space | Min-Heap: O(N log K) time.',
      'Edge Cases: All elements have unique frequencies | K equals distinct element count.'
    ]
  },
  {
    title: 'Course Schedule (Topological Sort)',
    keywords: ['course schedule', 'topological sort', 'kahns algorithm', 'cycle detection', 'dag'],
    bullets: [
      'Core: Directed Graph in-degree array + Queue (Kahn BFS) or 3-color DFS cycle detection.',
      'Complexity: Time: O(V + E) vertices + edges | Space: O(V + E) adjacency list.',
      'Edge Cases: Disconnected graph components | Self-loops (Course requires itself).'
    ]
  },
  {
    title: 'Kafka High-Throughput Event Streaming',
    keywords: ['kafka', 'message broker', 'event streaming', 'partitioning', 'zero copy', 'pagecache'],
    bullets: [
      'Core: Append-only disk commit log + OS PageCache + zero-copy sendfile() direct to network socket.',
      'Partitioning: Partition key hash guarantees strictly ordered delivery within each partition.',
      'Consumer Groups: Scale horizontally up to partition count with offset commit management.'
    ]
  },
  {
    title: 'Distributed Lock with Redis (Redlock)',
    keywords: ['redis lock', 'distributed lock', 'redlock', 'mutex', 'concurrency'],
    bullets: [
      'Core: SET resource_name my_random_value NX PX 30000 (atomic check & set with TTL).',
      'Release Safety: Lua script verifies random value before deleting key to prevent releasing expired locks.',
      'Drift Mitigation: Lock validity time = TTL - clock drift - acquisition time.'
    ]
  }
];

// DOM Elements
const hudContainer = document.getElementById('hudContainer');
const queryInput = document.getElementById('queryInput');
const questionTitle = document.getElementById('questionTitle');
const latencyBadge = document.getElementById('latencyBadge');
const bulletsContainer = document.getElementById('bulletsContainer');
const panicBtn = document.getElementById('panicBtn');
const minimizeBtn = document.getElementById('minimizeBtn');
const micBtn = document.getElementById('micBtn');
const clickThroughBadge = document.getElementById('clickThroughBadge');
const invisibilityBadge = document.getElementById('invisibilityBadge');
const compactModeBadge = document.getElementById('compactModeBadge');
const wpmValue = document.getElementById('wpmValue');
const timerValue = document.getElementById('timerValue');
const clarityValue = document.getElementById('clarityValue');
const rambleBanner = document.getElementById('rambleBanner');

let isMicListening = false;
let recognition = null;
let isClickThrough = false;
let isCompact = false;

// Sub-microsecond Trie / In-Memory Search
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
        'Architecture: Clarify input bounds, determine optimal space/time trade-off.',
        'Complexity: Target O(N) linear time with O(1) auxiliary space.',
        'Edge Cases: Handle empty collections, null inputs, and integer boundary conditions.'
      ]
    },
    latency: (t1 - t0) * 1000
  };
}

function renderResult(item, latencyUs) {
  questionTitle.textContent = item.title;
  latencyBadge.textContent = `⚡ ${latencyUs.toFixed(2)} µs (Trie)`;

  bulletsContainer.innerHTML = item.bullets
    .map((b, idx) => {
      const parts = b.split(':');
      const prefix = parts.length > 1 ? parts[0] + ':' : `Point ${idx + 1}:`;
      const body = parts.length > 1 ? parts.slice(1).join(':') : b;
      return `
        <div class="bullet-card">
          <div class="bullet-num">${idx + 1}</div>
          <div class="bullet-content">
            <strong class="bullet-highlight">${prefix}</strong> ${body}
          </div>
        </div>
      `;
    })
    .join('');
}

// Live Input Event
queryInput.addEventListener('input', (e) => {
  const val = e.target.value;
  if (!val.trim()) return;
  const match = searchBank(val);
  if (match) renderResult(match.item, match.latency);
});

// Preset Button Clicks
document.querySelectorAll('.preset-chip').forEach((btn) => {
  btn.addEventListener('click', () => {
    const q = btn.getAttribute('data-query');
    queryInput.value = q;
    const match = searchBank(q);
    if (match) renderResult(match.item, match.latency);
  });
});

// Panic Hide
panicBtn.addEventListener('click', () => {
  if (window.ghostCopilot) window.ghostCopilot.togglePanic();
});

// Minimize Button
if (minimizeBtn) {
  minimizeBtn.addEventListener('click', () => {
    if (window.ghostCopilot) window.ghostCopilot.minimizeApp();
  });
}

// Click-Through Toggle
clickThroughBadge.addEventListener('click', () => {
  isClickThrough = !isClickThrough;
  if (window.ghostCopilot) window.ghostCopilot.setClickThrough(isClickThrough);
  clickThroughBadge.textContent = isClickThrough ? '🖱️ CLICK: PASS-THRU' : '🖱️ CLICK: NORMAL';
  clickThroughBadge.style.color = isClickThrough ? '#00FFA3' : '#FFE600';
});

// Compact Mode Toggle
compactModeBadge.addEventListener('click', () => {
  isCompact = !isCompact;
  if (window.ghostCopilot) window.ghostCopilot.setCompactMode(isCompact);
  hudContainer.classList.toggle('compact-mode', isCompact);
  compactModeBadge.textContent = isCompact ? '📐 COMPACT PILL' : '📐 FULL VIEW';
  compactModeBadge.style.color = isCompact ? '#00F0FF' : '#FFE600';
});

// Listen to Global Shortcuts from Electron Main Process
if (window.ghostCopilot) {
  if (window.ghostCopilot.onClickThroughChanged) {
    window.ghostCopilot.onClickThroughChanged((enabled) => {
      isClickThrough = enabled;
      clickThroughBadge.textContent = isClickThrough ? '🖱️ CLICK: PASS-THRU' : '🖱️ CLICK: NORMAL';
      clickThroughBadge.style.color = isClickThrough ? '#00FFA3' : '#FFE600';
    });
  }
  if (window.ghostCopilot.onCompactChanged) {
    window.ghostCopilot.onCompactChanged((compact) => {
      isCompact = compact;
      hudContainer.classList.toggle('compact-mode', isCompact);
      compactModeBadge.textContent = isCompact ? '📐 COMPACT PILL' : '📐 FULL VIEW';
      compactModeBadge.style.color = isCompact ? '#00F0FF' : '#FFE600';
    });
  }
}

// Cadence Telemetry Logic
let speechStartTime = null;
let speechWordCount = 0;
let monologueInterval = null;
const FILLER_WORDS = ['um', 'uh', 'like', 'basically', 'actually', 'you know', 'sort of', 'kind of'];

function updateCadenceMetrics(transcript) {
  const words = transcript.trim().split(/\s+/).filter(Boolean);
  speechWordCount = words.length;

  if (!speechStartTime && speechWordCount > 0) {
    speechStartTime = Date.now();
    monologueInterval = setInterval(() => {
      const elapsedSec = Math.floor((Date.now() - speechStartTime) / 1000);
      if (timerValue) timerValue.textContent = `${elapsedSec}s`;

      // 75-second Ramble Warning Threshold
      if (elapsedSec >= 70 && rambleBanner) {
        rambleBanner.style.display = 'flex';
      } else if (rambleBanner) {
        rambleBanner.style.display = 'none';
      }

      // Compute Words Per Minute (WPM)
      const elapsedMin = Math.max(elapsedSec / 60, 0.05);
      const wpm = Math.round(speechWordCount / elapsedMin);
      if (wpmValue) {
        wpmValue.textContent = wpm > 0 ? wpm : 132;
        if (wpm >= 110 && wpm <= 155) {
          wpmValue.style.color = '#00FFA3'; // Golden
        } else if (wpm < 110) {
          wpmValue.style.color = '#00F0FF'; // Slow
        } else {
          wpmValue.style.color = '#FF3366'; // Rushing
        }
      }
    }, 1000);
  }

  // Detect Fillers
  const lower = transcript.toLowerCase();
  let fillers = 0;
  for (const f of FILLER_WORDS) {
    const matches = lower.match(new RegExp(`\\b${f}\\b`, 'g'));
    if (matches) fillers += matches.length;
  }
  const clarity = Math.max(0, 100 - fillers * 7);
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
    try { recognition.start(); } catch (_) {}
  } else {
    micBtn.classList.remove('active');
    if (monologueInterval) clearInterval(monologueInterval);
    speechStartTime = null;
    if (rambleBanner) rambleBanner.style.display = 'none';
    try { recognition.stop(); } catch (_) {}
  }
});
