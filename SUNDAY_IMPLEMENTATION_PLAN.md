# Sunday AI - Personal Assistant Implementation Plan & Hardware Feasibility

## 1. System Overview & Hardware Target

### Hardware Constraints
- **Host Laptop**: HP Pavilion i7 (16GB RAM, No Dedicated GPU, Windows 11).
- **Secondary / Primary Storage**: 1TB External Portable Hard Drive labeled **`SUNDAY_DRIVE`**.
- **Constraint Philosophy**:
  - The host laptop must have near **zero permanent footprint** (no heavy local model weights or gigabytes of databases cluttering the internal SSD).
  - Heavy intelligence is routed **Cloud-Primary** (OpenAI / Anthropic / Gemini).
  - Lightweight CPU fallback is maintained for disconnected offline survival.
  - Storage, long-term logs, SQLite databases, and sub-agent artifacts live on the **`SUNDAY_DRIVE`**.

---

## 2. Architecture & Execution Phases

### Phase 1: USB Auto-Trigger & Storage Architecture
- **Host Daemon**: `sunday/usb_trigger/usb_listener.ps1` runs quietly in Windows Startup (`shell:startup`).
- **Detection**: Polls every 5 seconds for volume labeled `SUNDAY_DRIVE`.
- **Bootstrap**: Executes `bootstrap_sunday.bat` on insertion, configuring `SUNDAY_DATA_DIR` and mounting Sunday.
- **Environment**: Automatically parses `.env` on the drive root and registers keys into `TokenPool`.

### Phase 2: Dual-Tier Intelligence & Rate-Limit Failover
- **Cloud-Primary**: High-speed GPT-4o / Claude 3.5 Sonnet / Gemini 1.5 Pro for deep coding and reasoning.
- **TokenPool**: Dynamically manages multiple API keys per provider, automatically failing over on HTTP 429 quota exhaustion.
- **Local Fallback**: Connects to local Ollama (Phi-3 / Mistral) when no network connectivity is present.

### Phase 3: Voice Pipeline & Biometric Speaker Recognition
- **Wake Word**: OpenWakeWord engine detecting "Hey Sunday" / "Hey Jarvis".
- **Biometric Verifier**: `BiometricVerifier` computes acoustic signatures, validates user identity, and personalizes greetings.
- **TTS/STT**: Fast Whisper + EdgeTTS/Piper engine with persona modulation (Senpai, Jarvis, Friday, GenZ).

### Phase 4: Academic Senpai Mode & Distraction Minimizer
- **Socratic Tutor**: `SocraticTutor` prompts guiding questions rather than immediately answering, fostering deep learning.
- **Focus Sentry**: 3-stage distraction escalation:
  1. Voice sigh/nudge.
  2. Windows desktop toast warning.
  3. Window minimization + tree wilting.
- **Forest Engine**: SQLite-backed tree growth game (`forest.db`).

### Phase 5: Autonomous Sub-Agents & IDE Switching
- **UniversalController**: Handles IDE workspace focus, account switching, and rate-limit recovery.
- **SubAgentExecutor**: Asynchronously spawns, monitors, and terminates isolated sub-agent processes and scripts.

### Phase 6: Mobile Connectivity (Telegram Bot)
- **Telegram Bridge**: Direct bidirectional remote link via `SundayTelegramBot`.
- **Capabilities**:
  - Send commands to laptop from phone.
  - Send voice notes (transcribed and handled by Swarm Conductor).
  - Proactive notification nudges.

### Phase 7: Sentience & 24/7 Nightly Self-Reflection
- **Insomnia Mode**: Windows AwayMode keeps background daemons alive with lid closed when connected to AC power.
- **SentienceEngine**: At 3:00 AM nightly:
  1. Consolidates daytime conversation history and task logs.
  2. Synthesizes memory into `reflections.db`.
  3. Derives user habit insights and generates self-improvement notes.

---

## 3. Quick Start & Execution Guide

1. **Format/Label External Drive**:
   - Right click drive in File Explorer -> Properties -> Label as `SUNDAY_DRIVE`.
2. **Setup Auto-Trigger**:
   - Press `Win + R` -> `shell:startup`.
   - Copy or create a shortcut to `sunday/usb_trigger/usb_listener.ps1`.
3. **Configure API Keys**:
   - Copy `.env.example` to `.env` on `SUNDAY_DRIVE`.
   - Enter your OpenAI / Anthropic / Gemini API keys and Telegram Bot token.
4. **Launch**:
   - Plug in `SUNDAY_DRIVE` or execute `sunday/usb_trigger/bootstrap_sunday.bat` manually.
