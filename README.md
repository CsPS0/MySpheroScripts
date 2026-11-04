# Sphero BOLT Interactive Presentation & Simulation Suite

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Hardware](https://img.shields.io/badge/Hardware-Sphero%20BOLT-00A4E4?logo=bluetooth&logoColor=white)](https://sphero.com/)
[![Hosting](https://img.shields.io/badge/Hosting-GitHub%20Pages%20%7C%20Vercel-black?logo=github&logoColor=white)](https://pages.github.com/)
[![OS](https://img.shields.io/badge/OS-Arch%20Linux%20Verified-1793d1?logo=archlinux&logoColor=white)](https://archlinux.org/)
[![Control](https://img.shields.io/badge/Joystick-60%20FPS%20Zero--Lag-2ea043)](#)
[![Audio](https://img.shields.io/badge/Audio-Web%20Audio%20API-orange)](#)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A complete control, simulation, and presentation platform for **Sphero BOLT** robots, designed for school presentations, open houses, and robotics demonstrations.

Featuring a **2D physics floor arena**, **Web Audio synthesizer sound effects**, **choreographed dance shows**, **multiplayer party games**, and a **smooth analog virtual joystick** with zero lag.

Runs **standalone in any web browser** (hosted on **GitHub Pages** or **Vercel** with full mobile touch controls) or as a **local Python backend** on **Arch Linux** with Bluetooth connectivity.

---

## Table of Contents
1. [Which Hosting is Better: Vercel vs GitHub Pages?](#which-hosting-is-better-vercel-vs-github-pages)
2. [Hosting on GitHub Pages (60 Seconds)](#hosting-on-github-pages-60-seconds)
3. [Hosting on Vercel (1-Click)](#hosting-on-vercel-1-click)
4. [Running on Arch Linux (Step-by-Step)](#running-on-arch-linux-step-by-step)
5. [Connecting Your Phone as a Remote Control](#connecting-your-phone-as-a-remote-control)
6. [Dynamic Bluetooth Discovery (No Hardcoded IDs)](#dynamic-bluetooth-discovery-no-hardcoded-ids)
7. [School Presentation Playbook (Ages 9–11)](#school-presentation-playbook-ages-911)

---

## Which Hosting is Better: Vercel vs GitHub Pages?

| Feature | GitHub Pages | Vercel |
| :--- | :--- | :--- |
| **Setup Effort** | **Easiest** (Toggle 1 switch in GitHub repo settings) | Requires connecting a free Vercel account |
| **Build & Deploy Time** | 30–60 seconds per push | **Instant** (5–10 seconds) |
| **Custom Domain & SSL** | Automatic free `*.github.io` + HTTPS | Automatic free `*.vercel.app` + Edge CDN |
| **Mobile Phone Speed** | Excellent | **Fastest** (Global edge caching) |
| **Backend Support** | Static / client-side simulation only | Static / client-side simulation (or serverless) |
| **Best For** | **Tomorrow's presentation** (zero accounts needed) | If you already use Vercel and want instant preview URLs |

### Recommendation:
- **GitHub Pages** is the recommended choice for tomorrow because it is already built into your repository. You don't need any new logins, APIs, or configuration. You push to GitHub, turn on Pages, and open the URL on your phone immediately.
- If you already have a [Vercel](https://vercel.com) account, Vercel gives you instant edge CDN loading and short URLs (`sphero.vercel.app`).

---

## Hosting on GitHub Pages (60 Seconds)

[![GitHub Pages Deployment](https://img.shields.io/badge/Deploy-GitHub%20Pages-181717?logo=github&logoColor=white)](https://pages.github.com/)

1. Commit and push your files:
   ```bash
   git add .
   git commit -m "Organize modular UI, virtual joystick, and simulation suite"
   git push origin main
   ```
2. Open your GitHub repository in your web browser:
   - Click **Settings** (top navigation tab).
   - Click **Pages** in the left sidebar menu.
   - Under **Build and deployment** -> **Branch**:
     - Select branch: `main`
     - Select folder: `/(root)`
   - Click **Save**.
3. In under a minute, your website will be live at:
   ```
   https://<your-username>.github.io/<your-repo-name>/
   ```
4. Open the link on your phone or laptop. The standalone simulation engine activates automatically with full audio and joystick steering!

---

## Hosting on Vercel (1-Click)

[![Deploy with Vercel](https://img.shields.io/badge/Deploy-Vercel-000000?logo=vercel&logoColor=white)](https://vercel.com/new)

1. Push your code to GitHub.
2. Go to [vercel.com](https://vercel.com) and log in.
3. Click **Add New...** -> **Project**.
4. Import your `MySpheroScripts` GitHub repository.
5. Keep default settings (`index.html` at root is automatically detected via [`vercel.json`](vercel.json)).
6. Click **Deploy**. Your custom URL (e.g. `sphero-sim.vercel.app`) is live instantly.

---

## Running on Arch Linux (Step-by-Step)

[![Arch Linux](https://img.shields.io/badge/Arch%20Linux-Pacman%20%7C%20BlueZ-1793d1?logo=archlinux&logoColor=white)](https://archlinux.org/)

If you have physical Sphero BOLT robots and want to run the full Python Bluetooth backend on your Arch Linux laptop:

### 1. Install System Dependencies
Open a terminal on Arch Linux and install BlueZ, Bluetooth tools, and Python:
```bash
sudo pacman -Syu --needed python python-pip bluez bluez-utils
```

### 2. Enable & Start Bluetooth Service
Ensure the Linux Bluetooth daemon is running:
```bash
sudo systemctl enable --now bluetooth.service
```
Verify Bluetooth is unblocked:
```bash
rfkill unblock bluetooth
bluetoothctl power on
```

### 3. Set Up Python Virtual Environment
Navigate to the `sphero-neu` project directory:
```bash
cd ~/MySpheroScripts/sphero-neu
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt fastapi "uvicorn[standard]"
```

### 4. Launch the Web Server
Run Uvicorn bound to `0.0.0.0` so other devices (like your phone) can connect:
```bash
python -m uvicorn web.server:app --host 0.0.0.0 --port 8080
```

- Local laptop URL: `http://localhost:8080`
- Simulation toggle: Click the **Simulation Mode** pill in the top header anytime to switch between physical Bluetooth and virtual simulation.

---

## Connecting Your Phone as a Remote Control

### Method A: Local Wi-Fi or Phone Hotspot (Fastest)
1. Ensure your laptop and phone are on the same Wi-Fi network, **or** turn on your phone's **Personal Hotspot** and connect your Arch laptop to it.
2. Check your laptop's IP address:
   ```bash
   hostname -I
   # Example output: 192.168.43.150
   ```
3. On your phone's browser, go to:
   ```
   http://192.168.43.150:8080
   ```

### Method B: Cloudflare Tunnel (Bypasses School Wi-Fi Restrictions)
School Wi-Fi networks often block direct peer-to-peer connections between devices. You can bypass this with a free, zero-config Cloudflare tunnel:
```bash
npx cloudflared tunnel --url http://localhost:8080
```
This prints a public HTTPS address:
```
https://random-words.trycloudflare.com
```
Open that address on your smartphone from anywhere in the room.

---

## Dynamic Bluetooth Discovery (No Hardcoded IDs)

[![Bluetooth LE](https://img.shields.io/badge/Bluetooth-LE%205.0%20Dynamic%20Scan-0082FC?logo=bluetooth&logoColor=white)](#)

Previously, scripts assumed specific robot names (e.g. `SB-3FF5`, `SB-034E`, `SB-61A9`). If robots were swapped or different BOLTs were brought, the programs failed.

**What was changed:**
- **Dynamic BLE Scan**: Scripts call `sphero_ble.discover_bolts(count)` to discover any advertising Sphero BOLTs in range.
- **Random / Auto Selection**: Discovered robots are automatically assigned roles:
  - **Robot 1**: Team Red
  - **Robot 2**: Team Green
  - **Robot 3**: Team Blue
- **Zero Configuration**: Any 3 Sphero BOLTs can be turned on and used immediately without editing names in the code!

---

## School Presentation Playbook (Ages 9–11)

Recommended order of demonstration to maximize excitement:

1. **Synchronized Dance Show (Tab: Shows)**
   - *Hook*: Tell the students: *"Let's see what happens when computer code coordinates multiple robots like dancers!"*
   - Start the dance show: the robots roll in parallel, execute synchronized spins, show glowing solo matrix patterns, and orbit in a circle before a rainbow finale!

2. **Hot Potato (Tab: Party Games)**
   - *Interactive Challenge*: Start the game.
   - The ball lights up green with ticking audio.
   - Tap to pass the ball as the fuse gets faster and turns flashing red.
   - Ends with a loud explosion blast and scream! Students will laugh and cheer.

3. **Whack-a-Mole & Simon Says (Tab: Party Games)**
   - Invite a student volunteer to the front to play **Whack-a-Mole** (tapping the neon green robot) or **Simon Says** (repeating the musical tones).

4. **Manual RC Drive (Tab: Manual Drive)**
   - Hand your phone to a student or steer the robot yourself using the **Virtual Joystick**.
   - Show how dragging the thumbstick controls heading ($0^\circ\text{ to }360^\circ$) and throttle with instant responsiveness.

5. **Floor Tic-Tac-Toe (Tab: Tic-Tac-Toe)**
   - 9 robots arranged in a 3x3 grid. Students play against each other (Red X vs Blue O).
   - Three in a row flashes green with victory audio!
