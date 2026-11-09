# Sphero BOLT Interactive Presentation & Simulation Suite

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Hardware](https://img.shields.io/badge/Hardware-Sphero%20BOLT%20(up%20to%2015%20Robots)-00A4E4?logo=bluetooth&logoColor=white)](https://sphero.com/)
[![Platforms](https://img.shields.io/badge/Platforms-Windows%20%7C%20macOS%20%7C%20Linux%20%7C%20Raspberry%20Pi-blue)](https://github.com/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A cross-platform web dashboard and control server for **Sphero BOLT** robots, designed for school presentations, robotics open houses, and interactive classroom demonstrations with up to 15 robots.

> 📖 **Looking for the user guide, phone control, shows, and minigames playbook?**  
> Check out the complete **[User & Presentation Guide (USAGE.md)](USAGE.md)**.  
> For technical architecture and hardware protocol details, see **[CLAUDE_HANDOFF.md](CLAUDE_HANDOFF.md)**.

---

## Three Ways to Use the Suite

### 1. Standalone Web Mode (Zero Installation / Browser-Only)
You can run the full web dashboard **without installing Python or running a server**:
- **Live Online (GitHub Pages)**: Open **[https://csps0.github.io/MySpheroScripts/](https://csps0.github.io/MySpheroScripts/)** in any modern browser.
- **Local Standalone File**: Double-click `index.html` in the extracted project folder.
- **Built-in 60 FPS Simulator**: All shows (`Neumann Formation`, `Dance Show`, `Autonomous Roam`), games (`Tic-Tac-Toe`, `Memory Game`, `Whack-a-Mole`, `Hot Potato`, `Rock-Paper-Scissors`), and `Joystick Drive` run directly in the browser on the interactive 2D Arena canvas.
- **Direct Web Bluetooth**: Click **Csatlakozás (Connect)** in the top bar (using Google Chrome, Microsoft Edge, or Bluefy on iOS) to pair and drive a physical Sphero BOLT directly from the browser.

### 2. Download as a Single Zipped Package (No Git Required)
1. Click the green **Code** button at the top of the GitHub page and select **Download ZIP** (or **[click here to download the full ZIP directly](https://github.com/CsPS0/MySpheroScripts/archive/refs/heads/main.zip)**).
2. Extract the `.zip` archive into any folder on your computer (e.g. `C:\MySpheroScripts` or `~/MySpheroScripts`).
3. Open `index.html` directly for **Standalone Web Mode**, or follow Steps 2–4 below to start the **Local Python Fleet Server** (`start.bat` on Windows / `./start.sh` on Linux & macOS).

### 3. Git Clone & Local Fleet Server (Up to 15 Robots + Phone QR Controllers)
Clone the repository with Git (or use GitHub Desktop / VS Code Git login) to run the local FastAPI backend for multi-robot Bluetooth orchestration and mobile QR-code controllers:
```bash
git clone https://github.com/CsPS0/MySpheroScripts.git
cd MySpheroScripts
```

---

### Step 2: Install Python (3.10 or newer)

Make sure Python 3.10+ is installed on your computer:

- **Windows**:
  - Download the official installer from [python.org](https://www.python.org/downloads/).
  - ⚠️ **Important**: On the very first installer screen, check the box: **"Add python.exe to PATH"** before clicking Install.
  - Ensure Bluetooth is switched **ON** in Windows Settings (`Settings > Bluetooth & devices`).
- **macOS**:
  - Install via [Homebrew](https://brew.sh/): `brew install python` (or download from [python.org](https://www.python.org/downloads/)).
  - Ensure Bluetooth permissions are granted for your terminal app (`System Settings > Privacy & Security > Bluetooth`).
- **Linux (Arch / Ubuntu / Debian)**:
  - **Arch Linux**: `sudo pacman -Syu python python-pip bluez bluez-utils`
  - **Ubuntu / Debian**: `sudo apt update && sudo apt install -y python3 python3-venv python3-pip bluez`
  - Enable Bluetooth: `sudo systemctl enable --now bluetooth.service`

---

### Step 3: Install Dependencies

Open a terminal or command prompt inside the project folder:

```bash
cd sphero-neu

# Create a virtual environment (.venv)
python -m venv .venv

# Activate and install dependencies:
# Windows (CMD / PowerShell):
.venv\Scripts\pip install -r requirements.txt

# Linux / macOS:
source .venv/bin/activate
pip install -r requirements.txt

cd ..
```

---

### Step 4: Start the Server

Launch scripts are provided for all operating systems in the repository root:

- **Windows**:
  - Double-click **`start.bat`**, or run in PowerShell:
    ```powershell
    .\start.ps1
    ```
- **Linux & macOS**:
  - Run the startup script:
    ```bash
    ./start.sh
    ```

#### Optional Startup Flags:
You can pass flags directly to any of the start scripts:
- **`--sim`**: Run in simulation mode (ideal for testing without physical Sphero robots).
  ```bash
  ./start.sh --sim        # Linux/macOS
  .\start.ps1 --sim       # Windows PowerShell
  ```
- **`--low-power`**: Enable low-memory and throttled execution for older school laptops or Raspberry Pi.
  ```bash
  ./start.sh --low-power
  ```

---

### Step 5: Open the Dashboard

1. Open your web browser on the host computer:
   **`http://localhost:8080`**
2. For visiting students and mobile controllers:
   - Ensure phones are connected to the same Wi-Fi network (or your laptop's Wi-Fi hotspot).
   - Scan the on-screen QR code with any phone's camera app to open the mobile controller interface.

---

## Automated QA & Test Suite

Run the end-to-end automated verification harness (covering backend physics simulation, all subprocess shows/minigames, Neumann letter orientation, and frontend synchronization):

```bash
.\sphero-neu\.venv\Scripts\python.exe sphero-neu\test_suite.py
```

---

## Documentation Links

- **[USAGE.md](USAGE.md)**: Full guide for the two-column dashboard, Dark & Creamy Light themes, built-in **Útmutató / Guide** tab, 15-robot fleet management, phone driving with directional calibration, NEUMANN formation with compass alignment, Big Dance, minigames, and open house presentation playbook.
- **[CLAUDE_HANDOFF.md](CLAUDE_HANDOFF.md)**: Architecture notes, hardware BLE quirks and workarounds for spherov2 0.12.1, caching specifications, and test reports.
- **Online Demo**: Test the web interface client-side via GitHub Pages at **[https://csps0.github.io/MySpheroScripts/](https://csps0.github.io/MySpheroScripts/)**.
