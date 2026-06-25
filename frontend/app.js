// State management
let currentUser = null;
let currentAuthMode = 'login'; // 'login' or 'signup'
let activeView = 'ask'; // 'ask' or 'history'

// DOM Elements
const authSection = document.getElementById('auth-section');
const dashboardSection = document.getElementById('dashboard-section');
const authForm = document.getElementById('auth-form');
const authEmail = document.getElementById('auth-email');
const authPassword = document.getElementById('auth-password');
const authSubmitBtn = document.getElementById('auth-submit-btn');
const authError = document.getElementById('auth-error');
const authErrorText = document.getElementById('auth-error-text');
const authSubtext = document.getElementById('auth-subtext');
const tabLoginBtn = document.getElementById('tab-login-btn');
const tabSignupBtn = document.getElementById('tab-signup-btn');

const userEmailDisplay = document.getElementById('user-email-display');
const navAskBtn = document.getElementById('nav-ask-btn');
const navHistoryBtn = document.getElementById('nav-history-btn');
const viewAsk = document.getElementById('view-ask');
const viewHistory = document.getElementById('view-history');

const askForm = document.getElementById('ask-form');
const questionInput = document.getElementById('question-input');
const askSubmitBtn = document.getElementById('ask-submit-btn');
const resultsPanel = document.getElementById('results-panel');
const resultTag = document.getElementById('result-tag');
const similarQuestionsList = document.getElementById('similar-questions-list');
const charCount = document.getElementById('char-count');

const historyTagFilter = document.getElementById('history-tag-filter');
const historyListContainer = document.getElementById('history-list-container');

// API Base URL (runs on the same host and port)
const API_BASE = '/api';

// ==========================================================================
// Initialization
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
    // Check if user is already logged in
    const token = localStorage.getItem('token');
    const email = localStorage.getItem('email');
    
    if (token && email) {
        currentUser = { token, email };
        userEmailDisplay.textContent = email;
        showDashboard();
        loadTags();
    } else {
        showAuth();
    }
});

// ==========================================================================
// Navigation & UI Toggle Helpers
// ==========================================================================
function showAuth() {
    authSection.classList.remove('hidden');
    dashboardSection.classList.add('hidden');
    clearAuthForm();
}

function showDashboard() {
    authSection.classList.add('hidden');
    dashboardSection.classList.remove('hidden');
    switchView('ask');
}

function clearAuthForm() {
    authEmail.value = '';
    authPassword.value = '';
    authError.classList.add('hidden');
}

function switchAuthTab(mode) {
    currentAuthMode = mode;
    authError.classList.add('hidden');
    
    if (mode === 'login') {
        tabLoginBtn.classList.add('active');
        tabSignupBtn.classList.remove('active');
        authSubtext.textContent = 'Find similar past questions and automatically tag subjects using advanced AI.';
        authSubmitBtn.querySelector('span').textContent = 'Log In';
    } else {
        tabLoginBtn.classList.remove('active');
        tabSignupBtn.classList.add('active');
        authSubtext.textContent = 'Create your free student account to start analyzing your study questions.';
        authSubmitBtn.querySelector('span').textContent = 'Sign Up';
    }
}

function switchView(view) {
    activeView = view;
    
    if (view === 'ask') {
        navAskBtn.classList.add('active');
        navHistoryBtn.classList.remove('active');
        viewAsk.classList.add('active');
        viewHistory.classList.remove('active');
    } else {
        navAskBtn.classList.remove('active');
        navHistoryBtn.classList.add('active');
        viewAsk.classList.remove('active');
        viewHistory.classList.add('active');
        loadHistory();
    }
}

function updateCharCount(textarea) {
    const length = textarea.value.length;
    charCount.textContent = `${length} / 1000`;
}

function getTagClass(tag) {
    return tag.toLowerCase().replace(/\s+/g, '-');
}

// ==========================================================================
// Authentication Logic
// ==========================================================================
async function handleAuthSubmit(event) {
    event.preventDefault();
    
    const email = authEmail.value.trim();
    const password = authPassword.value;
    
    // UI Loading State
    authSubmitBtn.disabled = true;
    const btnText = authSubmitBtn.querySelector('span');
    const originalText = btnText.textContent;
    btnText.innerHTML = '<span class="spinner"></span> Processing...';
    authError.classList.add('hidden');
    
    try {
        const endpoint = currentAuthMode === 'login' ? '/auth/login' : '/auth/signup';
        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Authentication failed');
        }
        
        // Save auth data
        localStorage.setItem('token', data.token);
        localStorage.setItem('email', data.email);
        currentUser = { token: data.token, email: data.email };
        
        // Update user UI and show dashboard
        userEmailDisplay.textContent = data.email;
        showDashboard();
        loadTags();
    } catch (err) {
        authErrorText.textContent = err.message;
        authError.classList.remove('hidden');
    } finally {
        authSubmitBtn.disabled = false;
        btnText.textContent = originalText;
    }
}

