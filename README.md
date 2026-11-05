# Sphero BOLT Interactive Presentation & Simulation Suite

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Hardware](https://img.shields.io/badge/Hardware-Sphero%20BOLT-00A4E4?logo=bluetooth&logoColor=white)](https://sphero.com/)
[![Hosting](https://img.shields.io/badge/Hosting-GitHub%20Pages%20%7C%20Vercel-black?logo=github&logoColor=white)](https://pages.github.com/)
[![OS](https://img.shields.io/badge/OS-Arch%20Linux%20Verified-1793d1?logo=archlinux&logoColor=white)](https://archlinux.org/)
[![Language](https://img.shields.io/badge/Language-Magyar%20(HU)%20%7C%20English-success)](#)
[![Control](https://img.shields.io/badge/Max%20Controllers-3%20Devices%20%7C%205m%20Watchdog-blue)](#)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A complete control, simulation, and presentation platform for **Sphero BOLT** robots, designed for school open houses, robotics presentations, and interactive classroom demonstrations.

Featuring a **unified single-page dashboard**, **startup robot fleet pool with real-time battery monitoring**, **smart device slot assignment with LED color-coding & number indicators**, **interactive monitor introduction view with QR Code connection**, **bilingual support (Hungarian default, English backup)**, a **3-controller device limit with automatic 5-minute inactivity disconnect**, **2D physics floor arena**, **party games**, and an **analog virtual joystick** with zero lag.

---

## Table of Contents
1. [Unified Single-Page Dashboard Layout](#unified-single-page-dashboard-layout)
2. [Startup Robot Fleet Pool & Battery Monitoring](#startup-robot-fleet-pool--battery-monitoring)
3. [QR Code & Mobile Controller Auto-Assignment (1=Red, 2=Green, 3=Blue)](#qr-code--mobile-controller-auto-assignment-1red-2green-3blue)
4. [Device Slots & Inactivity Management (3 Devices, 5 Min Timeout)](#device-slots--inactivity-management-3-devices-5-min-timeout)
5. [Full "NEUMANN" School Formation](#full-neumann-school-formation)
6. [Bilingual Support (Hungarian Default, English Backup)](#bilingual-support-hungarian-default-english-backup)
7. [Running on Arch Linux (Step-by-Step)](#running-on-arch-linux-step-by-step)
8. [Network & Firewall Configuration](#network--firewall-configuration)
9. [Hosting on GitHub Pages (Standalone Mode)](#hosting-on-github-pages-standalone-mode)
10. [School Presentation Playbook (Ages 10–14)](#school-presentation-playbook-ages-1014)

---

## Unified Single-Page Dashboard Layout

The interface features an all-in-one responsive 3-panel dashboard designed so hosts and visitors never need to hunt through menus or navigate back and forth:

- **Left Panel (2D Floor Arena)**:
  - An interactive, physics-based simulation canvas showing robot positions, headings, trail vectors, and collisions in real time.
  - Automatically visible on desktop monitors and projectors.
- **Center Panel (Controls & Program Dropdowns)**:
  - **Robot Fleet Pool**: Live status cards for every robot showing battery voltage, battery percentage gauge, and assigned controller slot.
  - **Quick Action Bar**: Aiming (Célzás) with rear LED calibration, Emergency Stop (Leállítás), Rescan Fleet (Újrakeresés), and Admin Settings.
  - **Műsorok (Shows Dropdown)**: Instant start for choreographed routines (Szinkrontánc / Dance Show, Önálló Séta / Autonomous Roam, NEUMANN Iskolai Felirat).
  - **Játékok (Minigames Dropdown)**: Party and multiplayer games (Tic-tac-toe / Amőba, Simon Says / Fény-utánzó, Whack-a-mole / Vakondvadászat, Hot Potato / Forró Krumpli, Kő-Papír-Olló / Rock-Paper-Scissors).
  - **Botkormány (Virtual Joystick)**: Zero-latency touch/pointer steering with real-time heading and speed controls.
- **Right Panel (Napló / Live Console)**:
  - Persistent real-time event log streaming telemetry, connection handshakes, battery readouts, and execution status.
  - Includes quick action buttons to copy or clear the log.

---

## Startup Robot Fleet Pool & Battery Monitoring

On server startup, the system automatically discovers, probes, and connects to all nearby Sphero BOLT robots:

- **Real-Time Battery Telemetry**:
  - Automatically queries each robot's battery voltage and calculates battery percentage.
  - Live battery indicators update dynamically in the web UI with color alerts (Green &ge; 70%, Amber &ge; 30%, Red < 30%).
- **MAC Address Fast-Path Caching**:
  - BLE MAC addresses are cached in `/tmp/sphero_bolts_cache.json`.
  - When a user starts a program (like Dance, Roam, or Joystick), connections establish **in under 1 second** without repeating lengthy BLE scan cycles.
- **Robot Identification**:
  - Clicking the **Azonosítás (Identify)** button on any robot card flashes its 8x8 LED matrix bright white and powers the front LED, making it effortless to identify physical robots in a classroom.
- **REST Endpoints**:
  - `GET /api/robots`: Returns fleet metadata, battery levels, connection status, and controller slots.
  - `POST /api/robots/refresh`: Triggers an active BLE rescan to detect newly powered-on robots.
  - `POST /api/robots/{id}/identify`: Triggers the visual identification sequence on the specific robot.

---

## QR Code & Mobile Controller Auto-Assignment (1=Red, 2=Green, 3=Blue)

When students or visitors scan the on-screen QR Code with their smartphone:

1. **Automatic Controller Slot Assignment**:
   - **Phone 1 &rarr; Robot 1**: Matrix displays **`1`** in **Red** (`#ff3b3b`).
   - **Phone 2 &rarr; Robot 2**: Matrix displays **`2`** in **Green** (`#2ecc71`).
   - **Phone 3 &rarr; Robot 3**: Matrix displays **`3`** in **Blue** (`#3498db`).
2. **Mobile View**:
   - The phone's browser automatically activates the **Joystick** driving interface with a colored banner identifying their assigned robot number and color.
3. **Laptop / Projector Auto-Map Switch**:
   - The host laptop screen automatically focuses on the 2D floor arena map when a phone connects so spectators can watch the robots navigate.
   - **Admin Toggle**: The host can enable or disable this auto-switching feature anytime in the **Admin beállítások (Admin Settings)** modal (`#toggle-auto-map`).

---

## Device Slots & Inactivity Management (3 Devices, 5 Min Timeout)

To maintain order and ensure every visiting student gets a turn:

- **3-Controller Limit**:
  - The server accepts up to **3 simultaneous mobile controller connections** (one per robot).
  - The laptop monitor itself (localhost) is recognized as the host display and does not take up a controller slot.
  - If a 4th student tries to connect, a friendly notification appears asking them to wait until a slot opens up.
- **5-Minute Inactivity Watchdog**:
  - If a student walks away without disconnecting, the server detects when 5 minutes (300 seconds) pass without touch or joystick inputs.
  - The server automatically frees up their slot so the next student in line can connect.
- **Host One-Click Disconnect**:
  - The **Csatlakoztatott telefonok** panel lists each active phone, IP address, and idle time.
  - The host can click the red **Lekapcsolás (Disconnect)** button next to any device to release its slot immediately.

---

## Full "NEUMANN" School Formation

The `neu.py` program represents the school's identity:
- Instead of showing just static letters, the program turns the robots into alignment, turns on their front LED headlights, and smoothly scrolls the full school name **"NEUMANN"** across each robot's 8x8 LED matrix display.
- Continuously loops the full name with rich school colors until stopped.

---

## School Monitor Setup (Arch Linux)

When running the presentation on your laptop connected to an external monitor or projector:

1. Start the server on Arch Linux:
   ```bash
   python web/server.py --host 0.0.0.0 --port 8080
   ```
2. Open `http://localhost:8080` in your browser on the laptop and put it in full screen (`F11`).
3. The monitor automatically displays the **Bemutató (Introduction)** view:
   - Welcomes students and visitors in natural Hungarian.
   - Generates a **live QR Code** with the laptop's exact local Wi-Fi / hotspot address (`http://192.168.x.x:8080`).
   - Displays how many phones are currently connected (`0 / 3 telefon`).
   - Allows the teacher / host to disconnect any idle phone with a single click.

---

## QR Code & Mobile Control Connection

Students or parents don't need to install any app:

1. They open the **Camera app** on their smartphone (Android or iPhone).
2. They point the camera at the **QR Code** on the laptop monitor.
3. Tapping the link opens the controller interface in their mobile browser.
4. The phone acts as a pure remote control interface; all Bluetooth commands to the Sphero robots are handled by the Arch Linux laptop setup.

---

## Device Slots & Inactivity Management (3 Devices, 5 Min Timeout)

To maintain order and ensure every visiting student gets a turn:

- **3-Controller Limit**:
  - The Arch server accepts up to **3 simultaneous mobile controller connections**.
  - The laptop monitor itself (localhost) is recognized as the host display and does not take up a controller slot.
  - If a 4th student tries to connect, a friendly notification appears asking them to wait until a slot opens up.
- **5-Minute Inactivity Watchdog**:
  - If a student or parent walks away without disconnecting, the server detects when 5 minutes (300 seconds) have passed without touch or joystick activity.
  - The server automatically frees up their slot so the next student in line can connect.
- **Host One-Click Disconnect**:
  - On the laptop monitor, the **Csatlakoztatott telefonok** panel lists each active phone, its IP address, and its idle time.
  - The host can click the red **Lekapcsolás (Disconnect)** button next to any device to release its slot immediately.

---

## Bilingual Support (Hungarian Default, English Backup)

- **Default Language**: **Magyar (Hungarian)**, tailored specifically for middle schoolers (10–14 years old) with natural, direct phrasing following humanizer editing principles.
- **English Backup**: Click the **HU | EN** button in the top navbar at any time to instantly toggle between Hungarian and English.
- User choice is saved in browser storage (`localStorage`).

---

## Running on Arch Linux (Step-by-Step)

[![Arch Linux](https://img.shields.io/badge/Arch%20Linux-Pacman%20%7C%20BlueZ-1793d1?logo=archlinux&logoColor=white)](https://archlinux.org/)

### 1. Install System Dependencies
```bash
sudo pacman -Syu --needed python python-pip bluez bluez-utils
```

### 2. Enable & Start Bluetooth Service
```bash
sudo systemctl enable --now bluetooth.service
rfkill unblock bluetooth
bluetoothctl power on
```

### 3. Set Up Virtual Environment
```bash
cd ~/MySpheroScripts/sphero-neu
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt fastapi "uvicorn[standard]"
```

### 4. Launch the Server
```bash
python web/server.py --host 0.0.0.0 --port 8080
```

- Open `http://localhost:8080` on the laptop monitor.
- The QR Code generates automatically for mobile connections.

---

## Network & Firewall Configuration

### Arch Linux UFW Firewall
If Arch Linux runs `ufw` (Uncomplicated Firewall), port `8080/tcp` must be open so mobile devices can reach the laptop:
```bash
sudo ufw allow 8080/tcp comment "Sphero Web Server"
sudo ufw reload
```

### Mobile Wi-Fi & Hotspot Connections
- **Same Network**: Ensure your mobile devices and the Arch laptop are connected to the same Wi-Fi network (or connect phones to your laptop's Wi-Fi hotspot).
- **HTTP / "Not Secure" Notice**:
  - Scanning the QR code directs to `http://<laptop-ip>:8080`.
  - Because it is a local network IP without a public domain TLS certificate, some mobile browsers (Chrome / Safari) may display a brief standard notice (*"Not secure"* or *"Your connection is not private"*).
  - Simply tap **Haladó / Advanced &rarr; Tovább / Proceed to site**.
  - All steering commands use lightweight, low-latency WebSockets directly to the local server.

---

## Hosting on GitHub Pages (Standalone Mode)

[![GitHub Pages Deployment](https://img.shields.io/badge/Deploy-GitHub%20Pages-181717?logo=github&logoColor=white)](https://pages.github.com/)

If presenting away from the Arch Linux laptop:
1. Open **`https://csps0.github.io/MySpheroScripts/`** on your smartphone.
2. Tap **Csatlakozás (Connect)** in the header.
3. Tap **Sphero Keresése és Párosítása (Scan & Pair via Bluetooth)** to connect directly over phone Web Bluetooth.

---

## School Presentation Playbook (Ages 10–14)

Recommended flow for visiting students:

1. **Bevezetés & QR-Kód Csatlakozás (Középső panel)**
   - Mutasd meg a monitoron a QR-kódot: *"Olvassátok be a telefonotokkal a QR-kódot, és próbáljátok ki az irányítást!"*
2. **Szinkrontánc (Műsorok menü)**
   - Indítsd el a 3 robot szinkronizált táncát a monitorról. A robotok köröznek, alakzatot váltanak, és szivárványos fénnyel zárnak.
3. **NEUMANN Iskolai Felirat (Műsorok menü)**
   - A robotok beállnak egymás mellé, fényszórókat kapcsolnak, és folyamatosan görgetik a teljes **NEUMANN** nevet a kijelzőjükön.
4. **Kézi Botkormány (Botkormány vezérlés)**
   - A csatlakozott 3 diák telefonján automatikusan megjelenik a botkormány a hozzárendelt sorszámmal és színnel (**1: Piros, 2: Zöld, 3: Kék**).
   - A nagy monitoron az **Aréna térkép** mutatja a robotok valós idejű mozgását és ütközéseit.
5. **Csapatjátékok (Játékok menü)**
   - **Amőba / Tic-tac-toe**: 9 robot interaktív 3x3-as táblát alkot; rázással lehet lépni, az X kezd.
   - **Forró Krumpli**: A diákok körben állnak, és gyorsan továbbadják a robotot a kanóc lejárta és a robbanás előtt.
   - **Vakondvadászat**: Gyors 60 másodperces reflexjáték a felvillanó neon zöld robot megérintésével.
   - **Kő-Papír-Olló**: Két robot látványos párbaja 3-2-1 visszaszámlálással a LED mátrixon.
   - **Simon Says**: Hang- és fényritmusok memorizálása egyre nehezedő szinteken.

