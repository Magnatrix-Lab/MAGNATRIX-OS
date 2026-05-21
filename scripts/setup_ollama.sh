#!/bin/bash
# MAGNATRIX Ollama Setup — REAL installer
set -e

echo "🧠 Setting up Ollama for MAGNATRIX..."

# Detect OS
OS=$(uname -s)
ARCH=$(uname -m)

echo "Detected: $OS $ARCH"

# Install Ollama
if ! command -v ollama &> /dev/null; then
    echo "📦 Installing Ollama..."
    if [[ "$OS" == "Linux" ]]; then
        curl -fsSL https://ollama.com/install.sh | sh
    elif [[ "$OS" == "Darwin" ]]; then
        brew install ollama || curl -fsSL https://ollama.com/install.sh | sh
    else
        echo "⚠️ Please install Ollama manually: https://ollama.com/download"
        exit 1
    fi
else
    echo "✅ Ollama already installed: $(ollama --version)"
fi

# Pull model
echo "📥 Pulling llama3 (lightweight model)..."
ollama pull llama3 || echo "⚠️ Pull failed. Manual: ollama pull llama3"

# Test
echo "🧪 Testing..."
RESPONSE=$(ollama run llama3 "Say 'MAGNATRIX OS ready' in 3 words" 2>/dev/null || echo "NOT_READY")
if echo "$RESPONSE" | grep -qi "ready"; then
    echo "✅ Ollama + llama3 working!"
    echo "Response: $RESPONSE"
else
    echo "⚠️ Ollama installed but model not responding. Start: ollama serve"
fi

# Update config
echo "📝 Updating magnatrix.toml..."
if [ -f magnatrix.toml ]; then
    sed -i 's/provider = "mock"/provider = "ollama"/' magnatrix.toml
    sed -i 's/model = "mock"/model = "llama3"/' magnatrix.toml
    echo "✅ Config updated."
fi

echo "🎯 Ollama setup complete!"
echo "   Start server: ollama serve"
echo "   Test: ollama run llama3 'Hello'"
