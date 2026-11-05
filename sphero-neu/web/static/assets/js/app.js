/**
 * Sphero BOLT Interactive Control Suite
 * Standalone browser simulation & real-time WebSocket controller.
 */

// ==========================================
// 1. Audio Synthesizer (Web Audio API)
// ==========================================
let audioCtx = null;
let soundOn = true;

function getAudioContext() {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (audioCtx.state === "suspended") {
    audioCtx.resume();
  }
  return audioCtx;
}

function playTone(freq, type = "sine", duration = 0.2, gainLevel = 0.15) {
  if (!soundOn) return;
  try {
    const ctx = getAudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, ctx.currentTime);
    gain.gain.setValueAtTime(gainLevel, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + duration);
  } catch (e) {}
}

function playPop() {
  if (!soundOn) return;
  try {
    const ctx = getAudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.frequency.setValueAtTime(360, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(80, ctx.currentTime + 0.12);
    gain.gain.setValueAtTime(0.25, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.12);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.12);
  } catch (e) {}
}

function playVictory() {
  if (!soundOn) return;
  const notes = [
    { f: 523.2, t: 0.12, d: 0 },
    { f: 659.2, t: 0.12, d: 0.12 },
    { f: 783.9, t: 0.12, d: 0.24 },
    { f: 1046.5, t: 0.38, d: 0.36 },
  ];
  notes.forEach(n => setTimeout(() => playTone(n.f, "triangle", n.t, 0.2), n.d * 1000));
}

function playBuzzer() {
  if (!soundOn) return;
  playTone(140, "sawtooth", 0.35, 0.25);
}

let lastBoom = 0;
function playBoom() {
  if (!soundOn || Date.now() - lastBoom < 1200) return;
  lastBoom = Date.now();
  try {
    const ctx = getAudioContext();
    const bufSize = ctx.sampleRate * 0.8;
    const buffer = ctx.createBuffer(1, bufSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufSize; i++) data[i] = Math.random() * 2 - 1;
    const noise = ctx.createBufferSource();
    noise.buffer = buffer;
    const filter = ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.setValueAtTime(800, ctx.currentTime);
    filter.frequency.linearRampToValueAtTime(50, ctx.currentTime + 0.8);
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.5, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.8);
    noise.connect(filter);
    filter.connect(gain);
    gain.connect(ctx.destination);
    noise.start();
    noise.stop(ctx.currentTime + 0.8);

    const audio = new Audio("assets/sounds/scream.wav");
    audio.volume = 0.55;
    audio.play().catch(() => {
      const audio2 = new Audio("/api/sound/scream");
      audio2.volume = 0.55;
      audio2.play().catch(() => {
        const audio3 = new Audio("scream.wav");
        audio3.volume = 0.55;
        audio3.play().catch(() => {});
      });
    });
  } catch (e) {}
}

const $ = (id) => document.getElementById(id);

// ==========================================
// Bilingual Translation (HU default, EN backup)
// ==========================================
let currentLang = localStorage.getItem("sphero_lang") || "hu";

const I18N = {
  hu: {
    lang: "HU",
    status_offline: "Offline",
    status_connected: "Csatlakozva",
    status_running: "Fut",
    sound_on: "Hang BE",
    sound_off: "Hang KI",
    stop: "Leállítás",
    connect_btn: "Csatlakozás",

    nav_intro: "Bemutató",
    nav_arena: "Aréna",
    nav_shows: "Műsorok",
    nav_games: "Játékok",
    nav_tictactoe: "Amőba",
    nav_drive: "Botkormány",
    nav_console: "Napló",

    intro_title: "Neumann Sphero Robotika Bemutató",
    intro_subtitle: "Irányítsd a robotokat közvetlenül a saját telefonodról!",
    qr_step_1: "Nyisd meg a kamerát a telefonodon.",
    qr_step_2: "Olvasd be a fenti QR-kódot a csatlakozáshoz.",
    qr_step_3: "Válaszd ki a virtuális botkormányt vagy indíts egy játékot!",
    host_panel_title: "Csatlakoztatott telefonok",
    no_devices_msg: "Nincs aktív telefon csatlakoztatva. Olvasd be a QR-kódot a kezdéshez!",
    host_rules_note: "Egyszerre legfeljebb 3 telefon kapcsolódhat. Ha egy eszköz 5 percig tétlen, a rendszer automatikusan bontja a kapcsolatot, hogy más is kipróbálhassa.",
    quick_launch_title: "Gyors Indítás a Monitorról",

    card_dance_title: "Szinkrontánc",
    badge_show: "Műsor",
    card_dance_desc: "Mindhárom robot egyszerre forog, szlalomozik, alakzatot vált, a végén pedig színes szivárványfénnyel zár.",
    btn_start_dance: "Tánc Indítása",

    card_drive_title: "Virtuális Botkormány",
    badge_drive: "Irányítás",
    card_drive_desc: "Irányítsd a Sphero robotot az analóg karral! Érintőképernyőn és billentyűzeten (W A S D) is azonnal reagál.",
    btn_open_joystick: "Botkormány Megnyitása",

    card_potato_title: "Forró Krumpli",
    badge_game: "Játék",
    card_potato_desc: "Add tovább a robotot körbe a többieknek, mielőtt lejár a kanóc! Egyre gyorsabban pittyeg, a végén robbanással és hanggal!",
    btn_play_potato: "Játék Indítása",

    card_ttt_title: "9 Robotos Amőba",
    card_ttt_desc: "9 Sphero a padlón 3x3-as elrendezésben. Koppints a mezőre a telefonon, és a robot azonnal felveszi a színedet!",
    btn_play_ttt: "Amőba Indítása",

    arena_title: "Élő Robot Aréna",
    arena_subtitle: "2D padlónézet. Kattints vagy koppints a robotra a megrázás szimulálásához!",
    arena_trails: "Nyomvonal",
    arena_recenter: "Középre",
    arena_shake: "Robotok Rázása",
    arena_hint: "Méretarány: 1 négyzet = 20 cm. Valós fizika és 8x8-as LED mátrix kijelző.",

    shows_title: "Koreográfia és Bemutatók",
    shows_subtitle: "Előre beprogramozott látványos robotmozgások és iskolai felirat.",
    card_neu_title: "NEU Iskolai Felirat",
    badge_matrix: "Mátrix",
    card_neu_desc: "A robotok felállnak a megfelelő pozícióba, és kirakják az N, E, U betűket a kijelzőjükön.",
    btn_show_neu: "NEU Megjelenítése",
    card_roam_title: "Önálló Bolyongás",
    badge_wander: "Mozgás",
    card_roam_desc: "Mindhárom robot szabadon pásztázza a padlót a saját 25 cm-es zónájában az akadályokat kikerülve.",
    btn_start_roam: "Bolyongás Indítása",
    neu_editor_title: "NEU Betűk Forgatása",
    neu_editor_desc: "A beállítások azonnal megjelennek a robotokon. 90°-os forgatás vagy tükrözés.",
    target_heading: "Célirány:",

    games_title: "Interaktív Csapatjátékok",
    games_subtitle: "Gyors, pörgős játékok iskolásoknak és látogatóknak.",
    card_mole_title: "Vakondvadászat",
    badge_reflex: "Reflex",
    card_mole_desc: "Egy robot felvillan neon zölden: érintsd meg minél gyorsabban, mielőtt eltűnik! 60 másodperces reflexjáték pontszámlálóval.",
    btn_play_mole: "Vakondvadászat Indítása",
    card_simon_title: "Simon Mondja",
    badge_memory: "Memória",
    card_simon_desc: "A robotok hangokkal és fényekkel mutatják a mintát. Ismételd meg a sorrendet! Minden szint egy lépéssel hosszabb.",
    btn_play_simon: "Simon Mondja Indítása",
    card_rps_title: "Kő-Papír-Olló",
    badge_duel: "Párbaj",
    card_rps_desc: "Két robot (Piros vs Kék). 3-2-1 visszaszámlálás, majd mindkét robot mutatja a választását. 2 nyert menetig tart.",
    btn_play_rps: "Kő-Papír-Olló Indítása",

    ttt_title: "9 Robotos Padló Amőba",
    ttt_subtitle: "9 robot a padlón 3x3-as rácsban. Koppints a mezőkre a lépéshez!",
    ttt_same_layout: "Újra (Ugyanitt)",
    ttt_renumber: "Újraszámozás",
    ttt_start: "Játék Kezdése",
    ttt_footer: "Három egymás mellett világító zöld fénnyel és győzelmi dallammal jelzi a nyertest!",

    drive_title: "Kézi Botkormány (Virtuális Joystick)",
    drive_subtitle: "Finom analóg irányítás. Érintsd meg és húzd a kart bármelyik irányba!",
    hud_heading: "Irány",
    hud_throttle: "Sebesség",
    hud_mode: "Üzemmód",
    hud_mode_val: "Sima RC",
    steer_robot: "Irányított robot:",
    drive_controls_hint: "Koppints és húzd a botkormányt az ujjaddal a telefonodon, vagy az egérrel. Számítógépen a W A S D és a nyilak is használhatók!",

    console_title: "Eseménynapló és Telemetria",
    console_subtitle: "Rendszerüzenetek, játékmenet és kapcsolatok naplózása.",
    btn_clear: "Törlés",

    disconnect_btn: "Lekapcsolás",
    active_now: "épp most aktív",
    idle_secs: "mp-e tétlen",
    idle_mins: "perce tétlen",

    timeout_modal_title: "Inaktivitás miatt bontva",
    timeout_modal_desc: "5 perc tétlenség után a kapcsolat bontásra került, hogy a többi várakozó diák is kipróbálhassa az irányítást.",
    btn_reconnect: "Újracsatlakozás",

    max_modal_title: "Tele a pálya (3/3)",
    max_modal_desc: "Jelenleg mind a 3 irányítói hely foglalt. Kérlek várj pár percet, amíg egy hely felszabadul!",
    btn_understood: "Értem",

    ble_modal_title: "Bluetooth Beállítás & Előkészület",
    ble_step_1_title: "Kapcsold be a Bluetooth-t",
    ble_step_1_desc: "Húzd le az értesítési sávot a telefonodon, és ellenőrizd, hogy a Bluetooth be van-e kapcsolva.",
    ble_step_2_title: "Ébreszd fel a Sphero BOLT-ot",
    ble_step_2_desc: "Rázd meg határozottan a robotot, amíg a LED kijelzőjén fel nem villan a neve (pl. SB-3FF5).",
    ble_step_3_title: "Párosítás és Csatlakozás",
    ble_step_3_desc: "Csatlakozz közvetlenül a böngészőből, vagy a tantermi Arch Linux géphez.",
    btn_pair_ble: "Sphero Keresése és Párosítása",
    or_connect_server: "— VAGY CSATLAKOZÁS ARCH LINUX GÉPHEZ —",
    btn_connect_server: "Szerver Csatlakozás"
  },
  en: {
    lang: "EN",
    status_offline: "Offline",
    status_connected: "Connected",
    status_running: "Running",
    sound_on: "Sound ON",
    sound_off: "Sound OFF",
    stop: "Stop",
    connect_btn: "Connect",

    nav_intro: "Introduction",
    nav_arena: "Arena",
    nav_shows: "Shows",
    nav_games: "Party Games",
    nav_tictactoe: "Tic-Tac-Toe",
    nav_drive: "Manual Drive",
    nav_console: "Activity Log",

    intro_title: "Sphero Robotics Presentation",
    intro_subtitle: "Control the robots directly from your own phone!",
    qr_step_1: "Open the camera app on your smartphone.",
    qr_step_2: "Scan the QR code above to connect.",
    qr_step_3: "Pick the virtual joystick or start an interactive game!",
    host_panel_title: "Connected Controller Phones",
    no_devices_msg: "No active phones connected. Scan the QR code to start!",
    host_rules_note: "Up to 3 phones can connect at once. If a phone is inactive for 5 minutes, the system frees up the slot for others.",
    quick_launch_title: "Quick Launch from Monitor",

    card_dance_title: "Synchronized Dance",
    badge_show: "Show",
    card_dance_desc: "All 3 robots execute synchronized 360° spins, side-to-side shuffles, and a colorful rainbow finale.",
    btn_start_dance: "Start Dance",

    card_drive_title: "Joystick Remote Drive",
    badge_drive: "Drive",
    card_drive_desc: "Drive your Sphero robot with the responsive analog virtual joystick. Supports touch and W A S D.",
    btn_open_joystick: "Open Joystick",

    card_potato_title: "Hot Potato",
    badge_game: "Game",
    card_potato_desc: "Pass the robot around before the fuse expires! Accelerates ticking, ends with an explosion sound!",
    btn_play_potato: "Play Potato",

    card_ttt_title: "9-Ball Tic-Tac-Toe",
    card_ttt_desc: "9 Sphero robots arranged in a 3x3 grid on the floor. Tap squares on your phone to take turns!",
    btn_play_ttt: "Start Tic-Tac-Toe",

    arena_title: "Live Robot Arena",
    arena_subtitle: "Interactive 2D floor view. Click or tap any robot on the floor to simulate shaking it!",
    arena_trails: "Trails",
    arena_recenter: "Recenter",
    arena_shake: "Shake Bots",
    arena_hint: "Floor scale: 1 grid square = 20 cm. Smooth physics and live 8x8 LED matrix display.",

    shows_title: "Choreography & Shows",
    shows_subtitle: "Pre-programmed routines and school formation displays.",
    card_neu_title: "NEU School Formation",
    badge_matrix: "Matrix",
    card_neu_desc: "The robots roll into formation, align to heading, and show glowing letters N, E, U on their matrices.",
    btn_show_neu: "Show NEU",
    card_roam_title: "Autonomous Roam",
    badge_wander: "Wander",
    card_roam_desc: "All 3 robots wander smoothly within their 25 cm zones, avoiding collisions, then return home.",
    btn_start_roam: "Start Roam",
    neu_editor_title: "NEU Matrix Letter Orientation",
    neu_editor_desc: "Changes update live on the robots. Adjust rotation (90° clockwise/counter-clockwise) or mirror flip.",
    target_heading: "Target Heading:",

    games_title: "Interactive Party Games",
    games_subtitle: "High-energy games designed for student engagement and classroom participation.",
    card_mole_title: "Whack-a-Mole",
    badge_reflex: "Reflexes",
    card_mole_desc: "A random ball lights up neon green with a pop sound: tap it before it hides! 60s round with score.",
    btn_play_mole: "Play Whack-a-Mole",
    card_simon_title: "Simon Says",
    badge_memory: "Memory",
    card_simon_desc: "Balls light up with distinct musical notes (C, E, G, High C). Repeat the sequence back by tapping!",
    btn_play_simon: "Play Simon Says",
    card_rps_title: "Rock-Paper-Scissors",
    badge_duel: "2-Player",
    card_rps_desc: "2 robots (Player 1 Red vs Player 2 Blue). Countdown 3-2-1, then reveal gestures. Best of 3 match!",
    btn_play_rps: "Play RPS",

    ttt_title: "9-Ball Floor Tic-Tac-Toe",
    ttt_subtitle: "9 robots arranged in a 3x3 grid on the floor. Tap squares to take turns.",
    ttt_same_layout: "Same Layout",
    ttt_renumber: "Renumber",
    ttt_start: "Start Game",
    ttt_footer: "Three in a row turns the winning robots bright green with victory fanfare!",

    drive_title: "Manual RC Drive (Virtual Joystick)",
    drive_subtitle: "Touch and drag the thumbstick in any direction. Zero lag, fluid return-to-center physics.",
    hud_heading: "Heading",
    hud_throttle: "Throttle",
    hud_mode: "Mode",
    hud_mode_val: "Smooth RC",
    steer_robot: "Steer Robot:",
    drive_controls_hint: "Drag the thumbstick with your finger on a mobile phone, or with your mouse. Keyboard: W A S D or arrows!",

    console_title: "Activity Console & Telemetry",
    console_subtitle: "Live system telemetry, connection events, and game diagnostics.",
    btn_clear: "Clear",

    disconnect_btn: "Disconnect",
    active_now: "active now",
    idle_secs: "s idle",
    idle_mins: "m idle",

    timeout_modal_title: "Disconnected Due to Inactivity",
    timeout_modal_desc: "After 5 minutes of no activity, your connection was closed so other students can have a turn.",
    btn_reconnect: "Reconnect",

    max_modal_title: "All Slots Full (3/3)",
    max_modal_desc: "All 3 controller slots are currently in use. Please wait a few minutes for a slot to open up!",
    btn_understood: "Understood",

    ble_modal_title: "Bluetooth Setup & Preparation",
    ble_step_1_title: "Turn On Bluetooth on your Phone",
    ble_step_1_desc: "Swipe down for Quick Settings (or open Settings) and make sure Bluetooth is toggled ON.",
    ble_step_2_title: "Wake Your Sphero BOLT",
    ble_step_2_desc: "Give your Sphero BOLT a quick shake. Its 8x8 LED matrix will light up with its ID.",
    ble_step_3_title: "Pair & Connect",
    ble_step_3_desc: "Connect directly from your smartphone browser, or connect to your Arch Linux laptop server.",
    btn_pair_ble: "Scan & Pair Sphero via Bluetooth",
    or_connect_server: "— OR CONNECT TO ARCH LINUX LAPTOP —",
    btn_connect_server: "Connect Server"
  }
};

