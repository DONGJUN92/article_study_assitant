/**
 * Article Study — Service Worker (Background Script)
 * Handles API communication, tab capture, and message routing.
 */

const API_BASE = 'http://127.0.0.1:8765/api';
console.log('[SW] Article Study Service Worker starting...');

// ── Side Panel setup ────────────────────────────────────
chrome.sidePanel?.setOptions?.({ enabled: true });

// ── Context Menu ────────────────────────────────────────
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'article-study-analyze',
    title: 'Article Study: 분석하기',
    contexts: ['selection'],
  });
  chrome.contextMenus.create({
    id: 'article-study-add-vocab',
    title: 'Article Study: 단어장에 추가',
    contexts: ['selection'],
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === 'article-study-analyze' && info.selectionText) {
    // 1. Save selection for the side panel to pick up
    await chrome.storage.local.set({ 
      pendingSelection: info.selectionText,
      panelMode: 'chat' 
    });
    
    // 2. Open Side Panel
    try {
      await chrome.sidePanel.open({ tabId: tab.id });
    } catch (e) {
      console.warn('sidePanel.open failed', e);
    }
  } else if (info.menuItemId === 'article-study-add-vocab' && info.selectionText) {
    const text = info.selectionText.trim();
    if (!text) return;

    chrome.runtime.sendMessage({ type: 'VOCAB_ADDING', word: text });

    // Directly call the Backend API from the Service Worker, bypassing content.js
    // This is required because native PDF Viewers block content.js DOM injection
    const res = await chrome.storage.local.get(['currentDocId']);
    const resp = await apiPost('/vocabulary', {
      word: text,
      meaning: '',
      context_sentence: text,
      doc_id: res.currentDocId || null
    });

    if (!resp.error) {
      // Broadcast to any active sidepanels to refresh the UI immediately
      chrome.runtime.sendMessage({ type: 'RELOAD_VOCAB' });
    }
  }
});

// ── Keyboard shortcuts ──────────────────────────────────
chrome.commands.onCommand.addListener((command, tab) => {
  if (command === 'ai-chat-toggle') {
     chrome.sidePanel.open({ tabId: tab.id });
  } else {
    chrome.tabs.sendMessage(tab.id, { type: 'COMMAND', command });
  }
});

// ── Message handler  ────────────────────────────────────
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  handleMessage(msg, sender).then(sendResponse).catch(err => {
    sendResponse({ error: err.message });
  });
  return true; // async
});

async function handleMessage(msg, sender) {
  switch (msg.type) {
    case 'HEALTH_CHECK':
      return apiGet('/health');

    case 'INGEST_PDF':
      return apiPost('/ingest', {
        pdf_data: msg.pdfData,
        filename: msg.filename,
        pdf_url: msg.pdfUrl,
      });

    case 'INGEST_STATUS':
      return apiGet(`/ingest/${msg.docId}/status`);

    case 'WORD_ANALYZE':
      return apiPost('/word', {
        word: msg.word,
        context: msg.context,
        doc_id: msg.docId,
      });

    case 'SENTENCE_ANALYZE':
      return apiPost('/sentence', {
        sentence: msg.sentence,
        doc_id: msg.docId,
      });

    case 'BRIEFING':
      return apiPost('/briefing', { doc_id: msg.docId });

    case 'OPEN_SIDEPANEL':
      try {
        await chrome.sidePanel.open({ tabId: sender.tab ? sender.tab.id : undefined });
      } catch (e) {
        console.warn('sidePanel.open failed', e);
      }
      return { ok: true };


    case 'GET_DOCUMENTS':
      return apiGet('/documents');

    case 'DELETE_DOCUMENT':
      return apiDelete(`/documents/${msg.docId}`);

    case 'VOCAB_LIST':
      return apiGet('/vocabulary');

    case 'VOCAB_ADD':
      return apiPost('/vocabulary', msg.entry);

    case 'VOCAB_DUE':
      return apiGet('/vocabulary/due');

    default:
      return { error: 'Unknown message type' };
  }
}


// ── API helpers ─────────────────────────────────────────
// ── Streaming Translation handler ───────────────────────
chrome.runtime.onConnect.addListener((port) => {
  if (port.name === 'translate') {
    port.onMessage.addListener(async (msg) => {
      try {
        const resp = await fetch(`${API_BASE}/translate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ doc_id: msg.docId, target_lang: msg.targetLang })
        });

        if (!resp.ok) {
          throw new Error(`API ${resp.status}`);
        }

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            port.postMessage({ done: true });
            break;
          }
          
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data:')) {
              const dataStr = line.slice(5).trim();
              if (dataStr) {
                try {
                  const data = JSON.parse(dataStr);
                  port.postMessage(data);
                } catch(e) {}
              }
            }
          }
        }
      } catch (err) {
        port.postMessage({ error: err.message });
      }
    });
  }
});

async function apiGet(path) {
  try {
    const resp = await fetch(`${API_BASE}${path}`);
    if (!resp.ok) throw new Error(`API ${resp.status}`);
    return await resp.json();
  } catch (err) {
    return { error: err.message };
  }
}

async function apiPost(path, body) {
  try {
    const resp = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!resp.ok) throw new Error(`API ${resp.status}`);
    return await resp.json();
  } catch (err) {
    return { error: err.message };
  }
}

async function apiDelete(path) {
  try {
    const resp = await fetch(`${API_BASE}${path}`, { method: 'DELETE' });
    if (!resp.ok) throw new Error(`API ${resp.status}`);
    return await resp.json();
  } catch (err) {
    return { error: err.message };
  }
}
