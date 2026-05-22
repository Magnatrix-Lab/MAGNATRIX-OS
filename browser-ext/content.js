// content.js — MAGNATRIX Browser Extension Content Script
// Injected into web pages for DOM interaction and data extraction

(function() {
    'use strict';

    const MAGNATRIX_ID = 'magnatrix-content-bridge';

    // Prevent double injection
    if (document.getElementById(MAGNATRIX_ID)) return;
    const marker = document.createElement('div');
    marker.id = MAGNATRIX_ID;
    marker.style.display = 'none';
    document.body.appendChild(marker);

    // Listen for messages from the extension
    window.addEventListener('message', (event) => {
        if (event.source !== window) return;
        if (event.data.type === 'MAGNATRIX_REQUEST') {
            handleMagnatrixRequest(event.data.payload);
        }
    });

    function handleMagnatrixRequest(request) {
        switch (request.action) {
            case 'extractDOM':
                const domData = {
                    url: window.location.href,
                    title: document.title,
                    meta: getMetaTags(),
                    forms: getForms(),
                    tables: getTables(),
                    structured: getStructuredData()
                };
                window.postMessage({
                    type: 'MAGNATRIX_RESPONSE',
                    id: request.id,
                    data: domData
                }, '*');
                break;
            case 'fillForm':
                fillFormFields(request.fields);
                break;
            case 'clickElement':
                clickElement(request.selector);
                break;
            case 'scrollTo':
                scrollToElement(request.selector);
                break;
            case 'highlight':
                highlightElements(request.selector);
                break;
        }
    }

    function getMetaTags() {
        const meta = {};
        document.querySelectorAll('meta').forEach(m => {
            const name = m.getAttribute('name') || m.getAttribute('property');
            const content = m.getAttribute('content');
            if (name && content) meta[name] = content;
        });
        return meta;
    }

    function getForms() {
        return Array.from(document.querySelectorAll('form')).map(f => ({
            action: f.action,
            method: f.method,
            fields: Array.from(f.querySelectorAll('input, textarea, select')).map(i => ({
                name: i.name,
                type: i.type,
                value: i.value,
                placeholder: i.placeholder
            }))
        }));
    }

    function getTables() {
        return Array.from(document.querySelectorAll('table')).map(t => {
            const rows = Array.from(t.querySelectorAll('tr')).map(r =>
                Array.from(r.querySelectorAll('td, th')).map(c => c.innerText)
            );
            return { rows };
        }).slice(0, 5);
    }

    function getStructuredData() {
        // Extract JSON-LD structured data
        const scripts = document.querySelectorAll('script[type="application/ld+json"]');
        return Array.from(scripts).map(s => {
            try {
                return JSON.parse(s.innerText);
            } catch (e) {
                return null;
            }
        }).filter(Boolean);
    }

    function fillFormFields(fields) {
        Object.entries(fields).forEach(([name, value]) => {
            const input = document.querySelector(`[name="${name}"]`);
            if (input) {
                input.value = value;
                input.dispatchEvent(new Event('input', { bubbles: true }));
            }
        });
    }

    function clickElement(selector) {
        const el = document.querySelector(selector);
        if (el) el.click();
    }

    function scrollToElement(selector) {
        const el = document.querySelector(selector);
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function highlightElements(selector) {
        document.querySelectorAll(selector).forEach(el => {
            el.style.outline = '3px solid #ff00ff';
            el.style.outlineOffset = '2px';
            setTimeout(() => {
                el.style.outline = '';
                el.style.outlineOffset = '';
            }, 3000);
        });
    }

    // Auto-detect and report page changes
    let lastUrl = window.location.href;
    const observer = new MutationObserver(() => {
        if (window.location.href !== lastUrl) {
            lastUrl = window.location.href;
            chrome.runtime.sendMessage({
                action: 'pageChanged',
                url: lastUrl,
                title: document.title
            });
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });

    console.log('[MAGNATRIX] Content script injected');
})();