function t(key) {
  if (I18N[currentLang] && I18N[currentLang][key]) return I18N[currentLang][key];
  if (I18N.en && I18N.en[key]) return I18N.en[key];
  return key;
}

function updateSoundButton() {
  const btn = $("sound-toggle");
  if (!btn) return;
  const icon = soundOn
    ? '<svg class="icon" viewBox="0 0 24 24"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>'
    : '<svg class="icon" viewBox="0 0 24 24"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>';
  btn.innerHTML = `${icon} <span id="sound-label">${soundOn ? t("sound_on") : t("sound_off")}</span>`;
}

function setLanguage(lang) {
  currentLang = lang;
  localStorage.setItem("sphero_lang", lang);
  document.documentElement.lang = lang;
  if ($("lang-label")) $("lang-label").textContent = lang.toUpperCase();

  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (key) el.textContent = t(key);
  });

  updateSoundButton();
  renderStatus();
  if (connectedClients.length > 0) renderClients(connectedClients);
}

function toggleLanguage() {
  setLanguage(currentLang === "hu" ? "en" : "hu");
}

if ($("lang-toggle")) $("lang-toggle").onclick = toggleLanguage;
if ($("sound-toggle")) $("sound-toggle").onclick = () => {
  soundOn = !soundOn;
  updateSoundButton();
};


// ==========================================
// 2. 8x8 LED Matrix Font Engine
// ==========================================
const GLYPHS = {
  "1": ["...XX...", "..XXX...", ".XXXX...", "...XX...", "...XX...", "...XX...", "...XX...", ".XXXXXX."],
  "2": ["..XXXX..", ".XX..XX.", ".....XX.", "....XX..", "...XX...", "..XX....", ".XX.....", ".XXXXXX."],
  "3": ["..XXXX..", ".XX..XX.", ".....XX.", "...XXX..", ".....XX.", ".....XX.", ".XX..XX.", "..XXXX.."],
  "4": ["....XX..", "...XXX..", "..XXXX..", ".XX.XX..", "XX..XX..", "XXXXXXX.", "....XX..", "....XX.."],
  "5": [".XXXXXX.", ".XX.....", ".XX.....", ".XXXXX..", ".....XX.", ".....XX.", ".XX..XX.", "..XXXX.."],
  "6": ["..XXXX..", ".XX.....", ".XXXXX..", ".XX..XX.", ".XX..XX.", "..XXXX..", "........", ".XXXXXX."],
  "7": [".XXXXXX.", ".....XX.", "....XX..", "....XX..", "...XX...", "...XX...", "..XX....", "..XX...."],
  "8": ["..XXXX..", ".XX..XX.", ".XX..XX.", "..XXXX..", ".XX..XX.", ".XX..XX.", ".XX..XX.", "..XXXX.."],
  "9": ["..XXXX..", ".XX..XX.", ".XX..XX.", "..XXXXX.", ".....XX.", "..XXXX..", "........", ".XXXXXX."],
  "X": ["XX....XX", "XXX..XXX", ".XXXXXX.", "..XXXX..", "..XXXX..", ".XXXXXX.", "XXX..XXX", "XX....XX"],
  "O": ["..XXXX..", ".XXXXXX.", "XXX..XXX", "XX....XX", "XX....XX", "XXX..XXX", ".XXXXXX.", "..XXXX.."],
  "?": ["..XXXX..", ".XX..XX.", ".....XX.", "....XX..", "...XX...", "...XX...", "........", "...XX..."],
  "N": ["XX....XX", "XXX...XX", "XXXX..XX", "XX.XX.XX", "XX..XXXX", "XX...XXX", "XX....XX", "XX....XX"],
  "E": ["XXXXXXXX", "XXXXXXXX", "XX......", "XXXXXX..", "XXXXXX..", "XX......", "XXXXXXXX", "XXXXXXXX"],
  "U": ["XX....XX", "XX....XX", "XX....XX", "XX....XX", "XX....XX", "XX....XX", "XXXXXXXX", ".XXXXXX."],
  "Arrow": ["...XX...", "..XXXX..", ".XXXXXX.", "XXXXXXXX", "...XX...", "...XX...", "...XX...", "...XX..."],
  "Rock": ["..XXXX..", ".XXXXXX.", "XXXXXXXX", "XXXXXXXX", "XXXXXXXX", "XXXXXXXX", ".XXXXXX.", "..XXXX.."],
  "Paper": ["XXXXXX..", "X....XX.", "X.....XX", "X.XXX..X", "X......X", "X.XXXX.X", "X......X", "XXXXXXXX"],
  "Scissors": ["X.....X.", ".X...X..", "..X.X...", "...X....", "..X.X...", "XXX.XXX.", "X.X.X.X.", "XXX.XXX."],
  "Boom": ["X..XX..X", ".XXXXXX.", "XXXXXXXX", "XXXXXXXX", "XXXXXXXX", "XXXXXXXX", ".XXXXXX.", "X..XX..X"],
  "Check": [".......X", "......XX", ".....XX.", "X...XX..", "XX.XX...", ".XXX....", "..X.....", "........"],
};

function makeMatrix(glyphKey, colorHex = "#ffffff", rotation = 0, mirror = false) {
  let rows = GLYPHS[glyphKey] || Array(8).fill("........");
  let grid = rows.map(r => r.split(""));
  if (mirror) {
    grid = grid.map(r => r.slice().reverse());
  }
  const turns = Math.floor(((rotation % 360) + 360) / 90) % 4;
  for (let t = 0; t < turns; t++) {
    const next = Array.from({ length: 8 }, () => Array(8).fill("."));
    for (let r = 0; r < 8; r++) {
      for (let c = 0; c < 8; c++) {
        next[c][7 - r] = grid[r][c];
      }
    }
    grid = next;
  }
  return grid.map(r => r.map(ch => ch === "X" ? colorHex : "#000000"));
}

function makeSolidMatrix(colorHex) {
  return Array.from({ length: 8 }, () => Array(8).fill(colorHex || "#000000"));
}

// ==========================================
// 3. Tab Navigation / View Switching
// ==========================================
let activeTab = "intro";
function switchTab(tabId) {
  activeTab = tabId;
  document.querySelectorAll(".nav-tab").forEach(tab => {
    tab.classList.toggle("active", tab.dataset.tab === tabId);
  });
  document.querySelectorAll(".view-page").forEach(page => {
    page.classList.toggle("active", page.id === `view-${tabId}`);
  });
}
document.querySelectorAll(".nav-tab").forEach(btn => {
  btn.onclick = () => switchTab(btn.dataset.tab);
});

