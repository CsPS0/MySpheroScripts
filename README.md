# Sphero BOLT Interactive Presentation & Simulation Suite

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Hardware](https://img.shields.io/badge/Hardware-Sphero%20BOLT%20(up%20to%2015%20Robots)-00A4E4?logo=bluetooth&logoColor=white)](https://sphero.com/)
[![Platforms](https://img.shields.io/badge/Platforms-Windows%20%7C%20macOS%20%7C%20Linux%20%7C%20Raspberry%20Pi-blue)](https://github.com/)
[![Hosting](https://img.shields.io/badge/Hosting-GitHub%20Pages%20%7C%20Vercel-black?logo=github&logoColor=white)](https://pages.github.com/)
[![Language](https://img.shields.io/badge/Language-Magyar%20(HU)%20%7C%20English-success)](#)
[![Control](https://img.shields.io/badge/Max%20Controllers-3%20Devices%20%7C%205m%20Watchdog-blue)](#)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A complete control, simulation, and presentation platform for **Sphero BOLT** robots, designed for school open houses, robotics presentations, and interactive classroom demonstrations.

Featuring a **decluttered, responsive two-column dashboard**, **support for up to 15 physical Sphero BOLT robots**, **real-time battery monitoring and identification**, **mobile controller auto-assignment via QR Code with LED color-coding**, **dedicated phone driving view with directional calibration**, **admin phone authentication**, **bilingual support (Hungarian default, English backup)**, a **3-controller device limit with automatic 5-minute inactivity watchdog**, **full NEUMANN school formation with magnetic compass alignment**, **fleet choreographies (Big Dance)**, **interactive minigames (Tic-tac-toe, Simon Says, etc.)**, and a **zero-latency virtual joystick**.

---

## Table of Contents
1. [Decluttered Two-Column Dashboard Layout](#decluttered-two-column-dashboard-layout)
2. [Robot Fleet Pool & Battery Monitoring (Up to 15 Robots)](#robot-fleet-pool--battery-monitoring-up-to-15-robots)
3. [QR Code & Mobile Controller Auto-Assignment (1=Red, 2=Green, 3=Blue)](#qr-code--mobile-controller-auto-assignment-1red-2green-3blue)
4. [Mobile Controller View & Dynamic Calibration](#mobile-controller-view--dynamic-calibration)
5. [Device Slots & Inactivity Management (3 Devices, 5 Min Timeout)](#device-slots--inactivity-management-3-devices-5-min-timeout)
6. [Admin Authentication for Mobile Devices](#admin-authentication-for-mobile-devices)
7. [Shows & Choreographies (NEUMANN Formation & Big Dance)](#shows--choreographies-neumann-formation--big-dance)
8. [Interactive Minigames (Tic-Tac-Toe, Simon Says, etc.)](#interactive-minigames-tic-tac-toe-simon-says-etc)
9. [Bilingual Support (Hungarian Default, English Backup)](#bilingual-support-hungarian-default-english-backup)
10. [Running on Windows (Step-by-Step)](#running-on-windows-step-by-step)
11. [Running on macOS (Step-by-Step)](#running-on-macos-step-by-step)
12. [Running on Linux (Arch / Ubuntu / Debian)](#running-on-linux-arch--ubuntu--debian)
13. [Running on Low-Level Hardware & Raspberry Pi](#running-on-low-level-hardware--raspberry-pi)
14. [Network & Firewall Configuration](#network--firewall-configuration)
15. [Hosting on GitHub Pages (Standalone Mode)](#hosting-on-github-pages-standalone-mode)
16. [School Presentation Playbook (Ages 10–14)](#school-presentation-playbook-ages-1014)

---

## Decluttered Two-Column Dashboard Layout

The interface is streamlined into a two-column responsive layout built for clarity during live demonstrations:

- **Top Navigation Bar**:
  - **Program Status Pill**: Real-time badge indicating server state and currently active routine.
  - **Fleet Counters**: Active robot count, low-battery indicator, and connected phone counter.
  - **Napló (Log) Button**: Toggles the slide-over drawer and displays an unread event badge.
  - **HU | EN Toggle**: One-click bilingual language switch.
  - **Hang (Sound) Toggle**: Mute or enable sound effects.
  - **Beállítások (Settings)**: Opens admin modal (Eco mode, auto-map focus, calibration reset).
  - **Leállítás (Stop)**: High-visibility red emergency stop button, accessible from every view.
- **Running Program Strip**:
  - Dynamically slides into view under the top bar whenever a routine runs, showing program name, elapsed time, and a dedicated Stop action.
- **Left Column**:
  - **2D Floor Arena**: Interactive canvas displaying robot headings, trail vectors, and collisions. Automatically displayed in simulation/offline mode, and intelligently suspended during real BLE hardware execution to eliminate Bluetooth bandwidth congestion.
  - **Telefon vezérlés (Phone Control Panel)**: Collapsible panel showing the live QR code, 3-step connection guide, connected phones list with active idle timers, and quick disconnect actions.
- **Right Column (Tabbed Control Panel & Fleet Grid)**:
  - **Vezetés / Drive Tab**: Robot selector (Robots 1–3), live heading & speed HUD, virtual joystick, and calibration slider.
  - **Műsorok / Shows Tab**: Start cards for **Szinkrontánc (Big Dance)**, **NEUMANN iskolai felirat (School Formation)**, and **Önálló séta (Autonomous Roam)**.
  - **Játékok / Games Tab**: Start cards for party games, including **Amőba (Tic-tac-toe)**, **Simon Says**, **Vakondvadászat (Whack-a-mole)**, **Forró Krumpli (Hot Potato)**, and **Kő-Papír-Olló (Rock-Paper-Scissors)**.
  - **Robot Flotta (Fleet Grid)**: Compact badges displaying all discovered robots (up to 15+), colored robot number, BLE name, battery status dot, and assigned phone driver badge.
- **Slide-Over Log Drawer**:
  - Clean slide-over drawer opening from the right edge, allowing inspection of live telemetry, BLE handshakes, and diagnostic logs without cluttering the main presentation screen.

---

## Robot Fleet Pool & Battery Monitoring (Up to 15 Robots)

On server startup, the system automatically scans for all nearby Sphero BOLT robots:

- **Support for Large Fleets (Up to 15 Robots)**:
  - Discovers all available BOLTs in the classroom and numbers them nearest-first.
  - Unique high-contrast color codes assigned for robots 1 through 15.
- **Battery Telemetry on Identification**:
  - Battery voltages are read directly from physical robots during identification and mapped to dynamic status dots:
    - **Green**: &ge; 70%
    - **Amber**: &ge; 30%
    - **Red**: < 30%
    - **Dash (`–`)**: Unknown until identified (preserves BLE scan speed at boot).
- **Cross-Platform Fast-Path Address Caching**:
  - Discovered BLE addresses and names (`BOLT-n` &rarr; `SB-xxxx`) are cached in the system temporary directory (`tempfile.gettempdir()`, e.g. `%TEMP%\sphero_bolts_cache.json` on Windows or `/tmp/sphero_bolts_cache.json` on Linux/macOS).
  - Programs connect directly to targeted robots in seconds without waiting for lengthy discovery scans.
- **Visual Robot Identification**:
  - Clicking **Azonosítás (Identify)** on any robot card illuminates its number on the 8x8 LED matrix, turns on its front headlight for 3 seconds, and updates its battery readout.
- **REST API Endpoints**:
  - `GET /api/robots`: Returns fleet metadata, battery levels, connection status, and assigned slots.
  - `POST /api/robots/refresh`: Triggers an active BLE rescan to find newly powered-on robots.
  - `POST /api/robots/{id}/identify`: Triggers the visual identification sequence on the specific robot.

---

## QR Code & Mobile Controller Auto-Assignment (1=Red, 2=Green, 3=Blue)

Visitors scan the QR code displayed on the laptop or projector screen:

1. **Automatic Controller Slot Assignment**:
   - **Phone 1 &rarr; Robot 1**: Red theme (`#ff3b3b`), matrix shows **`1`**.
   - **Phone 2 &rarr; Robot 2**: Green theme (`#2ecc71`), matrix shows **`2`**.
   - **Phone 3 &rarr; Robot 3**: Blue theme (`#3498db`), matrix shows **`3`**.
2. **Dedicated Mobile Controller Interface**:
   - Phones opening the link receive an uncluttered, distraction-free controller view:
     - Top banner showing assigned robot: *"Te irányítod: N. robot"*.
     - Large responsive analog virtual joystick.
     - Directional calibration slider and live forward arrow heading.
     - Host tools (arena, fleet grid, settings, emergency stop) remain hidden.
3. **Laptop Auto-Map Focus**:
   - When a phone begins driving, the laptop display can automatically focus on the arena map.
   - Hosts can toggle this feature in the **Beállítások (Admin Settings)** modal anytime.

---

## Mobile Controller View & Dynamic Calibration

Because robots may be positioned at different angles relative to where each student stands on the floor, each phone has independent directional calibration:

- **Per-Robot Calibration Slider**:
  - Located directly under the joystick on the mobile interface.
  - Students stand behind their robot and adjust the slider (or tap the **&plusmn;15°** fine-tuning buttons) until the robot's 8x8 matrix arrow and front white headlight point straight away from them.
  - Moving the joystick **UP** will always drive forward from the student's own perspective.
- **Persistent During Drive Session**:
  - Calibration offsets are maintained by the server per-robot for the duration of the driving session and reset automatically when a new drive session begins.

---

## Device Slots & Inactivity Management (3 Devices, 5 Min Timeout)

To ensure fair turns for all visiting students during open house events:

- **3-Controller Concurrency Limit**:
  - Up to 3 simultaneous mobile controllers are accepted (one per active drive robot).
  - The host laptop (`127.0.0.1` / `localhost`) is recognized as the presentation display and does not consume a controller slot.
  - If a 4th visitor scans the QR code, a polite notification asks them to wait until a slot opens.
- **5-Minute Inactivity Watchdog**:
  - If a student walks away without disconnecting, the server detects 300 seconds of inactivity and automatically frees their slot.
- **Host One-Click Disconnect**:
  - The **Telefon vezérlés (Phone Control)** panel lists each active phone, IP address, and idle duration.
  - The host can click the red **Lekapcsolás (Disconnect)** button next to any device to release its slot immediately.

---

## Admin Authentication for Mobile Devices

Teachers and hosts can control the entire presentation from their smartphone without consuming a driving slot:

- **Mobile Admin Login**:
  - Tapping the **Admin** button in the mobile header opens a password prompt.
  - Default password: `admin1234` (configurable via the `ADMIN_PASSWORD` environment variable).
- **Server-Side Enforcement**:
  - All control endpoints (`/api/start/*`, `/api/stop`, `/api/robots/refresh`, `/api/dance`, etc.) are protected. Requests from `localhost` are permitted automatically; external requests must present an authenticated HMAC admin cookie.
  - Authenticated admin phones get full host dashboard access with tabs, fleet controls, and emergency stop.

---

## Shows & Choreographies (NEUMANN Formation & Big Dance)

### 1. Full NEUMANN School Formation (`neu.py`)
- **7-Robot Letter Formation**: Robots 1 through 7 display **`N`**, **`E`**, **`U`**, **`M`**, **`A`**, **`N`**, **`N`** on their 8x8 LED matrices in rich school colors.
- **Automatic Compass Alignment**:
  - Robots calibrate their internal magnetometers simultaneously (spinning in place ~5 seconds) and turn to magnetic north plus heading slider offset.
- **Live Heading & Letter Rotation Controls**:
  - The dashboard includes a live heading slider to adjust the formation angle in real time.
  - Individual letter rotation controls allow turning or mirroring specific letters on the fly.
- **Kézi forgatás (Hand-Turn Lock)**:
  - Temporarily disables stabilization and powers the tail lights so robots can be arranged by hand, locking their orientation when released.
- **Spare Robot Fallback**:
  - If any of robots 1–7 fail to connect, spare robots from the pool (8, 9, ...) automatically take their place.

### 2. Szinkrontánc / Big Dance Show (`big_dance.py`)
- **Fleet Choreography for Up to 15 Robots**:
  - Supports large fleets with automatic multi-adapter routing (up to 10 robots per Bluetooth adapter).
  - **Phase 1: Szivárvány hullám (Rainbow Wave)**: Coordinated color wave with synchronized turns.
  - **Phase 2: Roham (Dash Rush)**: Out-and-back dashes with collision reaction flashes.
  - **Phase 3: Karakterek (Character Showcase)**: Animated letters, symbols, wiggles, and square formations.
  - **Phase 4: Finálé (Rainbow Finale)**.
- **Fleet Filter**: Individual robots can be excluded in the UI (`/api/dance`) if their battery is low.

### 3. Önálló Séta / Autonomous Roam (`roam.py`)
- Autonomous obstacle avoidance using the BOLT's collision detection and front headlights.

---

## Interactive Minigames (Tic-Tac-Toe, Simon Says, etc.)

- **Amőba / Tic-tac-toe (`tictactoe.py`)**:
  - 9 physical robots arranged in a 3x3 grid represent the board.
  - Players shake a robot to place their move (**X** or **O**).
  - Optimized BLE telemetry ensures responsiveness across all 9 robots.
- **Simon Says (Fény-utánzó)**:
  - Memory rhythm game with color and sound sequences on increasing difficulty levels.
- **Vakondvadászat / Whack-a-mole**:
  - Reflex game where players tap the robot that flashes bright neon green within 60 seconds.
- **Forró Krumpli / Hot Potato**:
  - Circle party game where players pass the robot before the fuse expires.
- **Kő-Papír-Olló / Rock-Paper-Scissors**:
  - Duel between two robots with countdown and randomized matrix symbols.

---

## Bilingual Support (Hungarian Default, English Backup)

- **Default Language**: **Magyar (Hungarian)**, tailored specifically for students (10–14 years old) with clear, engaging, and age-appropriate phrasing.
- **English Backup**: Toggle instantly between Hungarian and English with the **HU | EN** button in the top navigation bar.
- Selection is preserved across browser sessions via `localStorage`.

---

## Running on Windows (Step-by-Step)

[![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011%20Supported-0078D6?logo=windows&logoColor=white)](https://microsoft.com/windows)

### 1. Prerequisites
- **Python 3.10+**: Download from [python.org](https://www.python.org/downloads/) or the Microsoft Store. Ensure **"Add Python to PATH"** is checked.
- **Bluetooth**: Enable Bluetooth in `Settings > Bluetooth & devices > Bluetooth`.

### 2. Set Up Virtual Environment (First time)
Open PowerShell or Command Prompt in the repository folder:
```cmd
cd sphero-neu
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
cd ..
```

### 3. Launch the Server
Double-click `start.bat` in the project root, or run in PowerShell:
```powershell
.\start.ps1
```

- **Simulation Mode** (test without physical robots):
  ```powershell
  .\start.ps1 --sim
  ```
- **Low-Power Mode** (for older school laptops):
  ```powershell
  .\start.ps1 --low-power
  ```

Open `http://localhost:8080` in your browser. When Windows Defender Firewall prompts, allow access for Private networks.

---

## Running on macOS (Step-by-Step)

[![macOS](https://img.shields.io/badge/macOS-Intel%20%26%20Apple%20Silicon-000000?logo=apple&logoColor=white)](https://apple.com/macos)

### 1. Prerequisites
- **Python 3.10+**: Install via [Homebrew](https://brew.sh/) (`brew install python`) or [python.org](https://www.python.org/downloads/).
- **Bluetooth Permissions**:
  - Open `System Settings > Privacy & Security > Bluetooth`.
  - Ensure your terminal app (Terminal, iTerm2, or VS Code) is granted Bluetooth access.

### 2. Set Up Virtual Environment (First time)
```bash
cd sphero-neu
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
```

### 3. Launch the Server
```bash
./start.sh
```

- **Simulation Mode**: `./start.sh --sim`
- **Low-Power Mode**: `./start.sh --low-power`

Open `http://localhost:8080` in Safari or Chrome.

---

## Running on Linux (Arch / Ubuntu / Debian)

[![Linux](https://img.shields.io/badge/Linux-Arch%20%7C%20Ubuntu%20%7C%20Debian-FCC624?logo=linux&logoColor=black)](https://kernel.org/)

### 1. Install System Dependencies
- **Arch Linux**:
  ```bash
  sudo pacman -Syu --needed python python-pip bluez bluez-utils
  ```
- **Ubuntu / Debian / Raspberry Pi OS**:
  ```bash
  sudo apt update && sudo apt install -y python3 python3-venv python3-pip bluez
  ```

### 2. Enable Bluetooth Service
```bash
sudo systemctl enable --now bluetooth.service
rfkill unblock bluetooth
bluetoothctl power on
```

### 3. Set Up Virtual Environment & Run
```bash
cd sphero-neu
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
./start.sh
```

- Open `http://localhost:8080` on the laptop monitor.
- The QR Code generates automatically for mobile connections.

---

## Running on Low-Level Hardware & Raspberry Pi

[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-Pi%203%20%7C%204%20%7C%20Zero%202W-C51A4A?logo=raspberrypi&logoColor=white)](https://www.raspberrypi.com/)
[![Low Spec](https://img.shields.io/badge/Optimization-Eco%20Mode%20%7C%20Low%20RAM-brightgreen)](#)

Optimized specifically for school environments running on older laptops (2–4 GB RAM, dual-core Celeron/Atom netbooks, Intel HD Graphics) or single-board computers like **Raspberry Pi 3 / 4 / Zero 2W**:

### 1. Lightweight Server Mode
Start the server with the `--low-power` flag to optimize memory buffers and stream throttling:
```bash
./start.sh --low-power
```
*(Or set the `LOW_SPEC=1` environment variable).*

### 2. Built-in Client Eco Mode (Kímélő mód)
- **Automatic Off-Screen Suspension**: When the 2D floor arena map is hidden or the browser tab is minimized, canvas physics and drawing loops pause immediately to free up GPU and CPU cycles.
- **Eco Mode Switch**: In **Beállítások (Admin Settings)**, enable **"Kímélő mód (alacsony teljesítményű gépekhez)"**:
  - Bypasses expensive canvas blur filters (`shadowBlur`).
  - Caps render frame rate at an efficient 25 FPS instead of uncapped 60/120 FPS.
  - Shortens trail paths to minimize memory consumption.

---

## Network & Firewall Configuration

### Firewall Setup
- **Linux (ufw)**: Open port `8080/tcp`:
  ```bash
  sudo ufw allow 8080/tcp comment "Sphero Web Server"
  sudo ufw reload
  ```
- **Windows**: When prompted by Windows Defender Firewall, check **Private networks** and click Allow.

### Mobile Wi-Fi & Hotspot Connections
- **Same Network**: Ensure your mobile devices and the host laptop are on the same Wi-Fi network (or connect phones to your laptop's Wi-Fi hotspot).
- **Offline Hotspot Detection**: The server features multi-interface IP discovery to accurately identify your Wi-Fi hotspot IP even when operating offline without internet.
- **HTTP Notice**: Because it is a local network IP without a public domain TLS certificate, mobile browsers may show a standard notice (*"Not secure"*). Tap **Haladó / Advanced &rarr; Tovább / Proceed to site**.

---

## Hosting on GitHub Pages (Standalone Mode)

[![GitHub Pages Deployment](https://img.shields.io/badge/Deploy-GitHub%20Pages-181717?logo=github&logoColor=white)](https://pages.github.com/)

If presenting away from the Python server:
1. Open **`https://csps0.github.io/MySpheroScripts/`** in Chrome on your phone or computer.
2. Tap **Csatlakozás (Connect)** in the header.
3. Tap **Sphero Keresése és Párosítása (Scan & Pair via Bluetooth)** to connect directly using Web Bluetooth.

---

## School Presentation Playbook (Ages 10–14)

Recommended flow for visiting students:

1. **Bevezetés & QR-Kód Csatlakozás (Left Panel)**
   - Display the QR code on the monitor: *"Olvassátok be a telefonotokkal a QR-kódot, és próbáljátok ki az irányítást!"*
2. **NEUMANN Iskolai Felirat (Műsorok Tab)**
   - Start the 7-robot formation. Robots align automatically using their compasses, turn on headlights, and display the school name **NEUMANN**.
3. **Szinkrontánc (Műsorok Tab)**
   - Launch the synchronized fleet dance. Robots move in waves, perform synchronized turns, dash with collision reactions, and conclude with a rainbow finale.
4. **Kézi Botkormány (Vezetés Tab)**
   - Connected students drive their assigned robot (**1: Piros, 2: Zöld, 3: Kék**).
   - Students adjust the calibration slider until the arrow points straight ahead, ensuring intuitive steering.
5. **Csapatjátékok (Játékok Tab)**
   - **Amőba (Tic-tac-toe)**: 9 robots form an interactive 3x3 board; shake a robot to make your move.
   - **Forró Krumpli**: Passing game in a circle before the fuse expires.
   - **Vakondvadászat**: 60-second reflex challenge touching flashing green robots.
   - **Kő-Papír-Olló**: Quick head-to-head robot battles.
   - **Simon Says**: Audio-visual memory pattern challenge.
