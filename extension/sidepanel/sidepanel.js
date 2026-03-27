/**
 * Article Study — Side Panel Logic
 * Handles AI chat, vision query, vocabulary, and briefing tabs.
 */

const API_BASE = 'http://127.0.0.1:8765/api';
let currentDocId = null;
let chatHistory = [];

// ═══════════════════════════════════════════════════
// UI ELEMENTS
// ═══════════════════════════════════════════════════
const statusBox = document.getElementById('status-box');
const statusText = document.getElementById('status-text');
const progressFill = document.getElementById('progress-fill');

// ═══════════════════════════════════════════════════
// TAB SWITCHING
// ═══════════════════════════════════════════════════
document.querySelectorAll('.sp-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.sp-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.sp-panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(`panel-${tab.dataset.tab}`).classList.add('active');

    // Load data for the tab
    if (tab.dataset.tab === 'vocab') loadVocabulary();
    if (tab.dataset.tab === 'docs') loadDocuments();
  });
});

// ── INIT — Load state from storage ─────────────────────
function checkPendingActions() {
  chrome.storage.local.get(['currentDocId', 'panelMode', 'pendingSelection'], (data) => {
    currentDocId = data.currentDocId;

    if (data.panelMode === 'chat' && data.pendingSelection) {
      switchToTab('chat');
      handlePendingSelection(data.pendingSelection);
      chrome.storage.local.remove(['pendingSelection', 'panelMode']);
    } else if (data.panelMode === 'chat') {
      switchToTab('chat');
      chrome.storage.local.remove(['panelMode']);
    } else if (data.panelMode === 'docs') {
      switchToTab('docs');
      chrome.storage.local.remove(['panelMode']);
    } else if (data.panelMode === 'vocab') {
      switchToTab('vocab');
      chrome.storage.local.remove(['panelMode']);
    } else if (data.panelMode === 'briefing') {
      switchToTab('briefing');
      chrome.storage.local.remove(['panelMode']);
    }
    
    if (currentDocId) {
      console.log('[SP] Current Doc ID:', currentDocId);
      checkStatus();
    } else {
      console.warn('[SP] No currentDocId found in storage');
    }
  });
}

checkPendingActions();

async function loadPersistedState() {
  if (!currentDocId) return;
  
  // 1. Load Chat History
  const chatData = await chrome.storage.local.get([`chatHistory_${currentDocId}`]);
  const history = chatData[`chatHistory_${currentDocId}`] || [];
  
  chatHistory = history;
  chatMessages.innerHTML = '';
  
  if (history.length > 0) {
    for (const msg of history) {
      const el = document.createElement('div');
      el.className = `sp-chat-message sp-chat-message--${msg.role}`;
      el.innerHTML = `<div class="sp-chat-bubble">${escapeHtml(msg.content)}</div>`;
      chatMessages.appendChild(el);
    }
  } else {
    chatMessages.innerHTML = `
      <div class="sp-chat-welcome">
        <div class="sp-chat-welcome__icon">🤖</div>
        <h3>논문에 대해 질문하세요</h3>
        <p>학습된 논문 내용을 기반으로 답변합니다</p>
      </div>`;
  }
  chatMessages.scrollTop = chatMessages.scrollHeight;

  // 2. Load Briefing State
  const briefingData = await chrome.storage.local.get([`briefing_${currentDocId}`]);
  const briefingHtml = briefingData[`briefing_${currentDocId}`];
  if (briefingHtml) {
    const briefingContainer = document.getElementById('briefing-container');
    briefingContainer.innerHTML = briefingHtml;
    document.getElementById('btn-re-brief')?.addEventListener('click', generateBriefing);
  } else {
    const briefingContainer = document.getElementById('briefing-container');
    briefingContainer.innerHTML = `
      <div class="sp-empty-state">
        <div style="font-size:48px;margin-bottom:12px;">🎯</div>
        <p>논문 브리핑을 생성합니다</p>
        <button id="briefing-generate" class="sp-btn-primary" style="margin-top:16px;">브리핑 생성</button>
      </div>`;
    document.getElementById('briefing-generate')?.addEventListener('click', generateBriefing);
  }
}