// ==========================================
// 4. Activity Output Log
// ==========================================
function addLine(line) {
  const log = $("log");
  if (!log) return;
  const atBottom = log.scrollHeight - log.scrollTop - log.clientHeight < 40;
  const div = document.createElement("div");
  div.className = "log-line";
  div.textContent = line;
  if (line.startsWith("===")) div.className += " sys";
  else if (/error|failed|traceback|exception/i.test(line)) div.className += " err";
  else if (/wins|score|victory/i.test(line)) div.className += " win";
  log.appendChild(div);
  while (log.childNodes.length > 1000) log.removeChild(log.firstChild);
  if (atBottom) log.scrollTop = log.scrollHeight;
}
if ($("clear-log")) $("clear-log").onclick = () => { if ($("log")) $("log").innerHTML = ""; };

// ==========================================
// 5. Global State & Programs
// ==========================================
let programs = [];
let state = { running: null, started: null, last_exit: null };
let ws = null, online = false, clientMode = false;

const DEFAULT_PROGRAMS = [
  { id: "dance", title: "Dance Show", description: "Synchronized choreography: spins, circles, shuffles, individual solos, orbital circle, and rainbow finale.", moves: true, kind: "show" },
  { id: "neu", title: "NEU Formation", description: "Robots roll into formation, align to heading, and display glowing N, E, U on matrices.", moves: true, kind: "show" },
  { id: "roam", title: "Autonomous Roam", description: "All 3 robots explore within their floor zone, smoothly turning and avoiding collisions.", moves: true, kind: "show" },
  { id: "drive", title: "Joystick Drive", description: "Remote control driving with the virtual joystick! Smooth steering, speed throttle, and zero lag.", moves: true, kind: "drive" },
  { id: "potato", title: "Hot Potato", description: "Pass the potato before the fuse burns down! Ticking accelerates until a loud boom and scream explosion!", moves: false, kind: "game" },
  { id: "mole", title: "Whack-a-Mole", description: "A random ball flashes neon green: tap it fast before it disappears! 60s reflex round with score.", moves: false, kind: "game" },
  { id: "simon", title: "Simon Says", description: "Watch the pattern of glowing colors and musical tones, then repeat it back! Level progression.", moves: false, kind: "game" },
  { id: "rps", title: "Rock-Paper-Scissors", description: "Red vs Blue showdown! 3-2-1 countdown, reveals gestures on 8x8 matrix, first to 2 wins.", moves: false, kind: "game" },
  { id: "tictactoe", title: "Tic-Tac-Toe", description: "9 robots arranged in a 3x3 floor grid with live numbering, alternating X and O, and winning line.", moves: false, kind: "game" },
];

let connectedTarget = null;
let bleDevice = null;
let bleApiChar = null;
let bleSeq = 0;

function renderStatus() {
  const pill = $("status"), text = $("status-text");
  if (!pill || !text) return;
  const isConn = online && (connectedTarget || (ws && ws.readyState === WebSocket.OPEN));
  pill.className = "pill" + (!isConn ? " offline" : state.running ? " running" : " online");
  if (!isConn) {
    text.textContent = t("status_offline");
  } else if (state.running) {
    const p = programs.find((x) => x.id === state.running) || DEFAULT_PROGRAMS.find((x) => x.id === state.running);
    const secs = Math.round(Date.now() / 1000 - state.started);
    const title = p ? p.title : state.running;
    text.textContent = `${t("status_running")}: ${title} (${secs} ${currentLang === "hu" ? "mp" : "s"})`;
  } else {
    text.textContent = connectedTarget ? `${t("status_connected")}: ${connectedTarget}` : t("status_connected");
  }
  if ($("global-stop")) $("global-stop").disabled = !state.running;
}

// ==========================================
// 6. Virtual Joystick (Smooth Zero-Lag RC)
// ==========================================
let joystickHeading = 0;
let joystickSpeed = 0;
let activeBotIndex = 1; // 1 = BOLT 1 (Red), 2 = BOLT 2 (Green), 3 = BOLT 3 (Blue)
let joystickDragging = false;
let joystickAnimId = null;
let lastJoystickSend = 0;

const joyBase = $("joy-base");
const joyKnob = $("joy-knob");

function setKnobPosition(x, y) {
  if (!joyKnob) return;
  joyKnob.style.transform = `translate(${x}px, ${y}px)`;
}

function updateJoystickHUD(headingDeg, speedPercent) {
  if ($("hud-heading")) {
    const cardinals = ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"];
    const card = cardinals[Math.round(headingDeg / 45) % 8];
    $("hud-heading").textContent = `${Math.round(headingDeg)}° ${card}`;
  }
  if ($("hud-speed")) {
    $("hud-speed").textContent = `${Math.round(speedPercent)}%`;
  }
}

function handleJoystickMove(clientX, clientY) {
  if (!joyBase) return;
  const rect = joyBase.getBoundingClientRect();
  const centerX = rect.left + rect.width / 2;
  const centerY = rect.top + rect.height / 2;

  const dx = clientX - centerX;
  const dy = clientY - centerY;
  const dist = Math.hypot(dx, dy);
  const maxRadius = 65; // px

  const clampedDist = Math.min(dist, maxRadius);
  const angleRad = Math.atan2(dx, -dy); // 0 at top, clockwise
  let heading = (angleRad * 180 / Math.PI + 360) % 360;

  const knobX = (dx / (dist || 1)) * clampedDist;
  const knobY = (dy / (dist || 1)) * clampedDist;

  setKnobPosition(knobX, knobY);

  // Speed: deadzone of 8px
  const speed = dist < 8 ? 0 : (clampedDist / maxRadius) * 100;
  joystickHeading = heading;
  joystickSpeed = speed;

  updateJoystickHUD(heading, speed);
  dispatchDrive(heading, speed);
}

function snapKnobToCenter() {
  joystickSpeed = 0;
  updateJoystickHUD(joystickHeading, 0);
  dispatchDrive(joystickHeading, 0);

  if (joystickAnimId) cancelAnimationFrame(joystickAnimId);
  let startX = 0, startY = 0;
  if (joyKnob) {
    const style = window.getComputedStyle(joyKnob);
    const matrix = new DOMMatrixReadOnly(style.transform);
    startX = matrix.m41;
    startY = matrix.m42;
  }

  let startTime = null;
  function animateSnap(time) {
    if (!startTime) startTime = time;
    const progress = Math.min(1, (time - startTime) / 120);
    const ease = 1 - Math.pow(1 - progress, 3);
    const currX = startX * (1 - ease);
    const currY = startY * (1 - ease);
    setKnobPosition(currX, currY);
    if (progress < 1) {
      joystickAnimId = requestAnimationFrame(animateSnap);
    } else {
      setKnobPosition(0, 0);
    }
  }
  joystickAnimId = requestAnimationFrame(animateSnap);
}

function dispatchDrive(heading, speedPercent) {
  // 1. Simulation update
  if (clientRobots && clientRobots.length > 0) {
    const targetBot = clientRobots[activeBotIndex - 1] || clientRobots[0];
    if (targetBot) {
      targetBot.heading = heading;
      targetBot.speed = (speedPercent / 100) * 50; // cm/s
      if (speedPercent > 5) {
        targetBot.matrix = makeMatrix("Arrow", targetBot.baseColor);
      }
    }
  }

  // 2. Throttled dispatch (20 Hz) or immediate stop
  const now = Date.now();
  if (now - lastJoystickSend > 50 || speedPercent === 0) {
    lastJoystickSend = now;
    if (bleApiChar) {
      bleDrive(speedPercent, heading);
    } else if (ws && ws.readyState === WebSocket.OPEN) {
      const spheroSpeed = (speedPercent / 100) * 255;
      ws.send(JSON.stringify({
        type: "joystick",
        heading: Math.round(heading),
        speed: Math.round(spheroSpeed),
        robot: activeBotIndex,
      }));
    }
  }
}

if (joyBase && joyKnob) {
  joyBase.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    joystickDragging = true;
    joyBase.setPointerCapture(e.pointerId);
    handleJoystickMove(e.clientX, e.clientY);
  });
  joyBase.addEventListener("pointermove", (e) => {
    if (joystickDragging) {
      e.preventDefault();
      handleJoystickMove(e.clientX, e.clientY);
    }
  });
  const pointerEnd = (e) => {
    if (joystickDragging) {
      joystickDragging = false;
      snapKnobToCenter();
    }
  };
  joyBase.addEventListener("pointerup", pointerEnd);
  joyBase.addEventListener("pointercancel", pointerEnd);
}

// Bot Chip Selector
document.querySelectorAll(".bot-chip").forEach(chip => {
  chip.onclick = () => {
    document.querySelectorAll(".bot-chip").forEach(c => c.classList.remove("active"));
    chip.classList.add("active");
    activeBotIndex = parseInt(chip.dataset.bot, 10) || 1;
  };
});

// ==========================================
// 7. 2D Live Arena (Floor Canvas)
// ==========================================
const canvas = $("arena-canvas");
const actx = canvas ? canvas.getContext("2d") : null;
let arenaRobots = [];
let trails = {};
let maxTrailAge = 6.0;
let showTrails = true;
let shakeWobble = {};

if ($("arena-trails")) $("arena-trails").onchange = (e) => { showTrails = e.target.checked; };
if ($("arena-reset")) $("arena-reset").onclick = () => { trails = {}; };
if ($("arena-shake-all")) {
  $("arena-shake-all").onclick = () => {
    sendShake(1);
    arenaRobots.forEach(r => shakeWobble[r.name] = Date.now() + 500);
    playPop();
  };
}

function updateTelemetry(data) {
  if (!data || !data.robots) return;
  arenaRobots = data.robots;
  if ($("arena-stats")) {
    $("arena-stats").textContent = `Robots: ${arenaRobots.length} simulated | Floor: 2.2x scale`;
  }
  const now = Date.now() / 1000;
  for (const r of arenaRobots) {
    if (!trails[r.name]) trails[r.name] = [];
    trails[r.name].push({ x: r.x, y: r.y, t: now });
    while (trails[r.name].length && now - trails[r.name][0].t > maxTrailAge) {
      trails[r.name].shift();
    }
  }
}

function toCanvasCoords(cmX, cmY) {
  const originX = canvas.width * 0.45;
  const originY = canvas.height * 0.72;
  const scale = 2.2;
  return {
    cx: originX + cmX * scale,
    cy: originY - cmY * scale,
    scale,
  };
}

