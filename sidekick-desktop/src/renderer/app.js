// In-Memory Fast Trie & Radical Interview Knowledge Bank (Populated dynamically on startup)
let INTERVIEW_BANK = [
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
    title: 'StateFlow vs SharedFlow vs LiveData vs Channels in Kotlin',
    keywords: ['stateflow', 'sharedflow', 'stateflow vs sharedflow', 'livedata vs flow', 'channels vs flow'],
    bullets: [
      'StateFlow: Hot stream with initial value, conflates duplicate emissions, always retains latest state (replay=1).',
      'SharedFlow: Hot event bus with configurable replay cache and buffer capacity, ideal for one-off events (navigation, snackbars).',
      'Channels vs Flow: Channel is hot point-to-point stream (each event consumed once); Flow is declarative broadcast stream.'
    ]
  },
  {
    title: 'Kotlin Coroutines vs Threads',
    keywords: ['coroutines vs threads', 'coroutine vs thread', 'kotlin coroutine', 'structured concurrency'],
    bullets: [
      'Lightweight User-Space: Coroutines are cooperative routines multiplexed over shared OS thread pools with ~few KB stack.',
      'Non-Blocking Suspension: Suspending functions release carrier thread back to Dispatcher during I/O delays.',
      'Structured Concurrency: CoroutineScope guarantees parent awaits all children; cancellation cascades downward automatically.'
    ]
  },
  {
    title: 'ConcurrentHashMap Internals (Java 8+ vs 7)',
    keywords: ['concurrenthashmap', 'concurrenthashmap internals', 'java hashmap treeify', 'cas node bin'],
    bullets: [
      'Locking Strategy: Java 8+ eliminated ReentrantLock Segments; uses CAS for first node insertion and synchronized on bucket head.',
      'Treeification: Bucket converts from Linked List to Red-Black Tree when chain length >= 8 and table capacity >= 64 (O(log N) worst case).',
      'Concurrent Resizing: Multiple threads assist in table transfer using sizeCtl and ForwardingNode markers.'
    ]
  },
  {
    title: 'Virtual Threads (Java 21 Project Loom)',
    keywords: ['virtual threads', 'project loom', 'virtual thread java', 'carrier thread pinning'],
    bullets: [
      'M:N User Threads: Millions of virtual threads scheduled on small pool of carrier platform OS threads with unpark/continuation.',
      'Carrier Pinning Caveat: Avoid native JNI calls or synchronized blocks inside virtual threads; use ReentrantLock instead.',
      'High-Throughput I/O: Replaces reactive callback spaghetti with synchronous blocking code style without thread exhaustion.'
    ]
  },
  {
    title: 'volatile Keyword & Java Memory Model (JMM)',
    keywords: ['volatile', 'volatile java', 'java memory model', 'visibility memory barrier', 'happens-before'],
    bullets: [
      'Visibility Guarantee: Direct reads and writes bypass CPU L1/L2 core caches, flushing directly to main memory.',
      'Instruction Reordering: Emits hardware memory barriers (LoadLoad/StoreStore) enforcing Happens-Before ordering.',
      'Atomicity Caveat: volatile does NOT guarantee atomicity for compound operations (e.g., count++); use AtomicInteger or CAS.'
    ]
  }
];

// Asynchronously load all 550 documents from backend bank
async function loadFullKnowledgeBank() {
  try {
    const res = await fetch('http://127.0.0.1:8000/api/sidekick/bank');
    if (res.ok) {
      const data = await res.json();
      if (data.documents && Array.isArray(data.documents) && data.documents.length > 0) {
        INTERVIEW_BANK = data.documents;
      }
    }
  } catch (err) {
    console.warn('[GhostCopilot] Backend bank offline, using local bank.');
  }
}
loadFullKnowledgeBank();

// DOM Elements
const hudContainer = document.getElementById('hudContainer');
const queryInput = document.getElementById('queryInput');
const questionTitle = document.getElementById('questionTitle');
const latencyBadge = document.getElementById('latencyBadge');
const bulletsContainer = document.getElementById('bulletsContainer');
const panicBtn = document.getElementById('panicBtn');
const minimizeBtn = document.getElementById('minimizeBtn');
const micBtn = document.getElementById('micBtn');
const llmBtn = document.getElementById('llmBtn');
const clickThroughBadge = document.getElementById('clickThroughBadge');
const invisibilityBadge = document.getElementById('invisibilityBadge');
const compactModeBadge = document.getElementById('compactModeBadge');
const wpmValue = document.getElementById('wpmValue');
const timerValue = document.getElementById('timerValue');
const clarityValue = document.getElementById('clarityValue');
const rambleBanner = document.getElementById('rambleBanner');

