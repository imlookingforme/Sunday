# Sunday Implementation & Feasibility Plan

## Hardware Assessment: HP Pavilion i7 (16GB RAM, No Dedicated GPU, 1TB External HDD)

*   **CPU:** The i7 processor handles standard web requests, API routing, lightweight embedding models (`all-MiniLM-L6-v2`), and local text-to-speech without issue.
*   **RAM:** 16GB is sufficient to hold the OS, background tasks, and a quantized local language model (e.g., 4-bit quantized Phi-3 mini via Ollama) for offline fallback.
*   **GPU:** *No dedicated GPU.* Heavy AI tasks (unquantized large models, video diffusion, heavy local Whisper Large transcription) are routed to high-speed cloud providers (OpenAI, Anthropic, Gemini).
*   **Storage:** The 1TB external HDD labeled `SUNDAY_DRIVE` acts as the primary "brain drive," storing SQLite databases, vector embeddings, code repositories, and cache directories (`HF_HOME`, `OLLAMA_MODELS`), guaranteeing near-zero clutter on the laptop's internal drive.

---

### Strategic Architecture: Cloud-Primary / Local-Fallback
1.  **Primary Engine (Cloud):** Heavy intelligence tasks (coding, academic tutoring, complex reasoning) route to Cloud APIs (OpenAI/Anthropic/Gemini) with automatic key failover via `TokenPool`.
2.  **Fallback Engine (Local):** If disconnected, Sunday seamlessly falls back to CPU-quantized models via Ollama (`phi3:mini`).
3.  **Local "Reflexes" (CPU):** Wake word detection (`openWakeWord`), Text-to-Speech (`piper-tts` / `edge-tts`), and Vector Embeddings (`all-MiniLM-L6-v2`) run smoothly on the i7 CPU.

---

## Feature Roadmap & Implementation Details

### Phase 1: USB Auto-Trigger & Storage Sandbox (Foundation)
**Goal:** Create a plug-and-play experience where connecting the 1TB drive instantly launches Sunday, with zero data footprint left on the host laptop.
*   **Host Daemon:** `sunday/usb_trigger/usb_listener.ps1` runs in the Windows Startup folder (`shell:startup`) and polls for `SUNDAY_DRIVE`.
*   **External Bootstrapper:** `bootstrap_sunday.bat` launches Sunday directly from the drive, pointing cache directories and storage away from `C:\`.
*   **Environment Integration:** Reads `.env` from drive root and automatically populates `TokenPool`.

### Phase 2: Biometric Voice Pipeline & Speaker Verification
**Goal:** Continuous voice-first interface with biometric security and personalized speaker identity.
*   **Wake Word:** Detects "Hey Sunday" or "Hey Jarvis" locally.
*   **Biometric Verifier:** `BiometricVerifier` computes acoustic signatures, validates speaker profiles against `voice_profiles.db`, and tailors greetings.
*   **Transcription:** Cloud Whisper with local fallback.

### Phase 3: The Sentience & Insomnia Engine
**Goal:** 24/7 background execution with nightly memory consolidation and self-reflection.
*   **Windows Insomnia:** Uses `SetThreadExecutionState` (AwayMode) so Sunday stays running with the laptop lid closed when connected to AC power.
*   **Sentience Engine:** Every night at 3:00 AM, reviews daytime conversations and SQLite task logs, derives habit insights, and records self-improvement journals into `reflections.db`.

### Phase 4: IDE Management & Autonomous Sub-Agents
**Goal:** Coding agent capable of auto-switching IDEs, rotating Google accounts on usage limits, and spawning isolated background workers.
*   **Universal Controller:** Handles window focus, workspace switching, and IDE shortcuts.
*   **SubAgent Executor:** Spawns asynchronous sub-agent scripts, monitors stdout logs, enforces execution timeouts, and kills stalled processes.

### Phase 5: Academic Senpai Mode & Distraction Minimizer
**Goal:** Dedicated study tutor with gradual distraction intervention.
*   **Socratic Tutor:** Employs Socratic questioning and Pomodoro sprint planning.
*   **Focus Sentry:** 3-stage distraction escalation:
    1. Soft voice reminder.
    2. Minimal desktop notification toast.
    3. Auto-minimization of distraction windows and virtual Sakura tree wilting in the Forest garden.
*   **Forest Engine:** SQLite-backed virtual focus garden (`forest.db`).

### Phase 6: Mobile Connectivity (Telegram Bot)
**Goal:** Bidirectional remote control from your smartphone.
*   **Telegram Daemon:** `SundayTelegramBot` polls for text commands and voice notes from your phone, routes them to Swarm Conductor, and sends proactive notifications.

---

## Verification & Test Plan

1. **USB Auto-Trigger**:
   - `pytest tests/test_usb_trigger.py`
2. **Biometrics & Sentience**:
   - `pytest tests/test_biometric_sentience.py`
3. **Sub-Agent Execution**:
   - `pytest tests/test_sub_agent.py tests/test_sub_agent_executor.py`
4. **Academic Focus & Distraction**:
   - `pytest tests/test_phase5_academic_focus.py`
5. **Full Project Suite**:
   - `pytest tests/ -v` (100% passing across 45+ tests)