function renderArena() {
  if (!canvas || !actx) return;
  requestAnimationFrame(renderArena);
  const w = canvas.width, h = canvas.height;
  actx.clearRect(0, 0, w, h);

  // 1. Grid lines
  const origin = toCanvasCoords(0, 0);
  actx.lineWidth = 1;
  actx.strokeStyle = "rgba(255, 255, 255, 0.05)";
  for (let cm = -200; cm <= 200; cm += 20) {
    const p = toCanvasCoords(cm, 0);
    actx.beginPath(); actx.moveTo(p.cx, 0); actx.lineTo(p.cx, h); actx.stroke();
  }
  for (let cm = -60; cm <= 240; cm += 20) {
    const p = toCanvasCoords(0, cm);
    actx.beginPath(); actx.moveTo(0, p.cy); actx.lineTo(w, p.cy); actx.stroke();
  }

  // Major axes
  actx.strokeStyle = "rgba(255, 255, 255, 0.15)";
  actx.beginPath(); actx.moveTo(origin.cx, 0); actx.lineTo(origin.cx, h); actx.stroke();
  actx.beginPath(); actx.moveTo(0, origin.cy); actx.lineTo(w, origin.cy); actx.stroke();

  // Coordinates labels
  actx.fillStyle = "rgba(255, 255, 255, 0.25)";
  actx.font = "10px sans-serif";
  actx.textAlign = "left";
  for (let cm = -160; cm <= 160; cm += 40) {
    if (cm === 0) continue;
    const p = toCanvasCoords(cm, 0);
    actx.fillText(`${cm > 0 ? "+" : ""}${cm}cm`, p.cx - 14, origin.cy + 14);
  }
  for (let cm = 40; cm <= 200; cm += 40) {
    const p = toCanvasCoords(0, cm);
    actx.fillText(`+${cm}cm`, origin.cx + 6, p.cy + 4);
  }

  // Home spots
  const homeSpots = [
    { x: 0, y: 0, label: "BOLT 1", color: "#ff3b3b" },
    { x: 15, y: 0, label: "BOLT 2", color: "#2ecc71" },
    { x: 30, y: 0, label: "BOLT 3", color: "#3498db" },
  ];
  for (const sp of homeSpots) {
    const p = toCanvasCoords(sp.x, sp.y);
    actx.strokeStyle = sp.color;
    actx.setLineDash([3, 3]);
    actx.beginPath();
    actx.arc(p.cx, p.cy, 18, 0, Math.PI * 2);
    actx.stroke();
    actx.setLineDash([]);
    actx.fillStyle = sp.color;
    actx.font = "9px sans-serif";
    actx.fillText(sp.label, p.cx - 15, p.cy + 28);
  }

  // 2. Motion Trails
  if (showTrails) {
    const now = Date.now() / 1000;
    for (const [name, pts] of Object.entries(trails)) {
      if (pts.length < 2) continue;
      const robot = arenaRobots.find(r => r.name === name);
      const baseCol = robot && robot.front_led !== "#000000" ? robot.front_led : "#58a6ff";
      actx.lineWidth = 2.5;
      actx.lineCap = "round";
      for (let i = 1; i < pts.length; i++) {
        const p1 = toCanvasCoords(pts[i - 1].x, pts[i - 1].y);
        const p2 = toCanvasCoords(pts[i].x, pts[i].y);
        const age = now - pts[i].t;
        const alpha = Math.max(0.05, 1.0 - age / maxTrailAge);
        actx.strokeStyle = baseCol.startsWith("#") ? `${baseCol}${Math.floor(alpha * 255).toString(16).padStart(2, "0")}` : baseCol;
        actx.beginPath();
        actx.moveTo(p1.cx, p1.cy);
        actx.lineTo(p2.cx, p2.cy);
        actx.stroke();
      }
    }
  }

  // 3. Robots
  const nowMs = Date.now();
  for (const r of arenaRobots) {
    const p = toCanvasCoords(r.x, r.y);
    let rx = p.cx, ry = p.cy;
    if (shakeWobble[r.name] && nowMs < shakeWobble[r.name]) {
      rx += (Math.random() - 0.5) * 8;
      ry += (Math.random() - 0.5) * 8;
    }
    const rad = 22;

    actx.save();
    actx.translate(rx, ry);

    // Front headlight beam
    const headingRad = (r.heading * Math.PI) / 180;
    actx.rotate(headingRad);

    const beamGrad = actx.createRadialGradient(0, 0, rad, 0, -rad - 40, 50);
    beamGrad.addColorStop(0, "rgba(255, 255, 255, 0.35)");
    beamGrad.addColorStop(1, "rgba(255, 255, 255, 0.0)");
    actx.fillStyle = beamGrad;
    actx.beginPath();
    actx.moveTo(0, 0);
    actx.arc(0, 0, rad + 45, -Math.PI / 2 - 0.45, -Math.PI / 2 + 0.45);
    actx.closePath();
    actx.fill();

    // Tail light (blue dot at back)
    if (r.back_led && r.back_led !== "#000000") {
      actx.fillStyle = r.back_led;
      actx.shadowColor = r.back_led;
      actx.shadowBlur = 10;
      actx.beginPath();
      actx.arc(0, rad - 2, 4, 0, Math.PI * 2);
      actx.fill();
      actx.shadowBlur = 0;
    }

    // Outer spherical shell
    const ballGrad = actx.createRadialGradient(-rad * 0.3, -rad * 0.3, 2, 0, 0, rad);
    ballGrad.addColorStop(0, "rgba(255, 255, 255, 0.35)");
    ballGrad.addColorStop(0.7, "rgba(40, 50, 70, 0.65)");
    ballGrad.addColorStop(1, "rgba(20, 25, 35, 0.95)");
    actx.fillStyle = ballGrad;
    actx.beginPath();
    actx.arc(0, 0, rad, 0, Math.PI * 2);
    actx.fill();

    // Rim glow
    actx.strokeStyle = r.front_led !== "#000000" ? r.front_led : "rgba(100, 150, 255, 0.4)";
    actx.lineWidth = 2;
    actx.stroke();

    // 8x8 LED Matrix
    if (r.matrix && r.matrix.length === 8) {
      const dotSize = 2.2;
      const dotSpacing = 3.2;
      const startX = -((7 * dotSpacing) / 2);
      const startY = -((7 * dotSpacing) / 2);

      for (let row = 0; row < 8; row++) {
        for (let col = 0; col < 8; col++) {
          const colHex = r.matrix[row][col];
          const isLit = colHex && colHex !== "#000000";
          actx.fillStyle = isLit ? colHex : "rgba(255, 255, 255, 0.04)";
          if (isLit) {
            actx.shadowColor = colHex;
            actx.shadowBlur = 4;
          }
          actx.beginPath();
          actx.arc(startX + col * dotSpacing, startY + row * dotSpacing, dotSize / 2, 0, Math.PI * 2);
          actx.fill();
          actx.shadowBlur = 0;
        }
      }
    }

    actx.restore();

    // Robot Name Tag
    actx.fillStyle = "#ffffff";
    actx.font = "bold 11px sans-serif";
    actx.textAlign = "center";
    actx.fillText(r.name, rx, ry + rad + 14);

    actx.fillStyle = "rgba(255, 255, 255, 0.55)";
    actx.font = "9px monospace";
    actx.fillText(`(${Math.round(r.x)}, ${Math.round(r.y)}) ${Math.round(r.heading)}°`, rx, ry + rad + 25);
  }
}

function handleCanvasPointer(clientX, clientY) {
  if (!canvas) return;
  const rect = canvas.getBoundingClientRect();
  const mouseX = (clientX - rect.left) * (canvas.width / rect.width);
  const mouseY = (clientY - rect.top) * (canvas.height / rect.height);

  for (let idx = 0; idx < arenaRobots.length; idx++) {
    const r = arenaRobots[idx];
    const p = toCanvasCoords(r.x, r.y);
    const dist = Math.hypot(mouseX - p.cx, mouseY - p.cy);
    if (dist <= 30) {
      shakeWobble[r.name] = Date.now() + 600;
      playPop();
      sendShake(idx + 1, r.name);
      break;
    }
  }
}

if (canvas) {
  canvas.addEventListener("click", (e) => handleCanvasPointer(e.clientX, e.clientY));
  canvas.addEventListener("touchstart", (e) => {
    if (e.touches && e.touches.length > 0) {
      handleCanvasPointer(e.touches[0].clientX, e.touches[0].clientY);
    }
  }, { passive: true });
  requestAnimationFrame(renderArena);
}

// ==========================================
// 8. Standalone Simulation Engine
// ==========================================
let clientRobots = [];
let clientLoopId = null;
let clientSimState = {};

const DEFAULT_TTT_CONFIG = {
  auto: true,
  robots: ["BOLT 1", "BOLT 2", "BOLT 3", "BOLT 4", "BOLT 5", "BOLT 6", "BOLT 7", "BOLT 8", "BOLT 9"],
  rotation: 0,
  mirror: false,
};

const DEFAULT_LETTER_CONFIG = {
  heading: 270,
  letters: [
    { letter: "N", rotation: 0, mirror: false },
    { letter: "E", rotation: 0, mirror: false },
    { letter: "U", rotation: 0, mirror: false },
  ],
};

let gameState = null;
let tttCfg = DEFAULT_TTT_CONFIG;
let letterCfg = DEFAULT_LETTER_CONFIG;

function initClientRobots(count = 3) {
  const configs = [
    { name: "BOLT 1", x: 0, y: 0, col: "#ff3b3b", matrixKey: "N" },
    { name: "BOLT 2", x: 15, y: 0, col: "#2ecc71", matrixKey: "E" },
    { name: "BOLT 3", x: 30, y: 0, col: "#3498db", matrixKey: "U" },
    { name: "BOLT 4", x: -15, y: 0, col: "#f1c40f", matrixKey: "1" },
    { name: "BOLT 5", x: -30, y: 0, col: "#e84393", matrixKey: "2" },
    { name: "BOLT 6", x: 45, y: 0, col: "#00cec9", matrixKey: "3" },
    { name: "BOLT 7", x: -45, y: 0, col: "#e67e22", matrixKey: "4" },
    { name: "BOLT 8", x: 60, y: 0, col: "#ffffff", matrixKey: "5" },
    { name: "BOLT 9", x: -60, y: 0, col: "#9b59b6", matrixKey: "6" },
  ];
  clientRobots = [];
  for (let i = 0; i < Math.min(count, configs.length); i++) {
    const c = configs[i];
    clientRobots.push({
      name: c.name,
      x: c.x,
      y: c.y,
      heading: 0,
      speed: 0,
      front_led: "#ffffff",
      back_led: "#0000ff",
      matrix: makeMatrix(c.matrixKey, c.col),
      homeX: c.x,
      homeY: c.y,
      baseColor: c.col,
    });
  }
  updateTelemetry({ robots: clientRobots });
}

function enableClientMode(reason) {
  clientMode = true;
  if (!connectedTarget) {
    online = false;
  }
  renderStatus();
  initClientRobots(3);
}

function clientStop(resetState = true) {
  if (clientLoopId) {
    clearInterval(clientLoopId);
    cancelAnimationFrame(clientLoopId);
    clientLoopId = null;
  }
  if (bleApiChar) {
    bleDrive(0, 0);
  }
  clientSimState = {};
  if (resetState) {
    state.running = null;
    renderStatus();
    addLine("=== Stopped ===");
    for (const r of clientRobots) {
      r.x = r.homeX;
      r.y = r.homeY;
      r.heading = 0;
      r.speed = 0;
    }
    updateTelemetry({ robots: clientRobots });
  }
}

if ($("global-stop")) $("global-stop").onclick = () => {
  if (clientMode) {
    clientStop();
  } else {
    fetch("/api/stop", { method: "POST" }).catch(() => clientStop());
  }
};

function startProgram(id) {
  if (!online && !connectedTarget) {
    addLine("[NOTICE] Currently offline. Tap 'Connect' in the header to pair your Sphero BOLT via Bluetooth!");
  }
  if (clientMode) {
    clientStart(id);
    return;
  }
  fetch(`/api/start/${id}`, { method: "POST" })
    .then(r => { if (!r.ok) clientStart(id); })
    .catch(() => clientStart(id));
}

function clientStart(id) {
  clientStop(false);
  state.running = id;
  state.started = Date.now() / 1000;
  renderStatus();

  const prog = DEFAULT_PROGRAMS.find(p => p.id === id);
  addLine(`=== Started: ${prog ? prog.title : id} ===`);

  if (id === "dance") {
    switchTab("shows");
    runClientDance();
  } else if (id === "neu") {
    switchTab("shows");
    runClientNeu();
  } else if (id === "roam") {
    switchTab("arena");
    runClientRoam();
  } else if (id === "drive") {
    switchTab("drive");
    runClientDrive();
  } else if (id === "potato") {
    switchTab("games");
    runClientPotato();
  } else if (id === "mole") {
    switchTab("games");
    runClientMole();
  } else if (id === "simon") {
    switchTab("games");
    runClientSimon();
  } else if (id === "rps") {
    switchTab("games");
    runClientRps();
  } else if (id === "tictactoe") {
    switchTab("tictactoe");
    runClientTtt();
  }
}