// Listen for storage changes while sidepanel is open
chrome.storage.onChanged.addListener((changes) => {
  if (changes.pendingSelection || changes.panelMode || changes.currentDocId) {
    checkPendingActions();
  }
  if (changes.currentDocId) {
    loadPersistedState();
  }
});

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'RELOAD_VOCAB') {
    loadVocabulary();
  } else if (msg.type === 'VOCAB_ADDING') {
    const list = document.getElementById('vocab-list');
    if (!list) return;

    const loadingCard = document.createElement('div');
    loadingCard.className = 'sp-vocab-card sp-vocab-loading';
    loadingCard.innerHTML = `
      <div class="sp-vocab-card__word">${escapeHtml(msg.word)}</div>
      <div class="sp-loading" style="padding:16px; flex-direction:row; justify-content:center;">
        <div class="sp-spinner sp-spinner--small"></div>
        <span style="color:var(--sp-text-light);font-size:12px;margin-left:8px;">단어 의미 파악 중...</span>
      </div>
    `;
    
    // Clear initial empty state if present
    const emptyState = list.querySelector('.sp-empty-state');
    if (emptyState) {
      list.innerHTML = '';
    }
    
    list.prepend(loadingCard);
  }
});

function switchToTab(tabName) {
  document.querySelectorAll('.sp-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === tabName);
  });
  document.querySelectorAll('.sp-panel').forEach(p => {
    p.classList.toggle('active', p.id === `panel-${tabName}`);
  });
  
  // Load data for the tab if needed
  if (tabName === 'vocab') loadVocabulary();
  if (tabName === 'docs') loadDocuments();
}

async function handlePendingSelection(text) {
  chatInput.value = text + '\n\n(이 문장의 전후 맥락을 고려해서 분석해줘)';
  document.getElementById('chat-send').click();
}

// ═══════════════════════════════════════════════════
// AI CHAT
// ═══════════════════════════════════════════════════
const chatInput = document.getElementById('chat-input');
const chatSend = document.getElementById('chat-send');
const chatMessages = document.getElementById('chat-messages');
const vocabList = document.getElementById('vocab-list');
const vocabExportBtn = document.getElementById('vocab-export-csv');
const vocabClearBtn = document.getElementById('vocab-clear-btn');

chatSend.addEventListener('click', sendChatMessage);
document.getElementById('chat-clear-btn')?.addEventListener('click', async () => {
  if (!currentDocId) return;
  if (!confirm('현재 문서의 모든 채팅 기록을 초기화하시겠습니까?')) return;
  await chrome.storage.local.remove([`chatHistory_${currentDocId}`]);
  chatHistory = [];
  loadPersistedState();
});

chatInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendChatMessage();
  }
});

async function sendChatMessage() {
  const query = chatInput.value.trim();
  if (!query || !currentDocId) return;

  chatInput.value = '';
  addChatBubble('user', query);
  await performChatQuery(query);
}

async function performChatQuery(query) {
  chatSend.disabled = true;

  // Clear welcome
  const welcome = chatMessages.querySelector('.sp-chat-welcome');
  if (welcome) welcome.remove();

  // Add user message to history
  chatHistory.push({ role: 'user', content: query });
  if (currentDocId) {
    await chrome.storage.local.set({ [`chatHistory_${currentDocId}`]: chatHistory });
  }

  // Add loading bubble
  const loadingEl = addChatBubble('assistant', '');
  loadingEl.querySelector('.sp-chat-bubble').innerHTML = `
    <div class="sp-loading"><div class="sp-spinner"></div></div>
  `;

  try {
    const lang = document.getElementById('briefing-lang')?.value || 'ko';
    const resp = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        doc_id: currentDocId,
        history: chatHistory.slice(-10),
        language: lang,
      }),
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let answer = '';
    const bubble = loadingEl.querySelector('.sp-chat-bubble');

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data:')) {
          const token = line.slice(5);
          if (token.trim()) {
            answer += token;
            bubble.textContent = answer;
          }
        }
      }
    }

    chatHistory.push({ role: 'assistant', content: answer });
    if (currentDocId) {
      await chrome.storage.local.set({ [`chatHistory_${currentDocId}`]: chatHistory });
    }
  } catch (err) {
    const bubble = loadingEl.querySelector('.sp-chat-bubble');
    bubble.textContent = `오류: ${err.message}`;
    bubble.style.color = '#FF7675';
  }

  chatSend.disabled = false;
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addChatBubble(role, content) {
  const msg = document.createElement('div');
  msg.className = `sp-chat-message sp-chat-message--${role}`;
  msg.innerHTML = `<div class="sp-chat-bubble">${escapeHtml(content)}</div>`;
  chatMessages.appendChild(msg);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return msg;
}

