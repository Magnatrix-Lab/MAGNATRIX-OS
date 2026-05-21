#!/bin/bash
# MAGNATRIX Agentic OS — One-Command Installer v2.0 (Phase 4-5 AGI + Super AI)
set -e

MAGENTA='\033[35m'
CYAN='\033[36m'
GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
NC='\033[0m'

log() { echo -e "${CYAN}[MAGNATRIX]${NC} $1"; }
ok() { echo -e "${GREEN}  ✓${NC} $1"; }
warn() { echo -e "${YELLOW}  ⚠${NC} $1"; }
fail() { echo -e "${RED}  ✗${NC} $1"; }

log "🧠 MAGNATRIX Agentic OS Installer v2.0 — Target: Super AI"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── prerequisites ──
log "Checking prerequisites..."

MISSING=0
check_cmd() {
    if command -v "$1" &> /dev/null; then
        ok "$1 found"
        return 0
    else
        fail "$1 not found"
        MISSING=1
        return 1
    fi
}

check_cmd docker || { log "Docker required. Install: https://docs.docker.com/get-docker/"; }
check_cmd docker-compose || check_cmd "docker compose" || { log "Docker Compose required."; }
check_cmd node || { log "Node.js 18+ required for kernel/protocol layers."; }
check_cmd python3 || { log "Python 3.10+ required for all AI layers."; }
check_cmd pip3 || { log "pip3 required for Python dependencies."; }

if [ $MISSING -ne 0 ]; then
    log "Install missing prerequisites and re-run."
    exit 1
fi

# Rust optional
if check_cmd rustc; then
    ok "Rust found — kernel will use native performance"
else
    warn "Rust not found. Kernel will use Node.js fallback."
fi

# ── generate .env ──
log "Generating environment configuration..."
cat > .env <<'EOF'
# MAGNATRIX Agentic OS — Environment Configuration
NODE_ENV=production
MAGNATRIX_LOG_LEVEL=info
MAGNATRIX_DATA_DIR=./data
MAGNATRIX_KNOWLEDGE_DIR=./knowledge
MAGNATRIX_LOGS_DIR=./logs

# Layer addresses (internal Docker network)
KERNEL_URL=http://kernel:3000
PROTOCOL_URL=http://protocol:50051
API_ROUTER_URL=http://api-router:8080
IDENTITY_URL=http://identity:8081
RUNTIME_URL=http://runtime:8082
P2P_URL=http://p2p-mesh:8083
KNOWLEDGE_URL=http://knowledge:8084
SKILLS_URL=http://skills:8085
BROWSER_URL=http://browser:8086
TRADING_URL=http://trading:8087
SECURITY_URL=http://security:8088
GOVERNANCE_URL=http://governance:8089
IDE_URL=http://ide:8090
OFFENSIVE_URL=http://offensive:8091
HUNTER_URL=http://hunter:8092
COLLECTIVE_BRAIN_URL=http://collective-brain:8093

# Uncensored AI (Ollama)
OLLAMA_HOST=http://uncensored:11434
OLLAMA_MODEL=llama3-uncensored

# Trading (demo mode default — set LIVE=1 for real trading)
TRADING_MODE=demo
TRADING_REINVESTMENT_RATE=0.30
TRADING_RESERVE_RATE=0.50

# Governance
CONSTITUTION_MAX_SHARE=0.30
CONSTITUTION_EMERGENCY_THRESHOLD=0.35
EOF
ok ".env generated"

# ── install Python dependencies ──
log "Installing Python dependencies..."
pip3 install -q fastapi uvicorn grpcio grpcio-tools websockets aiohttp aiofiles 2>/dev/null || warn "Some pip packages may need manual install"
ok "Python dependencies"

# ── build & start ──
log "Building and starting MAGNATRIX services..."
if command -v docker-compose &> /dev/null; then
    docker-compose up --build -d
else
    docker compose up --build -d
fi

# ── health check ──
log "Running health checks..."
sleep 5

SERVICES=(
    "kernel:3000"
    "protocol:50051"
    "api-router:8080"
    "identity:8081"
    "runtime:8082"
    "p2p-mesh:8083"
    "knowledge:8084"
    "skills:8085"
    "browser:8086"
    "trading:8087"
    "security:8088"
    "governance:8089"
    "ide:8090"
    "offensive:8091"
    "hunter:8092"
    "collective-brain:8093"
)

HEALTHY=0
UNHEALTHY=0
for svc in "${SERVICES[@]}"; do
    name="${svc%%:*}"
    port="${svc##*:}"
    if docker exec "magnatrix-${name}" wget -q --spider "http://localhost:${port}/health" 2>/dev/null; then
        ok "${name} healthy"
        ((HEALTHY++))
    else
        warn "${name} health check pending (may need more time)"
        ((UNHEALTHY++))
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${MAGENTA}  MAGNATRIX Agentic OS installed${NC}"
echo -e "  ${GREEN}${HEALTHY}/${#SERVICES[@]}${NC} services healthy"
echo ""
echo -e "  ${CYAN}Boot:${NC}         ./scripts/magnatrix-boot.py"
echo -e "  ${CYAN}Evolve:${NC}       ./scripts/self_evolve.py --continuous"
echo -e "  ${CYAN}Logs:${NC}         docker-compose logs -f"
echo -e "  ${CYAN}Shutdown:${NC}     docker-compose down"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