// ------------------------------------------
// Dance Show
// ------------------------------------------
function runClientDance() {
  initClientRobots(3);
  const startTime = Date.now();
  let prevSection = -1;

  clientLoopId = setInterval(() => {
    const elapsed = (Date.now() - startTime) / 1000;
    let section = 0;

    if (elapsed < 2.0) {
      section = 0;
      if (prevSection !== 0) {
        addLine("=== Aiming (simulated 2s) ===");
        clientRobots.forEach(r => {
          r.heading = 0;
          r.front_led = "#ffffff";
          r.back_led = "#0000ff";
          r.matrix = makeMatrix("Arrow", "#00ffff");
        });
      }
    } else if (elapsed < 8.0) {
      section = 1;
      if (prevSection !== 1) {
        addLine("=== Section 1: Opening Synchronized Roll (+30 cm) ===");
        clientRobots.forEach(r => r.matrix = makeMatrix("Arrow", r.baseColor));
      }
      const progress = Math.min(1, (elapsed - 2.0) / 5.5);
      clientRobots.forEach(r => { r.y = progress * 30; r.heading = 0; });
    } else if (elapsed < 14.0) {
      section = 2;
      if (prevSection !== 2) {
        addLine("=== Section 2: Synchronized 360 Spin ===");
        playTone(440, "sine", 0.3, 0.15);
      }
      const spinAngle = ((elapsed - 8.0) / 5.5) * 360;
      clientRobots.forEach((r, i) => {
        r.heading = spinAngle % 360;
        const hue = Math.floor((spinAngle + i * 120) % 360);
        r.matrix = makeSolidMatrix(`hsl(${hue}, 90%, 55%)`);
      });
    } else if (elapsed < 22.0) {
      section = 3;
      if (prevSection !== 3) addLine("=== Section 3: Side-to-Side Shuffle ===");
      const sway = Math.sin((elapsed - 14.0) * 3.0) * 12;
      clientRobots.forEach(r => {
        r.x = r.homeX + sway;
        r.heading = sway > 0 ? 90 : 270;
      });
    } else if (elapsed < 30.0) {
      section = 4;
      if (prevSection !== 4) {
        addLine("=== Section 4: Solo 1 (BOLT 1 Red) ===");
        playTone(600, "triangle", 0.25, 0.2);
      }
      const t = (elapsed - 22.0) / 7.5;
      clientRobots[0].y = 30 + Math.sin(t * Math.PI) * 20;
      clientRobots[0].heading = (t * 720) % 360;
      clientRobots[0].matrix = makeMatrix("1", "#ff3b3b");
    } else if (elapsed < 38.0) {
      section = 5;
      if (prevSection !== 5) {
        addLine("=== Section 5: Solo 2 (BOLT 2 Green) ===");
        playTone(600, "triangle", 0.25, 0.2);
      }
      const t = (elapsed - 30.0) / 7.5;
      clientRobots[1].y = 30 + Math.sin(t * Math.PI) * 20;
      clientRobots[1].heading = (t * 720) % 360;
      clientRobots[1].matrix = makeMatrix("2", "#2ecc71");
    } else if (elapsed < 46.0) {
      section = 6;
      if (prevSection !== 6) {
        addLine("=== Section 6: Solo 3 (BOLT 3 Blue) ===");
        playTone(600, "triangle", 0.25, 0.2);
      }
      const t = (elapsed - 38.0) / 7.5;
      clientRobots[2].y = 30 + Math.sin(t * Math.PI) * 20;
      clientRobots[2].heading = (t * 720) % 360;
      clientRobots[2].matrix = makeMatrix("3", "#3498db");
    } else if (elapsed < 56.0) {
      section = 7;
      if (prevSection !== 7) addLine("=== Section 7: Circular Orbit Formation ===");
      const orbitAngle = (elapsed - 46.0) * 1.4;
      const centerX = 15, centerY = 25, radius = 22;
      clientRobots.forEach((r, i) => {
        const theta = orbitAngle + (i * Math.PI * 2) / 3;
        r.x = centerX + Math.cos(theta) * radius;
        r.y = centerY + Math.sin(theta) * radius;
        r.heading = ((theta + Math.PI / 2) * 180 / Math.PI) % 360;
        r.matrix = makeMatrix("Arrow", r.baseColor);
      });
    } else if (elapsed < 64.0) {
      section = 8;
      if (prevSection !== 8) addLine("=== Section 8: Return Home ===");
      const prog = Math.min(1, (elapsed - 56.0) / 7.0);
      clientRobots.forEach(r => {
        r.x = r.homeX * prog + r.x * (1 - prog);
        r.y = r.homeY * prog + r.y * (1 - prog);
        r.heading = 180;
      });
    } else {
      section = 9;
      if (prevSection !== 9) {
        addLine("=== Finale: Victory Celebration! ===");
        playVictory();
      }
      const spin = ((elapsed - 64.0) * 360) % 360;
      clientRobots.forEach((r, i) => {
        r.x = r.homeX;
        r.y = r.homeY;
        r.heading = spin;
        r.matrix = makeMatrix("Boom", i === 0 ? "#ff2222" : i === 1 ? "#2ecc71" : "#3498db");
      });
      if (elapsed > 72.0) {
        addLine("=== Dance complete! ===");
        clientStop();
        return;
      }
    }

    prevSection = section;
    updateTelemetry({ robots: clientRobots });
  }, 40);
}

// ------------------------------------------
// NEU Formation
// ------------------------------------------
function runClientNeu() {
  initClientRobots(3);
  let step = 0;
  addLine("=== NEU Formation Active ===");
  clientLoopId = setInterval(() => {
    step++;
    if (step < 25) {
      clientRobots.forEach(r => { r.y = (step / 25) * 20; r.heading = 0; });
    } else {
      const targetHeading = letterCfg ? letterCfg.heading : 270;
      clientRobots.forEach((r, i) => {
        r.heading = targetHeading;
        const lInfo = (letterCfg && letterCfg.letters[i]) || { letter: ["N","E","U"][i], rotation: 0, mirror: false };
        r.matrix = makeMatrix(lInfo.letter, r.baseColor, lInfo.rotation, lInfo.mirror);
      });
    }
    updateTelemetry({ robots: clientRobots });
  }, 40);
}

// ------------------------------------------
// Autonomous Roam
// ------------------------------------------
function runClientRoam() {
  initClientRobots(3);
  const wander = clientRobots.map(r => ({
    vx: (Math.random() - 0.5) * 14,
    vy: (Math.random() - 0.5) * 14,
    nextChange: Date.now() + 1500,
  }));

  clientLoopId = setInterval(() => {
    const now = Date.now();
    clientRobots.forEach((r, i) => {
      const w = wander[i];
      if (now > w.nextChange) {
        w.vx = (Math.random() - 0.5) * 18;
        w.vy = (Math.random() - 0.5) * 18;
        w.nextChange = now + 1500 + Math.random() * 2000;
      }
      r.x += w.vx * 0.05;
      r.y += w.vy * 0.05;
      const dist = Math.hypot(r.x - r.homeX, r.y - r.homeY);
      if (dist > 25) {
        w.vx += (r.homeX - r.x) * 0.1;
        w.vy += (r.homeY - r.y) * 0.1;
      }
      r.heading = (Math.atan2(w.vx, w.vy) * 180 / Math.PI + 360) % 360;
      r.matrix = makeMatrix("Arrow", r.baseColor);
    });
    updateTelemetry({ robots: clientRobots });
  }, 40);
}

// ------------------------------------------
// Joystick Drive (Simulation update loop)
// ------------------------------------------
function runClientDrive() {
  initClientRobots(3);
  let lastTime = Date.now();

  clientLoopId = setInterval(() => {
    const now = Date.now();
    const dt = Math.min(0.1, (now - lastTime) / 1000);
    lastTime = now;

    clientRobots.forEach(r => {
      if (r.speed > 0) {
        const rad = (r.heading * Math.PI) / 180;
        r.x = Math.max(-140, Math.min(140, r.x + Math.sin(rad) * r.speed * dt));
        r.y = Math.max(-30, Math.min(190, r.y + Math.cos(rad) * r.speed * dt));
      }
    });

    updateTelemetry({ robots: clientRobots });
  }, 33);
}

// Keyboard fallback for drive
const KEY_MAP = {
  KeyW: [0, 1], ArrowUp: [0, 1],
  KeyS: [0, -1], ArrowDown: [0, -1],
  KeyA: [-1, 0], ArrowLeft: [-1, 0],
  KeyD: [1, 0], ArrowRight: [1, 0],
};
const activeKeys = new Set();
window.addEventListener("keydown", (e) => {
  if (KEY_MAP[e.code]) {
    activeKeys.add(e.code);
    evalKeys();
  }
});
window.addEventListener("keyup", (e) => {
  if (KEY_MAP[e.code]) {
    activeKeys.delete(e.code);
    evalKeys();
  }
});
function evalKeys() {
  if (activeKeys.size === 0) {
    snapKnobToCenter();
    return;
  }
  let dx = 0, dy = 0;
  for (const k of activeKeys) {
    const [kx, ky] = KEY_MAP[k];
    dx += kx; dy += ky;
  }
  if (dx === 0 && dy === 0) {
    snapKnobToCenter();
    return;
  }
  const mag = Math.hypot(dx, dy);
  dx /= mag; dy /= mag;
  const angle = (Math.atan2(dx, dy) * 180 / Math.PI + 360) % 360;
  const speed = 75;
  setKnobPosition(dx * 50, -dy * 50);
  joystickHeading = angle;
  joystickSpeed = speed;
  updateJoystickHUD(angle, speed);
  dispatchDrive(angle, speed);
}

// ------------------------------------------
// Party Game 1: Hot Potato
// ------------------------------------------
function runClientPotato() {
  initClientRobots(1);
  const bot = clientRobots[0];
  bot.x = 0; bot.y = 15;

  clientSimState = {
    fuseTotal: 15 + Math.random() * 8,
    fuseElapsed: 0,
    exploded: false,
  };

  gameState = {
    kind: "party",
    game: "potato",
    title: "Hot Potato",
    phase: "idle",
    status: "Fuse unlit",
    info: "Tap 'Start' or click the ball to light the fuse and pass the potato!",
    cells: [{ robot: bot.name, color: "#2ecc71", label: "PASS ME" }],
  };

  renderParty();
  updateTelemetry({ robots: clientRobots });
}

function startPotatoFuse() {
  if (clientSimState.fuseElapsed > 0 || clientSimState.exploded) return;
  gameState.phase = "play";
  gameState.status = "[ALERT] FUSE LIT! Passing potato...";
  addLine("=== Hot Potato: Fuse is LIT! Pass it around! ===");
  renderParty();

  const tickInterval = 100;
  clientLoopId = setInterval(() => {
    clientSimState.fuseElapsed += tickInterval / 1000;
    const progress = clientSimState.fuseElapsed / clientSimState.fuseTotal;

    let col = "#2ecc71";
    if (progress > 0.7) {
      col = Math.floor(Date.now() / 150) % 2 === 0 ? "#ff0000" : "#f1c40f";
      playTone(700, "square", 0.04, 0.08);
    } else if (progress > 0.4) {
      col = "#f1c40f";
      if (Math.floor(Date.now() / 400) % 2 === 0) playTone(500, "square", 0.03, 0.05);
    } else {
      if (Math.floor(Date.now() / 800) % 2 === 0) playTone(400, "square", 0.02, 0.03);
    }

    clientRobots[0].matrix = makeSolidMatrix(col);
    gameState.cells[0].color = col;
    gameState.cells[0].label = progress > 0.7 ? "HURRY!" : "PASS!";
    renderParty();
    updateTelemetry({ robots: clientRobots });

    if (progress >= 1.0) {
      clearInterval(clientLoopId);
      clientSimState.exploded = true;
      gameState.phase = "boom";
      gameState.status = "[BOOM] The potato exploded!";
      gameState.info = "Whoever was holding the potato is OUT! Tap Start to play again.";
      addLine("=== [BOOM] The potato exploded! ===");
      playBoom();
      shakeWobble[clientRobots[0].name] = Date.now() + 1500;
      clientRobots[0].matrix = makeMatrix("Boom", "#ff0000");
      renderParty();
      updateTelemetry({ robots: clientRobots });
    }
  }, tickInterval);
}

