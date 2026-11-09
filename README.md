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

## Quick Start Guide

Follow these steps to get the server up and running on your computer.

### Step 1: Get the Code

Choose one of the two options below:

- **Option A: Download ZIP (Simplest)**:
  1. Click the green **Code** button at the top of this GitHub repository page and select **Download ZIP** (or [click here to download](https://github.com/CsPS0/MySpheroScripts/archive/refs/heads/main.zip)).
  2. Extract the downloaded ZIP archive into a folder of your choice (e.g. `C:\MySpheroScripts` or `~/MySpheroScripts`).
- **Option B: Git Clone**:
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

## Documentation Links

- **[USAGE.md](USAGE.md)**: Full guide for the two-column dashboard, 15-robot fleet management, phone driving with directional calibration, NEUMANN formation with compass alignment, Big Dance, minigames, and open house presentation playbook.
- **[CLAUDE_HANDOFF.md](CLAUDE_HANDOFF.md)**: Architecture notes, hardware BLE quirks and workarounds for spherov2 0.12.1, caching specifications, and test reports.
- **Online Demo**: Test the web interface client-side via GitHub Pages at **[https://csps0.github.io/MySpheroScripts/](https://csps0.github.io/MySpheroScripts/)**.
