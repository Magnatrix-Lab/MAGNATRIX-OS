// background.js — MAGNATRIX Browser Extension Background Service Worker
// Manages connections to MAGNATRIX API, tab monitoring, and data capture

const MAGNATRIX_API = 'http://localhost:8080';
let activeSessions = new Map();

chrome.runtime.onInstalled.addListener(() => {
    console.log('[MAGNATRIX] Extension installed');
    chrome.storage.local.set({ magnatrixEnabled: true, captureMode: 'auto' });
});

// Listen for messages from content scripts and popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    switch (request.action) {
        case 'capturePage':
            capturePageData(sender.tab).then(sendResponse);
            return true;
        case 'sendToMagnatrix':
            sendToMagnatrixAPI(request.data).then(sendResponse);
            return true;
        case 'getTabInfo':
            getTabInfo(sender.tab).then(sendResponse);
            return true;
        case 'startSession':
            startSession(request.sessionId, sender.tab);
            sendResponse({ status: 'started' });
            break;
        case 'endSession':
            endSession(request.sessionId);
            sendResponse({ status: 'ended' });
            break;
        case 'queryMagnatrix':
            queryMagnatrix(request.query).then(sendResponse);
            return true;
    }
});

async function capturePageData(tab) {
    try {
        const [result] = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: extractPageData
        });
        return { success: true, data: result.result };
    } catch (e) {
        return { success: false, error: e.message };
    }
}

function extractPageData() {
    return {
        url: window.location.href,
        title: document.title,
        timestamp: new Date().toISOString(),
        textContent: document.body.innerText.substring(0, 5000),
        links: Array.from(document.querySelectorAll('a[href]')).map(a => ({
            text: a.innerText,
            href: a.href
        })).slice(0, 50),
        images: Array.from(document.querySelectorAll('img[src]')).map(img => ({
            src: img.src,
            alt: img.alt
        })).slice(0, 20),
        headings: Array.from(document.querySelectorAll('h1,h2,h3')).map(h => ({
            level: h.tagName,
            text: h.innerText
        })).slice(0, 20)
    };
}

async function sendToMagnatrixAPI(data) {
    try {
        const response = await fetch(`${MAGNATRIX_API}/api/browser/capture`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return { success: response.ok, status: response.status };
    } catch (e) {
        return { success: false, error: e.message };
    }
}

async function getTabInfo(tab) {
    return {
        id: tab.id,
        url: tab.url,
        title: tab.title,
        active: tab.active,
        windowId: tab.windowId
    };
}

function startSession(sessionId, tab) {
    activeSessions.set(sessionId, {
        tabId: tab.id,
        startTime: Date.now(),
        captures: []
    });
}

function endSession(sessionId) {
    const session = activeSessions.get(sessionId);
    if (session) {
        activeSessions.delete(sessionId);
    }
}

async function queryMagnatrix(query) {
    try {
        const response = await fetch(`${MAGNATRIX_API}/api/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, source: 'browser-extension' })
        });
        const data = await response.json();
        return { success: true, data };
    } catch (e) {
        return { success: false, error: e.message };
    }
}

// Tab monitoring for auto-capture
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url) {
        chrome.storage.local.get(['magnatrixEnabled', 'captureMode'], (settings) => {
            if (settings.magnatrixEnabled && settings.captureMode === 'auto') {
                // Auto-capture after page load
                setTimeout(() => {
                    capturePageData(tab).then(result => {
                        if (result.success) {
                            sendToMagnatrixAPI({
                                type: 'auto-capture',
                                tabId,
                                ...result.data
                            });
                        }
                    });
                }, 2000);
            }
        });
    }
});

// Periodic health check to MAGNATRIX
setInterval(async () => {
    try {
        const response = await fetch(`${MAGNATRIX_API}/health`, { method: 'GET' });
        chrome.runtime.sendMessage({
            type: 'healthUpdate',
            status: response.ok ? 'online' : 'offline'
        });
    } catch (e) {
        chrome.runtime.sendMessage({
            type: 'healthUpdate',
            status: 'offline'
        });
    }
}, 30000);
