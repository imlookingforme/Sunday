# SUNDAY 2.0 — BASELINE ARCHITECTURAL AUDIT & IMPLEMENTATION BLUEPRINT

## 1. Executive Summary & Vision Alignment
Sunday is transitioning from an AI-assisted voice/chat agent into an **Autonomous Engineering Platform**. 
Governing Principle: **Autonomy + Verifiability + Safety + Project Understanding**.

All baseline checks pass (47/47 pytest suite verified in 164s on Python 3.12). This audit establishes the current architectural boundaries, gaps, risks, and a sequenced roadmap for the overhaul.

---

## 2. Architecture Map & Subsystem Boundaries

```
  [ UI & Ingress Layer ]
  Interactive CLI / Daemon Pipeline <---> FastAPI Dashboard / SSE / REST <---> Telegram Bot Bridge
                                      │
                                      ▼
  [ Security & Policy Enforcement ]
  Broker Pipeline (Validate -> Classify -> Gate -> Inject -> Execute -> Audit)
  PermissionChecker + KeyringVault + Hash-Chained AuditLedger
                                      │
                                      ▼
  [ Orchestration & Swarm Mesh ]
  SwarmBus (Priority Event Mesh) <---> Conductor Agent <---> LiveSteeringManager
       ├── Coder Specialist (Patch-Aware)
       ├── Automator Specialist (OS Shell & Actions)
       ├── Gatekeeper Specialist (Token/Security)
       └── SubAgentExecutor (Process Supervisor & Timeouts)
                                      │
                                      ▼
  [ Intelligence & Context Layer ]
  FluidIntent Engine + Titans Episodic Memory + TaskStore + Knowledge Graph
  + NEW: Project Intelligence AST Indexer & Dependency Graph
  + NEW: Autonomous Engineering Loop & Bounded Repair Engine
  + NEW: Git Worktree & Checkpoint Safety Manager
```

---

## 3. Inventory of Existing Capabilities

| Capability | Module | Verification Status | Evaluation / Status |
|---|---|---|---|
| Priority Event Bus & Live Steering | `sunday/core/swarm/bus.py`, `steering.py` | Verified (Tests Pass) | Robust pub/sub event bus with cancellation & priority topics |
| Fail-closed Tool Broker & Audit | `sunday/core/broker/broker.py`, `audit.py` | Verified (Tests Pass) | Pipeline exists: Validate -> Classify -> Gate -> Inject -> Execute -> Audit |
| Credential & Token Pool | `sunday/core/broker/token_pool.py`, `env_loader.py` | Verified (Tests Pass) | Auto-rotation on 429 errors across multiple providers |
| Voice Pipeline & Biometrics | `sunday/daemon/`, `biometric_verifier.py` | Verified (Tests Pass) | Wake-word, Whisper/Piper STT/TTS, deterministic voice hashing |
| Academic Senpai Focus & Forest | `sunday/core/focus/`, `sidecar/` | Verified (Tests Pass) | 3-stage distraction escalation & SQLite forest engine |
| 24/7 Insomnia & Sentience Loop | `sunday/daemon/insomnia.py`, `sentience_engine.py` | Verified (Tests Pass) | AwayMode lid-closed execution + nightly memory consolidation |
| Autonomous Script & SubAgent Exec | `sunday/core/swarm/sub_agent_executor.py` | Verified (Tests Pass) | Subprocess execution, log capturing, timeout bounds |

---

## 4. Key Gaps & Architectural Bottlenecks

1. **Durable Task State & Lifecycle**:
   - `TaskStore` in `sunday/memory/task_store.py` tracks basic to-do tasks (id, title, status) but lacks rich execution state: parent/child relationships, explicit state machine transitions (`queued -> planning -> ready -> running -> verifying -> completed`), checkpoints, budgets, tool call logs, and verification evidence.
2. **Project Intelligence & AST Indexer**:
   - `sunday` currently lacks deep static code analysis (symbol extraction, call graphs, import graphs, impact analysis, and test mapping). It needs a fast, AST-based project indexer with incremental file watching.
3. **Autonomous Engineering Loop (Plan -> Act -> Verify -> Repair)**:
   - Need an explicit `EngineeringLoop` that accepts high-level requirements, generates testable acceptance criteria, formulates structured execution plans, executes changes in isolated working trees, diagnoses failures from test evidence, and runs bounded repair loops (max $N$ attempts).
4. **Git Checkpointing & Safety**:
   - Agents currently write directly to the working directory without automated snapshot/rollback points, git worktree isolation for concurrent agents, or conflict detection.
5. **Centralized Policy & Sandbox Auditing**:
   - Broaden the `Broker` to intercept all filesystem modifications, command executions, and git operations with granular risk policies and approval workflows.

---

## 5. Phased Implementation Roadmap

1. **Phase 1: Durable Task Engine & State Machine**
   - Implement `DurableTaskEngine` with formal transition validation, recovery journaling, execution budgets, checkpoint tracking, and cancellation trees.
2. **Phase 2: Centralized Security & Policy Broker Extension**
   - Extend `Broker` with path-based workspace sandboxing, approval tokens, and strict fail-closed defaults for all filesystem/process/git operations.
3. **Phase 3: Project Intelligence & AST Dependency Indexer**
   - Build `sunday/core/indexer/` for parsing Python ASTs, symbol maps, import graphs, dependency impact analysis, and test association.
4. **Phase 4: Autonomous Engineering Loop & Bounded Repair**
   - Build `sunday/core/loop/` with acceptance criteria generator, test runner, failure diagnostician, and bounded repair loop.
5. **Phase 5: Git Safety & Worktree Checkpoint Manager**
   - Build `sunday/core/git_safety/` providing snapshot/rollback, worktree isolation for parallel agent tasks, and dirty-tree preservation.
6. **Phase 6: Multi-Agent Dependency Graph Orchestrator**
   - Enable DAG-based subtask scheduling across Coder, Test Engineer, Reviewer, and Verifier.
7. **Phase 7: Test Suite & End-to-End Verification**
   - Add unit and integration tests across all new modules and verify against the full project test suite.