// ── STATUS CHECK ──────────────────────────────────────
async function checkStatus() {
  if (!currentDocId) return;
  console.log('[SP] Checking status for:', currentDocId);

  try {
    const resp = await fetch(`${API_BASE}/ingest/${currentDocId}/status`);
    if (!resp.ok) {
        console.error('[SP] Status API error:', resp.status);
        return;
    }
    const data = await resp.json();
    console.log('[SP] Status data:', data);

    if (data.status === 'processing') {
      const percent = Math.round(data.progress * 100);
      const estText = data.estimated_seconds ? ` (약 ${Math.round(data.estimated_seconds)}초 남음)` : '';
      statusText.innerText = `${data.message || '학습 중...'} ${percent}%${estText}`;
      progressFill.style.width = `${percent}%`;
      statusBox.classList.remove('hidden');
      statusBox.querySelector('.sp-spinner')?.classList.remove('hidden');
      setTimeout(checkStatus, 1500);
    } else if (data.status === 'complete') {
      // Only show the "Success" toast if the box was already visible (meaning it just finished)
      // This prevents the bar from popping up every time the user switches tabs.
      if (!statusBox.classList.contains('hidden')) {
        statusText.innerText = '✅ 학습 완료!';
        progressFill.style.width = '100%';
        statusBox.querySelector('.sp-spinner')?.classList.add('hidden');
        setTimeout(() => {
          statusBox.classList.add('hidden');
          // Reset spinner visibility for next ingestion
          statusBox.querySelector('.sp-spinner')?.classList.remove('hidden');
        }, 3500);
      } else {
        statusBox.classList.add('hidden');
      }
    } else if (data.status === 'error') {
      statusText.innerText = `❌ 오류: ${data.message}`;
      statusBox.classList.remove('hidden');
      statusBox.querySelector('.sp-spinner')?.classList.add('hidden');
    } else {
      statusBox.classList.add('hidden');
    }
  } catch (err) {
    console.error('[SP] Status check failed:', err);
  }
}


// ═══════════════════════════════════════════════════
// VOCABULARY
// ═══════════════════════════════════════════════════

vocabExportBtn?.addEventListener('click', exportToCSV);
vocabClearBtn?.addEventListener('click', async () => {
  if (!currentDocId) return;
  if (!confirm('현재 문서에서 수집한 모든 단어장을 삭제하시겠습니까?')) return;
  try {
    const resp = await fetch(`${API_BASE}/vocabulary/document/${currentDocId}`, { method: 'DELETE' });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    vocabList.innerHTML = `<div class="sp-empty-state"><p>삭제 완료!</p></div>`;
    setTimeout(loadVocabulary, 1000);
  } catch (err) {
    alert(`단어장 삭제 실패: ${err.message}`);
  }
});

async function loadVocabulary() {
  if (!currentDocId) {
    vocabList.innerHTML = `
      <div class="sp-empty-state">
        <div style="font-size:48px;margin-bottom:12px;">📝</div>
        <p>PDF 문서를 열어주세요.</p>
      </div>
    `;
    return;
  }

  try {
    const resp = await fetch(`${API_BASE}/vocabulary?doc_id=${currentDocId}`);
    const entries = await resp.json();

    if (!entries.length) {
      vocabList.innerHTML = `
        <div class="sp-empty-state">
          <div style="font-size:48px;margin-bottom:12px;">📝</div>
          <p>논문에서 단어를 선택하면 자동으로 추가됩니다</p>
        </div>
      `;
      return;
    }

    vocabList.innerHTML = entries.map(e => `
      <div class="sp-vocab-card">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
          <div class="sp-vocab-card__word">${escapeHtml(e.word)}</div>
          <button class="sp-btn-icon-danger btn-delete-word" data-word="${escapeHtml(e.word)}" title="단어 삭제" style="padding:4px; font-size:14px; margin-top:-4px; margin-right:-4px;">🗑️</button>
        </div>
        <div class="sp-vocab-card__meaning">${escapeHtml(e.meaning).replace(/\n/g, '<br>')}</div>
        ${e.context_sentence ? `<div class="sp-vocab-card__context">"${escapeHtml(e.context_sentence.substring(0, 100))}"</div>` : ''}
        <div class="sp-vocab-card__meta">
          <span>저장일: ${e.added_at ? e.added_at.split('T')[0] : '-'}</span>
        </div>
      </div>
    `).join('');

    // Attach delete listeners
    document.querySelectorAll('.btn-delete-word').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const word = e.currentTarget.dataset.word;
        if (!confirm(`'${word}' 단어를 단어장에서 삭제하시겠습니까?`)) return;
        try {
          const resp = await fetch(`${API_BASE}/vocabulary/${encodeURIComponent(word)}?doc_id=${currentDocId}`, { method: 'DELETE' });
          if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
          loadVocabulary();
        } catch (err) {
          alert(`삭제 실패: ${err.message}`);
        }
      });
    });

  } catch (err) {
    vocabList.innerHTML = `<p style="color:#FF7675;padding:16px;">로딩 실패: ${err.message}</p>`;
  }
}

