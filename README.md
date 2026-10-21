# 🌅 Sunday AI

> **A Voice-First, Cloud-Primary, Local-Zero-Footprint Personal AI Assistant tailored for HP Pavilion laptops.**

Sunday is an autonomous, multi-agent AI companion designed to run seamlessly from an external 1TB portable hard drive (`SUNDAY_DRIVE`), leaving near-zero clutter on your laptop while delivering high-speed intelligence, academic tutoring, distraction mitigation, and remote phone connectivity.

---

## ✨ Key Features

- 🔌 **Plug & Play USB Auto-Trigger**:
  - Insert your 1TB `SUNDAY_DRIVE`, and Sunday wakes up automatically via silent Windows background detection.
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

## 🧪 Running Tests

To run the complete test suite:
```bash
pytest tests/ -v
```

---

## 📜 License
MIT License. See [LICENSE](LICENSE) for details.
