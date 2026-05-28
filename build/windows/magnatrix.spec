# -*- mode: python ; coding: utf-8 -*-
"""
MAGNATRIX-OS PyInstaller Spec
══════════════════════════════
Build single-folder Windows executable.
Usage:  python -m PyInstaller build/windows/magnatrix.spec
"""
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
from PyInstaller.building.datastruct import TOC
from pathlib import Path
import os

# ── Paths ──────────────────────────────────────────────────────────────────
SPEC_DIR = Path(os.path.abspath(SPECPATH))           # build/windows/
REPO_ROOT = SPEC_DIR.parent.parent                    # MAGNATRIX-OS/
ENTRY = str(SPEC_DIR / "magnatrix_win.py")
ICON = str(SPEC_DIR / "magnatrix.ico")

# ── Auto-scan hidden imports from *_native.py ─────────────────────────────
def _scan_native_modules(root: Path) -> list:
    """Find all *_native.py modules for hidden imports."""
    hidden = []
    for pyfile in root.rglob("*_native.py"):
        rel = pyfile.relative_to(root).with_suffix("")
        module = str(rel).replace(os.sep, ".")
        hidden.append(module)
    return sorted(set(hidden))

_native_imports = _scan_native_modules(REPO_ROOT)

# Extra hidden imports that may be dynamically imported
_extra_hidden = [
    "kernel.kernel_native",
    "kernel.api_versioning_native",
    "kernel.circuit_breaker_native",
    "kernel.event_store_native",
    "kernel.health_aggregator_native",
    "kernel.hooks_native",
    "kernel.interlayer_bridge_native",
    "kernel.log_rotator_native",
    "kernel.monitor_dashboard_native",
    "kernel.path_guard_native",
    "kernel.rate_limiter_native",
    "kernel.scheduler_native",
    "kernel.shutdown_manager_native",
    "kernel.syscall_native",
    "kernel.trace_propagator_native",
    "kernel.validate_input_native",
    "kernel.backpressure_native",
    "protocol.protocol_native",
    "api_router.api_router_native",
    "api_router.gateway_native",
    "identity.identity_native",
    "identity.agent_persona_native",
    "identity.crypto_identity_native",
    "runtime.asi_kernel_native",
    "runtime.autodev_native",
    "runtime.agent_collaboration_native",
    "runtime.multi_agent_swarm_native",
    "runtime.plugin_system_native",
    "runtime.state_management_native",
    "runtime.supervisor_native",
    "runtime.temporal_engine_native",
    "runtime.wasm_runtime_native",
    "runtime.websocket_server_native",
    "runtime.world_sim_native",
    "runtime.energy_grid_native",
    "runtime.sensor_mesh_native",
    "runtime.embodiment_native",
    "runtime.jit_compiler_native",
    "p2p_mesh.p2p_mesh_native",
    "p2p_mesh.p2p_transport_native",
    "p2p_mesh.dht_nat_native",
    "knowledge.vector_store_native",
    "knowledge.graph_database_native",
    "knowledge.episodic_native",
    "knowledge.agentic_rag_native",
    "knowledge.llamaindex_rag_native",
    "knowledge.document_agent_native",
    "knowledge.turbovec_native",
    "knowledge.openchronicle_native",
    "knowledge.context_manager_native",
    "knowledge.auto_research_native",
    "knowledge.applied_ml_native",
    "skills.hermes_skill_engine_native",
    "browser.browser_native",
    "browser.browser_engine_native",
    "browser.browser_automation_native",
    "hft.alpha101_native",
    "hft.quant_signal_engine_native",
    "security.crypto_engine_native",
    "security.secret_manager_native",
    "security.sandbox_native",
    "security.safe_eval_native",
    "security.replication_guard_native",
    "security.bytepeep_native",
    "security.offensive_security_native",
    "security.agentic_radar_native",
    "security.ajat_web3_security_native",
    "ai.autonomous_agent_native",
    "ai.meta_agent_native",
    "ai.self_improvement_native",
    "ai.cognitive_architecture_native",
    "ai.goal_alignment_native",
    "ai.theorem_prover_native",
    "ai.temporal_reasoning_native",
    "ai.counterfactual_native",
    "ai.causal_reasoning_native",
    "ai.ethical_reasoning_native",
    "ai.theory_of_mind_native",
    "ai.meta_cognition_native",
    "ai.uncensored_ai_native",
    "ai.llm_router_native",
    "ai.local_agent_native",
    "ai.gguf_loader_native",
    "ai.gguf_llama_bridge_native",
    "ai.openclaw_native",
    "ai.sandboxed_researcher_native",
    "ai.hyperpredict_native",
    "ai.reward_engine_native",
    "ai.rsi_engine_native",
    "ai.quantum_algo_native",
    "ai.quantum_bridge_native",
    "ai.bci_native",
    "ai.affective_native",
    "ai.hermes_agentic_native",
    "governance.governance_native",
    "governance.consensus_native",
    "governance.reputation_native",
    "governance.value_lock_native",
    "trading.exchange_adapter_native",
    "trading.paper_trading_native",
    "trading.amms_native",
    "trading.doppler_native",
    "trading.trademaster_native",
    "trading.fincept_terminal_native",
    "uncensored.ml_intern_native",
    "llm.llm_provider_native",
    "llm.inference_backend_native",
    "ide.ide_integration_native",
    "ide.terminal_multiplexer_native",
    "tasks.task_manager_native",
    "database.query_engine_native",
    "storage.persistence_native",
    "storage.file_ops_native",
    "storage.vfs_native",
    "storage.db_pool_native",
    "storage.time_series_native",
    "storage.migration_native",
    "streaming.event_stream_native",
    "system.mcp_server_native",
    "workflows.workflow_engine_native",
    "observability.metrics_native",
    "constitutional.constitutional_ai_native",
    "consensus.raft_native",
    "chat_bridge.chat_bridge_native",
    "config.config_schema_native",
    "desktop_tray.tray_native",
    "mobile.mobile_layer_native",
    "voice.voice_layer_native",
    "tests.chaos_native",
    "tests.chaos.raft_chaos_native",
    "tests.fuzzing.fuzz_harness_native",
    "tests.integration.test_tri_language",
    "auto_repo_hunter.repo_hunter_native",
    "auto_repo_hunter.pattern_extractor_native",
    "auto_repo_hunter.native_generator_native",
    "collective_brain.gbrain_native",
    "collective_brain.ai_agents_500_native",
    "collective_brain.anthropic_sdk_native",
    "collective_brain.autoagent_native",
    "collective_brain.bitterbot_native",
    "collective_brain.hermes_war_room_native",
    "collective_brain.livekit_agents_native",
    "collective_brain.agents.agent_zero_native",
    "collective_brain.agents.goose_native",
    "collective_brain.agents.nous_hermes_native",
    "runtime.go_patterns_native",
    "runtime.java_design_patterns_native",
    "runtime.linux_insides_native",
    "runtime.batch_c_devops_cloud_native",
    "runtime.batch_d_frontend_ui_native",
    "runtime.batch_e_misc_native",
    "runtime.cosmo_native",
    "runtime.hostinger_api_native",
    "runtime.nacos_native",
    "runtime.package_manager_native",
    "runtime.podman_native",
    "runtime.resource_optimizer_native",
    "runtime.ruff_native",
    "runtime.rye_native",
    "runtime.ue_modding_native",
    "platform_utils.puter_native",
    "collective_brain.openclaw_native",
]

