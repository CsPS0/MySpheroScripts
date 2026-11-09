# Sphero BOLT – User & Presentation Guide (Használati Útmutató)

This document provides a detailed breakdown of the dashboard interface, mobile phone control, shows, minigames, and presentation workflows for **Sphero BOLT** robots.

For setup and installation instructions, see the main [README.md](README.md).

---

## Table of Contents
1. [Dashboard Layout & Navigation](#dashboard-layout--navigation)
2. [Robot Fleet Management (Up to 15 Robots)](#robot-fleet-management-up-to-15-robots)
3. [QR Code & Mobile Controller Auto-Assignment](#qr-code--mobile-controller-auto-assignment)
4. [Mobile Controller View & Dynamic Calibration](#mobile-controller-view--dynamic-calibration)
5. [Device Slots & Inactivity Watchdog (3 Devices, 5 Min Timeout)](#device-slots--inactivity-watchdog-3-devices-5-min-timeout)
6. [Admin Authentication for Mobile Devices](#admin-authentication-for-mobile-devices)
7. [Shows & Choreographies (NEUMANN Formation & Big Dance)](#shows--choreographies-neumann-formation--big-dance)
8. [Interactive Minigames (Tic-Tac-Toe, Memory Game, etc.)](#interactive-minigames-tic-tac-toe-memory-game-etc)
9. [Bilingual Support (Hungarian Default, English Backup)](#bilingual-support-hungarian-default-english-backup)
10. [Standalone Mode (GitHub Pages / Web Bluetooth)](#standalone-mode-github-pages--web-bluetooth)
11. [School Presentation Playbook (Ages 10–14)](#school-presentation-playbook-ages-1014)

---

## Dashboard Layout & Navigation

The interface features an uncluttered two-column responsive layout built for live classroom demonstrations:

### Top Navigation Bar
- **Program Status Pill**: Real-time badge indicating server state (e.g. `Készenlét / Idle` or active program name).
- **Fleet Counters**: Active robot count, low-battery warning count, and connected phones count.
- **Napló (Log) Button**: Toggles the right slide-over log drawer; features an unread event badge counter.
- **HU | EN Toggle**: One-click bilingual switch between Hungarian and English.
- **Hang (Sound) Toggle**: Mutes or enables audio cues.
- **Beállítások (Settings)**: Opens admin options (Eco mode, auto-map focus toggle, calibration reset).
- **Leállítás (Stop)**: High-visibility red emergency stop button, accessible from every view.

### Running Program Strip
Slides down under the top bar while a program is executing, displaying:
- Current running routine name.
- Elapsed runtime counter.
- Immediate **Leállítás (Stop)** button.

### Left Column
- **2D Floor Arena**: Interactive canvas visualizing robot positions, headings, trail vectors, and collisions. Automatically displayed in simulation/offline mode, and intelligently suspended during real hardware execution to conserve Bluetooth bandwidth.
- **Telefon vezérlés (Phone Control Panel)**: Collapsible panel showing the live QR code, 3-step connection guide, connected phones list with active idle timers, and quick disconnect actions.

### Right Column (Tabbed Control Panel & Fleet Grid)
- **Vezetés / Drive Tab**: Robot selector (Robots 1–3), live heading & speed HUD, virtual joystick, and calibration slider.
- **Műsorok / Shows Tab**: Start cards for choreographed routines:
  - **Szinkrontánc (Big Dance)**: Coordinated fleet choreography for up to 15 robots.
  - **NEUMANN iskolai felirat (School Formation)**: 7-robot letter formation with compass alignment.
  - **Önálló séta (Autonomous Roam)**: Obstacle-avoiding wandering mode.
- **Játékok / Games Tab**: Start cards for interactive party games.
- **Robot Flotta (Fleet Grid)**: Compact cards for all discovered robots showing robot number, BLE name, battery status dot, and assigned phone driver badge.

### Slide-Over Log Drawer
A slide-over drawer opening from the right edge. Accessible via the **Napló** button or the `Esc` key, featuring copy-to-clipboard and clear actions.

---

## Robot Fleet Management (Up to 15 Robots)

- **Automatic Fleet Discovery**: On server startup, all available BOLT robots are discovered and ordered nearest-first.
- **Battery Telemetry on Identification**:
  - Batteries are read during the identification sequence to avoid slowing down boot discovery:
    - **Zöld (Green)**: &ge; 70%
    - **Sárga (Amber)**: &ge; 30%
    - **Piros (Red)**: < 30%
    - **Kötőjel (`–`)**: Unknown until identified.
- **Azonosítás (Identify Robot)**:
  - Tapping **Azonosítás** on any robot card illuminates its number on the 8x8 LED matrix, turns on its front headlight for 3 seconds, and updates its battery readout.
- **Flotta frissítése (Rescan)**:
  - Tapping **Újrakeresés (Rescan)** detects any newly turned-on robots without restarting the server.

---

## QR Code & Mobile Controller Auto-Assignment

When students scan the QR code displayed on the screen:

1. **Automatic Slot Assignment**:
   - **Phone 1 &rarr; Robot 1**: Red theme (`#ff3b3b`), matrix displays **`1`**.
   - **Phone 2 &rarr; Robot 2**: Green theme (`#2ecc71`), matrix displays **`2`**.
   - **Phone 3 &rarr; Robot 3**: Blue theme (`#3498db`), matrix displays **`3`**.
2. **Dedicated Mobile Controller View**:
   - The phone loads a minimal interface with its assigned robot banner, virtual joystick, and calibration controls. Host tools (arena, fleet grid, settings, emergency stop) remain hidden.
3. **Laptop Auto-Map Focus**:
   - The laptop display can automatically switch focus to the arena when a phone starts driving. This behavior can be toggled in **Beállítások (Admin Settings)** (`#toggle-auto-map`).

---

## Mobile Controller View & Dynamic Calibration

Because robots can face different directions relative to where each student stands in the room:

- **Per-Robot Calibration Slider**:
  - Located under the joystick on the phone screen.
  - The student stands directly behind their robot and drags the slider (or taps **&plusmn;15°**) until the robot's LED matrix arrow and white headlight point straight away from them.
  - Moving the joystick **UP** will then steer the robot forward from the student's perspective.
- **Session-Based Calibration**:
  - Offsets are maintained by the server for that driving session and reset when a new drive session starts.

---

## Device Slots & Inactivity Watchdog (3 Devices, 5 Min Timeout)

- **3-Controller Concurrency Limit**: Up to 3 simultaneous mobile controllers are allowed. If a 4th visitor connects, a friendly notification asks them to wait until a slot opens.
- **Host Laptop Exclusion**: The host laptop (`localhost` / `127.0.0.1`) does not consume a controller slot.
- **5-Minute Inactivity Watchdog**: After 300 seconds of inactivity, the server automatically frees the slot so the next student can take a turn.
- **One-Click Disconnect**: The host can click the red **Lekapcsolás (Disconnect)** button next to any phone in the Phone Control panel to immediately release its slot.

---

## Admin Authentication for Mobile Devices

Teachers can control the entire system from their smartphone:

1. Tap the **Admin** button in the mobile header.
2. Enter the admin password (default: `admin1234`, configurable via `ADMIN_PASSWORD` environment variable).
3. Authenticated phones gain full dashboard access (tabs, fleet management, emergency stop) without consuming a driving slot.

---

## Shows & Choreographies (NEUMANN Formation & Big Dance)

### 1. Full NEUMANN School Formation (`neu.py`)
- **7-Robot Letter Formation**: Robots 1 through 7 display **`N`**, **`E`**, **`U`**, **`M`**, **`A`**, **`N`**, **`N`** on their LED matrices in school colors.
- **Automatic Compass Alignment**: Robots calibrate magnetometers simultaneously and turn to magnetic north plus the heading slider offset.
- **Live Heading & Letter Rotation Controls**: Adjust the formation heading live or rotate/mirror individual letters.
- **Kézi forgatás (Hand-Turn Lock)**: Disables stabilization and turns on tail lights so robots can be arranged by hand, locking their heading once released.
- **Spare Robot Fallback**: If a robot fails to connect, spare robots from the pool (8, 9, ...) step in automatically.

### 2. Szinkrontánc / Big Dance Show (`big_dance.py`)
- **Fleet Choreography for Up to 15 Robots**:
  - Automatically distributes robots across multiple Bluetooth adapters (up to 10 robots per adapter).
  - **Phase 1: Szivárvány hullám (Rainbow Wave)**: Synchronized color wave and turns.
  - **Phase 2: Roham (Dash Rush)**: Out-and-back dashes with collision reaction flashes.
  - **Phase 3: Karakterek (Character Showcase)**: Animated letters, symbols, and square formations.
  - **Phase 4: Finálé (Rainbow Finale)**.
- **Fleet Filter**: Exclude low-battery robots in the UI (`/api/dance`).

### 3. Önálló Séta / Autonomous Roam (`roam.py`)
- Autonomous obstacle avoidance using collision sensors and front headlights.

---

## Interactive Minigames (Tic-Tac-Toe, Memory Game, etc.)

- **Amőba / Tic-tac-toe (`tictactoe.py`)**: 9 physical robots arranged in a 3x3 grid represent the board. Players shake a robot to place their move (**X** or **O**).
- **Memory Game (Memóriajáték)**: Memory rhythm game with color and sound sequences.
- **Vakondvadászat / Whack-a-mole**: 60-second reflex challenge touching flashing neon green robots.
- **Forró Krumpli / Hot Potato**: Circle passing game before the fuse expires.
- **Kő-Papír-Olló / Rock-Paper-Scissors**: Head-to-head robot duel with animated matrix symbols.

---

## Bilingual Support (Hungarian Default, English Backup)

- **Default Language**: Magyar (Hungarian), written for middle-schoolers (10–14 years old).
- **English Backup**: Toggle anytime with the **HU | EN** button in the top navigation bar.
- Language preference is stored in `localStorage`.

---

## Standalone Mode (GitHub Pages / Web Bluetooth)

If presenting without the Python server:
1. Open **`https://csps0.github.io/MySpheroScripts/`** in Google Chrome on your phone or laptop.
2. Tap **Csatlakozás (Connect)** in the header.
3. Tap **Sphero Keresése és Párosítása (Scan & Pair via Bluetooth)** to connect directly using Web Bluetooth.

---

## School Presentation Playbook (Ages 10–14)

Recommended flow for visiting students during open house events:

1. **Bevezetés & QR-Kód Csatlakozás (Bal oldali panel)**
   - Show the QR code on the screen: *"Olvassátok be a telefonotokkal a QR-kódot, és próbáljátok ki az irányítást!"*
2. **NEUMANN Iskolai Felirat (Műsorok fül)**
   - Start the 7-robot formation. Robots align automatically with their compasses, turn on headlights, and scroll **NEUMANN**.
3. **Szinkrontánc (Műsorok fül)**
   - Run the synchronized fleet dance with rainbow wave, dashes, and finale.
4. **Kézi Botkormány (Vezetés fül)**
   - Connected students drive their assigned robot (**1: Piros, 2: Zöld, 3: Kék**).
   - Guide students to adjust the calibration slider until the arrow points straight forward.
5. **Csapatjátékok (Játékok fül)**
   - **Amőba**: 9 robots form an interactive 3x3 board; shake a robot to claim the spot.
   - **Forró Krumpli**: Passing game before the time runs out.
   - **Vakondvadászat**: Reflex game tapping flashing robots.
   - **Kő-Papír-Olló**: Quick head-to-head battles.
