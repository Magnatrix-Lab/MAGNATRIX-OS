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
        ("social_scraper", "core.social_media_scraper_native", "SocialMediaScraper"),
        ("youtube_transcript", "core.youtube_transcript_native", "YouTubeTranscriptExtractor"),
        ("web_reader", "core.web_content_reader_native", "WebContentReader"),
        ("aggregator", "core.content_aggregator_native", "ContentAggregator"),
        ("backend_router", "core.multi_backend_router_native", "MultiBackendRouter"),
        ("internet_search", "core.internet_search_engine_native", "InternetSearchEngine"),
        ("driver_import", "core.driver_import_scanner_native", "DriverImportScanner"),
        ("ioctl_extract", "core.ioctl_dispatch_extractor_native", "IOCTLDispatchExtractor"),
        ("byovd_intel", "core.byovd_threat_intel_native", "BYOVDThreatIntel"),
        ("driver_emulate", "core.driver_emulation_engine_native", "DriverEmulationEngine"),
        ("driver_blocklist", "core.vulnerable_driver_blocklist_native", "VulnerableDriverBlocklistManager"),
        ("byovd_hunter", "core.byovd_hunter_pipeline_native", "BYOVDHunterPipeline"),
        ("poly_shellcode", "core.polymorphic_shellcode_detector_native", "PolymorphicShellcodeDetector"),
        ("peb_resolver", "core.peb_api_resolver_detector_native", "PEBAPIResolverDetector"),
        ("chacha20_analyze", "core.chacha20_payload_analyzer_native", "ChaCha20PayloadAnalyzer"),
        ("c2_detect", "core.c2_communications_detector_native", "C2CommunicationsDetector"),
        ("coff_analyze", "core.coff_layout_analyzer_native", "COFFLayoutAnalyzer"),
        ("mythic_detect", "core.mythic_framework_detector_native", "MythicFrameworkDetector"),
        ("semantic_memory", "core.typed_semantic_memory_native", "TypedSemanticMemoryStore"),
        ("temporal_query", "core.temporal_memory_query_native", "TemporalMemoryQueryEngine"),
        ("provenance", "core.memory_provenance_tracker_native", "MemoryProvenanceTracker"),
        ("agent_sync", "core.multi_agent_memory_sync_native", "MultiAgentMemorySync"),
        ("conflict_resolve", "core.memory_conflict_resolver_native", "MemoryConflictResolver"),
        ("memory_export", "core.memory_export_sync_engine_native", "MemoryExportSyncEngine"),
        ("copilot_agent", "core.copilot_agent_manager_native", "CopilotAgentManager"),
        ("copilot_skill", "core.copilot_skill_manager_native", "CopilotSkillManager"),
        ("copilot_instruction", "core.copilot_instruction_engine_native", "CopilotInstructionEngine"),
        ("copilot_cookbook", "core.copilot_cookbook_engine_native", "CopilotCookbookEngine"),
        ("copilot_plugin", "core.copilot_plugin_manager_native", "CopilotPluginManager"),
        ("copilot_workflow", "core.copilot_workflow_automator_native", "CopilotWorkflowAutomator"),
        ("stock_data", "core.stock_data_provider_native", "StockDataProvider"),
        ("stock_analysis", "core.stock_analysis_engine_native", "StockAnalysisEngine"),
        ("stock_signal", "core.stock_signal_generator_native", "StockSignalGenerator"),
        ("financial_news", "core.financial_news_aggregator_native", "FinancialNewsAggregator"),
        ("portfolio", "core.portfolio_tracker_native", "PortfolioTracker"),
        ("stock_scheduler", "core.stock_scheduler_native", "StockScheduler"),
        ("stock_alert", "core.stock_alert_engine_native", "StockAlertEngine"),
        ("technical_indicator", "core.technical_indicator_native", "TechnicalIndicator"),
        ("game_theory", "core.game_theory_engine_native", "GameTheoryEngine"),
        ("nash_solver", "core.nash_equilibrium_solver_native", "NashEquilibriumSolver"),
        ("mixed_strategy", "core.mixed_strategy_calculator_native", "MixedStrategyCalculator"),
        ("backward_induction", "core.backward_induction_engine_native", "BackwardInductionEngine"),
        ("subgame_perfect", "core.subgame_perfect_solver_native", "SubgamePerfectSolver"),
        ("bayesian_game", "core.bayesian_game_solver_native", "BayesianGameSolver"),
        ("cooperative_game", "core.cooperative_game_native", "CooperativeGame"),
        ("evolutionary_game", "core.evolutionary_game_theory_native", "EvolutionaryGameTheory"),
        ("kv_cache", "core.kv_cache_manager_native", "KVCacheManager"),
        ("attention_scorer", "core.attention_scorer_native", "AttentionScorer"),
        ("cache_eviction", "core.cache_eviction_engine_native", "CacheEvictionEngine"),
        ("cache_quantization", "core.cache_quantization_engine_native", "CacheQuantizationEngine"),
        ("rate_distortion", "core.rate_distortion_allocator_native", "RateDistortionAllocator"),
        ("water_filling", "core.water_filling_optimizer_native", "WaterFillingOptimizer"),
        ("packed_decode", "core.packed_decode_layout_native", "PackedDecodeLayout"),
        ("inference_optimizer", "core.inference_memory_optimizer_native", "InferenceMemoryOptimizer"),
        ("attack_surface", "core.attack_surface_mapper_native", "AttackSurfaceMapper"),
        ("subdomain_enum", "core.subdomain_enumerator_native", "SubdomainEnumerator"),
        ("port_scanner", "core.port_scanner_native", "PortScanner"),
        ("web_asset", "core.web_asset_discoverer_native", "WebAssetDiscoverer"),
        ("tls_monitor", "core.tls_certificate_monitor_native", "TLSCertificateMonitor"),
        ("email_posture", "core.email_posture_analyzer_native", "EmailPostureAnalyzer"),
        ("secret_detector", "core.exposed_secret_detector_native", "ExposedSecretDetector"),
        ("asset_scoring", "core.asset_scoring_engine_native", "AssetScoringEngine"),
        ("scalability_fundamentals", "core.scalability_fundamentals_native", "ScalabilityFundamentals"),
        ("database_scaling", "core.database_scaling_engine_native", "DatabaseScalingEngine"),
        ("caching_strategy", "core.caching_strategy_engine_native", "CachingStrategyEngine"),
        ("load_balancer", "core.load_balancer_simulator_native", "LoadBalancerSimulator"),
        ("cap_theorem", "core.cap_theorem_analyzer_native", "CAPTheoremAnalyzer"),
        ("microservices", "core.microservices_orchestrator_native", "MicroservicesOrchestrator"),
        ("message_queue", "core.message_queue_engine_native", "MessageQueueEngine"),
        ("system_design_interviewer", "core.system_design_interviewer_native", "SystemDesignInterviewer"),
        ("persona_manager", "core.persona_manager_native", "PersonaManager"),
        ("skill_library", "core.skill_library_native", "SkillLibrary"),
        ("code_graph_analyzer", "core.code_graph_analyzer_native", "CodeGraphAnalyzer"),
        ("security_suite", "core.security_suite_native", "SecuritySuite"),
        ("tech_persona_card", "core.tech_persona_card_native", "TechPersonaCardEngine"),
        ("style_engine", "core.style_engine_native", "StyleEngine"),
        ("self_evolution_forge", "core.self_evolution_forge_native", "SelfEvolutionForge"),
        ("agent_hook_manager", "core.agent_hook_manager_native", "AgentHookManager"),
        ("yagni_engine", "core.yagni_engine_native", "YAGNIEngine"),
        ("code_reuse_detector", "core.code_reuse_detector_native", "CodeReuseDetector"),
        ("comprehension_guard", "core.comprehension_first_guard_native", "ComprehensionFirstGuard"),
        ("minimalism_scoreboard", "core.minimalism_scoreboard_native", "MinimalismScoreboard"),
        ("agent_skills_library", "core.agent_skills_library_native", "AgentSkillsLibrary"),
        ("subagent_injector", "core.subagent_rules_injector_native", "SubagentRulesInjector"),
        ("lazy_senior_dev", "core.lazy_senior_dev_native", "LazySeniorDev"),
        ("agentic_benchmark", "core.agentic_benchmark_native", "AgenticBenchmark"),
        ("longhorizon_task", "core.longhorizon_task_engine_native", "LongHorizonTaskEngine"),
        ("sandbox", "core.sandbox_executor_native", "SandboxExecutor"),
        ("agent_memory", "core.agent_memory_store_native", "AgentMemoryStore"),
        ("subagent_orchestrator", "core.subagent_orchestrator_native", "SubagentOrchestrator"),
        ("agentic_tools", "core.agentic_tool_registry_native", "AgenticToolRegistry"),
        ("message_gateway", "core.message_gateway_native", "MessageGateway"),
        ("skill_engine", "core.skill_execution_engine_native", "SkillExecutionEngine"),
        ("agent_harness", "core.agent_harness_native", "AgentHarness"),
        ("visual_flow", "core.visual_flow_builder_native", "VisualFlowBuilder"),
        ("flow_component", "core.flow_component_node_native", "FlowComponentNode"),
        ("flow_execution", "core.flow_execution_engine_native", "FlowExecutionEngine"),
        ("vector_store", "core.vector_store_connector_native", "VectorStoreConnector"),
        ("chat", "core.chat_interface_native", "ChatInterface"),
        ("agent_workflow", "core.agent_workflow_builder_native", "AgentWorkflowBuilder"),
        ("flow_deployer", "core.flow_deployer_native", "FlowDeployer"),
        ("component_lib", "core.component_library_native", "ComponentLibrary"),
        ("recon_engine", "core.reconnaissance_engine_native", "ReconnaissanceEngine"),
        ("exploit_matcher", "core.exploit_pattern_matcher_native", "ExploitPatternMatcher"),
        ("c2_simulator", "core.c2_simulator_native", "C2Simulator"),
        ("payload_obfuscator", "core.payload_obfuscator_native", "PayloadObfuscator"),
        ("lateral_tracker", "core.lateral_movement_tracker_native", "LateralMovementTracker"),
        ("post_exploitation", "core.post_exploitation_native", "PostExploitation"),
        ("redteam_planner", "core.redteam_operation_planner_native", "RedTeamOperationPlanner"),
        ("evasion_library", "core.evasion_technique_library_native", "EvasionTechniqueLibrary"),
        ("medical_kb", "core.medical_knowledge_base_native", "MedicalKnowledgeBase"),
        ("clinical_reasoning", "core.clinical_reasoning_engine_native", "ClinicalReasoningEngine"),
        ("medical_qa", "core.medical_qa_system_native", "MedicalQASystem"),
        ("medical_text", "core.medical_text_processor_native", "MedicalTextProcessor"),
        ("medical_guideline", "core.medical_guideline_parser_native", "MedicalGuidelineParser"),
        ("diagnosis_assistant", "core.diagnosis_assistant_native", "DiagnosisAssistant"),
        ("medical_benchmark", "core.medical_evaluation_benchmark_native", "MedicalEvaluationBenchmark"),
        ("medical_model", "core.medical_model_adapter_native", "MedicalModelAdapter"),
        ("clarification", "core.clarification_engine_native", "ClarificationEngine"),
        ("complexity_assessor", "core.complexity_assessor_native", "ComplexityAssessor"),
        ("plan_crafter", "core.plan_crafter_native", "PlanCrafter"),
        ("plan_executor", "core.plan_executor_native", "PlanExecutor"),
        ("review_validator", "core.review_validator_native", "ReviewValidator"),
        ("milestone_planner", "core.milestone_planner_native", "MilestonePlanner"),
        ("implementation_guardrails", "core.implementation_guardrails_native", "ImplementationGuardrails"),
        ("ai_slop_cleaner", "core.ai_slop_cleaner_native", "AISlopCleaner"),
        ("llm_gateway", "core.llm_gateway_native", "LLMGateway"),
        ("free_api_key_hunter", "core.free_api_key_hunter_native", "FreeAPIKeyHunter"),
        ("token_compression", "core.token_compression_native", "TokenCompressionEngine"),
        ("provider_fallback", "core.provider_fallback_native", "ProviderFallbackEngine"),
        ("mcp_a2a_bridge", "core.mcp_a2a_bridge_native", "MCPA2ABridge"),
        ("multimodal_api", "core.multimodal_api_native", "MultimodalAPI"),
        ("api_key_vault", "core.api_key_vault_native", "APIKeyVault"),
        ("provider_health", "core.provider_health_monitor_native", "ProviderHealthMonitor"),
        ("exploit_archive", "core.exploit_archive_manager_native", "ExploitArchiveManager"),
        ("cve_tracker", "core.cve_tracker_native", "CVETracker"),
        ("vuln_fingerprinter", "core.vulnerability_fingerprinter_native", "VulnerabilityFingerprinter"),
        ("exploit_chain", "core.exploit_chain_analyzer_native", "ExploitChainAnalyzer"),
        ("poc_validator", "core.poc_validator_native", "PoCValidator"),
        ("writeup_parser", "core.research_writeup_parser_native", "ResearchWriteupParser"),
        ("exploit_classifier", "core.exploit_classifier_native", "ExploitClassifier"),
        ("target_recon", "core.target_reconnaissance_native", "TargetReconnaissance"),
        ("fugu_orchestrator", "core.fugu_orchestrator_native", "FuguOrchestrator"),
        ("agent_native_memory", "core.agent_native_memory_native", "AgentNativeMemory"),
        ("autodata_synthetic", "core.autodata_synthetic_native", "AutodataSynthetic"),
        ("agent_critique", "core.agent_critique_analyzer_native", "AgentCritiqueAnalyzer"),
        ("agent_router", "core.agent_router_native", "AgentRouter"),
        ("agent_comm_taxonomy", "core.agent_comm_taxonomy_native", "AgentCommTaxonomy"),
        ("self_play_autonomy", "core.self_play_autonomy_native", "SelfPlayAutonomyTrainer"),
        ("skill_mas_evolver", "core.skill_mas_evolver_native", "SkillMASEvolver"),
        ("llm_judge_evaluator", "core.llm_judge_evaluator_native", "LLMJudgeEvaluator"),
        ("nature_bench", "core.nature_bench_native", "NatureBench"),
        ("skill_tree", "core.skill_tree_builder_native", "SkillTreeBuilder"),
        ("skill_dag", "core.skill_dag_orchestrator_native", "SkillDAGOrchestrator"),
        ("skill_search", "core.skill_search_engine_native", "SkillSearchEngine"),
        ("skill_registry", "core.skill_registry_native", "SkillRegistry"),
        ("workflow_executor", "core.workflow_executor_native", "WorkflowExecutor"),
        ("benchmark_engine", "core.benchmark_engine_native", "BenchmarkEngine"),
        ("human_in_loop", "core.human_in_loop_controller_native", "HumanInLoopController"),
        ("skill_scanner", "core.skill_scanner_indexer_native", "SkillScannerIndexer"),
        ("nuclei_template_builder", "core.nuclei_template_builder_native", "NucleiTemplateBuilder"),
        ("nuclei_template_validator", "core.nuclei_template_validator_native", "NucleiTemplateValidator"),
        ("nuclei_matcher_engine", "core.nuclei_matcher_engine_native", "NucleiMatcherEngine"),
        ("nuclei_extractor_engine", "core.nuclei_extractor_engine_native", "NucleiExtractorEngine"),
        ("nuclei_template_scanner", "core.nuclei_template_scanner_native", "NucleiTemplateScanner"),
        ("nuclei_workflow_engine", "core.nuclei_workflow_engine_native", "NucleiWorkflowEngine"),
        ("nuclei_template_library", "core.nuclei_template_library_native", "NucleiTemplateLibrary"),
        ("nuclei_dsl_executor", "core.nuclei_dsl_executor_native", "NucleiDSLExecutor"),
        ("triple_extractor", "core.triple_extractor_native", "TripleExtractor"),
        ("text_chunker", "core.text_chunker_native", "TextChunker"),
        ("entity_standardizer", "core.entity_standardizer_native", "EntityStandardizer"),
        ("relationship_inference", "core.relationship_inference_native", "RelationshipInferenceEngine"),
        ("knowledge_graph", "core.knowledge_graph_builder_native", "KnowledgeGraphBuilder"),
        ("graph_visualizer", "core.graph_visualizer_native", "GraphVisualizer"),
        ("prompt_factory", "core.prompt_factory_native", "PromptFactory"),
        ("graph_community_detector", "core.graph_community_detector_native", "GraphCommunityDetector"),
        ("conversation_buffer", "core.conversation_buffer_memory_native", "ConversationBufferMemory"),
        ("sliding_window_memory", "core.sliding_window_memory_native", "SlidingWindowMemory"),
        ("summary_buffer", "core.summary_buffer_memory_native", "SummaryBufferMemory"),
        ("token_buffer", "core.token_buffer_memory_native", "TokenBufferMemory"),
        ("memory_consolidation", "core.memory_consolidation_engine_native", "MemoryConsolidationEngine"),
        ("temporal_memory", "core.temporal_memory_native", "TemporalMemory"),
        ("forgetting_decay", "core.forgetting_decay_engine_native", "ForgettingDecayEngine"),
        ("multi_agent_shared", "core.multi_agent_shared_memory_native", "MultiAgentSharedMemory"),
        ("gjc_workflow", "core.gjc_workflow_engine_native", "GJCWorkflowEngine"),
        ("tmux_session", "core.tmux_session_manager_native", "TmuxSessionManager"),
        ("team_coordinator", "core.team_coordinator_native", "TeamCoordinator"),
        ("image_input", "core.image_input_processor_native", "ImageInputProcessor"),
        ("mobile_notification", "core.mobile_notification_bridge_native", "MobileNotificationBridge"),
        ("role_agent_dispatcher", "core.role_agent_dispatcher_native", "RoleAgentDispatcher"),
        ("research_repl", "core.research_repl_mode_native", "ResearchREPLMode"),
        ("worktree_isolation", "core.worktree_isolation_manager_native", "WorktreeIsolationManager"),
        # Domain: Sandbox
        ("sandbox_process", "core.sandbox_process_isolator_native", "SandboxProcessIsolator"),
        ("sandbox_resource", "core.sandbox_resource_limiter_native", "SandboxResourceLimiter"),
        ("sandbox_seccomp", "core.sandbox_seccomp_simulator_native", "SandboxSeccompSimulator"),
        ("sandbox_chroot", "core.sandbox_chroot_manager_native", "SandboxChrootManager"),
        ("sandbox_runner", "core.sandbox_code_runner_native", "SandboxCodeRunner"),
        ("sandbox_syscall_audit", "core.sandbox_syscall_auditor_native", "SandboxSyscallAuditor"),
        ("sandbox_network", "core.sandbox_network_restrictor_native", "SandboxNetworkRestrictor"),
        ("sandbox_fsguard", "core.sandbox_file_system_guard_native", "SandboxFileSystemGuard"),
        # Domain: OSINT
        ("osint_domain", "core.osint_domain_recon_native", "OsintDomainRecon"),
        ("osint_email", "core.osint_email_harvester_native", "OsintEmailHarvester"),
        ("osint_social", "core.osint_social_scanner_native", "OsintSocialScanner"),
        ("osint_metadata", "core.osint_metadata_extractor_native", "OsintMetadataExtractor"),
        ("osint_dns", "core.osint_dns_enumerator_native", "OsintDnsEnumerator"),
        ("osint_whois", "core.osint_whois_parser_native", "OsintWhoisParser"),
        ("osint_screenshot", "core.osint_screenshot_collector_native", "OsintScreenshotCollector"),
        ("osint_report", "core.osint_report_generator_native", "OsintReportGenerator"),
        # Domain: Vector DB
        ("vector_hnsw", "core.vector_hnsw_index_native", "VectorHNSWIndex"),
        ("vector_storage", "core.vector_storage_engine_native", "VectorStorageEngine"),
        ("vector_search", "core.vector_similarity_search_native", "VectorSimilaritySearch"),
        ("vector_reduction", "core.vector_dimension_reduction_native", "VectorDimensionReduction"),
        ("vector_ann", "core.vector_ann_query_engine_native", "VectorANNQueryEngine"),
        ("vector_merger", "core.vector_index_merger_native", "VectorIndexMerger"),
        ("vector_batch", "core.vector_batch_inserter_native", "VectorBatchInserter"),
        ("vector_metadata_filter", "core.vector_metadata_filter_native", "VectorMetadataFilter"),
        # Domain: WebSocket
        ("websocket_server", "core.websocket_server_native", "WebSocketServer"),
        ("websocket_pubsub", "core.websocket_pubsub_broker_native", "WebSocketPubSubBroker"),
        ("websocket_channel", "core.websocket_channel_manager_native", "WebSocketChannelManager"),
        ("websocket_queue", "core.websocket_message_queue_native", "WebSocketMessageQueue"),
        ("websocket_registry", "core.websocket_client_registry_native", "WebSocketClientRegistry"),
        ("websocket_heartbeat", "core.websocket_heartbeat_monitor_native", "WebSocketHeartbeatMonitor"),
        ("websocket_broadcast", "core.websocket_broadcast_engine_native", "WebSocketBroadcastEngine"),
        ("websocket_presence", "core.websocket_presence_tracker_native", "WebSocketPresenceTracker"),
        # Domain: Raft Consensus
        ("raft_node", "core.raft_node_state_machine_native", "RaftNodeStateMachine"),
        ("raft_log", "core.raft_log_replicator_native", "RaftLogReplicator"),
        ("raft_election", "core.raft_election_manager_native", "RaftElectionManager"),
        ("raft_heartbeat", "core.raft_heartbeat_coordinator_native", "RaftHeartbeatCoordinator"),
        ("raft_snapshot", "core.raft_snapshot_manager_native", "RaftSnapshotManager"),
        ("raft_membership", "core.raft_membership_changer_native", "RaftMembershipChanger"),
        ("raft_persistence", "core.raft_persistence_store_native", "RaftPersistenceStore"),
        ("raft_network", "core.raft_network_simulator_native", "RaftNetworkSimulator"),
        # Domain: Quantization
        ("quant_gguf", "core.quantization_gguf_loader_native", "QuantizationGGUFLoader"),
        ("quant_gptq", "core.quantization_gptq_simulator_native", "QuantizationGPTQSimulator"),
        ("quant_awq", "core.quantization_awq_simulator_native", "QuantizationAWQSimulator"),
        ("quant_bitpack", "core.quantization_bit_packer_native", "QuantizationBitPacker"),
        ("quant_calibration", "core.quantization_calibration_engine_native", "QuantizationCalibrationEngine"),
        ("quant_fuser", "core.quantization_layer_fuser_native", "QuantizationLayerFuser"),
        ("quant_kv_cache", "core.quantization_kv_cache_compressor_native", "QuantizationKVCacheCompressor"),
        ("quant_exporter", "core.quantization_model_exporter_native", "QuantizationModelExporter"),
        # Domain: Squad Multi-Agent Collaboration
        ("squad_agent_registry", "core.squad_agent_registry_native", "SquadAgentRegistry"),
        ("squad_message_bus", "core.squad_message_bus_native", "SquadMessageBus"),
        ("squad_role_dispatcher", "core.squad_role_dispatcher_native", "SquadRoleDispatcher"),
        ("squad_workspace", "core.squad_workspace_manager_native", "SquadWorkspaceManager"),
        ("squad_slash_command", "core.squad_slash_command_native", "SquadSlashCommand"),
        ("squad_terminal", "core.squad_terminal_coordinator_native", "SquadTerminalCoordinator"),
        ("squad_inspector", "core.squad_inspector_native", "SquadInspector"),
        ("squad_collaboration_log", "core.squad_collaboration_log_native", "SquadCollaborationLog"),
        # Domain: Free LLM APIs
        ("freellm_provider_registry", "core.freellm_provider_registry_native", "FreellmProviderRegistry"),
        ("freellm_model_catalog", "core.freellm_model_catalog_native", "FreellmModelCatalog"),
        ("freellm_config_generator", "core.freellm_config_generator_native", "FreellmConfigGenerator"),
        ("freellm_rate_limit_tracker", "core.freellm_rate_limit_tracker_native", "FreellmRateLimitTracker"),
        ("freellm_provider_monitor", "core.freellm_provider_monitor_native", "FreellmProviderMonitor"),
        ("freellm_api_key_manager", "core.freellm_api_key_manager_native", "FreellmApiKeyManager"),
        ("freellm_capability_matcher", "core.freellm_capability_matcher_native", "FreellmCapabilityMatcher"),
        ("freellm_free_tier_quota", "core.freellm_free_tier_quota_native", "FreellmFreeTierQuota"),
        # Domain: TMax Terminal Agent Training
        ("tmax_training_pipeline", "core.tmax_training_pipeline_native", "TmaxTrainingPipeline"),
        ("tmax_rl_data_generator", "core.tmax_rl_data_generator_native", "TmaxRLDataGenerator"),
        ("tmax_evaluation_suite", "core.tmax_evaluation_suite_native", "TmaxEvaluationSuite"),
        ("tmax_task_builder", "core.tmax_task_builder_native", "TmaxTaskBuilder"),
        ("tmax_dataset_curator", "core.tmax_dataset_curator_native", "TmaxDatasetCurator"),
        ("tmax_training_launcher", "core.tmax_training_launcher_native", "TmaxTrainingLauncher"),
        ("tmax_agent_rollout", "core.tmax_agent_rollout_simulator_native", "TmaxAgentRolloutSimulator"),
        ("tmax_reward_processor", "core.tmax_reward_signal_processor_native", "TmaxRewardSignalProcessor"),
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
