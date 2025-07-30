// Telegram Parser - Main JavaScript

// Global variables
let searchTimeout;
const API_BASE = '';

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize search
    initializeSearch();
    
    // Initialize export functionality
    initializeExport();
    
    // Add fade-in animation to cards
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        setTimeout(() => {
            card.classList.add('fade-in');
        }, index * 100);
    });
}

// Search functionality
function initializeSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');
    
    if (!searchInput) return;
    
    searchInput.addEventListener('input', function() {
        const query = this.value.trim();
        
        clearTimeout(searchTimeout);
        
        if (query.length < 3) {
            hideSearchResults();
            return;
        }
        
        searchTimeout = setTimeout(() => {
            performSearch(query);
        }, 300);
    });
    
    // Hide results when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.search-container')) {
            hideSearchResults();
        }
    });
}

async function performSearch(query) {
    const searchResults = document.getElementById('searchResults');
    const chatId = document.getElementById('searchChatId')?.value;
    
    if (!searchResults) return;
    
    try {
        showSearchLoading();
        
        const params = new URLSearchParams({
            q: query,
            limit: 10
        });
        
        if (chatId) {
            params.append('chat_id', chatId);
        }
        
        const response = await fetch(`${API_BASE}/api/search?${params}`);
        const data = await response.json();
        
        if (response.ok) {
            displaySearchResults(data.results);
        } else {
            showSearchError(data.error);
        }
    } catch (error) {
        showSearchError('Ошибка поиска: ' + error.message);
    }
}

function showSearchLoading() {
    const searchResults = document.getElementById('searchResults');
    searchResults.innerHTML = `
        <div class="search-result-item text-center">
            <div class="loading"></div>
            <span class="ms-2">Поиск...</span>
        </div>
    `;
    searchResults.style.display = 'block';
}

function displaySearchResults(results) {
    const searchResults = document.getElementById('searchResults');
    
    if (results.length === 0) {
        searchResults.innerHTML = `
            <div class="search-result-item text-center text-muted">
                <i class="bi bi-search"></i>
                <span class="ms-2">Ничего не найдено</span>
            </div>
        `;
        return;
    }
    
    const html = results.map(result => `
        <div class="search-result-item" onclick="selectSearchResult(${result.chat_id}, ${result.id})">
            <div class="d-flex justify-content-between align-items-start">
                <div class="flex-grow-1">
                    <div class="fw-bold">${escapeHtml(result.chat_name)}</div>
                    <div class="text-muted small">${escapeHtml(result.sender_name)}</div>
                    <div class="mt-1">${highlightSearchTerm(escapeHtml(result.text), document.getElementById('searchInput').value)}</div>
                </div>
                <small class="text-muted">${formatDate(result.date)}</small>
            </div>
        </div>
    `).join('');
    
    searchResults.innerHTML = html;
    searchResults.style.display = 'block';
}

function showSearchError(error) {
    const searchResults = document.getElementById('searchResults');
    searchResults.innerHTML = `
        <div class="search-result-item text-center text-danger">
            <i class="bi bi-exclamation-triangle"></i>
            <span class="ms-2">${escapeHtml(error)}</span>
        </div>
    `;
}

function hideSearchResults() {
    const searchResults = document.getElementById('searchResults');
    if (searchResults) {
        searchResults.style.display = 'none';
    }
}

function selectSearchResult(chatId, messageId) {
    // Navigate to chat detail page
    window.location.href = `/chat/${chatId}#message-${messageId}`;
    hideSearchResults();
}

// Export functionality
function initializeExport() {
    const exportButtons = document.querySelectorAll('[data-export-type]');
    
    exportButtons.forEach(button => {
        button.addEventListener('click', function() {
            const exportType = this.dataset.exportType;
            const chatId = this.dataset.chatId;
            const days = this.dataset.days;
            
            performExport(exportType, chatId, days, this);
        });
    });
}