// ------------------------------------------
// Party Game 2: Whack-a-Mole
// ------------------------------------------
function runClientMole() {
  initClientRobots(4);
  clientSimState = {
    score: 0,
    activeMole: -1,
    timeLeft: 60,
    moleTimeout: null,
  };

  gameState = {
    kind: "party",
    game: "mole",
    title: "Whack-a-Mole",
    phase: "play",
    status: "Round active: 60s remaining",
    info: "Whack the neon green ball as fast as you can!",
    score: 0,
    cells: clientRobots.map(r => ({ robot: r.name, color: "#111111", label: "" })),
  };

  renderParty();
  addLine("=== Whack-a-Mole Started ===");

  function nextMole() {
    if (!state.running || state.running !== "mole") return;
    const moleIdx = Math.floor(Math.random() * clientRobots.length);
    clientSimState.activeMole = moleIdx;

    clientRobots.forEach((r, i) => {
      if (i === moleIdx) {
        r.matrix = makeSolidMatrix("#00ff44");
        gameState.cells[i].color = "#00ff44";
        gameState.cells[i].label = "WHACK!";
      } else {
        r.matrix = makeSolidMatrix("#000000");
        gameState.cells[i].color = "#111111";
        gameState.cells[i].label = "";
      }
    });

    renderParty();
    updateTelemetry({ robots: clientRobots });
    playPop();

    const speed = Math.max(500, 1500 - clientSimState.score * 65);
    clientSimState.moleTimeout = setTimeout(() => {
      if (clientSimState.activeMole === moleIdx) {
        clientSimState.activeMole = -1;
        clientRobots[moleIdx].matrix = makeSolidMatrix("#000000");
        gameState.cells[moleIdx].color = "#111111";
        gameState.cells[moleIdx].label = "";
        renderParty();
        updateTelemetry({ robots: clientRobots });
        setTimeout(nextMole, 250);
      }
    }, speed);
  }

  nextMole();

  clientLoopId = setInterval(() => {
    clientSimState.timeLeft--;
    if (clientSimState.timeLeft <= 0) {
      clearInterval(clientLoopId);
      clearTimeout(clientSimState.moleTimeout);
      gameState.phase = "over";
      gameState.status = `Game Over! Final Score: ${clientSimState.score}`;
      gameState.info = "Great reflexes! Press Start to play again.";
      addLine(`=== Whack-a-Mole Finished! Final Score: ${clientSimState.score} ===`);
      playVictory();
      renderParty();
    } else {
      gameState.status = `${clientSimState.timeLeft}s left | Score: ${clientSimState.score}`;
      renderParty();
    }
  }, 1000);
}

// ------------------------------------------
// Party Game 3: Simon Says
// ------------------------------------------
const SIMON_NOTES = [261.6, 329.6, 392.0, 523.2];
const SIMON_COLORS = ["#ff3b3b", "#2ecc71", "#3498db", "#f1c40f"];

function runClientSimon() {
  const pos = [
    { x: -15, y: 25 }, { x: 15, y: 25 },
    { x: -15, y: 5 },  { x: 15, y: 5 },
  ];
  clientRobots = pos.map((p, i) => ({
    name: `BOLT ${i + 1}`,
    x: p.x,
    y: p.y,
    heading: 0,
    speed: 0,
    front_led: SIMON_COLORS[i],
    back_led: "#000000",
    matrix: makeSolidMatrix(SIMON_COLORS[i]),
    homeX: p.x,
    homeY: p.y,
    baseColor: SIMON_COLORS[i],
  }));

  clientSimState = {
    sequence: [Math.floor(Math.random() * 4)],
    playerIdx: 0,
    playingSeq: false,
    level: 1,
  };

  gameState = {
    kind: "party",
    game: "simon",
    title: "Simon Says",
    phase: "watch",
    status: "Level 1: Watch sequence",
    info: "Watch which balls light up, then repeat the pattern!",
    cells: clientRobots.map((r, i) => ({ robot: r.name, color: SIMON_COLORS[i], label: String(i + 1) })),
  };

  renderParty();
  updateTelemetry({ robots: clientRobots });
  setTimeout(playSimonSequence, 1000);
}

function playSimonSequence() {
  if (!clientSimState || !clientSimState.sequence) return;
  clientSimState.playingSeq = true;
  gameState.phase = "watch";
  gameState.status = `Level ${clientSimState.level}: Watch sequence`;
  gameState.info = "Watch the sequence...";
  renderParty();

  let step = 0;
  const timer = setInterval(() => {
    if (step >= clientSimState.sequence.length) {
      clearInterval(timer);
      clientSimState.playingSeq = false;
      clientSimState.playerIdx = 0;
      gameState.phase = "play";
      gameState.status = `Level ${clientSimState.level}: Your turn!`;
      gameState.info = "Repeat the sequence by tapping the balls or buttons!";
      renderParty();
      return;
    }
    const ballIdx = clientSimState.sequence[step];
    flashSimonBall(ballIdx);
    step++;
  }, 750);
}

function flashSimonBall(idx) {
  playTone(SIMON_NOTES[idx], "triangle", 0.35, 0.25);
  shakeWobble[clientRobots[idx].name] = Date.now() + 400;
  clientRobots[idx].matrix = makeSolidMatrix("#ffffff");
  updateTelemetry({ robots: clientRobots });
  setTimeout(() => {
    if (clientRobots[idx]) {
      clientRobots[idx].matrix = makeSolidMatrix(SIMON_COLORS[idx]);
      updateTelemetry({ robots: clientRobots });
    }
  }, 350);
}

// ------------------------------------------
// Party Game 4: Rock-Paper-Scissors
// ------------------------------------------
function runClientRps() {
  const pos = [{ x: -15, y: 15 }, { x: 15, y: 15 }];
  clientRobots = pos.map((p, i) => ({
    name: [`BOLT 1 (Red)`, `BOLT 2 (Blue)`][i],
    x: p.x,
    y: p.y,
    heading: 0,
    speed: 0,
    front_led: i === 0 ? "#ff3b3b" : "#3498db",
    back_led: "#0000ff",
    matrix: makeMatrix("?", i === 0 ? "#ff3b3b" : "#3498db"),
    homeX: p.x,
    homeY: p.y,
    baseColor: i === 0 ? "#ff3b3b" : "#3498db",
  }));

  clientSimState = {
    p1Score: 0,
    p2Score: 0,
    roundActive: false,
  };

  gameState = {
    kind: "party",
    game: "rps",
    title: "Rock-Paper-Scissors",
    phase: "idle",
    status: "Player 1: 0 | Player 2: 0",
    info: "Tap 'Start' or shake either ball to countdown and shoot!",
    cells: clientRobots.map(r => ({ robot: r.name, color: r.baseColor, label: "?" })),
  };

  renderParty();
  updateTelemetry({ robots: clientRobots });
}

function startRpsShoot() {
  if (clientSimState.roundActive) return;
  clientSimState.roundActive = true;
  const choices = ["Rock", "Paper", "Scissors"];

  playTone(400, "sine", 0.2, 0.2);
  gameState.info = "3...";
  clientRobots.forEach(r => r.matrix = makeMatrix("3", r.baseColor));
  renderParty();
  updateTelemetry({ robots: clientRobots });

  setTimeout(() => {
    playTone(500, "sine", 0.2, 0.2);
    gameState.info = "2...";
    clientRobots.forEach(r => r.matrix = makeMatrix("2", r.baseColor));
    renderParty();
    updateTelemetry({ robots: clientRobots });

    setTimeout(() => {
      playTone(600, "sine", 0.2, 0.2);
      gameState.info = "1...";
      clientRobots.forEach(r => r.matrix = makeMatrix("1", r.baseColor));
      renderParty();
      updateTelemetry({ robots: clientRobots });

      setTimeout(() => {
        playTone(850, "triangle", 0.35, 0.25);
        const c1 = choices[Math.floor(Math.random() * 3)];
        const c2 = choices[Math.floor(Math.random() * 3)];

        clientRobots[0].matrix = makeMatrix(c1, "#ff3b3b");
        clientRobots[1].matrix = makeMatrix(c2, "#3498db");
        gameState.cells[0].label = c1;
        gameState.cells[1].label = c2;

        let resultText = "";
        if (c1 === c2) {
          resultText = `Tie! Both chose ${c1}.`;
        } else if (
          (c1 === "Rock" && c2 === "Scissors") ||
          (c1 === "Scissors" && c2 === "Paper") ||
          (c1 === "Paper" && c2 === "Rock")
        ) {
          clientSimState.p1Score++;
          resultText = `Player 1 wins! (${c1} beats ${c2})`;
          playVictory();
        } else {
          clientSimState.p2Score++;
          resultText = `Player 2 wins! (${c2} beats ${c1})`;
          playVictory();
        }

        gameState.status = `Player 1: ${clientSimState.p1Score} | Player 2: ${clientSimState.p2Score}`;
        gameState.info = resultText;
        addLine(`RPS: P1 [${c1}] vs P2 [${c2}] -> ${resultText}`);

        if (clientSimState.p1Score >= 2 || clientSimState.p2Score >= 2) {
          const winner = clientSimState.p1Score >= 2 ? "Player 1 (Red)" : "Player 2 (Blue)";
          gameState.info = `[WINNER] ${winner} wins the MATCH!`;
          addLine(`=== [WINNER] ${winner} wins the match! ===`);
        }

        clientSimState.roundActive = false;
        renderParty();
        updateTelemetry({ robots: clientRobots });
      }, 700);
    }, 700);
  }, 700);
}

// ------------------------------------------
// Tic-Tac-Toe
// ------------------------------------------
function runClientTtt() {
  const tttPositions = [
    { name: "BOLT 1", x: -25, y: 50 }, { name: "BOLT 2", x: 0, y: 50 }, { name: "BOLT 3", x: 25, y: 50 },
    { name: "BOLT 4", x: -25, y: 25 }, { name: "BOLT 5", x: 0, y: 25 }, { name: "BOLT 6", x: 25, y: 25 },
    { name: "BOLT 7", x: -25, y: 0  }, { name: "BOLT 8", x: 0, y: 0  }, { name: "BOLT 9", x: 25, y: 0  },
  ];

  clientRobots = tttPositions.map((pos, i) => ({
    name: (tttCfg && tttCfg.robots[i]) || pos.name,
    x: pos.x,
    y: pos.y,
    heading: 0,
    speed: 0,
    front_led: "#ffffff",
    back_led: "#0000ff",
    matrix: makeMatrix("?", "#f1c40f", tttCfg ? tttCfg.rotation : 0, tttCfg ? tttCfg.mirror : false),
    homeX: pos.x,
    homeY: pos.y,
    baseColor: "#f1c40f",
  }));

  gameState = {
    kind: "tictactoe",
    phase: "numbering",
    board: Array(9).fill(""),
    turn: "X",
    robots: 9,
    numbered: 0,
    next: 1,
    cells: clientRobots.map(r => ({ robot: r.name, connected: true })),
    line: null,
    winner: null,
  };

  addLine("=== Tic-tac-toe Active ===");
  renderGame();
  updateTelemetry({ robots: clientRobots });
}

// ==========================================
// 9. User Action Dispatchers & UI Rendering
// ==========================================
function sendGameAction(body) {
  if (clientMode) {
    handleClientGameAction(body);
    return;
  }
  fetch("/api/game", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).catch(() => handleClientGameAction(body));
}