function handleLogout() {
    localStorage.removeItem('token');
    localStorage.removeItem('email');
    currentUser = null;
    showAuth();
}

// ==========================================================================
// Question Analysis & Search
// ==========================================================================
async function handleAskSubmit(event) {
    event.preventDefault();
    
    const text = questionInput.value.trim();
    if (!text) return;
    
    // UI Loading State
    askSubmitBtn.disabled = true;
    const btnText = askSubmitBtn.querySelector('span');
    const originalText = btnText.textContent;
    btnText.innerHTML = '<span class="spinner"></span> Matching past questions...';
    resultsPanel.classList.add('hidden');
    
    try {
        const response = await fetch(`${API_BASE}/questions/ask`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${currentUser.token}`
            },
            body: JSON.stringify({ text })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Failed to submit question');
        }
        
        // Populate results
        resultTag.textContent = data.tag;
        // Reset classes and apply correct tag class
        resultTag.className = 'tag-badge';
        resultTag.classList.add(getTagClass(data.tag));
        
        // Populate similar questions list
        similarQuestionsList.innerHTML = '';
        
        if (data.similar_questions && data.similar_questions.length > 0) {
            data.similar_questions.forEach(item => {
                const percentage = Math.round(item.similarity_score * 100);
                const scoreLabel = percentage >= 85 ? 'Highly Similar' : (percentage >= 60 ? 'Moderate Match' : 'Weak Match');
                
                const card = document.createElement('div');
                card.className = 'similar-card';
                card.innerHTML = `
                    <div class="similar-card-header">
                        <span class="tag-badge ${getTagClass(item.tag)}">${item.tag}</span>
                        <div class="match-score-container" title="Similarity Score: ${item.similarity_score.toFixed(4)}">
                            <i class="fa-solid fa-gauge-high"></i>
                            <span>${percentage}% Match (${scoreLabel})</span>
                        </div>
                    </div>
                    <div class="similar-card-body">
                        "${escapeHtml(item.text)}"
                    </div>
                    <div class="similar-card-footer">
                        <div class="similarity-bar-wrapper">
                            <span class="similarity-bar-label">Confidence</span>
                            <div class="similarity-bar-bg">
                                <div class="similarity-bar-fill" style="width: 0%"></div>
                            </div>
                        </div>
                        <span class="created-date">Asked: ${formatDate(item.created_at)}</span>
                    </div>
                `;
                similarQuestionsList.appendChild(card);
                
                // Animate similarity bar fill
                setTimeout(() => {
                    const fill = card.querySelector('.similarity-bar-fill');
                    if (fill) fill.style.width = `${percentage}%`;
                }, 100);
            });
        } else {
            similarQuestionsList.innerHTML = `
                <div class="no-results-card">
                    <i class="fa-regular fa-folder-open"></i>
                    <p>No similar past questions found yet in the system.</p>
                    <span style="font-size:12px; color:var(--text-muted);">As other students ask questions, matches will start to show up here.</span>
                </div>
            `;
        }
        
        // Show results panel
        resultsPanel.classList.remove('hidden');
        resultsPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch (err) {
        alert(`Error: ${err.message}`);
    } finally {
        askSubmitBtn.disabled = false;
        btnText.textContent = originalText;
    }
}

// ==========================================================================
// History Management
// ==========================================================================
async function loadTags() {
    try {
        const response = await fetch(`${API_BASE}/tags`, {
            headers: { 'Authorization': `Bearer ${currentUser.token}` }
        });
        if (!response.ok) return;
        
        const tags = await response.json();
        
        // Populate filter dropdown
        historyTagFilter.innerHTML = '<option value="All">All Subjects</option>';
        tags.forEach(tag => {
            const option = document.createElement('option');
            option.value = tag;
            option.textContent = tag;
            historyTagFilter.appendChild(option);
        });
    } catch (err) {
        console.error('Failed to load topic tags:', err);
    }
}

async function loadHistory() {
    historyListContainer.innerHTML = `
        <div style="text-align:center; padding: 40px;">
            <span class="spinner" style="border-top-color: var(--primary)"></span>
            <p style="margin-top: 10px; color: var(--text-secondary)">Loading your search history...</p>
        </div>
    `;
    
    const filterTag = historyTagFilter.value;
    
    try {
        const response = await fetch(`${API_BASE}/questions/history?tag=${encodeURIComponent(filterTag)}`, {
            headers: { 'Authorization': `Bearer ${currentUser.token}` }
        });
        
        if (!response.ok) {
            throw new Error('Failed to load history items');
        }
        
        const historyData = await response.json();
        historyListContainer.innerHTML = '';
        
        if (historyData.length === 0) {
            historyListContainer.innerHTML = `
                <div class="empty-history">
                    <i class="fa-regular fa-comments"></i>
                    <h4>No history entries found</h4>
                    <p>${filterTag === 'All' ? 'You have not asked any study questions yet.' : `No past questions found in the "${filterTag}" category.`}</p>
                </div>
            `;
            return;
        }
        
        historyData.forEach(item => {
            const card = document.createElement('div');
            card.className = 'history-card';
            
            // Build similar questions html
            let similarHtml = '';
            if (item.similar_questions && item.similar_questions.length > 0) {
                item.similar_questions.forEach(sim => {
                    const percentage = Math.round(sim.similarity_score * 100);
                    similarHtml += `
                        <div class="similar-card" style="margin-bottom:10px;">
                            <div class="similar-card-header" style="padding-bottom:0;">
                                <span class="tag-badge ${getTagClass(sim.tag)}">${sim.tag}</span>
                                <div class="match-score-container">
                                    <i class="fa-solid fa-gauge-high"></i>
                                    <span>${percentage}% Match</span>
                                </div>
                            </div>
                            <div class="similar-card-body" style="font-size:13.5px; padding:10px 0 5px 0;">
                                "${escapeHtml(sim.text)}"
                            </div>
                            <div class="similar-card-footer">
                                <span>Asked: ${formatDate(sim.created_at)}</span>
                            </div>
                        </div>
                    `;
                });
            } else {
                similarHtml = '<p style="color:var(--text-muted); font-size:13px;">No similar questions were found at the time.</p>';
            }
            
            card.innerHTML = `
                <div class="history-card-summary" onclick="toggleHistoryCard(this)">
                    <div class="history-q-meta">
                        <div class="history-q-text">"${escapeHtml(item.text)}"</div>
                        <div class="history-q-badges">
                            <span class="tag-badge ${getTagClass(item.tag)}">${item.tag}</span>
                            <span class="history-date">
                                <i class="fa-regular fa-clock" style="margin-right:4px;"></i>
                                ${formatDate(item.created_at)}
                            </span>
                        </div>
                    </div>
                    <div class="history-card-actions">
                        <i class="fa-solid fa-chevron-down history-toggle-icon"></i>
                    </div>
                </div>
                <div class="history-card-details">
                    <h5>Matches Found:</h5>
                    <div class="history-matches-list">
                        ${similarHtml}
                    </div>
                </div>
            `;
            
            historyListContainer.appendChild(card);
        });
    } catch (err) {
        historyListContainer.innerHTML = `
            <div class="empty-history" style="border-color: var(--error)">
                <i class="fa-solid fa-triangle-exclamation" style="color: var(--error)"></i>
                <h4 style="color: var(--error)">Error loading history</h4>
                <p>${err.message}</p>
            </div>
        `;
    }
}

function toggleHistoryCard(summaryEl) {
    const card = summaryEl.parentElement;
    card.classList.toggle('expanded');
}

// ==========================================================================
// Formatting & Escaping Utilities
// ==========================================================================
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, function(m) { return map[m]; });
}

function formatDate(dateString) {
    // Converts SQLite UTC timestamp to a local readable date/time
    // Handles format like "YYYY-MM-DD HH:MM:SS" or standard ISO
    let dateStr = dateString;
    if (dateString && !dateString.includes('T') && !dateString.includes('Z')) {
        // Appends UTC designation to SQLite's date representation to parse correctly
        dateStr = dateString.replace(' ', 'T') + 'Z';
    }
    
    try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateString;
        
        return d.toLocaleDateString(undefined, {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return dateString;
    }
}