async function performExport(exportType, chatId = null, days = null, button = null) {
    if (button) {
        button.disabled = true;
        const originalText = button.innerHTML;
        button.innerHTML = '<div class="loading me-2"></div>Экспорт...';
        
        // Restore button after timeout
        setTimeout(() => {
            button.disabled = false;
            button.innerHTML = originalText;
        }, 5000);
    }
    
    try {
        const params = new URLSearchParams();
        if (chatId) params.append('chat_id', chatId);
        if (days) params.append('days', days);
        
        const response = await fetch(`${API_BASE}/api/export/${exportType}?${params}`);
        const data = await response.json();
        
        if (response.ok) {
            if (data.files) {
                // Multiple files
                showNotification('success', `Создано файлов: ${Object.keys(data.files).length}`);
                displayExportFiles(data.files);
            } else {
                // Single file
                showNotification('success', `Файл создан: ${data.filename}`);
            }
        } else {
            showNotification('error', data.error);
        }
    } catch (error) {
        showNotification('error', 'Ошибка экспорта: ' + error.message);
    } finally {
        if (button) {
            button.disabled = false;
            button.innerHTML = button.dataset.originalText || 'Экспорт';
        }
    }
}

function displayExportFiles(files) {
    const exportResults = document.getElementById('exportResults');
    if (!exportResults) return;
    
    const html = Object.entries(files).map(([type, path]) => `
        <div class="alert alert-success">
            <i class="bi bi-file-earmark-check"></i>
            <strong>${type}:</strong> ${path.split('/').pop()}
        </div>
    `).join('');
    
    exportResults.innerHTML = html;
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function highlightSearchTerm(text, term) {
    if (!term) return text;
    
    const regex = new RegExp(`(${escapeRegex(term)})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
}

function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
        return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    } else if (diffDays === 1) {
        return 'Вчера';
    } else if (diffDays < 7) {
        return `${diffDays} дн. назад`;
    } else {
        return date.toLocaleDateString('ru-RU');
    }
}

function showNotification(type, message) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : 'success'} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Chart helpers
function createTimeChart(canvasId, data, label) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    
    new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            labels: data.map(item => item.label),
            datasets: [{
                label: label,
                data: data.map(item => item.value),
                borderColor: 'rgba(13, 110, 253, 1)',
                backgroundColor: 'rgba(13, 110, 253, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

function createEmojiChart(canvasId, emojiData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || !emojiData || emojiData.length === 0) return;
    
    new Chart(ctx.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: emojiData.map(item => item.emoji),
            datasets: [{
                data: emojiData.map(item => item.count),
                backgroundColor: [
                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                    '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// Analytics page specific functionality
if (window.location.pathname.includes('/analytics')) {
    document.addEventListener('DOMContentLoaded', function() {
        // Initialize charts for analytics page
        setTimeout(() => {
            initializeAnalyticsCharts();
        }, 500);
    });
}

function initializeAnalyticsCharts() {
    // Time activity chart
    const timeData = window.timeAnalysisData;
    if (timeData && timeData.by_hour) {
        createTimeChart('timeChart', 
            timeData.by_hour.map(h => ({
                label: h.hour + ':00',
                value: h.count
            })), 
            'Сообщений по часам'
        );
    }
    
    // Emoji chart
    const emojiData = window.emojiData;
    if (emojiData && emojiData.most_used_emojis) {
        createEmojiChart('emojiChart', emojiData.most_used_emojis.slice(0, 8));
    }
}

// Real-time updates (if needed)
function startRealTimeUpdates() {
    // Poll for updates every 30 seconds
    setInterval(async () => {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            if (data.new_data_available) {
                showNotification('info', 'Доступны новые данные. Обновите страницу.');
            }
        } catch (error) {
            // Silently fail
        }
    }, 30000);
}

// Export current page as PDF (future feature)
function exportToPDF() {
    showNotification('info', 'Функция экспорта в PDF будет добавлена в следующей версии');
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl+K for search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.focus();
        }
    }
    
    // Escape to close search results
    if (e.key === 'Escape') {
        hideSearchResults();
    }
});

console.log('🚀 Telegram Parser Web Interface loaded successfully!');