---
id: n8n-workflow-runtime
name: n8n Native Workflow Runtime
version: 1.0.0
category: automation
tags: [workflow, automation, dag, node, execution, runtime]
author: MAGNATRIX-OS
layer: 3
description: |
  Native workflow automation runtime inspired by n8n.
  Pola AMATI-PELAJARI-TIRU dari github.com/n8n-io/n8n:
  - DAG-based workflow execution dengan topological sort
  - Node-based modularity: trigger, action, transform, condition, code, AI
  - Expression evaluation engine (Python-native, reimagined dari JS {{ }})
  - Trigger system: webhook, cron, mesh event, polling, manual
  - Credential vault dengan Fernet encryption
  - Queue mode dengan worker pool untuk horizontal scaling
  - 13 built-in node types terintegrasi dengan MAGNATRIX ecosystem

  Features:
  - Visual workflow builder backend (JSON DAG persistensi)
  - Expression evaluator dengan $json, $vars, $env, $node context
  - HTTP Request node dengan credential integration
  - Code node (Python) untuk custom logic
  - AI node terintegrasi dengan Free LLM Router
  - Mesh node untuk swarm broadcast
  - Skill node untuk skill registry invocation
  - Error handling dengan retry, continue, stop policies

inputs:
  - name: workflow_name
    type: string
    description: Workflow name
    required: true
  - name: nodes
    type: array
    description: Array of workflow nodes
    required: true
  - name: trigger
    type: object
    description: Trigger configuration
    required: false
  - name: trigger_data
    type: object
    description: Input data untuk manual execution
    default: {}

outputs:
  - name: execution_id
    type: string
    description: Workflow execution ID
  - name: status
    type: string
    description: Execution status
  - name: node_results
    type: object
    description: Results dari setiap node

execution:
  module: runtime.n8n_native_runtime
  class: WorkflowOrchestrator
  method: execute

examples:
  - description: Simple HTTP pipeline
    input:
      workflow_name: API Pipeline
      nodes:
        - type: http
          name: Fetch Data
          parameters:
            method: GET
            url: https://api.example.com/data
        - type: transform
          name: Filter
          parameters:
            operations:
              - type: filter
                expression: "$item.json.status == 'active'"
        - type: ai
          name: Analyze
          parameters:
            prompt: "Summarize: {{ $item.json }}"

integration:
  mesh_channel: workflow.executions
  triggers: [webhook, cron, mesh, manual]
  credential_vault: true
