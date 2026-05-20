#!/bin/bash
# MAGNATRIX Agentic OS — One-Command Installer
set -e

echo "🧠 Installing MAGNATRIX Agentic OS..."

# Check prerequisites
check_cmd() {
    if command -v "$1" &> /dev/null; then
        echo "✅ $1 found"
        return 0
    else
        echo "❌ $1 not found"
        return 1
    fi
}

check_cmd node || { echo "Install Node.js 18+"; exit 1; }
check_cmd npm || { echo "Install npm"; exit 1; }
check_cmd python3 || { echo "Install Python 3.10+"; exit 1; }
check_cmd pip3 || { echo "Install pip3"; exit 1; }

# Rust optional
if check_cmd rustc; then
    echo "✅ Rust found"
else
    echo "⚠️ Rust not found. Kernel will use Node.js fallback."
fi

# Install dependencies
echo "📦 Installing Node.js dependencies..."
cd protocol && npm install @modelcontextprotocol/sdk && cd ..
cd collective-brain && npm install @grpc/grpc-js @grpc/proto-loader && cd ..

echo "📦 Installing Python dependencies..."
cd trading && pip3 install -r requirements.txt && cd ..
cd mobile && pip3 install -r requirements.txt && cd ..

echo "🔧 Generating default config..."
cp magnatrix.toml ~/.magnatrix.toml

echo "✅ MAGNATRIX installed. Run: ./scripts/boot.js"
