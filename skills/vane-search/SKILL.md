---
id: vane-search-engine
name: Vane Native AI Search Engine
version: 1.0.0
category: knowledge
tags: [search, rag, answering, ai, searxng, research]
author: MAGNATRIX-OS
layer: 5
description: |
  Native AI-powered answering engine inspired by Vane/Perplexica.
  Pola AMATI-PELAJARI-TIRU dari github.com/ItzCrazyKns/Vane:
  - RAG-based answering dengan multi-source aggregation
  - Copilot Mode: multi-query generation untuk comprehensive search
  - Focus Modes: All, Academic, Writing, YouTube, Wolfram, Reddit, News, Code, MAGNATRIX
  - Hybrid source ranking: relevance + freshness + authority + credibility
  - Citation-aware context assembly
  - Streaming answer generation
  - Parallel search via SearXNG + arXiv + GitHub + internal KG

  Features:
  - Query planning dengan intent detection dan heuristic expansion
  - Async parallel search orchestrator
  - Source ranker dengan domain authority scoring
  - Context assembler dengan token-aware truncation
  - Streaming answer generator terintegrasi Free LLM Router
  - Knowledge Hub untuk deep research synthesis
  - MAGNATRIX mesh integration untuk knowledge discovery broadcast

inputs:
  - name: query
    type: string
    description: Search query atau pertanyaan
    required: true
  - name: focus_mode
    type: string
    description: all | academic | writing | youtube | reddit | news | code | magnatrix
    default: all
  - name: copilot_mode
    type: boolean
    description: Generate multiple queries untuk comprehensive search
    default: false
  - name: stream
    type: boolean
    description: Stream answer secara real-time
    default: true
  - name: model
    type: string
    description: LLM model untuk answer generation
    default: openrouter/auto

outputs:
  - name: answer
    type: string
    description: Generated answer dengan citations
  - name: sources
    type: array
    description: Array of ranked sources dengan scores
  - name: citations
    type: array
    description: Citation map [1], [2], etc.
  - name: search_time_ms
    type: number
    description: Total search pipeline time

execution:
  module: knowledge.vane_native_search
  class: KnowledgeHub
  method: ask

examples:
  - description: Academic research query
    input:
      query: "Latest advances in reinforcement learning for trading"
      focus_mode: academic
      copilot_mode: true
  - description: Internal knowledge query
    input:
      query: "What is the MAGNATRIX architecture?"
      focus_mode: magnatrix
      copilot_mode: false

integration:
  mesh_channel: knowledge.discoveries
  search_providers: [searxng, arxiv, github, internal_kg]
  llm_router: free_llm_router
