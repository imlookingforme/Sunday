# Sunday Implementation & Feasibility Plan

## Hardware Assessment: HP Pavilion i7 (16GB RAM, No Dedicated GPU, 1TB External HDD)

*   **CPU:** The i7 processor is capable of handling standard web requests, API routing, lightweight embedding models, and local text-to-speech without issue.
*   **RAM:** 16GB is sufficient to hold the OS, background tasks, and a deeply quantized local language model (e.g., a 4-bit quantized Phi-3 or Llama-3 8B) for offline fallback.
*   **GPU:** *No dedicated GPU.* This means running complex AI (like image generation, unquantized large language models, or highly complex real-time speech-to-text models like Whisper Large) locally will be impractically slow.
*   **Storage:** The 1TB external HDD will act as the "brain drive." It has ample space for vector databases, SQLite logs, model weights, and the Sunday codebase itself.

### Strategic Architecture: Cloud-Primary / Local-Fallback
To maximize productivity while remaining hardware compliant:
1.  **Primary Engine (Cloud):** Sunday will route heavy intelligence tasks (coding, academic tutoring, complex reasoning) to Cloud APIs (OpenAI/Anthropic). This bypasses the local GPU constraint entirely and provides instant, high-quality responses.
2.  **Fallback Engine (Local):** If internet is unavailable, Sunday will fallback to a small, heavily quantized model running on the CPU via Ollama (e.g., `phi3:mini`). Responses will be slower and less complex, but functional.
3.  **Local "Reflexes" (CPU):** Wake word detection (`openWakeWord`), Text-to-Speech (`piper-tts`), and Vector Embeddings (`all-MiniLM-L6-v2`) are lightweight enough to run smoothly on the i7 CPU.

---

## Feature Roadmap & Implementation Details

### Phase 1: USB Auto-Trigger & Storage Sandbox (Foundation)
**Goal:** Create a plug-and-play experience where connecting the 1TB drive instantly launches Sunday, with zero data footprint left on the host laptop.