function handleClientGameAction(body) {
  if (!body) return;
  const action = body.action;

  // Tic-Tac-Toe
  if (state.running === "tictactoe" && gameState) {
    if (action === "start") {
      gameState.phase = "play";
      gameState.turn = "X";
      gameState.numbered = 9;
      clientRobots.forEach((r, i) => {
        r.matrix = makeMatrix(String(i + 1), "#c8c8c8", tttCfg.rotation, tttCfg.mirror);
      });
      renderGame();
      updateTelemetry({ robots: clientRobots });
      addLine("Numbering complete! X starts the game.");
    } else if (action === "play") {
      const idx = body.cell - 1;
      if (gameState.phase !== "play" || gameState.board[idx] || gameState.winner) return;
      gameState.board[idx] = gameState.turn;

      const player = gameState.turn;
      const col = player === "X" ? "#ff3b3b" : "#3498db";
      clientRobots[idx].matrix = makeMatrix(player, col, tttCfg.rotation, tttCfg.mirror);
      clientRobots[idx].front_led = col;
      playTone(player === "X" ? 523 : 440, "triangle", 0.2, 0.2);

      const lines = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],
        [0, 3, 6], [1, 4, 7], [2, 5, 8],
        [0, 4, 8], [2, 4, 6]
      ];
      let won = false;
      for (const line of lines) {
        const [a, b, c] = line;
        if (gameState.board[a] && gameState.board[a] === gameState.board[b] && gameState.board[a] === gameState.board[c]) {
          gameState.winner = player;
          gameState.line = line;
          won = true;
          line.forEach(pos => {
            clientRobots[pos].matrix = makeMatrix(player, "#2ecc71", tttCfg.rotation, tttCfg.mirror);
          });
          playVictory();
          addLine(`=== ${player} WINS Tic-tac-toe! ===`);
          break;
        }
      }

      if (!won) {
        if (gameState.board.every(m => m !== "")) {
          gameState.winner = "draw";
          addLine("=== Game ended in a DRAW! ===");
          playTone(250, "sine", 0.4, 0.2);
        } else {
          gameState.turn = gameState.turn === "X" ? "O" : "X";
        }
      }

      renderGame();
      updateTelemetry({ robots: clientRobots });
    } else if (action === "new") {
      gameState.board = Array(9).fill("");
      gameState.turn = "X";
      gameState.winner = null;
      gameState.line = null;
      clientRobots.forEach((r, i) => {
        r.matrix = makeMatrix(String(i + 1), "#c8c8c8", tttCfg.rotation, tttCfg.mirror);
        r.front_led = "#ffffff";
      });
      renderGame();
      updateTelemetry({ robots: clientRobots });
    } else if (action === "recount") {
      runClientTtt();
    }
    return;
  }

  // Simon Says
  if (state.running === "simon" && clientSimState) {
    if (action === "start") {
      runClientSimon();
    } else if (action === "tap") {
      if (clientSimState.playingSeq) return;
      const tappedIdx = body.cell - 1;
      flashSimonBall(tappedIdx);

      const expected = clientSimState.sequence[clientSimState.playerIdx];
      if (tappedIdx === expected) {
        clientSimState.playerIdx++;
        if (clientSimState.playerIdx >= clientSimState.sequence.length) {
          playVictory();
          clientSimState.level++;
          clientSimState.sequence.push(Math.floor(Math.random() * 4));
          setTimeout(playSimonSequence, 1200);
        }
      } else {
        playBuzzer();
        gameState.phase = "over";
        gameState.status = `Game Over! Reached Level ${clientSimState.level}`;
        gameState.info = "Wrong ball! Press Start to try again.";
        renderParty();
      }
    }
    return;
  }

  // Whack-a-Mole
  if (state.running === "mole" && clientSimState) {
    if (action === "tap") {
      const tappedIdx = body.cell - 1;
      if (tappedIdx === clientSimState.activeMole) {
        clientSimState.score++;
        gameState.score = clientSimState.score;
        playPop();
        shakeWobble[clientRobots[tappedIdx].name] = Date.now() + 400;
        clientRobots[tappedIdx].matrix = makeMatrix("Check", "#f1c40f");
        updateTelemetry({ robots: clientRobots });
      } else {
        clientSimState.score = Math.max(0, clientSimState.score - 1);
        gameState.score = clientSimState.score;
        playBuzzer();
      }
      renderParty();
    }
    return;
  }

  // Hot Potato
  if (state.running === "potato") {
    if (action === "start" || action === "tap") {
      if (clientSimState.exploded) {
        runClientPotato();
      } else if (clientSimState.fuseElapsed === 0) {
        startPotatoFuse();
      } else {
        playPop();
        shakeWobble[clientRobots[0].name] = Date.now() + 300;
      }
    }
    return;
  }

  // Rock-Paper-Scissors
  if (state.running === "rps") {
    if (action === "start" || action === "tap") {
      startRpsShoot();
    }
    return;
  }
}

function sendShake(cell = 1, robot = "") {
  if (clientMode) {
    handleClientShake(cell, robot);
    return;
  }
  fetch("/api/shake", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cell, robot }),
  }).catch(() => handleClientShake(cell, robot));
}

function handleClientShake(cell, robot) {
  if (state.running === "tictactoe") {
    if (gameState && gameState.phase === "numbering") {
      sendGameAction({ action: "start" });
    } else {
      sendGameAction({ action: "play", cell });
    }
  } else if (state.running === "simon") {
    sendGameAction({ action: "tap", cell });
  } else if (state.running === "mole") {
    sendGameAction({ action: "tap", cell });
  } else if (state.running === "potato") {
    sendGameAction({ action: "start" });
  } else if (state.running === "rps") {
    sendGameAction({ action: "start" });
  } else {
    playPop();
  }
}

function renderGame() {
  const game = gameState && gameState.kind !== "party" ? gameState : null;
  const board = $("board");
  if (!board) return;
  board.innerHTML = "";
  const running = !!game;
  const numbering = running && game.phase === "numbering";

  if ($("ttt-new")) $("ttt-new").disabled = !running;
  if ($("ttt-recount")) $("ttt-recount").disabled = !running || numbering;
  if ($("ttt-start")) $("ttt-start").disabled = !numbering;

  if ($("ttt-status")) {
    if (!running) {
      $("ttt-status").textContent = "Start Tic-tac-toe to play.";
    } else if (numbering) {
      $("ttt-status").textContent = `Numbering: shake or tap ball for square ${game.next} (${game.numbered} of 9 done).`;
    } else if (game.winner === "draw") {
      $("ttt-status").textContent = "Draw! Press Same layout to play again.";
    } else if (game.winner) {
      $("ttt-status").textContent = `${game.winner} wins! Press Same layout to play again.`;
    } else {
      $("ttt-status").innerHTML = `Turn: <span style="color:${game.turn === "X" ? "var(--r1)" : "var(--r3)"}">${game.turn}</span>`;
    }
  }

  for (let c = 0; c < 9; c++) {
    const b = document.createElement("button");
    const mark = running && !numbering ? game.board[c] : null;
    const cell = running ? game.cells[c] : null;
    b.className = "ttt-cell " + (mark || "num") + (running && game.line && game.line.includes(c) ? " win" : "");
    const label = numbering ? (cell && cell.connected ? cell.robot : (c + 1 === game.next ? "shake next" : ""))
      : cell ? (cell.connected ? cell.robot : "click to play") : "";
    b.innerHTML = `${mark || c + 1}<small>${label}</small>`;
    b.disabled = !running || numbering || !!mark || !!game.winner;
    b.onclick = () => sendGameAction({ action: "play", cell: c + 1 });
    board.appendChild(b);
  }
}

for (const [id, action] of [["ttt-new", "new"], ["ttt-recount", "recount"], ["ttt-start", "start"]]) {
  if ($(id)) $(id).onclick = () => sendGameAction({ action });
}

function renderParty() {
  const g = gameState && gameState.kind === "party" ? gameState : null;
  const container = $("party-container");
  if (container) container.hidden = !g;
  if (!g) return;

  if ($("party-title")) $("party-title").textContent = g.title;
  if ($("party-status")) $("party-status").textContent = g.status;
  if ($("party-info")) $("party-info").textContent = g.info;

  const box = $("balls");
  if (box && box.childNodes.length !== g.cells.length) {
    box.innerHTML = "";
    g.cells.forEach((_, i) => {
      const b = document.createElement("button");
      b.className = "ball-btn";
      b.onclick = () => {
        playPop();
        sendGameAction({ action: "tap", cell: i + 1 });
      };
      box.appendChild(b);
    });
  }
  if (box) {
    g.cells.forEach((c, i) => {
      const b = box.childNodes[i];
      if (b) {
        const [r, gr, bl] = [1, 3, 5].map((k) => parseInt((c.color || "#000000").slice(k, k + 2), 16) || 0);
        const dark = 0.299 * r + 0.587 * gr + 0.114 * bl < 140;
        b.style.background = c.color === "#000000" ? "var(--bg)" : c.color;
        b.style.color = c.color === "#000000" ? "var(--text)" : dark ? "#fff" : "#111";
        b.innerHTML = `<span>${c.label || ""}</span><small>${c.robot}</small>`;
      }
    });
  }
}
if ($("party-start")) $("party-start").onclick = () => sendGameAction({ action: "start" });

// Letters Controls
const ROBOT_COLORS = ["var(--r1)", "var(--r2)", "var(--r3)"];
const ROBOT_LABELS = ["BOLT 1", "BOLT 2", "BOLT 3"];

function renderLetters() {
  if (!letterCfg) return;
  const box = $("letter-rows");
  if (!box) return;
  box.innerHTML = "";
  const row = (target, big, color, who, state) => {
    const el = document.createElement("div");
    el.className = "letter-row";
    el.innerHTML = `<span class="letter-big" style="color:${color}">${big}</span><span class="letter-who">${who}</span>
      <span class="letter-state">${state}</span>
      <button class="sm" data-a="ccw">&#8634; 90&deg;</button>
      <button class="sm" data-a="cw">&#8635; 90&deg;</button>
      <button class="sm" data-a="mirror">Mirror</button>
      <button class="sm" data-a="reset">Reset</button>`;
    el.querySelectorAll("button").forEach((b) => b.onclick = () => changeLetters({ target, action: b.dataset.a }));
    box.appendChild(el);
  };
  letterCfg.letters.forEach((item, i) =>
    row(i, item.letter, ROBOT_COLORS[i], ROBOT_LABELS[i], `${item.rotation}&deg;${item.mirror ? ", mirrored" : ""}`));
  row("all", "&#8727;", "var(--muted)", "All three", "");
  if ($("heading")) $("heading").value = String(letterCfg.heading);
}

function handleClientLetters(body) {
  if (body.heading !== undefined) letterCfg.heading = body.heading;
  if (body.target !== undefined && body.action) {
    const applyAction = (item) => {
      if (body.action === "cw") item.rotation = (item.rotation + 90) % 360;
      if (body.action === "ccw") item.rotation = (item.rotation + 270) % 360;
      if (body.action === "mirror") item.mirror = !item.mirror;
      if (body.action === "reset") { item.rotation = 0; item.mirror = false; }
    };
    if (body.target === "all") {
      letterCfg.letters.forEach(applyAction);
    } else if (letterCfg.letters[body.target]) {
      applyAction(letterCfg.letters[body.target]);
    }
  }
  renderLetters();
  if (state.running === "neu") {
    clientRobots.forEach((r, i) => {
      const l = letterCfg.letters[i];
      if (l) r.matrix = makeMatrix(l.letter, r.baseColor, l.rotation, l.mirror);
    });
    updateTelemetry({ robots: clientRobots });
  }
}

