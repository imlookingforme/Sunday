# 🌅 Sunday AI

> **A Voice-First, Cloud-Primary, Local-Zero-Footprint Personal AI Assistant tailored for HP Pavilion laptops.**

Sunday is an autonomous, multi-agent AI companion designed to run seamlessly from an external 1TB portable hard drive (`SUNDAY_DRIVE`), leaving near-zero clutter on your laptop while delivering high-speed intelligence, academic tutoring, distraction mitigation, and remote phone connectivity.

---

## ✨ Key Features

- 🔌 **Plug & Play USB Auto-Trigger**:
  - Insert your 1TB `SUNDAY_DRIVE`, and Sunday wakes up automatically via silent Windows background detection (`usb_listener.ps1`).
  - Zero permanent footprint on host laptop; all memory stores, databases, and logs live on the external drive.

- 🧠 **Dual-Tier Intelligence (Cloud-Primary / Local-Fallback)**:
  - High-performance cloud intelligence (GPT-4o, Claude 3.5, Gemini 1.5) with automatic `TokenPool` API key failover on rate limits (429).
  - Offline fallback support via Ollama (Phi-3).

- 🎙️ **Voice First with Biometric Speaker Identification**:
  - Continuous wake-word detection ("Hey Sunday", "Hey Jarvis").
  - `BiometricVerifier` validates speaker identity before executing sensitive operations and tailors greetings.

- 🎓 **Senpai Academic Tutor & Focus Sentry**:
  - Socratic study tutor providing guiding questions and Pomodoro plans.
  - 3-stage distraction escalation: verbal nudge -> toast warning -> auto-minimization & virtual Sakura tree wilting in the Forest garden.

- 🤖 **Autonomous Sub-Agents & Swarm Specialists**:
  - Spawns background scripts, monitors output, handles timeouts, and self-heals code issues.
  - Core Swarm Specialists: `Conductor`, `Coder`, `Scout`, `Automator`, and `Gatekeeper`.

- 📱 **Mobile Phone Link (Telegram Bot)**:
  - Control your laptop remotely via Telegram.
  - Send voice notes or text commands from anywhere; receive proactive notifications and study reminders.

- 🌙 **24/7 Sentience & Nightly Self-Reflection**:
  - Windows Insomnia AwayMode keeps background workers active with the laptop lid closed.
  - `SentienceEngine` consolidates daily memories and generates self-improvement notes every night at 3:00 AM.

---

## 🚀 Quick Start Guide

### 1. Drive Preparation
1. Plug in your 1TB external hard drive.
2. Open **This PC**, right-click the drive -> **Rename** / **Properties**, and set the label to:
   ```
   SUNDAY_DRIVE
   ```
3. Copy the Sunday codebase to the drive root.

### 2. Configure Environment (.env)
Copy `.env.example` to `.env` on your drive root:
```bash
cp .env.example .env
```
Add your API keys (OpenAI, Anthropic, Gemini) and your Telegram Bot token.

### 3. Auto-Trigger Setup (Plug & Play)
To have Sunday automatically boot whenever you plug in the drive:
1. Press `Win + R`, type `shell:startup`, and hit Enter.
2. Create a shortcut to `sunday/usb_trigger/usb_listener.ps1` in this Startup folder.

---

## 🎮 Interactive Commands & Controls

### In-Console Slash Commands
When running in text mode, you have direct control via interactive slash commands:

| Command | Action | Description |
|---|---|---|
| `/status` | **System Diagnostics** | Shows daemon mode, tool count, active MCP connections, and memory episode stats. |
| `/swarm` | **Swarm Mesh Inspection** | Lists all 5 specialists (`conductor`, `coder`, `scout`, `automator`, `gatekeeper`) and running background tasks. |
| `/tools` | **Tool Catalog** | Displays all 140+ enabled tools categorized by domain with risk classifications. |
| `/help` | **Quick Help** | Interactive guide of available commands and shortcut keys. |

### Mid-Flight Conversational Steering
Sunday's Live Steering Engine listens to natural voice corrections while running background tasks:
- **Patch a running task**: *"Wait, also make it output JSON"* (steers background Coder/Automator without aborting context).
- **Abort a task**: *"Cancel that"* (instantly halts the specialist).
- **Status check**: *"What's the swarm doing right now?"* (returns real-time progress across all specialists).

---

## 🧪 Testing & Verification

Sunday includes a 100% passing test suite across all development phases:

```powershell
# Run the complete test suite
pytest tests/ -v
```

---

## 📜 License & Author

**Author**: Raghuram Vedantam & The Sunday Development Team  
**License**: MIT License. See [LICENSE](LICENSE) for details.
