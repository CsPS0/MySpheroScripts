# Sphero BOLT Interactive Presentation & Simulation Suite

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Hardware](https://img.shields.io/badge/Hardware-Sphero%20BOLT-00A4E4?logo=bluetooth&logoColor=white)](https://sphero.com/)
[![Hosting](https://img.shields.io/badge/Hosting-GitHub%20Pages%20%7C%20Vercel-black?logo=github&logoColor=white)](https://pages.github.com/)
[![OS](https://img.shields.io/badge/OS-Arch%20Linux%20Verified-1793d1?logo=archlinux&logoColor=white)](https://archlinux.org/)
[![Language](https://img.shields.io/badge/Language-Magyar%20(HU)%20%7C%20English-success)](#)
[![Control](https://img.shields.io/badge/Max%20Controllers-3%20Devices%20%7C%205m%20Watchdog-blue)](#)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A complete control, simulation, and presentation platform for **Sphero BOLT** robots, designed for school open houses, robotics presentations, and interactive classroom demonstrations.

Featuring an **interactive monitor introduction view with QR Code connection**, **bilingual support (Hungarian default, English backup)**, a **3-controller device limit with automatic 5-minute inactivity disconnect**, **2D physics floor arena**, **party games**, and an **analog virtual joystick** with zero lag.

---

## Table of Contents
1. [School Monitor Setup (Arch Linux)](#school-monitor-setup-arch-linux)
2. [QR Code & Mobile Control Connection](#qr-code--mobile-control-connection)
3. [Device Slots & Inactivity Management (3 Devices, 5 Min Timeout)](#device-slots--inactivity-management-3-devices-5-min-timeout)
4. [Bilingual Support (Hungarian Default, English Backup)](#bilingual-support-hungarian-default-english-backup)
5. [Running on Arch Linux (Step-by-Step)](#running-on-arch-linux-step-by-step)
6. [Hosting on GitHub Pages (Standalone Mode)](#hosting-on-github-pages-standalone-mode)
7. [School Presentation Playbook (Ages 10–14)](#school-presentation-playbook-ages-1014)

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

## Hosting on GitHub Pages (Standalone Mode)

[![GitHub Pages Deployment](https://img.shields.io/badge/Deploy-GitHub%20Pages-181717?logo=github&logoColor=white)](https://pages.github.com/)

If presenting away from the Arch Linux laptop:
1. Open **`https://csps0.github.io/MySpheroScripts/`** on your smartphone.
2. Tap **Csatlakozás (Connect)** in the header.
3. Tap **Sphero Keresése és Párosítása (Scan & Pair via Bluetooth)** to connect directly over phone Web Bluetooth.

---

## School Presentation Playbook (Ages 10–14)

Recommended flow for visiting students:

1. **Bevezetés & QR-Kód Csatlakozás (Tab: Bemutató)**
   - Mutasd meg a monitoron a QR-kódot: *"Olvassátok be a telefonotokkal a QR-kódot, és próbáljátok ki az irányítást!"*
2. **Szinkrontánc (Tab: Műsorok)**
   - Indítsd el a 3 robot szinkronizált táncát a monitorról. A robotok köröznek, alakzatot váltanak, és szivárványos fénnyel zárnak.
3. **NEU Iskolai Felirat (Tab: Műsorok)**
   - A robotok beállnak egymás mellé, és kirakják az N, E, U betűket a kijelzőjükön.
4. **Kézi Botkormány (Tab: Botkormány)**
   - A csatlakozott 3 diák a telefonján lévő analóg virtuális karral szabadon navigálhatja a robotokat a padlón.
5. **Csapatjátékok (Tab: Játékok)**
   - **Forró Krumpli**: A diákok körben állnak, és gyorsan továbbadják a robotot a kanóc lejárta előtt.
   - **Vakondvadászat**: Gyors reflexjáték a felvillanó zöld robot megérintésével.
   - **Kő-Papír-Olló**: Két robot párbaja 3-2-1 visszaszámlálással.
