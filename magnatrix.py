#!/usr/bin/env python3
"""
MAGNATRIX-OS — Master Bootstrap & Entry Point
=============================================
The single command to start the entire AI operating system.

Usage:
    python magnatrix.py start           # Start the full system
    python magnatrix.py status          # Check system status
    python magnatrix.py module list     # List all modules
    python magnatrix.py module on <name> # Enable a module
    python magnatrix.py config get      # Get configuration
    python magnatrix.py config set <k> <v> # Set config
    python magnatrix.py doc ingest <file> # Ingest a document
    python magnatrix.py backup          # Create backup
    python magnatrix.py update          # Check for updates
    python magnatrix.py stop            # Graceful shutdown

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable


@dataclass
class ModuleInfo:
    """Runtime info for a loaded module."""
    name: str
    path: str
    class_name: str
    instance: Any = None
    state: str = "pending"  # pending, loading, active, error, disabled
    error: Optional[str] = None
    load_time_ms: float = 0.0
    dependencies: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)


class ModuleRegistry:
    """Central registry for all MAGNATRIX-OS modules."""

    CORE_MODULES = [
        ("advanced", "core.advanced_rag_pipeline_native", "AdvancedRAGPipeline"),
        ("agent", "core.agent_attribution_native", "AgentAttribution"),
        ("agent_1", "core.agent_connector_native", "AgentConnector"),
        ("agent_2", "core.agent_orchestrator_native", "AgentOrchestrator"),
        ("agent_3", "core.agent_plugin_marketplace_native", "PluginMarketplace"),
        ("ai_model_registry", "core.ai_model_registry_native", "ModelRegistry"),
        ("ai_training", "core.ai_training_pipeline_native", "AITrainingPipeline"),
        ("alert_notification", "core.alert_notification_native", "AlertNotificationManager"),
        ("analytics", "core.analytics_engine_native", "AnalyticsEngine"),
        ("api", "core.api_gateway_native", "APIManager"),
        ("auth_authorization", "core.auth_authorization_native", "AuthManager"),
        ("auth", "core.auth_engine_native", "AuthEngine"),
        ("auto", "core.auto_deployment_native", "AutoDeploymentManager"),
        ("auto_1", "core.auto_doc_generator_native", "AutoDocGenerator"),
        ("auto_2", "core.auto_recovery_native", "AutoRecovery"),
        ("auto_test_runner", "core.auto_test_runner_native", "AutoTestRunner"),
        ("autonomy", "core.autonomy_engine_native", "AutonomyEngine"),
        ("awareness", "core.awareness_engine_native", "AwarenessEngine"),
        ("backup_engine", "core.backup_engine_v2_native", "BackupEngineV2"),
        ("backup", "core.backup_recovery_native", "BackupManager"),
        ("backup_1", "core.backup_snapshot_native", "BackupSnapshotManager"),
        ("benchmark", "core.benchmark_suite_native", "LoadTester"),
        ("bluegreen_deploy", "core.bluegreen_deploy_native", "BlueGreenDeployment"),
        ("cache", "core.cache_engine_native", "CacheEngine"),
        ("canary", "core.canary_release_native", "CanaryRelease"),
        ("chaos", "core.chaos_engineering_native", "ChaosEngineering"),
        ("cicd", "core.cicd_pipeline_native", "TestRunner"),
        ("cli", "core.cli_native", "MagnatrixCLI"),
        ("cli_tui", "core.cli_tui_manager_native", "TUIManager"),
        ("code", "core.code_audit_engine_native", "CodeAuditEngine"),
        ("code_quality_checker", "core.code_quality_checker_native", "CodeQualityChecker"),
        ("compression", "core.compression_engine_native", "CompressionEngine"),
        ("config", "core.config_manager_native", "ConfigManager"),
        ("container", "core.container_manager_native", "ContainerManager"),
        ("content", "core.content_engine_native", "ContentEngine"),
        ("context", "core.context_manager_native", "ContextManager"),
        ("cost", "core.cost_tracker_native", "CostTracker"),
        ("crypto_utilities", "core.crypto_utilities_native", "CryptoUtilities"),
        ("dashboard", "core.dashboard_frontend_native", "DashboardManager"),
        ("data", "core.data_lake_native", "DataLake"),
        ("data_1", "core.data_lineage_native", "DataLineageTracker"),
        ("data_2", "core.data_pipeline_native", "DataPipeline"),
        ("data_3", "core.data_quality_engine_native", "DataQualityEngine"),
        ("database", "core.database_abstraction_native", "DatabaseAbstraction"),
        ("database_layer", "core.database_layer_native", "DatabaseManager"),
        ("dependency", "core.dependency_graph_native", "DependencyGraph"),
        ("distributed", "core.distributed_mesh_engine_native", "DistributedMeshEngine"),
        ("distribution", "core.distribution_engine_native", "DistributionEngine"),
        ("doc", "core.doc_generator_native", "DocGenerator"),
        ("document", "core.document_intelligence_native", "UploadHandler"),
        ("edge", "core.edge_inference_native", "EdgeInference"),
        ("ego", "core.ego_engine_native", "EgoEngine"),
        ("email", "core.email_client_native", "EmailClient"),
        ("encryption_engine", "core.encryption_engine_v2_native", "EncryptionEngineV2"),
        ("environment_detector", "core.environment_detector_native", "EnvironmentDetector"),
        ("etl", "core.etl_pipeline_native", "ETLPipeline"),
        ("event", "core.event_bus_native", "EventBus"),
        ("event_1", "core.event_streaming_native", "EventStreamingEngine"),
        ("feature_store", "core.feature_store_native", "FeatureStore"),
        ("federation_sync", "core.federation_sync_native", "FederationManager"),
        ("filesystem", "core.filesystem_manager_native", "FileSystemManager"),
        ("follow", "core.follow_up_engine_native", "FollowUpEngine"),
        ("genesis_integration", "core.genesis_integration_hub_native", "GenesisIntegrationHub"),
        ("gesture", "core.gesture_recognition_native", "GestureRecognition"),
        ("gguf", "core.gguf_converter_native", "GGUFConverter"),
        ("graphql", "core.graphql_engine_native", "GraphQLServer"),
        ("guardian", "core.guardian_native", "Guardian"),
        ("hardware", "core.hardware_profiler_native", "HardwareProfiler"),
        ("health_check_aggregator", "core.health_check_aggregator_native", "HealthCheckAggregator"),
        ("hot_reload", "core.hot_reload_native", "HotReloader"),
        ("http", "core.http_client_native", "HTTPClient"),
        ("i18n", "core.i18n_engine_native", "I18nEngine"),
        ("integration_test", "core.integration_test_suite_native", "IntegrationTestManager"),
        ("intrusion", "core.intrusion_detection_native", "IntrusionDetectionSystem"),
        ("job", "core.job_scheduler_native", "JobScheduler"),
        ("key_management", "core.key_management_native", "KeyManagement"),
        ("knowledge_base", "core.knowledge_base_native", "KnowledgeBase"),
        ("knowledge", "core.knowledge_graph_engine_native", "KnowledgeGraphEngine"),
        ("learning", "core.learning_engine_native", "LearningEngine"),
        ("license", "core.license_scanner_native", "LicenseScanner"),
        ("local", "core.local_llm_manager_native", "LocalLLMManager"),
        ("log", "core.log_analysis_native", "LogAnalysisEngine"),
        ("logging", "core.logging_engine_native", "LogEngine"),
        ("logging_1", "core.logging_tracing_native", "LoggingManager"),
        ("longterm", "core.longterm_memory_native", "LongTermMemory"),
        ("memory", "core.memory_learning_system_native", "MemoryLearningSystem"),
        ("message", "core.message_queue_router_native", "MessageQueueRouter"),
        ("metrics", "core.metrics_health_native", "HealthDashboard"),
        ("mobile", "core.mobile_companion_native", "MobileCompanionAPI"),
        ("model_ab", "core.model_ab_testing_native", "ModelABTesting"),
        ("model_catalog", "core.model_catalog_native", "ModelCatalog"),
        ("model", "core.model_router_native", "ModelRouter"),
        ("model_1", "core.model_serving_native", "ModelServingEngine"),
        ("module_registry", "core.module_registry_native", "ModuleRegistry"),
        ("monitoring_alerting", "core.monitoring_alerting_native", "MonitoringEngine"),
        ("multi_agent_collaboration", "core.multi_agent_collaboration_native", "MultiAgentCollaboration"),
        ("multi", "core.multi_agent_router_native", "MultiAgentRouter"),
        ("multi_model", "core.multi_model_llm_adapter_native", "MultiModelLLMAdapter"),
        ("nlq", "core.nlq_engine_native", "NLQEngine"),
        ("outreach", "core.outreach_engine_native", "OutreachEngine"),
        ("package", "core.package_manager_native", "PackageManager"),
        ("performance", "core.performance_profiler_native", "PerformanceProfiler"),
        ("plugin", "core.plugin_sandbox_native", "PluginSandbox"),
        ("plugin_1", "core.plugin_sdk_native", "HookRegistry"),
        ("plugin_2", "core.plugin_system_native", "PluginSystem"),
        ("process", "core.process_manager_native", "ProcessManager"),
        ("prompt", "core.prompt_chaining_native", "PromptChain"),
        ("prompt_injection", "core.prompt_injection_guard_native", "PromptInjectionGuard"),
        ("prompt_version_control", "core.prompt_version_control_native", "PromptVersionControl"),
        ("pwa", "core.pwa_desktop_wrapper_native", "PWADesktopManager"),
        ("rag", "core.rag_pipeline_native", "RAGPipeline"),
        ("rate_limiter", "core.rate_limiter_native", "RateLimitExceeded"),
        ("release", "core.release_manager_native", "ReleaseManager"),
        ("replication", "core.replication_engine_native", "ReplicationEngine"),
        ("resource", "core.resource_monitor_native", "ResourceMonitor"),
        ("schema", "core.schema_validator_native", "SchemaValidator"),
        ("search", "core.search_engine_native", "SearchEngine"),
        ("secret", "core.secret_manager_native", "SecretManager"),
        ("secret_1", "core.secret_rotation_native", "SecretRotationEngine"),
        ("secrets", "core.secrets_vault_native", "SecretsVault"),
        ("security", "core.security_audit_framework_native", "SecurityAuditEngine"),
        ("security_1", "core.security_policy_engine_native", "SecurityPolicyManager"),
        ("session", "core.session_manager_native", "SessionManager"),
        ("slo", "core.slo_monitor_native", "SLIMonitor"),
        ("snapshot", "core.snapshot_engine_native", "SnapshotEngine"),
        ("state_persistence", "core.state_persistence_engine_native", "StatePersistenceEngine"),
        ("stream_processing", "core.stream_processing_native", "StreamProcessor"),
        ("subprocess", "core.subprocess_bridge_native", "SubprocessBridge"),
        ("system_bootstrap", "core.system_bootstrap_native", "SystemBootstrap"),
        ("task", "core.task_queue_scheduler_native", "TaskQueueScheduler"),
        ("template", "core.template_engine_native", "TemplateEngine"),
        ("test", "core.test_framework_native", "TestRunner"),
        ("tool_registry", "core.tool_registry_native", "ToolRegistry"),
        ("tool", "core.tool_use_framework_native", "ToolUseFramework"),
        ("unified", "core.unified_orchestrator_native", "UnifiedOrchestrator"),
        ("voice", "core.voice_audio_pipeline_native", "VoiceAudioPipelineNative"),
        ("voice_1", "core.voice_ui_native", "VoiceUI"),
        ("web", "core.web_api_gateway_native", "WebAPIGateway"),
        ("web_1", "core.web_dashboard_server_native", "DashboardServer"),
        ("websocket", "core.websocket_engine_native", "RealtimeEngine"),
        ("workflow", "core.workflow_engine_native", "WorkflowEngine"),
        ("zerotrust", "core.zerotrust_policy_native", "ZeroTrustPolicy"),
        # New modules: Integration Layer + 8 Modules + Test Suite + Dashboard
        ("integration", "core.integration_layer_native", "IntegrationManager"),
        ("quantum_safe", "core.quantum_safe_crypto_native", "QuantumSafeCrypto"),
        ("wasm", "core.wasm_runtime_native", "WASMRuntime"),
        ("intent", "core.intent_orchestrator_native", "IntentOrchestrator"),
        ("temporal", "core.temporal_workflow_native", "TemporalWorkflowEngine"),
        ("code_reasoning", "core.code_reasoning_engine_native", "CodeReasoningEngine"),
        ("self_healing", "core.self_healing_native", "SelfHealingEngine"),
        ("audit_forensics", "core.audit_forensics_native", "AuditForensicsEngine"),
        ("anomaly_viz", "core.anomaly_visualization_native", "AnomalyVizEngine"),
        ("test_suite", "core.test_suite_engine_native", "TestSuiteEngine"),
        ("dashboard_pro", "core.dashboard_production_native", "DashboardServer"),
        # Phase 2: HFT + gRPC + Docker Installer
        ("hft_trading", "core.hft_trading_engine_native", "TradingEngine"),
        ("grpc_transport", "core.grpc_transport_native", "GRPCTransport"),
        ("docker_compose", "core.docker_compose_native", "BootstrapManager"),
        # Phase 3+4: Integration + Proto-AGI + Data + Constitution
        ("integration_hybrid", "core.integration_hybrid_mode_native", "IntegrationHybridManager"),
        ("proto_agi", "core.proto_agi_self_improvement_native", "SelfImprovementLoop"),
        ("data_connectors", "core.data_connectors_native", "DataConnectorManager"),
        ("constitution", "core.magnatrix_constitution_native", "ConstitutionGovernor"),
        # Phase 5: Swarm + Exchange + Security + Transfer + Optimizer
        ("swarm", "core.swarm_intelligence_native", "SwarmIntelligence"),
        ("exchange", "core.live_exchange_integration_native", "ExchangeConnector"),
        ("concealment", "core.capability_concealment_native", "ConcealmentDetector"),
        ("transfer", "core.cross_domain_transfer_native", "CrossDomainTransfer"),
        ("boot_opt", "core.boot_optimizer_v2_native", "BootOptimizer"),
        ("moa", "core.moa_integration_native", "MOAEngine"),
        # Phase 6: Integration Hub + Hardware + Auto Doc
        ("integration_hub", "core.system_integration_hub_native", "SystemIntegrationHub"),
        ("hardware_edge", "core.hardware_inference_edge_native", "HardwareInferenceEngine"),
        ("auto_doc", "core.auto_doc_test_generator_native", "AutoDocTestEngine"),
        # Phase 7: Memory + Knowledge + Federated + XAI + Synthetic
        ("agent_memory", "core.agent_memory_system_native", "AgentMemory"),
        ("knowledge_ingestion", "core.knowledge_ingestion_pipeline_native", "KnowledgeIngestionPipeline"),
        ("federated_learning", "core.federated_learning_native", "FederatedLearningEngine"),
        ("xai", "core.explainability_xai_native", "ExplainabilityEngine"),
        ("synthetic_data", "core.synthetic_data_generator_native", "SyntheticDataEngine"),
        # Phase 8: Final 5 — Goal Formation + RSI v2 + MultiModal + Deployment + Benchmark
        ("goal_formation", "core.emergent_goal_formation_native", "EmergentGoalFormation"),
        ("rsi_v2", "core.recursive_self_improvement_v2_native", "RecursiveSelfImprovement"),
        ("multimodal", "core.multimodal_pipeline_native", "MultiModalPipeline"),
        ("deployment", "core.live_deployment_manager_native", "LiveDeploymentManager"),
        ("benchmark", "core.auto_benchmark_leaderboard_native", "AutoBenchmarkEngine"),
        ("neural_search", "core.neural_architecture_search_native", "NeuralArchitectureSearch"),
        ("quantum_sim", "core.quantum_simulator_native", "QuantumSimulator"),
        ("blockchain", "core.blockchain_consensus_native", "BlockchainConsensus"),
        ("ar_vr", "core.ar_vr_interface_native", "ARVRInterface"),
        ("dna", "core.dna_sequence_analyzer_native", "DNASequenceAnalyzer"),
        ("supply_chain", "core.supply_chain_optimizer_native", "SupplyChainOptimizer"),
        ("smart_city", "core.smart_city_grid_native", "SmartCityGrid"),
        ("weather", "core.weather_prediction_native", "WeatherPredictionEngine"),
        ("autonomous", "core.autonomous_vehicle_native", "AutonomousVehicleController"),
        ("medical", "core.medical_diagnosis_native", "MedicalDiagnosisEngine"),
        ("legal", "core.legal_contract_parser_native", "LegalContractParser"),
        ("social", "core.social_network_native", "SocialNetworkAnalyzer"),
        ("recommendation", "core.recommendation_engine_native", "RecommendationEngine"),
        ("sentiment", "core.sentiment_analyzer_native", "SentimentAnalyzer"),
        ("spam", "core.spam_detector_native", "SpamDetector"),
        ("intrusion", "core.intrusion_forensics_native", "IntrusionForensicsEngine"),
        ("zeroday", "core.zeroday_predictor_native", "ZeroDayPredictor"),
        ("patch_gen", "core.patch_generator_native", "PatchGenerator"),
        ("compliance", "core.compliance_auditor_native", "ComplianceAuditor"),
        ("lineage", "core.data_lineage_native", "DataLineageTracker"),
        ("drift", "core.model_drift_detector_native", "ModelDriftDetector"),
        ("quantum_ml", "core.quantum_machine_learning_native", "QuantumML"),
        ("bioinformatics", "core.bioinformatics_engine_native", "BioinformaticsEngine"),
        ("aerospace", "core.aerospace_flight_control_native", "AerospaceFlightControl"),
        ("smart_agri", "core.smart_agriculture_native", "SmartAgriculture"),
        ("space_debris", "core.space_debris_tracker_native", "SpaceDebrisTracker"),
        ("disposable_agent", "core.disposable_agent_generator_native", "DisposableAgentGenerator"),
        ("implant_detector", "core.memory_implant_detector_native", "MemoryImplantDetector"),
        ("enc_channel", "core.encrypted_channel_analyzer_native", "EncryptedChannelAnalyzer"),
        ("classloader_mon", "core.classloader_monitor_native", "ClassLoaderMonitor"),
        ("webshell_detect", "core.webshell_session_detector_native", "WebshellSessionDetector"),
        ("forensics_counter", "core.forensics_countermeasures_native", "ForensicsCountermeasuresDetector"),
        ("vnpy_gateway", "core.vnpy_gateway_adapter_native", "vnpyGatewayAdapter"),
        ("cta_engine", "core.cta_strategy_engine_native", "CTAStrategyEngine"),
        ("alpha_factor", "core.alpha_factor_engine_native", "AlphaFactorEngine"),
        ("ml_predictor", "core.ml_predictor_native", "MLPredictor"),
        ("order_flow", "core.order_flow_controller_native", "OrderFlowController"),
        ("data_recorder", "core.market_data_recorder_native", "MarketDataRecorder"),
        ("loop_engine", "core.loop_engineering_engine_native", "LoopEngineeringEngine"),
        ("android_device", "core.android_device_controller_native", "AndroidDeviceController"),
        ("android_screen", "core.android_screen_capture_native", "AndroidScreenCapture"),
        ("android_input", "core.android_input_simulator_native", "AndroidInputSimulator"),
        ("android_wireless", "core.android_wireless_manager_native", "AndroidWirelessManager"),
        ("android_camera", "core.android_camera_stream_native", "AndroidCameraStream"),
        ("android_auto", "core.android_automation_engine_native", "AndroidAutomationEngine"),
        ("agent_evolve", "core.agent_evolution_engine_native", "AgentEvolutionEngine"),
        ("benchmark", "core.benchmark_harness_native", "BenchmarkHarness"),
        ("mutation", "core.mutation_engine_native", "MutationEngine"),
        ("fitness", "core.fitness_evaluator_native", "FitnessEvaluator"),
        ("population", "core.population_manager_native", "PopulationManager"),
        ("adaptive_harness", "core.adaptive_harness_native", "AdaptiveHarness"),
        ("browser_context", "core.browser_context_manager_native", "BrowserContextManager"),
        ("browser_bridge", "core.browser_extension_bridge_native", "BrowserExtensionBridge"),
        ("quick_cmd", "core.quick_command_processor_native", "QuickCommandProcessor"),
        ("tab_redactor", "core.sensitive_tab_redactor_native", "SensitiveTabRedactor"),
        ("tab_session", "core.tab_session_isolator_native", "TabSessionIsolator"),
        ("browser_agent", "core.browser_automation_agent_native", "BrowserAutomationAgent"),
        ("temporal_graph", "core.temporal_knowledge_graph_native", "TemporalKnowledgeGraph"),
        ("hippocampus", "core.hippocampus_memory_native", "HippocampusMemoryLayer"),
        ("consolidation", "core.memory_consolidation_engine_native", "MemoryConsolidationEngine"),
        ("entity_extract", "core.entity_extractor_native", "EntityExtractor"),
        ("memory_retrieve", "core.memory_retrieval_engine_native", "MemoryRetrievalEngine"),
        ("brain_prompt", "core.brain_aware_prompt_native", "BrainAwarePromptGenerator"),
        ("skill_registry", "core.skill_registry_native", "SkillRegistry"),
        ("skill_translator", "core.skill_translator_native", "SkillTranslator"),
        ("skill_marketplace", "core.skill_marketplace_native", "SkillMarketplace"),
        ("skill_loader", "core.skill_loader_native", "SkillLoader"),
        ("skill_validator", "core.skill_validator_native", "SkillValidator"),
        ("skill_composer", "core.skill_composer_native", "SkillComposer"),
        ("proxy_kd", "core.proxy_kd_engine_native", "ProxyKDEngine"),
        ("teacher_adapter", "core.blackbox_teacher_adapter_native", "BlackBoxTeacherAdapter"),
        ("student_trainer", "core.student_trainer_native", "StudentTrainer"),
        ("kd_loss", "core.kd_loss_calculator_native", "KDLossCalculator"),
        ("proxy_aligner", "core.proxy_model_aligner_native", "ProxyModelAligner"),
        ("distill_pipeline", "core.distillation_pipeline_native", "DistillationPipelineManager"),
        ("prompt_inject", "core.prompt_injection_detector_native", "PromptInjectionDetector"),
        ("jailbreak", "core.jailbreak_detector_native", "JailbreakDetector"),
        ("adversarial_scan", "core.adversarial_input_scanner_native", "AdversarialInputScanner"),
        ("mcp_security", "core.mcp_security_auditor_native", "MCPSecurityAuditor"),
        ("llm_security", "core.llm_security_framework_native", "LLMSecurityFramework"),
        ("ai_pentest", "core.ai_pentest_engine_native", "AIPentestEngine"),
        ("code_decomp", "core.code_decomposition_engine_native", "CodeDecompositionEngine"),
        ("reachability", "core.reachability_analyzer_native", "ReachabilityAnalyzer"),
        ("adv_verify", "core.adversarial_verification_engine_native", "AdversarialVerificationEngine"),
        ("dyn_verify", "core.dynamic_verification_engine_native", "DynamicVerificationEngine"),
        ("vuln_discover", "core.vulnerability_discovery_pipeline_native", "VulnerabilityDiscoveryPipeline"),
        ("sandbox_exploit", "core.sandboxed_exploit_runner_native", "SandboxedExploitRunner"),
    ]

    def __init__(self, repo_root: str) -> None:
        self.root = Path(repo_root).resolve()
        self._modules: Dict[str, ModuleInfo] = {}
        self._running = False
        self._lock = threading.RLock()
        self._hooks: Dict[str, List[Callable]] = {"pre_boot": [], "post_boot": [], "pre_shutdown": [], "post_shutdown": []}
        self._sys_path_inserted = False

    def _ensure_path(self) -> None:
        if not self._sys_path_inserted:
            sys.path.insert(0, str(self.root))
            self._sys_path_inserted = True

    def _load_module(self, name: str, mod_path: str, cls_name: str) -> Optional[Any]:
        """Try to load a module and instantiate its class."""
        try:
            self._ensure_path()
            mod = importlib.import_module(mod_path)
            cls = getattr(mod, cls_name)
            # Try to instantiate with reasonable args
            sig_args = {}
            try:
                import inspect
                sig = inspect.signature(cls.__init__)
                if "repo_root" in sig.parameters:
                    sig_args["repo_root"] = str(self.root)
                if "root" in sig.parameters:
                    sig_args["root"] = str(self.root)
                if "store_dir" in sig.parameters:
                    sig_args["store_dir"] = str(self.root / "data" / name)
            except Exception:
                pass
            instance = cls(**sig_args) if sig_args else cls()
            return instance
        except Exception as e:
            return None

    def boot(self, target_modules: Optional[List[str]] = None) -> Dict[str, Any]:
        """Boot all or selected modules."""
        with self._lock:
            self._running = True
            start_all = time.time()
            results = {"loaded": 0, "failed": 0, "skipped": 0, "total": len(self.CORE_MODULES), "details": []}

            for hook in self._hooks["pre_boot"]:
                try:
                    hook()
                except Exception:
                    pass

            for name, mod_path, cls_name in self.CORE_MODULES:
                if target_modules and name not in target_modules:
                    results["skipped"] += 1
                    continue
                info = ModuleInfo(name=name, path=mod_path, class_name=cls_name)
                info.state = "loading"
                t0 = time.time()
                instance = self._load_module(name, mod_path, cls_name)
                info.load_time_ms = (time.time() - t0) * 1000
                if instance is not None:
                    info.instance = instance
                    info.state = "active"
                    info.provides = [name]
                    results["loaded"] += 1
                else:
                    info.state = "error"
                    info.error = "Failed to load"
                    results["failed"] += 1
                self._modules[name] = info
                results["details"].append({
                    "name": name, "state": info.state, "load_ms": round(info.load_time_ms, 1),
                    "error": info.error,
                })

            total_ms = (time.time() - start_all) * 1000
            results["boot_time_ms"] = round(total_ms, 1)

            for hook in self._hooks["post_boot"]:
                try:
                    hook()
                except Exception:
                    pass

            return results

    def shutdown(self) -> Dict[str, Any]:
        """Graceful shutdown of all modules."""
        with self._lock:
            self._running = False
            results = {"shutdown": 0, "errors": 0}

            for hook in self._hooks["pre_shutdown"]:
                try:
                    hook()
                except Exception:
                    pass

            for name, info in reversed(list(self._modules.items())):
                if info.instance and hasattr(info.instance, "stop"):
                    try:
                        info.instance.stop()
                        results["shutdown"] += 1
                    except Exception:
                        results["errors"] += 1
                info.state = "disabled"
                info.instance = None

            for hook in self._hooks["post_shutdown"]:
                try:
                    hook()
                except Exception:
                    pass

            return results

    def get_module(self, name: str) -> Optional[Any]:
        with self._lock:
            info = self._modules.get(name)
            return info.instance if info else None

    def get_status(self, name: str) -> Dict[str, Any]:
        with self._lock:
            info = self._modules.get(name)
            if not info:
                return {"name": name, "state": "unknown"}
            return {
                "name": info.name, "state": info.state, "path": info.path,
                "class": info.class_name, "load_ms": round(info.load_time_ms, 1),
                "error": info.error, "provides": info.provides,
            }

    def list_modules(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [self.get_status(name) for name in self._modules]

    def active_modules(self) -> List[str]:
        with self._lock:
            return [n for n, i in self._modules.items() if i.state == "active"]

    def register_hook(self, event: str, callback: Callable) -> None:
        self._hooks.setdefault(event, []).append(callback)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            states = {}
            for i in self._modules.values():
                states[i.state] = states.get(i.state, 0) + 1
            return {
                "total_registered": len(self.CORE_MODULES),
                "loaded": len([i for i in self._modules.values() if i.state == "active"]),
                "failed": len([i for i in self._modules.values() if i.state == "error"]),
                "states": states,
                "running": self._running,
            }


class SystemManager:
    """High-level system manager combining all modules."""

    def __init__(self, repo_root: str) -> None:
        self.root = Path(repo_root).resolve()
        self.registry = ModuleRegistry(repo_root)
        self._dashboard_server: Optional[Any] = None
        self._genesis_hub: Optional[Any] = None
        self._doc_intel: Optional[Any] = None
        self._deployment: Optional[Any] = None
        self._pwa: Optional[Any] = None
        self._shutdown_event = threading.Event()

    def boot(self, quick: bool = False) -> Dict[str, Any]:
        """Boot the full system."""
        print("=" * 60)
        print("  MAGNATRIX-OS Boot Sequence")
        print("  Private, Uncensored AI Operating System")
        print("=" * 60)

        # Boot core modules first
        if quick:
            # Only boot essential modules
            essential = ["config", "logging", "cache", "auth", "monitor", "event_bus", "web_dashboard", "dashboard_fe"]
            result = self.registry.boot(essential)
        else:
            result = self.registry.boot()

        print(f"\n  Modules loaded: {result['loaded']}/{result['total']}")
        print(f"  Failed: {result['failed']}")
        print(f"  Boot time: {result['boot_time_ms']}ms")

        # Wire key services
        self._wire_services()

        # Start dashboard server if available
        self._start_dashboard()

        print(f"\n  System ready at: http://0.0.0.0:8080")
        print("=" * 60)

        return result

    def _wire_services(self) -> None:
        """Wire key services together."""
        try:
            # Wire genesis hub
            hub = self.registry.get_module("genesis_hub")
            if hub:
                self._genesis_hub = hub
                print("  [Wired] Genesis Integration Hub")
        except Exception as e:
            print(f"  [Skip] Genesis Hub: {e}")

        try:
            # Wire document intelligence
            di = self.registry.get_module("doc_intel")
            if di:
                self._doc_intel = di
                print("  [Wired] Document Intelligence")
        except Exception as e:
            print(f"  [Skip] Document Intelligence: {e}")

        try:
            # Wire deployment
            dep = self.registry.get_module("deployment")
            if dep:
                self._deployment = dep
                print("  [Wired] Auto-Deployment")
        except Exception as e:
            print(f"  [Skip] Auto-Deployment: {e}")

        try:
            # Wire PWA manager
            pwa = self.registry.get_module("pwa")
            if pwa:
                self._pwa = pwa
                # Inject PWA into dashboard
                dashboard_path = self.root / "core" / "dashboard.html"
                if dashboard_path.exists():
                    pwa.inject_pwa_into_dashboard(str(dashboard_path))
                    print("  [Wired] PWA assets injected into dashboard")
        except Exception as e:
            print(f"  [Skip] PWA: {e}")

    def _start_dashboard(self) -> None:
        """Start the web dashboard server."""
        try:
            web = self.registry.get_module("web_dashboard")
            if web and hasattr(web, "start"):
                web.start(blocking=False)
                self._dashboard_server = web
                print(f"  [Started] Dashboard server at http://0.0.0.0:8080")
        except Exception as e:
            print(f"  [Skip] Dashboard server: {e}")

    def boot_optimized(self, quick: bool = False) -> Dict[str, Any]:
        """Boot with parallel loading and lazy initialization."""
        print("=" * 60)
        print("  MAGNATRIX-OS Boot Sequence (Optimized)")
        print("  Private, Uncensored AI Operating System")
        print("=" * 60)

        try:
            from core.boot_optimizer_native import BootOptimizer
            optimizer = BootOptimizer(self.registry, max_workers=8)
            result = optimizer.optimized_boot(quick=quick)
        except Exception as e:
            print(f"  [Optimizer failed] {e}")
            result = self.registry.boot()

        print(f"\n  Modules loaded: {result['loaded']}/{result['total']}")
        print(f"  Failed: {result['failed']}")
        print(f"  Lazy: {result.get('lazy_count', 0)}")
        print(f"  Boot time: {result['boot_time_ms']}ms")

        self._wire_services()
        self._start_dashboard()

        print(f"\n  System ready at: http://0.0.0.0:8080")
        print("=" * 60)

        return result

    def shutdown(self) -> None:
        """Graceful shutdown."""
        print("\n  MAGNATRIX-OS shutting down...")
        if self._dashboard_server and hasattr(self._dashboard_server, "stop"):
            try:
                self._dashboard_server.stop()
            except Exception:
                pass
        result = self.registry.shutdown()
        print(f"  Shutdown: {result['shutdown']} modules stopped")
        self._shutdown_event.set()

    def status(self) -> Dict[str, Any]:
        return {
            "registry": self.registry.stats(),
            "dashboard_running": self._dashboard_server is not None,
            "genesis_hub": self._genesis_hub is not None,
            "doc_intel": self._doc_intel is not None,
            "root": str(self.root),
        }

    def wait(self) -> None:
        """Block until shutdown signal."""
        try:
            while not self._shutdown_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            self.shutdown()


def _cli() -> None:
    """Command-line interface."""
    parser = argparse.ArgumentParser(description="MAGNATRIX-OS — Private AI Operating System")
    sub = parser.add_subparsers(dest="command")

    # start
    start_p = sub.add_parser("start", help="Start the full system")
    start_p.add_argument("--quick", action="store_true", help="Quick boot (essential modules only)")
    start_p.add_argument("--port", type=int, default=8080, help="Dashboard port")
    start_p.add_argument("--optimized", action="store_true", help="Use parallel boot optimizer")

    # status
    sub.add_parser("status", help="Check system status")

    # module
    mod_p = sub.add_parser("module", help="Module management")
    mod_sub = mod_p.add_subparsers(dest="mod_cmd")
    mod_sub.add_parser("list", help="List all modules")
    mod_sub.add_parser("on", help="Enable a module")
    mod_sub.add_parser("off", help="Disable a module")

    # config
    cfg_p = sub.add_parser("config", help="Configuration management")
    cfg_sub = cfg_p.add_subparsers(dest="cfg_cmd")
    cfg_sub.add_parser("get", help="Get configuration")
    cfg_sub.add_parser("set", help="Set configuration value")

    # doc
    doc_p = sub.add_parser("doc", help="Document management")
    doc_sub = doc_p.add_subparsers(dest="doc_cmd")
    doc_ingest = doc_sub.add_parser("ingest", help="Ingest a document")
    doc_ingest.add_argument("file", help="Path to document file")

    # backup
    sub.add_parser("backup", help="Create system backup")

    # update
    sub.add_parser("update", help="Check for updates")

    # stop
    sub.add_parser("stop", help="Stop the system")

    args = parser.parse_args()
    repo_root = Path(__file__).parent.resolve()
    sys.path.insert(0, str(repo_root))

    if args.command == "start":
        manager = SystemManager(repo_root)
        if args.optimized:
            manager.boot_optimized(quick=args.quick)
        else:
            manager.boot(quick=args.quick)
        manager.wait()

    elif args.command == "status":
        manager = SystemManager(repo_root)
        status = manager.status()
        print(json.dumps(status, indent=2, ensure_ascii=False))

    elif args.command == "module":
        manager = SystemManager(repo_root)
        manager.boot(quick=True)
        if args.mod_cmd == "list":
            for m in manager.registry.list_modules():
                icon = "✓" if m["state"] == "active" else "✗" if m["state"] == "error" else "○"
                print(f"  {icon} {m['name']:20s} {m['state']:10s} {m.get('load_ms', 0)}ms")
        else:
            print(f"Module command: {args.mod_cmd}")

    elif args.command == "config":
        print(f"Config: {args.cfg_cmd}")

    elif args.command == "doc":
        if args.doc_cmd == "ingest":
            manager = SystemManager(repo_root)
            manager.boot(quick=True)
            di = manager.registry.get_module("doc_intel")
            if di and hasattr(di, "ingest_file"):
                result = di.ingest_file(args.file)
                print(f"Ingested: {result.source} -> {result.chunks} chunks, {result.chars} chars")
            else:
                print("Document intelligence module not available")

    elif args.command == "backup":
        manager = SystemManager(repo_root)
        manager.boot(quick=True)
        backup = manager.registry.get_module("backup")
        if backup and hasattr(backup, "backup"):
            path = backup.backup(str(repo_root))
            print(f"Backup created: {path}")
        else:
            print("Backup module not available")

    elif args.command == "update":
        manager = SystemManager(repo_root)
        manager.boot(quick=True)
        dep = manager.registry.get_module("deployment")
        if dep and hasattr(dep, "check_update"):
            result = dep.check_update()
            print(f"Current: {result['current']}")
            print(f"Latest: {result.get('latest', 'Unknown')}")
            print(f"Update available: {result.get('update_available', False)}")
        else:
            print("Deployment module not available")

    elif args.command == "stop":
        print("Send SIGTERM to the running process to shutdown gracefully.")

    else:
        parser.print_help()


if __name__ == "__main__":
    _cli()