*   **Implementation:**
    1.  Create a lightweight Windows daemon (e.g., a simple C# or PowerShell background process) that runs invisibly on the host laptop.
    2.  The daemon polls for USB connection events. When it detects the specific Volume ID of the 1TB drive, it executes a bootstrap script located on the drive (`E:\launch_sunday.bat`).
    3.  The bootstrap script dynamically sets environment variables (e.g., `HF_HOME`, `OLLAMA_MODELS`, database paths) to point to directories *within* the external drive.
*   **Rigid Verification Check:**
    *   *Test:* Connect the USB drive. Verify the Sunday process starts automatically.
    *   *Check:* Disconnect the drive. Verify no Sunday cache files, database logs, or model weights exist on the laptop's `C:\` drive.

### Phase 2: Biometric Voice Pipeline
**Goal:** Implement continuous listening with speaker recognition to provide a personalized, voice-first interface.

*   **Implementation:**
    1.  Integrate `openWakeWord` to listen for "Hey Sunday" (runs on CPU).
    2.  Pass audio to a lightweight speaker verification model (e.g., SpeechBrain's CPU-friendly embedding models) to generate a voice print.
    3.  Compare the voice print against a stored profile. If it matches, accept the command; otherwise, reject or adapt the persona.
    4.  Route transcription to Cloud Whisper (for speed) or local `faster-whisper` (base model, for offline).
*   **Rigid Verification Check:**
    *   *Test:* Have the primary user speak "Hey Sunday", then have a different person speak it.
    *   *Check:* Verify the system accurately identifies the primary user and logs an authorization event.

### Phase 3: The "Sentience" & Insomnia Engine
**Goal:** Enable Sunday to run 24/7, self-reflect on interactions, and update its memory and code autonomously.

*   **Implementation:**
    1.  Utilize Windows `SetThreadExecutionState` to prevent the laptop from sleeping when the lid is closed (Insomnia mode).
    2.  Implement a background cron job. During idle periods (e.g., 3:00 AM), Sunday will wake up, review the day's SQLite memory logs, and extract key facts/preferences into the Vector Database (Titans Memory).
    3.  *Self-Reflection:* Sunday will occasionally review its own error logs. Using a Tree-of-Thought cloud prompt, it will attempt to write a patch for its own code, test it in a sandbox, and commit it if successful.
*   **Rigid Verification Check:**
    *   *Test:* Close the laptop lid. Send a Telegram message to Sunday.
    *   *Check:* Verify Sunday responds while the lid is closed. Review memory logs to ensure the nightly background summarization task executed successfully.

### Phase 4: IDE Management & Autonomous Sub-Agents
**Goal:** Automate coding workflows, handle account switching, and allow Sunday to spin up workers.

*   **Implementation:**
    1.  Enhance the `UniversalController` to integrate with the command-line interfaces of preferred IDEs (VS Code/Cursor).
    2.  Create a "Credential Manager" tool. If Sunday hits an API limit (e.g., a 429 error), it automatically swaps the API key or triggers an account switch script (e.g., updating GitHub CLI auth).
    3.  Implement a `SubAgent` class. Sunday can write a Python script, spawn it as a background process, and monitor its output asynchronously (e.g., "Sunday, write a script to scrape this website every hour").
*   **Rigid Verification Check:**
    *   *Test:* Instruct Sunday to create a sub-agent that prints the time every minute.
    *   *Check:* Verify the script is generated, executed, and the output is successfully captured in the logs.

### Phase 5: Academic Tutor & Distraction Minimizer
**Goal:** Create a focused study environment (Senpai Mode) with proactive interventions.

*   **Implementation:**
    1.  Implement the `FocusSentry` sidecar using Windows APIs to poll the active window title.
    2.  If the user opens a distracting application (e.g., YouTube) during a focus session, trigger a 3-stage escalation: (1) Voice warning, (2) Screen overlay, (3) Force minimize the window.
    3.  Integrate the Cloud LLM to act as a Socratic tutor, helping write research papers by querying arXiv and summarizing findings.
*   **Rigid Verification Check:**
    *   *Test:* Start a focus session. Open a known distracting website.
    *   *Check:* Verify the 3-stage escalation triggers accurately and the window is minimized.

### Phase 6: Phone Connectivity & Dashboard
**Goal:** Remote control and notifications via mobile.

*   **Implementation:**
    1.  Deploy a Telegram bot integrated directly into the `SwarmBus`. This allows sending text/voice notes to Sunday from the phone.
    2.  Serve the FastAPI web dashboard. Use Cloudflare Tunnels (or similar) to securely expose the local port 8000 to the internet, allowing access to the UI from the phone.
*   **Rigid Verification Check:**
    *   *Test:* Send a command via Telegram from the phone.
    *   *Check:* Verify the command executes on the laptop and the response is sent back to the phone.



# USB Auto-Trigger & Environment Architecture

To ensure Sunday leaves a zero-data footprint on the host laptop (HP Pavilion) and boots directly from the 1TB external HDD, we employ a two-part architecture:

1.  **The Host Daemon (Laptop):** A tiny background process that listens for USB events.
2.  **The Bootstrap Script (HDD):** A script that sets local paths and launches the Sunday pipeline.

## 1. The Host Daemon (`usb_listener.ps1` or C# Service)

This script must be placed on the host laptop (e.g., in the Startup folder) and run in the background. It continuously monitors Windows Management Instrumentation (WMI) for `Win32_VolumeChangeEvent`.

```powershell
# usb_listener.ps1 (Runs on Host Laptop)
$query = "SELECT * FROM Win32_VolumeChangeEvent WHERE EventType = 2"
Register-WmiEvent -Query $query -SourceIdentifier "USBPluggedIn" -Action {
    $drive = Get-WmiObject Win32_Volume | Where-Object { $_.Label -eq "SUNDAY_DRIVE" }
    if ($drive) {
        $driveLetter = $drive.DriveLetter
        $scriptPath = "$driveLetter\bootstrap_sunday.bat"
        if (Test-Path $scriptPath) {
            # Execute the bootstrap script silently
            Start-Process -FilePath $scriptPath -WindowStyle Hidden
        }
    }
}
```

## 2. The Bootstrap Script (`bootstrap_sunday.bat`)

This script resides on the root of the 1TB HDD. When triggered by the Host Daemon, it forces all Python environment variables to point *inside* the HDD, ensuring no models or databases leak onto the `C:\` drive.

```bat
@echo off
:: bootstrap_sunday.bat (Resides on the 1TB HDD)

:: Get the current drive letter (e.g., E:)
set DRIVE_LETTER=%~d0

:: Set all AI paths to point to the external drive
set HF_HOME=%DRIVE_LETTER%\sunday_env\huggingface_cache
set OLLAMA_MODELS=%DRIVE_LETTER%\sunday_env\ollama_models
set SUNDAY_DB_PATH=%DRIVE_LETTER%\sunday_env\data\sunday.db
set SUNDAY_VECTOR_PATH=%DRIVE_LETTER%\sunday_env\data\vectors

:: Activate the virtual environment located on the drive
call %DRIVE_LETTER%\sunday_env\Scripts\activate.bat

:: Launch the Sunday Daemon with Insomnia (24/7) and Mobile Dashboard enabled
cd %DRIVE_LETTER%\Sunday
python -m sunday.daemon.pipeline --insomnia --dashboard --telegram
```

## Rigid Verification

**Test Procedure:**
1. Configure `usb_listener.ps1` to run on startup on the host laptop.
2. Label the 1TB external drive as `SUNDAY_DRIVE`.
3. Place `bootstrap_sunday.bat` and the `Sunday` codebase on the drive.
4. Unplug the drive, then plug it back in.

**Expected Outcome:**
1. The Sunday process (and FastAPI dashboard) should start automatically within 10 seconds of plugging in the drive.
2. Check the host laptop's `C:\Users\<User>\.cache\huggingface` and `C:\Users\<User>\.ollama` directories. They must be completely empty or non-existent, confirming that all heavy weights are stored on the external drive.

---

## Development & Execution Roadmap

The following roadmap synthesizes the features into an actionable, step-by-step implementation sequence:

### Step 1: Local Environment & USB Foundation (Week 1)
- **Task:** Create the `usb_listener.ps1` and `bootstrap_sunday.bat` scripts.
- **Task:** Set up the isolated Python virtual environment on the 1TB drive.
- **Verification:** Plug in the drive on the HP Pavilion; verify the environment activates automatically and no caches leak to the `C:\` drive.

### Step 2: Core Intelligence & Token Pool (Week 2)
- **Task:** Finalize the `TokenPool` implementation (fix missing dependencies like `keyring`).
- **Task:** Implement the `FluidIntentEngine` routing logic to default to Cloud APIs (OpenAI/Anthropic).
- **Task:** Integrate the fallback `Ollama` local LLM (e.g., `phi3:mini`) and ensure it runs within the 16GB RAM constraint without crashing.
- **Verification:** Run a complex reasoning query (ensure Cloud API is used). Disconnect the internet and run a simple query (ensure Ollama fallback engages).

### Step 3: Voice Pipeline & Biometrics (Week 3)
- **Task:** Integrate `openWakeWord` and `piper-tts`.
- **Task:** Implement speaker verification (e.g., using `speechbrain` or `pyannote.audio` CPU models).
- **Verification:** Speak "Hey Sunday" to trigger the system. Have an unregistered voice speak it and verify rejection. Ensure TTS responds smoothly.

### Step 4: Academic Tutor & IDE Controller (Week 4)
- **Task:** Expand `UniversalController` to handle Cursor/VS Code switching.
- **Task:** Implement `FocusSentry` to monitor active windows and trigger the 3-stage distraction escalation.
- **Verification:** Start Senpai Mode. Open YouTube and verify Sunday automatically minimizes it after warning. Instruct Sunday to run a script in Cursor and verify it executes.

### Step 5: Insomnia Engine & Sub-Agents (Week 5)
- **Task:** Implement the `SetThreadExecutionState` Windows API call to keep the laptop awake.
- **Task:** Develop the nightly background cron job for memory summarization.
- **Task:** Build the `SubAgent` code execution sandbox.
- **Verification:** Close the laptop lid. Verify the system stays alive via Telegram ping. Check logs the next morning to ensure the daily summarization job ran.

### Step 6: Polish & Mobile Dashboard (Week 6)
- **Task:** Finalize the FastAPI server and React/PWA dashboard.
- **Task:** Setup Cloudflare Tunnels (or Tailscale) for secure remote access.
- **Verification:** Open the web app on the phone using cellular data. Send a command and verify the laptop receives and processes it.