let isMicListening = false;
let isClickThrough = false;
let isCompact = false;
let lastLiveHintTimestamp = 0;

// Conversational filler cleaner
const CONV_PREFIXES = [
  /^(can you|could you|would you|please)?\s*(walk me through|tell me about|explain|describe|what is|what are|how does|how do you|how would you|what are the trade-offs of|what is the difference between|compare)\s+/i,
  /^(so|well|okay|now|next|also|tell me|give me|can you share)\s+/i,
];

function cleanQuestion(raw) {
  let cleaned = raw.trim();
  for (const rx of CONV_PREFIXES) {
    cleaned = cleaned.replace(rx, '');
  }
  return cleaned.trim() || raw.trim();
}

// Multi-Tier Search: Backend Trie/RAG API (<100µs) with Local In-Memory Fallback
async function executeQuery(query) {
  const t0 = performance.now();
  const cleaned = cleanQuestion(query);
  if (!cleaned) return;

  try {
    const res = await fetch('http://127.0.0.1:8000/api/sidekick/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: cleaned })
    });
    if (res.ok) {
      const data = await res.json();
      const t1 = performance.now();
      const latencyUs = data.latency_microseconds || (t1 - t0) * 1000;
      renderResult(data, latencyUs);
      return;
    }
  } catch (_) {
    // Local offline fallback
  }

  // Local Trie Search
  const match = searchLocalBank(cleaned);
  if (match) {
    renderResult(match.item, match.latency);
  }
}

// Direct Inference on Local Ollama Qwen2.5:3b
async function askLocalLLM(query) {
  if (!query || !query.trim()) return;
  const q = query.trim();
  questionTitle.textContent = `🤖 Ollama Thinking: "${q}"...`;
  latencyBadge.textContent = '⚡ Inferring Qwen2.5...';
  bulletsContainer.innerHTML = `
    <div class="bullet-card">
      <div class="bullet-num">⏳</div>
      <div class="bullet-content">
        <strong class="bullet-highlight">Generating:</strong> Streaming local LLM tokens from Ollama qwen2.5:3b on Apple Silicon...
      </div>
    </div>
  `;

  try {
    const res = await fetch('http://127.0.0.1:8000/api/sidekick/ask-llm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: q, force_llm: true })
    });
    if (res.ok) {
      const data = await res.json();
      renderResult(data, data.latency_milliseconds * 1000);
      return;
    }
  } catch (err) {
    console.warn('Local LLM inference error:', err);
  }

  executeQuery(q);
}

// Live Hint Polling from Native Hardware Mic Daemon
async function pollLiveHint() {
  try {
    const res = await fetch('http://127.0.0.1:8000/api/sidekick/live-hint');
    if (res.ok) {
      const data = await res.json();
      if (data.timestamp && data.timestamp > lastLiveHintTimestamp && data.hint) {
        lastLiveHintTimestamp = data.timestamp;
        if (data.transcript && queryInput) {
          queryInput.value = data.transcript;
        }
        renderResult(data.hint, data.hint.latency_microseconds || 50);
      }
    }
  } catch (_) {}
}
setInterval(pollLiveHint, 350);

// Sub-microsecond Local In-Memory Fallback
function searchLocalBank(query) {
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

// Live Input Event & Enter Key for Local LLM
queryInput.addEventListener('input', (e) => {
  const val = e.target.value;
  if (!val.trim()) return;
  executeQuery(val);
});

queryInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    e.preventDefault();
    const val = queryInput.value;
    if (val && val.trim()) {
      askLocalLLM(val);
    }
  }
});

if (llmBtn) {
  llmBtn.addEventListener('click', () => {
    const val = queryInput.value || questionTitle.textContent;
    if (val && val.trim()) {
      askLocalLLM(val);
    }
  });
}