hiddenimports = sorted(set(_native_imports + _extra_hidden))

# ── Data files to bundle ───────────────────────────────────────────────────
datas = [
    (str(REPO_ROOT / "website"), "website"),
    (str(REPO_ROOT / "README.md"), "."),
    (str(REPO_ROOT / "CHANGELOG.md"), "."),
    (str(REPO_ROOT / "LICENSE"), "."),
    (str(REPO_ROOT / "SECURITY.md"), "."),
    (str(REPO_ROOT / "requirements.txt"), "."),
]

# Also bundle any JSON/YAML config files
for cfg in REPO_ROOT.rglob("*.json"):
    rel_parent = str(cfg.parent.relative_to(REPO_ROOT))
    datas.append((str(cfg), rel_parent))
for cfg in REPO_ROOT.rglob("*.yaml"):
    rel_parent = str(cfg.parent.relative_to(REPO_ROOT))
    datas.append((str(cfg), rel_parent))
for cfg in REPO_ROOT.rglob("*.yml"):
    rel_parent = str(cfg.parent.relative_to(REPO_ROOT))
    datas.append((str(cfg), rel_parent))

# ── C++ / Rust extensions (if compiled) ────────────────────────────────────
binaries = []
for ext in [".pyd", ".dll", ".so", ".dylib"]:
    for f in REPO_ROOT.rglob(f"*{ext}"):
        rel = str(f.parent.relative_to(REPO_ROOT))
        binaries.append((str(f), rel))

# ── Analysis ───────────────────────────────────────────────────────────────
a = Analysis(
    [ENTRY],
    pathex=[str(REPO_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="MAGNATRIX-OS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON if Path(ICON).exists() else None,
    version=str(SPEC_DIR / "version_info.txt") if Path(SPEC_DIR / "version_info.txt").exists() else None,
)