async function changeLetters(body) {
  if (clientMode) {
    handleClientLetters(body);
    return;
  }
  try {
    const r = await fetch("/api/letters", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (r.ok) {
      letterCfg = await r.json();
      renderLetters();
      return;
    }
  } catch (e) {}
  handleClientLetters(body);
}
if ($("heading")) $("heading").onchange = (e) => changeLetters({ heading: Number(e.target.value) });

// ==========================================
// 10. Web Bluetooth API Driver & Server Setup
// ==========================================
const BLE_SERVICES = {
  antiDosService: "00020001-574f-4f20-5370-6865726f2121",
  antiDosChar:    "00020005-574f-4f20-5370-6865726f2121",
  apiService:     "00010001-574f-4f20-5370-6865726f2121",
  apiChar:        "00010002-574f-4f20-5370-6865726f2121"
};

function buildSpheroPacket(did, cid, data = [], proc = 2) {
  const flags = 0x3a;
  const tid = 0x12;
  const sid = 0x01;
  const seq = (bleSeq++) % 255;
  const payload = [flags, tid, sid, did, cid, seq, ...data];
  let sum = 0;
  for (const b of payload) sum += b;
  const chk = (0xff - (sum & 0xff)) & 0xff;

  const escaped = [0x8d];
  for (const b of [...payload, chk]) {
    if (b === 0xab) escaped.push(0xab, 0x23);
    else if (b === 0x8d) escaped.push(0xab, 0x05);
    else if (b === 0xd8) escaped.push(0xab, 0x50);
    else escaped.push(b);
  }
  escaped.push(0xd8);
  return new Uint8Array(escaped);
}

async function bleSendPacket(packet) {
  if (!bleApiChar) return;
  try {
    await bleApiChar.writeValueWithoutResponse(packet);
  } catch (err) {
    try {
      await bleApiChar.writeValue(packet);
    } catch (e) {
      console.warn("BLE packet write note:", e);
    }
  }
}

async function bleDrive(speed, heading) {
  const h = Math.round(heading) % 360;
  const s = Math.min(255, Math.max(0, Math.round(speed * 2.55)));
  const packet = buildSpheroPacket(0x16, 0x07, [s, (h >> 8) & 0xff, h & 0xff, 0]);
  await bleSendPacket(packet);
}

async function bleSetMainColor(r, g, b) {
  const packet = buildSpheroPacket(0x1a, 0x1c, [0x07, r, g, b]);
  await bleSendPacket(packet);
}

async function bleSetMatrixLetter(char, r = 0, g = 200, b = 255) {
  const packet = buildSpheroPacket(0x1a, 0x42, [r, g, b, char.charCodeAt(0)]);
  await bleSendPacket(packet);
}

async function bleSetMatrixColor(r, g, b) {
  const packet = buildSpheroPacket(0x1a, 0x2f, [r, g, b]);
  await bleSendPacket(packet);
}

async function connectWebBluetooth() {
  if (!navigator.bluetooth) {
    alert(
      "Web Bluetooth is not supported in this browser!\n\n" +
      "• On Android: Open this page in Google Chrome or Microsoft Edge.\n" +
      "• On iPhone / iPad: Apple blocks Web Bluetooth in Safari. Install the free 'Bluefy' or 'WebBLE' browser from the App Store and open this website there!\n\n" +
      "Alternatively, enter your Arch Linux laptop IP below to connect over Wi-Fi."
    );
    return;
  }

  addLine("Scanning for Sphero BOLT over Bluetooth...");
  try {
    bleDevice = await navigator.bluetooth.requestDevice({
      filters: [{ namePrefix: "SB-" }],
      optionalServices: [
        BLE_SERVICES.antiDosService,
        BLE_SERVICES.apiService
      ]
    });

    addLine(`Found ${bleDevice.name}. Connecting GATT...`);
    const server = await bleDevice.gatt.connect();

    try {
      const antiDosService = await server.getPrimaryService(BLE_SERVICES.antiDosService);
      const antiDosChar = await antiDosService.getCharacteristic(BLE_SERVICES.antiDosChar);
      const enc = new TextEncoder();
      await antiDosChar.writeValue(enc.encode("usetheforce...band"));
    } catch (dosErr) {
      console.warn("Handshake note:", dosErr);
    }

    const apiService = await server.getPrimaryService(BLE_SERVICES.apiService);
    bleApiChar = await apiService.getCharacteristic(BLE_SERVICES.apiChar);

    online = true;
    connectedTarget = bleDevice.name;
    renderStatus();
    closeBluetoothModal();
    playVictory();
    addLine(`=== Connected to ${bleDevice.name} via Phone Bluetooth! ===`);
    addLine("Ready! Use the Virtual Joystick or launch any game to control your robot.");

    await bleSetMainColor(0, 255, 0);
    await bleSetMatrixColor(0, 255, 0);

    bleDevice.addEventListener("gattserverdisconnected", () => {
      online = false;
      connectedTarget = null;
      bleApiChar = null;
      renderStatus();
      addLine(`[DISCONNECTED] Lost connection to ${bleDevice.name}`);
    });
  } catch (err) {
    if (err.name !== "NotFoundError") {
      addLine(`Bluetooth connection error: ${err.message || err}`);
    }
  }
}

function openBluetoothModal() {
  const modal = $("modal-bluetooth");
  if (modal) modal.hidden = false;
}

function closeBluetoothModal() {
  const modal = $("modal-bluetooth");
  if (modal) modal.hidden = true;
}

if ($("btn-bluetooth")) $("btn-bluetooth").onclick = openBluetoothModal;
if ($("status")) {
  $("status").onclick = () => {
    if (!online) openBluetoothModal();
  };
}
if ($("modal-close-btn")) $("modal-close-btn").onclick = closeBluetoothModal;
if ($("modal-bluetooth")) {
  $("modal-bluetooth").onclick = (e) => {
    if (e.target === $("modal-bluetooth")) closeBluetoothModal();
  };
}
if ($("btn-scan-ble")) $("btn-scan-ble").onclick = connectWebBluetooth;

// ==========================================
// 11. QR Code & Device Management (Arch Host)
// ==========================================
let connectedClients = [];

async function initQRCode() {
  const box = $("qrcode-box");
  const urlLabel = $("qr-url-text");
  if (!box) return;

  let targetUrl = window.location.href;
  try {
    const res = await fetch("/api/info");
    if (res.ok) {
      const info = await res.json();
      if (info.url) targetUrl = info.url;
    }
  } catch (e) {}

  if (urlLabel) urlLabel.textContent = targetUrl;

  box.innerHTML = "";
  if (typeof QRCode !== "undefined") {
    new QRCode(box, {
      text: targetUrl,
      width: 175,
      height: 175,
      colorDark: "#0b0e14",
      colorLight: "#ffffff",
      correctLevel: QRCode.CorrectLevel.M,
    });
  }
}

function renderClients(clients, maxSlots = 3) {
  connectedClients = clients || [];
  const badge = $("slots-badge");
  const list = $("connected-devices-list");
  if (badge) {
    const unit = currentLang === "hu" ? "telefon" : "phones";
    badge.textContent = `${connectedClients.length} / ${maxSlots} ${unit}`;
  }
  if (!list) return;

  if (connectedClients.length === 0) {
    list.innerHTML = `<div style="color:var(--muted); font-size:0.85rem; text-align:center; padding:8px 0;">${t("no_devices_msg")}</div>`;
    return;
  }

  list.innerHTML = "";
  connectedClients.forEach((c, idx) => {
    const row = document.createElement("div");
    row.className = "device-row";

    let idleStr = "";
    if (c.idle < 10) {
      idleStr = t("active_now");
    } else if (c.idle < 60) {
      idleStr = `${c.idle} ${t("idle_secs")}`;
    } else {
      idleStr = `${Math.floor(c.idle / 60)} ${t("idle_mins")}`;
    }

    const nameLabel = currentLang === "hu" ? `${idx + 1}. Telefon` : `Phone ${idx + 1}`;
    row.innerHTML = `
      <div class="device-info">
        <span class="dot"></span>
        <div>
          <b>${nameLabel}</b> <span style="font-family:var(--font-mono); color:var(--muted); font-size:0.8rem;">(${c.ip})</span>
          <div class="device-time">${idleStr}</div>
        </div>
      </div>
      <button class="stop sm" data-kick="${c.id}" style="padding:3px 8px; font-size:0.75rem;">${t("disconnect_btn")}</button>
    `;
    const btn = row.querySelector("button[data-kick]");
    if (btn) {
      btn.onclick = () => kickClient(c.id);
    }
    list.appendChild(row);
  });
}

function kickClient(clientId) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "kick", client_id: clientId }));
  } else {
    fetch(`/api/clients/kick/${clientId}`, { method: "POST" }).catch(() => {});
  }
}

function showTimeoutModal(message) {
  const m = $("modal-timeout");
  if (m) {
    if (message) {
      const desc = m.querySelector("[data-i18n='timeout_modal_desc']");
      if (desc) desc.textContent = message;
    }
    m.hidden = false;
  }
}

function showMaxClientsModal(message) {
  const m = $("modal-max-clients");
  if (m) {
    if (message) {
      const desc = m.querySelector("[data-i18n='max_modal_desc']");
      if (desc) desc.textContent = message;
    }
    m.hidden = false;
  }
}

function closeMaxClientsModal() {
  const m = $("modal-max-clients");
  if (m) m.hidden = true;
}

function reconnectClient() {
  const m = $("modal-timeout");
  if (m) m.hidden = true;
  connect();
}

// Activity tracker (resets last_active and pings server)
let lastActivityTime = Date.now();
function markUserActive() {
  const now = Date.now();
  if (now - lastActivityTime > 15000) {
    lastActivityTime = now;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "ping" }));
    }
  }
}

window.addEventListener("pointerdown", markUserActive);
window.addEventListener("keydown", markUserActive);
setInterval(markUserActive, 25000);

function handleWsMessage(e) {
  const msg = JSON.parse(e.data);
  if (msg.type === "status") {
    state = msg;
    renderStatus();
  } else if (msg.type === "log") {
    addLine(msg.line);
  } else if (msg.type === "letters") {
    letterCfg = msg.config;
    renderLetters();
  } else if (msg.type === "game") {
    gameState = msg.state;
    renderGame();
    renderParty();
  } else if (msg.type === "telemetry") {
    updateTelemetry(msg.data);
  } else if (msg.type === "history") {
    if ($("log")) $("log").innerHTML = "";
    msg.lines.forEach((l) => addLine(l.line));
  } else if (msg.type === "clients") {
    renderClients(msg.clients, msg.max || 3);
  } else if (msg.type === "error" && msg.code === "MAX_CLIENTS") {
    showMaxClientsModal(msg.message);
  } else if (msg.type === "timeout" || msg.type === "kicked") {
    showTimeoutModal(msg.message);
  }
}

function connectCustomServer(hostUrl) {
  let target = hostUrl.trim().replace(/^https?:\/\//, "").replace(/^wss?:\/\//, "").replace(/\/+$/, "").replace(/\/ws$/, "");
  if (!target) return;
  const wsUrl = `ws://${target}/ws`;
  addLine(`Connecting to Arch server at ${wsUrl}...`);
  if (ws) {
    try { ws.close(); } catch (e) {}
  }
  try {
    ws = new WebSocket(wsUrl);
    ws.onopen = () => {
      online = true;
      connectedTarget = `Arch (${target})`;
      renderStatus();
      closeBluetoothModal();
      playVictory();
      addLine(`=== Connected to Arch Linux server: ${target} ===`);
    };
    ws.onerror = () => {
      alert(`Could not connect to ${wsUrl}. Make sure python server is running with --host 0.0.0.0 and your phone is on the same Wi-Fi!`);
      addLine(`Connection to ${wsUrl} failed.`);
    };
    ws.onclose = () => {
      online = false;
      connectedTarget = null;
      renderStatus();
    };
    ws.onmessage = handleWsMessage;
  } catch (err) {
    alert(`Invalid server address: ${err.message || err}`);
  }
}

if ($("btn-connect-server")) {
  $("btn-connect-server").onclick = () => {
    const input = $("input-server-url");
    if (input && input.value.trim()) {
      connectCustomServer(input.value.trim());
    }
  };
}

// Connect to backend WebSocket or enable client mode
let wsRetry = 0;
function connect() {
  const isStatic = location.protocol === "file:" ||
    location.hostname.endsWith("github.io") ||
    location.hostname.endsWith("vercel.app") ||
    (location.hostname === "localhost" && location.port === "");

  if (isStatic) {
    enableClientMode();
    return;
  }

  try {
    ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
    ws.onopen = () => {
      online = true;
      connectedTarget = "Arch Server";
      wsRetry = 0;
      renderStatus();
      addLine("=== Connected to Arch Linux server ===");
    };
    ws.onclose = () => {
      online = false;
      connectedTarget = null;
      wsRetry++;
      renderStatus();
      if (wsRetry > 2) {
        enableClientMode();
      } else {
        setTimeout(connect, 1500);
      }
    };
    ws.onerror = () => {
      if (wsRetry > 1) enableClientMode();
    };
    ws.onmessage = handleWsMessage;
  } catch (e) {
    enableClientMode();
  }
}

// Initial setup
renderLetters();
renderGame();
initClientRobots(3);
setLanguage(currentLang);
initQRCode();
connect();
