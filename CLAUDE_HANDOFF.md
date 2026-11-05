# Sphero BOLT Web Dashboard – Handoff & UI Decluttering Task

## 1. Project Context & Environment
- **Repository Root**: `/home/csps/REPOS/MySpheroScripts`
- **Environment**: Arch Linux with BlueZ BLE stack, Python 3.14 virtual environment (`sphero-neu/.venv`).
- **Server Startup Script**: Run `./start.sh` from the repository root (or `cd sphero-neu && .venv/bin/python web/server.py --host 0.0.0.0 --port 8080`).
- **Frontend Files**:
  - `index.html`
  - `assets/css/styles.css`
  - `assets/js/app.js`
  - *(Crucial: any modifications to these root files must remain identical to `sphero-neu/web/static/`)*.
- **Hardware Status**: **15 physical Sphero BOLT robots** are powered on and present with the user.

---

## 2. Core Problem: The Site Feels Cluttered
The current 3-column layout (Left: 2D Arena, Center: Fleet Cards & Controls & Dropdowns & Joystick, Right: Napló) is crowded and visually overwhelming, especially when scaling up to 15 robots:
- Displaying 15 large individual robot cards in the center pushes the action buttons, program dropdowns, and joystick far down or off-screen.
- The 2D Arena canvas and the Napló console compete for horizontal screen real estate.
- The interface lacks visual hierarchy, breathing room, and modern responsive ergonomics.

### Goals for Decluttering:
1. **Compact Fleet Overview (15 Robots)**:
   - Replace the bulky robot cards with a sleek, compact badge grid or collapsible bottom/side drawer.
   - Display key status at a glance: robot number/name, compact battery pill (`%` with color-coded dot: Green &ge; 70%, Amber &ge; 30%, Red < 30%), assigned controller badge, and a subtle "Azonosítás / Identify" button.
2. **Streamlined Controls & Dropdowns**:
   - Provide a clean, unified hero control bar (Aim / Célzás, Stop / Leállítás, Rescan / Újrakeresés, Admin).
   - Group shows and minigames into intuitive, modern segmented selectors or dropdown cards without visual noise.
3. **Collapsible / Floating Utility Panels**:
   - Make the Napló (console log) collapsible or accessible via a slide-over drawer / bottom sheet so it doesn't permanently consume 30% of desktop horizontal space.
   - Allow the 2D Arena map and Joystick to have dedicated prominence depending on whether the user is in spectator/host mode or direct control mode.
4. **Preserve Existing Constraints & Features**:
   - Keep bilingual support (Hungarian default, English secondary via the HU/EN toggle).
   - Preserve mobile controller slot assignment:
     - Phone 1 &rarr; Robot 1: Matrix shows **`1`** in **Red** (`#ff3b3b`).
     - Phone 2 &rarr; Robot 2: Matrix shows **`2`** in **Green** (`#2ecc71`).
     - Phone 3 &rarr; Robot 3: Matrix shows **`3`** in **Blue** (`#3498db`).
   - Keep the host laptop auto-map focus toggle in the Admin settings modal.

---

## 3. How to Test with 15 Physical Robots

### Step 1: Start the Server
From the repository root, run:
```bash
./start.sh
```
On boot, `Runner.init_robot_pool()` automatically queries and logs the battery voltage/percentage of all nearby Sphero BOLTs, caching their MAC addresses in `/tmp/sphero_bolts_cache.json` for sub-second program starts.

### Step 2: Verify Robot Fleet Discovery via API
In a separate terminal, inspect all detected robots:
```bash
curl -s http://127.0.0.1:8080/api/robots | python3 -m json.tool
```
To force a live rescan of newly powered robots:
```bash
curl -s -X POST http://127.0.0.1:8080/api/robots/refresh
```

### Step 3: Test Hardware Identification
Trigger visual LED matrix identification on any robot (e.g. Robot 1, Robot 8, or Robot 15):
```bash
curl -s -X POST http://127.0.0.1:8080/api/robots/1/identify
```
The targeted robot's 8x8 LED matrix flashes bright white and its front LED headlight turns on.

### Step 4: Test Multi-Robot Programs
- **Amőba / Tic-tac-toe** (`tictactoe.py`):
  ```bash
  curl -s -X POST http://127.0.0.1:8080/api/start/tictactoe
  ```
  Connects the nearest 9 robots and sets their LED matrix to numbers 1–9 arranged in a 3x3 grid.
- **Szinkrontánc / Dance Show** or **Neumann Formation** (`neu.py`):
  ```bash
  curl -s -X POST http://127.0.0.1:8080/api/start/neu
  ```
  Scrolls the full name "NEUMANN" across all robot displays with illuminated headlights.
- **Stop Any Active Program**:
  ```bash
  curl -s -X POST http://127.0.0.1:8080/api/stop
  ```

### Step 5: Test Mobile Phone Driving & Slot Routing
1. Open `http://localhost:8080` in the laptop browser.
2. Scan the on-screen QR Code using a mobile phone camera.
3. Verify Phone 1 is assigned to Robot 1 (matrix displays "1" in Red) and the virtual joystick drives the robot smoothly.
