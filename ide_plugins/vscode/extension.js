// extension.js — MAGNATRIX VS Code Extension
// AI-powered coding assistant with swarm integration

const vscode = require('vscode');

const MAGNATRIX_API = 'http://localhost:8080';

function activate(context) {
    console.log('[MAGNATRIX] VS Code extension activated');

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('magnatrix.start', startMagnatrix),
        vscode.commands.registerCommand('magnatrix.stop', stopMagnatrix),
        vscode.commands.registerCommand('magnatrix.query', queryKnowledgeGraph),
        vscode.commands.registerCommand('magnatrix.generate', generateCode),
        vscode.commands.registerCommand('magnatrix.explain', explainCode),
        vscode.commands.registerCommand('magnatrix.refactor', refactorCode),
        vscode.commands.registerCommand('magnatrix.status', showStatus)
    );

    // Status bar item
    const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBarItem.text = "$(hubot) MAGNATRIX";
    statusBarItem.tooltip = "MAGNATRIX Agentic OS";
    statusBarItem.command = 'magnatrix.status';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    // Auto-start if configured
    const config = vscode.workspace.getConfiguration('magnatrix');
    if (config.get('autoStart')) {
        startMagnatrix();
    }
}

async function startMagnatrix() {
    vscode.window.showInformationMessage('🧠 Starting MAGNATRIX Agentic OS...');
    try {
        const response = await fetch(`${MAGNATRIX_API}/health`);
        if (response.ok) {
            vscode.window.showInformationMessage('✅ MAGNATRIX is running');
        } else {
            vscode.window.showWarningMessage('⚠️ MAGNATRIX API not responding');
        }
    } catch (e) {
        vscode.window.showErrorMessage(`❌ MAGNATRIX connection failed: ${e.message}`);
    }
}

async function stopMagnatrix() {
    vscode.window.showInformationMessage('🛑 Stopping MAGNATRIX...');
}

async function queryKnowledgeGraph() {
    const query = await vscode.window.showInputBox({
        prompt: 'Enter knowledge graph query',
        placeHolder: 'e.g., "trading strategies" or "security vulnerabilities"'
    });
    if (!query) return;

    try {
        const response = await fetch(`${MAGNATRIX_API}/api/v2/knowledge/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ entity: query, depth: 2 })
        });
        const data = await response.json();
        const panel = vscode.window.createWebviewPanel(
            'magnatrixQuery',
            `MAGNATRIX: ${query}`,
            vscode.ViewColumn.Two,
            {}
        );
        panel.webview.html = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
    } catch (e) {
        vscode.window.showErrorMessage(`Query failed: ${e.message}`);
    }
}

async function generateCode() {
    const prompt = await vscode.window.showInputBox({
        prompt: 'Describe the code you want to generate',
        placeHolder: 'e.g., "function to calculate fibonacci"'
    });
    if (!prompt) return;

    try {
        const editor = vscode.window.activeTextEditor;
        const language = editor ? editor.document.languageId : 'python';
        
        vscode.window.showInformationMessage(`🤖 MAGNATRIX generating ${language} code...`);
        
        // Simulated code generation
        const generated = `// MAGNATRIX Auto-generated code
// Prompt: ${prompt}
// Generated: ${new Date().toISOString()}

function ${prompt.replace(/\s+/g, '_')}() {
    // TODO: Implement based on prompt
    console.log("Implement: ${prompt}");
}

module.exports = { ${prompt.replace(/\s+/g, '_')} };`;

        if (editor) {
            const position = editor.selection.active;
            editor.edit(editBuilder => {
                editBuilder.insert(position, '\n' + generated + '\n');
            });
        }
        
        vscode.window.showInformationMessage('✅ Code generated and inserted');
    } catch (e) {
        vscode.window.showErrorMessage(`Generation failed: ${e.message}`);
    }
}

async function explainCode() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('No code selected');
        return;
    }

    const selection = editor.document.getText(editor.selection);
    if (!selection) {
        vscode.window.showWarningMessage('Please select some code first');
        return;
    }

    const panel = vscode.window.createWebviewPanel(
        'magnatrixExplain',
        'MAGNATRIX: Code Explanation',
        vscode.ViewColumn.Two,
        {}
    );

    panel.webview.html = `
        <h2>Code Explanation</h2>
        <pre><code>${escapeHtml(selection)}</code></pre>
        <h3>Explanation:</h3>
        <p>This code performs operations on the selected snippet.</p>
        <p>MAGNATRIX AI would provide detailed semantic analysis here.</p>
    `;
}

async function refactorCode() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) return;

    const selection = editor.document.getText(editor.selection);
    if (!selection) {
        vscode.window.showWarningMessage('Please select code to refactor');
        return;
    }

    vscode.window.showInformationMessage('🔧 MAGNATRIX refactoring code...');
    
    // Simulated refactoring
    const refactored = selection
        .replace(/var /g, 'const ')
        .replace(/function\s+(\w+)/g, 'const $1 = function');

    editor.edit(editBuilder => {
        editBuilder.replace(editor.selection, refactored);
    });

    vscode.window.showInformationMessage('✅ Refactoring applied');
}

async function showStatus() {
    try {
        const response = await fetch(`${MAGNATRIX_API}/api/v2/status`);
        const data = await response.json();
        
        const panel = vscode.window.createWebviewPanel(
            'magnatrixStatus',
            'MAGNATRIX System Status',
            vscode.ViewColumn.One,
            {}
        );
        
        panel.webview.html = `
            <h1>🧠 MAGNATRIX Agentic OS</h1>
            <h2>System Status</h2>
            <pre>${JSON.stringify(data, null, 2)}</pre>
            <hr>
            <p>Layers: ${data.layers ? data.layers.length : 0} active</p>
            <p>Emergency Mode: ${data.emergency_mode ? '🔴 ACTIVE' : '🟢 Normal'}</p>
            <p>Cycles: ${data.cycle_count || 0}</p>
        `;
    } catch (e) {
        vscode.window.showErrorMessage(`Status check failed: ${e.message}`);
    }
}

function escapeHtml(text) {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function deactivate() {
    console.log('[MAGNATRIX] VS Code extension deactivated');
}

module.exports = { activate, deactivate };