// Preset Button Clicks
document.querySelectorAll('.preset-chip').forEach((btn) => {
  btn.addEventListener('click', () => {
    const q = btn.getAttribute('data-query');
    queryInput.value = q;
    executeQuery(q);
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

// ═══════════════════════════════════════════════════════════════════════════
// Continuous Standalone Audio Stream & Real-Time Voice Transcriber Pipeline
// ═══════════════════════════════════════════════════════════════════════════

let mediaStream = null;
let currentRecorder = null;
let captureTimer = null;
let recognition = null;

// Initialize Web Speech API for Chromium/Web Browsers
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
  try {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRec();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
      let finalStr = '';
      let interimStr = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalStr += event.results[i][0].transcript;
        } else {
          interimStr += event.results[i][0].transcript;
        }
      }
      const text = (finalStr || interimStr).trim();
      if (text && text.length >= 2) {
        queryInput.value = text;
        updateCadenceMetrics(text);
        executeQuery(text);
      }
    };

    recognition.onerror = (e) => {
      if (e.error !== 'no-speech') {
        console.log('[GhostCopilot] WebSpeech event:', e.error);
      }
    };

    recognition.onend = () => {
      if (isMicListening) {
        setTimeout(() => {
          if (isMicListening && recognition) {
            try { recognition.start(); } catch (_) {}
          }
        }, 200);
      }
    };
  } catch (_) {}
}

async function sendAudioBlobToBackend(blob) {
  try {
    const formData = new FormData();
    formData.append('file', blob, 'speech_chunk.webm');
    const res = await fetch('http://127.0.0.1:8000/api/sidekick/audio/transcribe', {
      method: 'POST',
      body: formData,
    });
    if (res.ok) {
      const data = await res.json();
      if (data.status === 'success' && data.transcript && data.transcript.trim()) {
        const text = data.transcript.trim();
        queryInput.value = text;
        updateCadenceMetrics(text);
        if (data.query_response) {
          renderResult(data.query_response, data.query_response.latency_microseconds || 45);
        } else {
          executeQuery(text);
        }
      }
    }
  } catch (err) {
    console.warn('[GhostCopilot] Backend transcribe call:', err);
  }
}

function runStandaloneAudioCycle(stream) {
  if (!isMicListening || !stream) return;

  const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
    ? 'audio/webm;codecs=opus'
    : MediaRecorder.isTypeSupported('audio/webm')
    ? 'audio/webm'
    : '';

  const chunks = [];
  let recorder;
  try {
    recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
  } catch (e) {
    recorder = new MediaRecorder(stream);
  }
  currentRecorder = recorder;

  recorder.ondataavailable = (e) => {
    if (e.data && e.data.size > 0) {
      chunks.push(e.data);
    }
  };

  recorder.onstop = () => {
    if (chunks.length > 0 && isMicListening) {
      const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' });
      if (blob.size > 600) {
        sendAudioBlobToBackend(blob);
      }
    }
    // Continue next audio cycle seamlessly
    if (isMicListening) {
      runStandaloneAudioCycle(stream);
    }
  };

  recorder.start();

  // 2.5 second audio chunk interval
  captureTimer = setTimeout(() => {
    if (recorder.state === 'recording') {
      try {
        recorder.stop();
      } catch (_) {}
    }
  }, 2500);
}

async function startListeningPipeline() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      }
    });
    mediaStream = stream;

    // Start standalone chunk recording loop
    runStandaloneAudioCycle(stream);

    // Also try WebSpeech API if available
    if (recognition) {
      try { recognition.start(); } catch (_) {}
    }
  } catch (err) {
    console.error('[GhostCopilot] Mic access failed:', err);
  }
}

function stopListeningPipeline() {
  if (captureTimer) {
    clearTimeout(captureTimer);
    captureTimer = null;
  }
  if (currentRecorder && currentRecorder.state !== 'inactive') {
    try { currentRecorder.stop(); } catch (_) {}
    currentRecorder = null;
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop());
    mediaStream = null;
  }
  if (recognition) {
    try { recognition.stop(); } catch (_) {}
  }
}

// Mic Button Click Listener
micBtn.addEventListener('click', () => {
  isMicListening = !isMicListening;
  if (isMicListening) {
    micBtn.classList.add('active');
    const label = micBtn.querySelector('.mic-label');
    if (label) label.textContent = 'LISTENING';
    speechStartTime = Date.now();
    startListeningPipeline();
  } else {
    micBtn.classList.remove('active');
    const label = micBtn.querySelector('.mic-label');
    if (label) label.textContent = 'LISTEN';
    if (monologueInterval) {
      clearInterval(monologueInterval);
      monologueInterval = null;
    }
    speechStartTime = null;
    if (rambleBanner) rambleBanner.style.display = 'none';
    stopListeningPipeline();
  }
});