async function exportToCSV() {
  if (!currentDocId) {
    alert('학습된 논문을 먼저 열어주세요.');
    return;
  }
  try {
    const resp = await fetch(`${API_BASE}/vocabulary?doc_id=${currentDocId}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const entries = await resp.json();

    if (!entries || entries.length === 0) {
      alert('내보낼 단어가 없습니다.');
      return;
    }

    // CSV Header
    let csvContent = '단어 저장연월일,단어,1. 일반적 의미,2. 문맥적 의미\n';

    entries.forEach(e => {
      const dateStr = e.added_at ? e.added_at.split('T')[0] : 'None';
      const wordStr = e.word || '';
      
      let generalMeaning = '';
      let contextMeaning = '';

      // Parse standardized meaning lines "1. ...\n2. ..."
      if (e.meaning) {
        const lines = e.meaning.split('\\n');
        for (const line of lines) {
          if (line.includes('1. 일반적 의미') || line.startsWith('1.')) generalMeaning = line.replace(/^1\\.\\s*(\\[일반적 의미\\])?\\s*/, '').trim();
          else if (line.includes('2. 문맥적 의미') || line.startsWith('2.')) contextMeaning = line.replace(/^2\\.\\s*(\\[문맥적 의미\\])?\\s*/, '').trim();
        }
        // Fallback if parsing fails
        if (!generalMeaning && !contextMeaning) {
          generalMeaning = e.meaning.replace(/\\n/g, ' ');
        }
      }

      // Escape strings for CSV
      const esc = (text) => `"${(text || '').replace(/"/g, '""')}"`;
      
      csvContent += `${esc(dateStr)},${esc(wordStr)},${esc(generalMeaning)},${esc(contextMeaning)}\n`;
    });

    // Download logic
    const blob = new Blob(['\\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' }); // UFEEF for Excel UTF-8 BOM
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `article_study_vocabulary_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

  } catch (err) {
    alert(`CSV 내보내기 실패: ${err.message}`);
  }
}

// ═══════════════════════════════════════════════════
// BRIEFING
// ═══════════════════════════════════════════════════
const briefingBtn = document.getElementById('briefing-generate');
const briefingContainer = document.getElementById('briefing-container');

briefingBtn?.addEventListener('click', generateBriefing);

document.getElementById('briefing-clear-btn')?.addEventListener('click', async () => {
  if (!currentDocId) return;
  if (!confirm('현재 문서의 브리핑을 초기화하시겠습니까?')) return;
  await chrome.storage.local.remove([`briefing_${currentDocId}`]);
  briefingContainer.innerHTML = `
      <div class="sp-empty-state">
        <div style="font-size:48px;margin-bottom:12px;">🎯</div>
        <p>논문 브리핑을 생성합니다</p>
        <button id="briefing-generate" class="sp-btn-primary" style="margin-top:16px;">브리핑 생성</button>
      </div>`;
  document.getElementById('briefing-generate')?.addEventListener('click', generateBriefing);
});

async function generateBriefing() {
  if (!currentDocId) {
    briefingContainer.innerHTML = `<p style="color:#FF7675;padding:16px;">먼저 PDF를 학습시켜주세요</p>`;
    return;
  }

  briefingContainer.innerHTML = `
    <div class="sp-loading" style="padding:60px;">
      <div class="sp-spinner"></div>
      <span style="color:var(--sp-text-light);font-size:13px">브리핑 생성중...</span>
    </div>
  `;

  try {
    const lang = document.getElementById('briefing-lang')?.value || 'ko';
    const resp = await fetch(`${API_BASE}/briefing`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ doc_id: currentDocId, language: lang }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();

    const diffClass = (data.difficulty || '').toLowerCase().includes('easy') ? 'easy'
      : (data.difficulty || '').toLowerCase().includes('hard') ? 'hard' : 'medium';

    const questionsHtml = (data.key_questions || []).map(q => `<li>${escapeHtml(q)}</li>`).join('');

    briefingContainer.innerHTML = `
      <div class="sp-briefing-section">
        <h4>📊 난이도</h4>
        <span class="sp-briefing-difficulty sp-briefing-difficulty--${diffClass}">${escapeHtml(data.difficulty || 'Unknown')}</span>
      </div>
      <div class="sp-briefing-section">
        <h4>📝 핵심 요약</h4>
        <p>${escapeHtml(data.summary || '')}</p>
      </div>
      ${questionsHtml ? `
      <div class="sp-briefing-section">
        <h4>❓ 핵심 연구 질문</h4>
        <ol>${questionsHtml}</ol>
      </div>` : ''}
      ${data.reading_guide ? `
      <div class="sp-briefing-section">
        <h4>📖 읽기 가이드</h4>
        <p>${escapeHtml(data.reading_guide)}</p>
      </div>` : ''}
      <button class="sp-btn-outline" id="btn-re-brief" style="margin-top:8px;">🔄 다시 생성</button>
    `;

    document.getElementById('btn-re-brief')?.addEventListener('click', generateBriefing);

    if (currentDocId) {
      await chrome.storage.local.set({ [`briefing_${currentDocId}`]: briefingContainer.innerHTML });
    }
  } catch (err) {
    briefingContainer.innerHTML = `<p style="color:#FF7675;padding:16px;">브리핑 생성 실패: ${err.message}</p>`;
  }
}

// ═══════════════════════════════════════════════════
// DOCUMENTS (STUDY HISTORY)
// ═══════════════════════════════════════════════════
const docsList = document.getElementById('docs-list');

async function loadDocuments() {
  try {
    const resp = await fetch(`${API_BASE}/documents`);
    const docs = await resp.json();

    if (!docs.length) {
      docsList.innerHTML = `
        <div class="sp-empty-state">
          <div style="font-size:48px;margin-bottom:12px;">📂</div>
          <p>학습된 논문이 없습니다</p>
        </div>
      `;
      return;
    }

    docsList.innerHTML = docs.map(d => `
      <div class="sp-doc-card">
        <div class="sp-doc-card__main">
          <div class="sp-doc-card__title">${escapeHtml(d.title || d.filename)}</div>
          <div class="sp-doc-card__meta">
            <span>📄 ${d.page_count}페이지</span>
            <span>📅 ${d.ingested_at ? new Date(d.ingested_at).toLocaleDateString('ko') : '기록 없음'}</span>
          </div>
        </div>
        <button class="sp-btn-icon-danger" data-id="${escapeHtml(d.doc_id)}" title="학습 데이터 삭제">🗑️</button>
      </div>
    `).join('');
  } catch (err) {
    docsList.innerHTML = `<p style="color:#FF7675;padding:16px;">목록 로딩 실패: ${err.message}</p>`;
  }
}

// Event Delegation for delete buttons
docsList.addEventListener('click', (e) => {
  const btn = e.target.closest('.sp-btn-icon-danger');
  if (btn) {
    const docId = btn.dataset.id;
    if (docId) deleteDocument(docId);
  }
});

async function deleteDocument(docId) {
  if (!confirm('해당 논문의 학습 데이터를 삭제하시겠습니까?\n(채팅 및 요약 내용이 모두 삭제됩니다)')) return;

  try {
    const resp = await fetch(`${API_BASE}/documents/${docId}`, { method: 'DELETE' });
    if (resp.ok) {
      loadDocuments();
      if (currentDocId === docId) {
        currentDocId = null;
        chrome.storage.local.remove(['currentDocId', 'currentTitle']);
      }
    } else {
      alert('삭제 실패');
    }
  } catch (err) {
    alert('삭제 오류: ' + err.message);
  }
}

// Global expose for onclick
window.deleteDocument = deleteDocument;
window.loadDocuments = loadDocuments;

// ═══════════════════════════════════════════════════
// UTILS
// ═══════════════════════════════════════════════════
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str || '';
  return div.innerHTML;
}
