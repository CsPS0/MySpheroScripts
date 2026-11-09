/**
 * Sphero BOLT Interactive Control Suite
 * Standalone browser simulation & real-time WebSocket controller.
 */

// Automatically unregister stale ServiceWorkers from other localhost projects
if (typeof navigator !== "undefined" && "serviceWorker" in navigator &&
    (location.hostname === "localhost" || location.hostname === "127.0.0.1")) {
  navigator.serviceWorker.getRegistrations().then((registrations) => {
    for (const reg of registrations) {
      reg.unregister();
    }
  }).catch(() => {});
}

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

// localStorage can throw (blocked storage, some private modes): never let it break the page
const store = {
  get(key) { try { return window.localStorage.getItem(key); } catch (e) { return null; } },
  set(key, value) { try { window.localStorage.setItem(key, value); } catch (e) {} },
};

// ==========================================
// Bilingual Translation (HU default, EN secondary)
// ==========================================
let currentLang = store.get("sphero_lang") || "hu";
try {
  const urlLang = new URLSearchParams(window.location.search).get("lang");
  if (urlLang === "en" || urlLang === "hu") {
    currentLang = urlLang;
    store.set("sphero_lang", urlLang);
  }
} catch (e) {}

const I18N = {
  hu: {
    status_offline: "Offline",
    status_connected: "Csatlakozva",
    status_running: "Fut",
    status_sim: "Szimuláció",
    status_hint: "Kapcsolat állapota. Offline állapotban kattints a csatlakozáshoz.",
    connect_btn: "Csatlakozás",
    log_btn: "Napló",
    log_title: "Rendszernapló megnyitása",
    theme_title: "Téma váltása (Krém / Sötét)",
    sound_title: "Hang be/ki",
    admin_btn: "Beállítások",
    stop: "Leállítás",

    robots_unit: "robot",
    phones_unit: "telefon",
    low_batt: "{n} alacsony akku",

    arena_title: "Aréna",
    arena_trails: "Nyomvonal",
    arena_clear: "Törlés",
    arena_stats: "{n} robot · 1 négyzet = 20 cm · koppints egy robotra a rázáshoz",

    phones_title: "Telefonos irányítás",
    qr_step_1: "Olvasd be a QR-kódot a telefon kamerájával.",
    qr_step_2: "A telefon kap egy számot: 1 piros, 2 zöld, 3 kék.",
    qr_step_3: "Indítsd el a Vezetést, és a botkormánnyal irányíthatsz.",
    no_devices_msg: "Még nincs telefon csatlakoztatva.",
    drive_hint: "Telefon csatlakozott, de a Vezetés nem fut.",
    btn_start_drive: "Vezetés indítása",
    disconnect_btn: "Bontás",
    active_now: "aktív",
    idle_secs: "{n} mp tétlen",
    idle_mins: "{n} perce tétlen",
    phone_n: "{n}. telefon",

    controller_wait: "Várj, amíg a bemutató vezetője elindítja a Vezetést.",
    assigned_title: "Te irányítod: {n}. robot",
    assigned_desc: "A robot kijelzőjén a(z) {n} szám világít, {color} színnel.",

    tab_drive: "Vezetés",
    tab_shows: "Műsorok",
    tab_games: "Játékok",
    tab_docs: "Útmutató",
    docs_btn_title: "Használati útmutató és dokumentáció megnyitása",
    docs_standalone_title: "1. Önálló weboldal (Telepítés nélkül)",
    docs_standalone_desc: "A weboldal szerver nélkül, közvetlenül a böngészőben is működik (GitHub Pages vagy az index.html megnyitásával).",
    docs_standalone_1: "Beépített 60 FPS fizikai és 8x8 LED mátrix szimulátor minden műsorhoz (Neumann, Szinkrontánc, Bolyongás) és játékhoz.",
    docs_standalone_2: "Közvetlen Web Bluetooth kapcsolat: kattints a felső sávban a Csatlakozás gombra (Chrome / Edge / Bluefy böngészőben) valódi Sphero BOLT irányításához.",
    docs_open_live: "Élő webes verzió megnyitása",
    docs_zip_title: "2. Letöltés egyetlen ZIP csomagban",
    docs_zip_desc: "Git fiók és parancssor nélkül is letöltheted a teljes csomagot egyetlen tömörített fájlban (helyi szerverről vagy GitHubról).",
    docs_zip_1: "Töltsd le és csomagold ki a ZIP fájlt egy tetszőleges mappába.",
    docs_zip_2: "Önálló módhoz nyisd meg az index.html fájlt, vagy teljes szerver módhoz indítsd el a start.bat (Windows) / ./start.sh (Linux/macOS) fájlt.",
    docs_local_zip: "Helyi ZIP csomag letöltése",
    docs_download_zip: "GitHub ZIP letöltése",
    docs_open_repo: "GitHub adattár",
    docs_git_title: "3. Git klónozás & Helyi Flotta Szerver (15 robotig)",
    docs_git_desc: "Több robot egyidejű Bluetooth vezérléséhez, QR-kódos telefonos irányításhoz és távoli Admin belépéshez futtasd a Python szervert:",
    docs_git_1: "Nyisd meg a http://localhost:8080 (vagy http://localhost:8080/docs) címet; a diákok a QR-kód beolvasásával csatlakozhatnak (1: Piros, 2: Zöld, 3: Kék robot).",
    docs_git_2: "Távoli telefonos vezérléshez használd a felső sáv Admin gombját (alapértelmezett jelszó: admin1234 vagy ADMIN_PASSWORD környezeti változó).",
    docs_local_guide_title: "4. Helyi Dokumentáció & Bemutató Útmutató (Offline is elérhető)",
    docs_local_guide_desc: "Minden műsor, játék és beállítás részletes leírása közvetlenül a helyi felületen, internetkapcsolat nélkül is:",
    docs_shows_head: "Műsorok (Shows)",
    docs_shows_neu: "Neumann-formáció (7 robot): N-E-U-M-A-N-N kirajzolása egy sorban. Iránytűs észak-igazítás vagy kézi célzás, 90°-os betűforgatás, tükrözés és 15°-os robotirány-finomhangolás.",
    docs_shows_dance: "Szinkrontánc (1–15 robot): Számozott sorba állítás (1..15), kihagyható robotok, szivárványhullám, ütközéses roham (robbanás hanggal), szóló táncok és hazatérés.",
    docs_shows_roam: "Önálló bolyongás (1–15 robot): Minden robot 25 cm-es körzetben kóborol rugalmas ütközésfizikával, majd Leállításkor visszatér a helyére.",
    docs_games_head: "Vezetés & Minijátékok",
    docs_games_drive: "Botkormányos Vezetés (1–3 robot): Irányítás egérrel, érintéssel, WASD/nyilakkal vagy 3 QR-kódos telefonnal, -180°..+180° kalibrálással.",
    docs_games_ttt: "Amőba / Tic-Tac-Toe (9 robot): 3x3-as rács számozással, fizikai rázás/érintés érzékeléssel vagy webes kattintással.",
    docs_games_party: "Memóriajáték (9), Vakondvadászat (9), Forró krumpli (1) & Kő-papír-olló (2): Menthető sebesség, 3x3/véletlen elrendezés és finom kóborlás (Gentle drift).",
    docs_view_usage: "USAGE.md megnyitása helyben",
    docs_view_readme: "README.md megnyitása helyben",
    hud_heading: "Irány",
    hud_throttle: "Sebesség",
    steer_robot: "Melyik robotot vezeted?",
    drive_controls_hint: "Húzd a botkormányt ujjal vagy egérrel. Billentyűzeten: W A S D vagy nyilak.",
    calib_title: "Kalibrálás",
    calib_hint: "Állj a robot mögé, és húzd a csúszkát, amíg a nyíl és a fehér fény tőled előre mutat. Utána a botkormány felfelé mindig előre visz.",
    calib_off_hint: "A kalibrálás a Vezetés futása közben működik, mert akkor csatlakozik a robot.",
    calib_reset: "Nullázás",

    target_heading: "Célirány",
    letters_adjust: "Betűk forgatása és tükrözése",
    align_label: "Igazítás",
    admin_login_btn: "Admin",
    admin_login_title: "Admin belépés",
    admin_login_desc: "Jelszóval ez a telefon a teljes vezérlőpultot kapja, mint a laptop.",
    admin_password: "Jelszó",
    admin_login_submit: "Belépés",
    admin_login_ok: "Belépve adminként",
    admin_login_wrong: "Hibás jelszó.",
    admin_login_failed: "Nem sikerült csatlakozni a szerverhez.",
    admin_logout: "Kijelentkezés (ez a telefon)",
    admin_required: "Ehhez admin belépés kell.",
    dance_robots: "Robotok a táncban",
    dance_robots_hint: "Koppints egy számra, hogy kihagyd azt a robotot. A foglalt (máshoz csatlakozott) robotokat a tánc magától kihagyja.",
    dance_in: "Táncol. Koppints a kihagyáshoz.",
    dance_out: "Kihagyva. Koppints a visszavételhez.",
    dance_busy: "Foglalt vagy kikapcsolt: most kimarad.",
    dance_lost: "Megszakadt a kapcsolat: kimarad.",
    dance_go: "Mehet! (sorban állnak)",
    dance_next: "Következő rész",
    dance_phase_connecting: "Csatlakozás...",
    dance_phase_setup: "Állítsd sorba őket a számuk szerint, balról jobbra, kék fénnyel feléd",
    dance_phase_rainbow: "Szivárvány hullám",
    dance_phase_rush: "Száguldás",
    dance_phase_chars: "Betűk és tánc",
    dance_phase_home: "Vissza a helyükre",
    dance_phase_finale: "Finálé",
    dance_phase_done: "Vége",
    hand_off: "Kézi forgatás",
    hand_on: "Kézi forgatás BE: forgasd a robotokat",
    hand_off_hint: "Bekapcsolva a robotok elengednek: kézzel forgathatod őket, és ott maradnak. Kikapcsoláskor megtartják az irányt.",
    hand_on_hint: "Az automatikus forgatás le van tiltva. Forgasd a robotokat kézzel (kék hátsó fény = hátul), majd kapcsold ki: megtartják az irányt.",
    align_compass: "Iránytű: mind északra",
    align_aim: "Kézi célzás",
    align_compass_hint: "Indításkor minden robot megkeresi az északot (pár mp-ig forog), és mind ugyanarra néz. A Célirány északhoz képest értendő.",
    align_aim_hint: "Indításkor 10 mp célzás: fordítsd a robotokat úgy, hogy a kék hátsó fény feléd nézzen. Váltás után indítsd újra a műsort.",
    letters_each: "Betűk egyenként",
    letters_each_hint: "Betű: a kijelzőn forgat 90°-kal. Robot: az egész robotot fordítja 15°-kal, ha ferdén áll.",
    letter_word: "Betű",
    robot_word: "Robot",
    letter_ccw: "Betű forgatása balra 90°",
    letter_cw: "Betű forgatása jobbra 90°",
    robot_left: "Robot fordítása balra 15°",
    robot_right: "Robot fordítása jobbra 15°",
    start_x: "Indítás: {name}",
    restart_x: "Újraindítás: {name}",
    running_label: "fut",
    robots_needed: "{n} robot",

    ttt_same_layout: "Új játék",
    ttt_renumber: "Újraszámozás",
    ttt_start: "Számozás kész",
    ttt_idle: "Indítsd el az Amőbát a játékhoz.",
    ttt_numbering: "Számozás: rázd meg a(z) {n}. mező labdáját ({done}/9 kész).",
    ttt_draw: "Döntetlen! Új játékhoz nyomd meg az Új játék gombot.",
    ttt_win: "{p} nyert! Új játékhoz nyomd meg az Új játék gombot.",
    ttt_turn: "Következik:",
    ttt_shake_next: "rázd meg",
    ttt_tap: "koppints",
    party_round: "Új kör",
    party_idle: "Nyomd meg az Indítás gombot a kezdéshez.",
    party_speed: "Sebesség",
    party_speed_slow: "Lassú",
    party_speed_normal: "Normál",
    party_speed_fast: "Gyors",
    party_speed_insane: "Őrült",
    party_layout: "Elrendezés",
    party_layout_3x3: "3x3 Rács",
    party_layout_random: "Véletlenszerű",
    party_drift: "Finom mozgás",
    party_drift_on: "Be (kóborlás)",
    party_drift_off: "Ki",
    party_save_prefs: "Beállítások mentése",
    party_prefs_saved: "Elmentve! (Megmarad új körben is)",

    fleet_title: "Robotok",
    btn_refresh_pool: "Újrakeresés",
    btn_refresh_title: "Robotok újrakeresése Bluetooth-on",
    btn_identify_all: "Mind azonosítása",
    btn_identify_all_title: "Minden robot kijelzi a saját számát",
    fleet_tap_hint: "Koppints egy robotra: kijelzi a számát.",
    fleet_empty: "Nincs robot. Kapcsold be és rázd fel őket, majd nyomd meg az Újrakeresés gombot.",
    battery_unknown: "Az akkuszint azonosításkor frissül",
    identify_title: "Azonosítás: a robot kijelzi a(z) {n} számot",
    identify_sent: "Azonosítás: {n}. robot",
    refresh_started: "Robotok keresése...",
    refresh_done: "{n} robot megtalálva",
    controlled_by: "{n}. telefon irányítja",

    console_title: "Rendszernapló",
    btn_clear: "Törlés",

    admin_modal_title: "Beállítások",
    admin_auto_map_label: "Aréna kiemelése telefon csatlakozásakor",
    admin_auto_map_desc: "Amikor egy telefon beolvassa a QR-kódot, a laptop az Aréna térképre ugrik.",
    admin_low_power_label: "Kímélő mód (alacsony teljesítményű gépekhez)",
    admin_low_power_desc: "Csökkenti a grafikai terhelést régebbi laptopokon vagy Raspberry Pi-n (árnyékok kikapcsolása, kímélő képfrissítés).",
    admin_controllers_label: "Telefonos irányítók: max 3",
    slot_1: "1. telefon: piros",
    slot_2: "2. telefon: zöld",
    slot_3: "3. telefon: kék",
    host_rules_note: "5 perc tétlenség után a telefon kapcsolata bont, hogy más is sorra kerülhessen.",
    btn_close: "Kész",

    ble_modal_title: "Csatlakozás",
    ble_step_1: "Kapcsold be a Bluetooth-t.",
    ble_step_2: "Rázd meg a robotot, amíg a kijelzője felvillan.",
    ble_step_3: "Csatlakozz a böngészőből, vagy add meg a laptop címét.",
    btn_pair_ble: "Robot keresése Bluetooth-on",
    or_connect_server: "vagy csatlakozás a laptophoz",
    btn_connect_server: "Csatlakozás",

    timeout_modal_title: "Kapcsolat bontva",
    timeout_modal_desc: "5 perc tétlenség után a kapcsolat bontott, hogy más is kipróbálhassa.",
    btn_reconnect: "Újracsatlakozás",
    max_modal_title: "Minden hely foglalt",
    max_modal_desc: "Mind a 3 irányítói hely foglalt. Várj egy kicsit, amíg felszabadul egy!",
    btn_retry: "Újrapróbálás",
    btn_understood: "Rendben",

    mirror: "Tükrözés",
    reset: "Alaphelyzet",
    all_three: "Mind",
    mirrored: "tükrözve",
    started_x: "Elindítva: {name}",
    offline_sim: "Nincs szerver: a programok szimulációban futnak.",
  },
  en: {
    status_offline: "Offline",
    status_connected: "Connected",
    status_running: "Running",
    status_sim: "Simulation",
    status_hint: "Connection status. Click to connect while offline.",
    connect_btn: "Connect",
    log_btn: "Log",
    log_title: "Open system log",
    theme_title: "Switch theme (Cream / Dark)",
    sound_title: "Sound on/off",
    admin_btn: "Settings",
    stop: "Stop",

    robots_unit: "robots",
    phones_unit: "phones",
    low_batt: "{n} low battery",

    arena_title: "Arena",
    arena_trails: "Trails",
    arena_clear: "Clear",
    arena_stats: "{n} robots · 1 square = 20 cm · tap a robot to shake it",

    phones_title: "Phone control",
    qr_step_1: "Scan the QR code with your phone camera.",
    qr_step_2: "Each phone gets a number: 1 red, 2 green, 3 blue.",
    qr_step_3: "Start Drive and steer with the joystick.",
    no_devices_msg: "No phones connected yet.",
    drive_hint: "A phone is connected but Drive is not running.",
    btn_start_drive: "Start Drive",
    disconnect_btn: "Disconnect",
    active_now: "active",
    idle_secs: "{n}s idle",
    idle_mins: "{n} min idle",
    phone_n: "Phone {n}",

    controller_wait: "Wait for the host to start Drive.",
    assigned_title: "You control robot {n}",
    assigned_desc: "Robot {n} shows the number {n} in {color} on its display.",

    tab_drive: "Drive",
    tab_shows: "Shows",
    tab_games: "Games",
    tab_docs: "Guide",
    docs_btn_title: "Open user guide and local documentation",
    docs_standalone_title: "1. Standalone Website (No Installation Needed)",
    docs_standalone_desc: "The dashboard runs directly in the browser without a backend server (via GitHub Pages or opening index.html locally).",
    docs_standalone_1: "Built-in 60 FPS 2D physics & 8x8 LED matrix simulator for all shows (Neumann, Dance, Roam) and minigames.",
    docs_standalone_2: "Direct Web Bluetooth pairing: click Connect in the top bar (in Chrome, Edge, or Bluefy on iOS) to drive a physical Sphero BOLT directly.",
    docs_open_live: "Open Live Web Version",
    docs_zip_title: "2. Download in One Zipped Package",
    docs_zip_desc: "Download the entire suite as a single .zip archive without needing a Git account or command-line tools (from the local server or GitHub).",
    docs_zip_1: "Download and extract the ZIP archive into any folder on your computer.",
    docs_zip_2: "Open index.html directly for standalone browser mode, or launch start.bat (Windows) / ./start.sh (Linux/macOS) for the full fleet server.",
    docs_local_zip: "Download Local ZIP Package",
    docs_download_zip: "Download GitHub ZIP",
    docs_open_repo: "GitHub Repository",
    docs_git_title: "3. Git Clone & Local Fleet Server (Up to 15 Robots)",
    docs_git_desc: "For multi-robot Bluetooth fleet control, QR-code phone controllers, and remote Admin login, run the local Python server:",
    docs_git_1: "Open http://localhost:8080 (or http://localhost:8080/docs); students scan the QR code with their phone camera to join (Slot 1: Red, 2: Green, 3: Blue).",
    docs_git_2: "Use the Admin button in the top bar for remote host control from a phone (default password: admin1234 or set ADMIN_PASSWORD).",
    docs_local_guide_title: "4. Local Documentation & Presentation Guide (Offline-Ready)",
    docs_local_guide_desc: "Complete reference for all shows, minigames, and controls directly inside the local dashboard without internet access:",
    docs_shows_head: "Shows & Choreography",
    docs_shows_neu: "Neumann Formation (7 robots): Displays N-E-U-M-A-N-N in a single row. Supports Compass North auto-alignment or Manual Aim, 90° letter rotation, mirror toggle, and 15° robot yaw tuning.",
    docs_shows_dance: "Synchronized Dance Show (1–15 robots): Numbered horizontal line (1..15), tap numbers to skip robots, Rainbow Wave, Collision Rush (with explosion sound), Character Solos, and Return Home.",
    docs_shows_roam: "Autonomous Roam (1–15 robots): Each robot wanders within a 25 cm home radius with elastic collision physics, then returns home on Stop.",
    docs_games_head: "Driving & Minigames",
    docs_games_drive: "Joystick Drive (1–3 robots): Steer via mouse/touch joystick, WASD/Arrow keys, or up to 3 QR-connected phones, with -180°..+180° heading calibration.",
    docs_games_ttt: "Tic-Tac-Toe (9 robots): 3x3 grid with ball numbering and physical tap/shake detection or web grid clicks.",
    docs_games_party: "Memory / Simon (9), Whack-a-Mole (9), Hot Potato (1) & Rock-Paper-Scissors (2): Persistent Speed, 3x3/Random layout, and Gentle drift wander settings.",
    docs_view_usage: "Open USAGE.md Locally",
    docs_view_readme: "Open README.md Locally",
    hud_heading: "Heading",
    hud_throttle: "Speed",
    steer_robot: "Which robot do you drive?",
    drive_controls_hint: "Drag the joystick with your finger or mouse. Keyboard: W A S D or arrow keys.",
    calib_title: "Calibration",
    calib_hint: "Stand behind the robot and move the slider until the arrow and the white light point straight ahead, away from you. Then pushing the joystick up always drives forward.",
    calib_off_hint: "Calibration works while Drive is running, because that is when the robot is connected.",
    calib_reset: "Reset",

    target_heading: "Heading",
    letters_adjust: "Rotate and mirror letters",
    align_label: "Alignment",
    admin_login_btn: "Admin",
    admin_login_title: "Admin login",
    admin_login_desc: "With the password this phone gets the full dashboard, like the laptop.",
    admin_password: "Password",
    admin_login_submit: "Log in",
    admin_login_ok: "Logged in as admin",
    admin_login_wrong: "Wrong password.",
    admin_login_failed: "Could not reach the server.",
    admin_logout: "Log out (this phone)",
    admin_required: "This needs an admin login.",
    dance_robots: "Robots in the dance",
    dance_robots_hint: "Tap a number to leave that robot out. Busy robots (connected elsewhere) are skipped automatically.",
    dance_in: "Dances. Tap to leave it out.",
    dance_out: "Left out. Tap to take it back.",
    dance_busy: "Busy or switched off: skipped this time.",
    dance_lost: "Connection lost: sits out.",
    dance_go: "Go! (they are lined up)",
    dance_next: "Next part",
    dance_phase_connecting: "Connecting...",
    dance_phase_setup: "Line them up by number, left to right, blue light towards you",
    dance_phase_rainbow: "Rainbow wave",
    dance_phase_rush: "Rush",
    dance_phase_chars: "Characters and dancing",
    dance_phase_home: "Back to their spots",
    dance_phase_finale: "Finale",
    dance_phase_done: "Done",
    hand_off: "Turn by hand",
    hand_on: "Turn by hand ON: turn the robots",
    hand_off_hint: "When on, the robots let go: turn them by hand and they stay there. Switching it off keeps their directions.",
    hand_on_hint: "Automatic turning is off. Turn the robots by hand (blue tail light = back), then switch this off: they keep their directions.",
    align_compass: "Compass: all face north",
    align_aim: "Manual aim",
    align_compass_hint: "At start every robot finds north (it spins for a few seconds) and they all face the same way. The heading is relative to north.",
    align_aim_hint: "At start, 10 s aim: turn the robots so their blue tail light faces you. Restart the show after switching.",
    letters_each: "Letters one by one",
    letters_each_hint: "Letter: turns it on the display by 90°. Robot: turns the whole robot by 15° if it stands crooked.",
    letter_word: "Letter",
    robot_word: "Robot",
    letter_ccw: "Turn letter left 90°",
    letter_cw: "Turn letter right 90°",
    robot_left: "Turn robot left 15°",
    robot_right: "Turn robot right 15°",
    start_x: "Start: {name}",
    restart_x: "Restart: {name}",
    running_label: "running",
    robots_needed: "{n} robots",

    ttt_same_layout: "New game",
    ttt_renumber: "Renumber",
    ttt_start: "Numbering done",
    ttt_idle: "Start Tic-tac-toe to play.",
    ttt_numbering: "Numbering: shake the ball for square {n} ({done} of 9 done).",
    ttt_draw: "Draw! Press New game to play again.",
    ttt_win: "{p} wins! Press New game to play again.",
    ttt_turn: "Turn:",
    ttt_shake_next: "shake",
    ttt_tap: "tap",
    party_round: "New round",
    party_idle: "Press Start to begin.",
    party_speed: "Speed",
    party_speed_slow: "Slow",
    party_speed_normal: "Normal",
    party_speed_fast: "Fast",
    party_speed_insane: "Insane",
    party_layout: "Layout",
    party_layout_3x3: "3x3 Grid",
    party_layout_random: "Random",
    party_drift: "Gentle drift",
    party_drift_on: "On (wander)",
    party_drift_off: "Off",
    party_save_prefs: "Save preferences",
    party_prefs_saved: "Saved! (Retained on new round)",

    fleet_title: "Robots",
    btn_refresh_pool: "Rescan",
    btn_refresh_title: "Rescan robots over Bluetooth",
    btn_identify_all: "Identify all",
    btn_identify_all_title: "Every robot shows its own number",
    fleet_tap_hint: "Tap a robot to show its number.",
    fleet_empty: "No robots found. Switch them on, shake them, then press Rescan.",
    battery_unknown: "Battery level updates when identified",
    identify_title: "Identify: robot shows the number {n}",
    identify_sent: "Identify: robot {n}",
    refresh_started: "Scanning for robots...",
    refresh_done: "{n} robots found",
    controlled_by: "Driven by phone {n}",

    console_title: "System log",
    btn_clear: "Clear",

    admin_modal_title: "Settings",
    admin_auto_map_label: "Highlight the arena when a phone connects",
    admin_auto_map_desc: "When a phone scans the QR code, the laptop jumps to the Arena map.",
    admin_low_power_label: "Eco mode (for low-spec hardware)",
    admin_low_power_desc: "Reduces graphical load on older laptops or Raspberry Pi (disables canvas shadows, limits frame rate).",
    admin_controllers_label: "Phone controllers: max 3",
    slot_1: "Phone 1: red",
    slot_2: "Phone 2: green",
    slot_3: "Phone 3: blue",
    host_rules_note: "After 5 minutes of inactivity a phone is disconnected so someone else can play.",
    btn_close: "Done",

    ble_modal_title: "Connect",
    ble_step_1: "Turn on Bluetooth.",
    ble_step_2: "Shake the robot until its display lights up.",
    ble_step_3: "Connect from the browser, or enter the laptop address.",
    btn_pair_ble: "Find robot over Bluetooth",
    or_connect_server: "or connect to the laptop",
    btn_connect_server: "Connect",

    timeout_modal_title: "Disconnected",
    timeout_modal_desc: "After 5 minutes without activity the connection was closed so others can play.",
    btn_reconnect: "Reconnect",
    max_modal_title: "All slots taken",
    max_modal_desc: "All 3 controller slots are in use. Please wait a moment for one to free up!",
    btn_retry: "Try again",
    btn_understood: "OK",

    mirror: "Mirror",
    reset: "Reset",
    all_three: "All",
    mirrored: "mirrored",
    started_x: "Started: {name}",
    offline_sim: "No server: programs run in simulation.",
  },
};

// Program names and short descriptions shown in the Shows / Games lists.
const PROGRAM_INFO = {
  drive: { kind: "drive", robots: 3,
    hu: ["Vezetés", "Botkormányos irányítás telefonról vagy a laptopról."],
    en: ["Drive", "Joystick control from a phone or the laptop."] },
  neu: { kind: "show", robots: 7,
    hu: ["Neumann felirat", "Az 1-7. robot egy-egy betűt mutat: N E U M A N N. Tedd őket sorban egymás mellé, balról jobbra."],
    en: ["Neumann formation", "Robots 1-7 show one letter each: N E U M A N N. Line them up left to right."] },
  dance: { kind: "show", robots: 15,
    hu: ["Szinkrontánc", "Minden szabad robot sorban (Bluetooth adapterenként max 10, két adapterrel 15): szivárvány hullám forgással, száguldás robbanással ütközéskor, véletlen betűk és tánc, végül haza. Kb. 4 perc."],
    en: ["Dance show", "All free robots in a line (10 per Bluetooth adapter, 15 with two adapters): rainbow wave with turns, a rush with explosions on collisions, random characters and dancing, then home. About 4 min."] },
  roam: { kind: "show", robots: 3,
    hu: ["Önálló bolyongás", "Minden robot a saját 25 cm-es körében járőrözik, amíg le nem állítod."],
    en: ["Autonomous roam", "Each robot wanders inside its own 25 cm circle until you stop it."] },
  tictactoe: { kind: "game", robots: 9,
    hu: ["Amőba", "9 robot 3x3-as rácsban. Rázz meg egy labdát vagy koppints a mezőre. X kezd."],
    en: ["Tic-tac-toe", "9 robots in a 3x3 grid. Shake a ball or tap a square. X starts."] },
  potato: { kind: "game", robots: 1,
    hu: ["Forró krumpli", "Add körbe a labdát, mielőtt felrobban! Egyre gyorsabban villog."],
    en: ["Hot potato", "Pass the ball around before it explodes! It blinks faster and faster."] },
  simon: { kind: "game", robots: 9,
    hu: ["Memóriajáték", "Jegyezd meg a fények sorrendjét, és ismételd meg. Minden szint egy lépéssel hosszabb."],
    en: ["Memory game", "Remember the order of the lights and repeat it. Each level adds a step."] },
  mole: { kind: "game", robots: 9,
    hu: ["Vakondvadászat", "Koppints a zölden világító labdára, mielőtt kialszik! 60 mp."],
    en: ["Whack-a-mole", "Tap the ball that lights up green before it goes dark! 60 s."] },
  rps: { kind: "game", robots: 2,
    hu: ["Kő-papír-olló", "Piros a kék ellen: 3-2-1 után mutatják a választást. 2 nyert körig."],
    en: ["Rock-paper-scissors", "Red vs blue: after 3-2-1 they reveal their pick. First to 2 wins."] },
};

function programTitle(id) {
  const p = PROGRAM_INFO[id];
  return p ? p[currentLang][0] : id;
}

function t(key, vars) {
  let s = (I18N[currentLang] && I18N[currentLang][key]) || I18N.en[key] || key;
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(v);
  return s;
}

function updateSoundButton() {
  const use = $("sound-icon");
  if (use) use.setAttribute("href", soundOn ? "#i-sound" : "#i-mute");
}

function isDarkTheme() {
  const meta = document.querySelector('meta[name="color-scheme"]');
  if (meta && meta.content === "light") return false;
  if (meta && meta.content === "dark") return true;
  return true;
}

function updateThemeButton() {
  const dark = isDarkTheme();
  const use = $("theme-icon");
  if (use) use.setAttribute("href", dark ? "#i-sun" : "#i-moon");
  const brandLogo = $("brand-logo-use");
  if (brandLogo) brandLogo.setAttribute("href", dark ? "#i-sphero-dark" : "#i-sphero-light");
  const fav = $("site-favicon");
  if (fav) fav.href = dark ? "assets/icons/sphero-dark.svg" : "assets/icons/sphero-light.svg";
}

function applyColorScheme(scheme) {
  const meta = document.querySelector('meta[name="color-scheme"]');
  if (meta) meta.content = scheme;
  updateThemeButton();
}

if ($("theme-toggle")) {
  $("theme-toggle").onclick = () => {
    const next = isDarkTheme() ? "light" : "dark";
    store.set("color-scheme", next);
    applyColorScheme(next);
  };
}
window.addEventListener("storage", (e) => {
  if (e.key === "color-scheme") {
    applyColorScheme(e.newValue || "dark");
  }
});
updateThemeButton();

function setLanguage(lang) {
  currentLang = lang;
  store.set("sphero_lang", lang);
  document.documentElement.lang = lang;
  if ($("lang-label")) $("lang-label").textContent = lang.toUpperCase();
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-title]").forEach((el) => { el.title = t(el.dataset.i18nTitle); });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => { el.placeholder = t(el.dataset.i18nPlaceholder); });
  refreshAllViews();
}

if ($("lang-toggle")) $("lang-toggle").onclick = () => setLanguage(currentLang === "hu" ? "en" : "hu");
soundOn = store.get("sphero_sound") !== "off";
if ($("sound-toggle")) $("sound-toggle").onclick = () => {
  soundOn = !soundOn;
  store.set("sphero_sound", soundOn ? "on" : "off");
  updateSoundButton();
};

// ==========================================
// 2. 8x8 LED Matrix Font Engine
// ==========================================
const GLYPHS = {
  "1": ["...XX...", "..XXX...", "...XX...", "...XX...", "...XX...", "...XX...", "...XX...", ".XXXXXX."],
  "2": ["..XXXX..", ".XX..XX.", ".....XX.", "....XX..", "...XX...", "..XX....", ".XX.....", ".XXXXXX."],
  "3": ["..XXXX..", ".XX..XX.", ".....XX.", "...XXX..", ".....XX.", ".....XX.", ".XX..XX.", "..XXXX.."],
  "4": ["....XX..", "...XXX..", "..XXXX..", ".XX.XX..", "XXXXXXX.", "....XX..", "....XX..", "....XX.."],
  "5": [".XXXXXX.", ".XX.....", ".XXXXX..", ".....XX.", ".....XX.", ".....XX.", ".XX..XX.", "..XXXX.."],
  "6": ["..XXXX..", ".XX.....", ".XXXXX..", ".XX..XX.", ".XX..XX.", ".XX..XX.", "..XXXX..", "........"],
  "7": [".XXXXXX.", ".....XX.", "....XX..", "...XX...", "...XX...", "..XX....", "..XX....", "..XX...."],
  "8": ["..XXXX..", ".XX..XX.", ".XX..XX.", "..XXXX..", ".XX..XX.", ".XX..XX.", ".XX..XX.", "..XXXX.."],
  "9": ["..XXXX..", ".XX..XX.", ".XX..XX.", "..XXXXX.", ".....XX.", ".....XX.", "..XXXX..", "........"],
  "10": [".X..XXX.", "XX..X.X.", ".X..X.X.", ".X..X.X.", ".X..X.X.", ".X..X.X.", "XXX.XXX.", "........"],
  "11": [".X...X..", "XX..XX..", ".X...X..", ".X...X..", ".X...X..", ".X...X..", "XXX.XXX.", "........"],
  "12": [".X..XXX.", "XX....X.", ".X..XXX.", ".X..X...", ".X..X...", ".X..X...", "XXX.XXX.", "........"],
  "13": [".X..XXX.", "XX....X.", ".X..XXX.", ".X....X.", ".X....X.", ".X....X.", "XXX.XXX.", "........"],
  "14": [".X..X.X.", "XX..X.X.", ".X..X.X.", ".X..XXX.", ".X....X.", ".X....X.", "XXX...X.", "........"],
  "15": [".X..XXX.", "XX..X...", ".X..XXX.", ".X....X.", ".X....X.", ".X....X.", "XXX.XXX.", "........"],
  "X": ["XX....XX", "XXX..XXX", ".XXXXXX.", "..XXXX..", "..XXXX..", ".XXXXXX.", "XXX..XXX", "XX....XX"],
  "O": ["..XXXX..", ".XXXXXX.", "XXX..XXX", "XX....XX", "XX....XX", "XXX..XXX", ".XXXXXX.", "..XXXX.."],
  "?": ["..XXXX..", ".XX..XX.", ".....XX.", "....XX..", "...XX...", "...XX...", "........", "...XX..."],
  "N": ["XX....XX", "XXX...XX", "XXXX..XX", "XX.XX.XX", "XX.XX.XX", "XX..XXXX", "XX...XXX", "XX....XX"],
  "E": ["XXXXXXXX", "XXXXXXXX", "XX......", "XXXXXX..", "XXXXXX..", "XX......", "XXXXXXXX", "XXXXXXXX"],
  "U": ["XX....XX", "XX....XX", "XX....XX", "XX....XX", "XX....XX", "XX....XX", "XXXXXXXX", ".XXXXXX."],
  "M": ["XX....XX", "XXX..XXX", "XXXXXXXX", "XX.XX.XX", "XX....XX", "XX....XX", "XX....XX", "XX....XX"],
  "A": ["..XXXX..", ".XXXXXX.", "XX....XX", "XX....XX", "XXXXXXXX", "XXXXXXXX", "XX....XX", "XX....XX"],
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
// 3. Control Tabs (Drive / Shows / Games / Docs)
// ==========================================
let activeTab = "drive";
const TAB_FOR = { drive: "drive", shows: "shows", games: "games", docs: "docs", guide: "docs", tictactoe: "games", arena: null };

function switchTab(tabId) {
  const target = TAB_FOR[tabId] === undefined ? tabId : TAB_FOR[tabId];
  if (!target || document.body.classList.contains("role-controller")) return;
  activeTab = target;
  document.querySelectorAll(".tab").forEach((tab) => {
    const isAct = tab.dataset.tab === target;
    tab.classList.toggle("active", isAct);
    tab.setAttribute("aria-selected", isAct ? "true" : "false");
  });
  document.querySelectorAll(".tab-page").forEach((page) => page.classList.toggle("active", page.id === `tab-${target}`));
}
document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});
if ($("btn-docs")) {
  $("btn-docs").addEventListener("click", () => switchTab("docs"));
}

function checkUrlTab() {
  try {
    const params = new URLSearchParams(window.location.search);
    const qTab = (params.get("tab") || "").toLowerCase();
    const hash = (window.location.hash || "").replace(/^#/, "").toLowerCase();
    if (qTab && TAB_FOR[qTab]) {
      switchTab(qTab);
    } else if (hash && TAB_FOR[hash]) {
      switchTab(hash);
    }
  } catch (e) {}
}
window.addEventListener("hashchange", checkUrlTab);
checkUrlTab();

let activeLocalDoc = null;
async function toggleLocalDoc(docName) {
  const viewer = $("local-doc-viewer");
  const codeEl = $("local-doc-content");
  if (!viewer || !codeEl) return;
  if (!viewer.hidden && activeLocalDoc === docName) {
    viewer.hidden = true;
    activeLocalDoc = null;
    return;
  }
  activeLocalDoc = docName;
  viewer.hidden = false;
  codeEl.textContent = "Loading " + docName + "...";
  try {
    const r = await fetch(`/${docName}`);
    if (r.ok) {
      codeEl.textContent = await r.text();
      return;
    }
  } catch (e) {}
  try {
    const r2 = await fetch("/api/docs");
    if (r2.ok) {
      const data = await r2.json();
      const key = docName.toLowerCase().startsWith("usage") ? "usage" : "readme";
      if (data && data[key]) {
        codeEl.textContent = data[key];
        return;
      }
    }
  } catch (e2) {}
  codeEl.textContent = `# ${docName}\n\n` +
    `1. Standalone Web Mode: Open index.html directly in your browser.\n` +
    `2. Local Fleet Server: Run 'python web/server.py --sim' inside sphero-neu/ and open http://localhost:8080\n` +
    `3. Full Markdown Files: Open ${docName} in the repository root folder.`;
}
if ($("btn-view-usage")) {
  $("btn-view-usage").addEventListener("click", () => toggleLocalDoc("USAGE.md"));
}
if ($("btn-view-readme")) {
  $("btn-view-readme").addEventListener("click", () => toggleLocalDoc("README.md"));
}

// ==========================================
// 4. Activity Log (slide-over drawer)
// ==========================================
let unreadLog = 0, unreadErr = false;

function addLine(line) {
  const log = $("log");
  if (!log) return;
  const atBottom = log.scrollHeight - log.scrollTop - log.clientHeight < 40;
  const div = document.createElement("div");
  div.className = "log-line";
  div.textContent = line;
  const isErr = /error|failed|traceback|exception|hiba|sikertelen/i.test(line);
  if (line.startsWith("===")) div.className += " sys";
  else if (isErr) div.className += " err";
  else if (/wins|score|victory|nyert/i.test(line)) div.className += " win";
  log.appendChild(div);
  while (log.childNodes.length > 1000) log.removeChild(log.firstChild);
  if (atBottom) log.scrollTop = log.scrollHeight;

  if (!$("log-drawer").classList.contains("open")) {
    unreadLog++;
    unreadErr = unreadErr || isErr;
    renderLogBadge();
  }
}

function renderLogBadge() {
  const b = $("log-badge");
  if (!b) return;
  b.hidden = unreadLog === 0;
  b.textContent = unreadLog > 99 ? "99+" : String(unreadLog);
  b.classList.toggle("err", unreadErr);
}

function openLog() {
  $("log-drawer").classList.add("open");
  $("log-drawer").setAttribute("aria-hidden", "false");
  $("drawer-backdrop").hidden = false;
  unreadLog = 0; unreadErr = false;
  renderLogBadge();
  const log = $("log");
  log.scrollTop = log.scrollHeight;
}

function closeLog() {
  $("log-drawer").classList.remove("open");
  $("log-drawer").setAttribute("aria-hidden", "true");
  $("drawer-backdrop").hidden = true;
}

$("btn-log").onclick = () => ($("log-drawer").classList.contains("open") ? closeLog() : openLog());
$("close-log").onclick = closeLog;
$("drawer-backdrop").onclick = closeLog;
$("clear-log").onclick = () => { $("log").innerHTML = ""; };

let toastTimer = null;
function toast(msg, isErr = false) {
  const el = $("toast");
  if (!el) return;
  el.textContent = msg;
  el.classList.toggle("err", isErr);
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, 2600);
}

document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  closeLog();
  document.querySelectorAll(".modal-overlay").forEach((m) => {
    if (m.id === "modal-admin-settings" || m.id === "modal-bluetooth") m.hidden = true;
  });
});

// ==========================================
// 5. Global State & Programs
// ==========================================
let programs = [];
let state = { running: null, started: null, last_exit: null };
let ws = null, online = false, clientMode = false;

const DEFAULT_PROGRAMS = Object.keys(PROGRAM_INFO).map((id) => ({ id, title: PROGRAM_INFO[id].en[0] }));

let connectedTarget = null;
let bleDevice = null;
let bleApiChar = null;
let bleSeq = 0;

function renderStatus() {
  const pill = $("status"), text = $("status-text");
  if (!pill || !text) return;
  const isConn = online && (connectedTarget || (ws && ws.readyState === WebSocket.OPEN));
  pill.className = "pill" + (state.running ? " running" : isConn ? " online" : " offline");

  if (state.running) {
    text.textContent = `${t("status_running")}: ${programTitle(state.running)}`;
  } else if (isConn) {
    text.textContent = state.simulation ? `${t("status_connected")} (${t("status_sim")})` : t("status_connected");
  } else if (clientMode) {
    text.textContent = t("status_sim");
  } else {
    text.textContent = t("status_offline");
  }

  const stopBtn = $("global-stop");
  if (stopBtn) stopBtn.disabled = !state.running;
  if ($("btn-bluetooth")) $("btn-bluetooth").hidden = isConn || !clientMode;
  // The arena shows robot positions, which only the simulation reports. With real
  // robots it would stay empty, so it is hidden.
  if ($("panel-arena")) $("panel-arena").hidden = !clientMode && isConn && state.simulation === false;

  const strip = $("running-strip");
  if (strip) {
    strip.hidden = !state.running;
    if (state.running) {
      const secs = state.started ? Math.max(0, Math.round(Date.now() / 1000 - state.started)) : 0;
      const mm = Math.floor(secs / 60), ss = String(secs % 60).padStart(2, "0");
      $("running-text").textContent = `${t("status_running")}: ${programTitle(state.running)} · ${mm}:${ss}`;
    }
  }

  document.querySelectorAll(".tab").forEach((tab) => {
    const id = state.running;
    const runsHere = id && PROGRAM_INFO[id] && (PROGRAM_INFO[id].kind === tab.dataset.tab.replace(/s$/, "")
      || (tab.dataset.tab === "drive" && id === "drive"));
    let dot = tab.querySelector(".run-dot");
    if (runsHere && !dot) {
      dot = document.createElement("span");
      dot.className = "run-dot";
      tab.appendChild(dot);
    } else if (!runsHere && dot) {
      dot.remove();
    }
  });

  renderProgramLists();
  renderControllerWait();
  renderDriveHint();
  renderCalib();
}
setInterval(() => { if (state.running) renderStatus(); }, 1000);

function stopProgram() {
  if (clientMode) {
    clientStop();
  } else {
    fetch("/api/stop", { method: "POST" }).catch(() => clientStop());
  }
}
$("running-stop").onclick = stopProgram;
function stopCurrentProgram() { stopProgram(); }

// ---------- Shows / games option lists ----------
let selectedShow = "neu";
let selectedGame = "tictactoe";

function renderOptionList(boxId, kind, selected, onPick) {
  const box = $(boxId);
  if (!box) return;
  box.innerHTML = "";
  for (const [id, info] of Object.entries(PROGRAM_INFO)) {
    if (info.kind !== kind) continue;
    const [title, desc] = info[currentLang];
    const b = document.createElement("button");
    b.type = "button";
    const running = state.running === id;
    b.className = "option" + (id === selected ? " selected" : "") + (running ? " running" : "");
    b.innerHTML = `<span class="opt-title"></span><span class="opt-desc"></span>`;
    b.querySelector(".opt-title").textContent = title;
    const meta = document.createElement("span");
    meta.className = "opt-meta";
    meta.textContent = running ? t("running_label") : t("robots_needed", { n: info.robots });
    b.querySelector(".opt-title").appendChild(meta);
    b.querySelector(".opt-desc").textContent = desc;
    b.onclick = () => onPick(id);
    b.ondblclick = () => { onPick(id); startProgram(id); };
    box.appendChild(b);
  }
}

function renderProgramLists() {
  renderOptionList("show-list", "show", selectedShow, (id) => { selectedShow = id; renderProgramLists(); });
  renderOptionList("game-list", "game", selectedGame, (id) => { selectedGame = id; renderProgramLists(); });

  if ($("neu-settings")) $("neu-settings").hidden = selectedShow !== "neu";
  if ($("dance-settings")) $("dance-settings").hidden = selectedShow !== "dance";
  renderDance();
  const showLabel = $("btn-start-show-label");
  if (showLabel) showLabel.textContent = t(state.running === selectedShow ? "restart_x" : "start_x", { name: programTitle(selectedShow) });
  const gameLabel = $("btn-start-game-label");
  if (gameLabel) gameLabel.textContent = t(state.running === selectedGame ? "restart_x" : "start_x", { name: programTitle(selectedGame) });

  const isTtt = selectedGame === "tictactoe";
  if ($("card-game-tictactoe")) $("card-game-tictactoe").hidden = !isTtt;
  if ($("card-game-party")) $("card-game-party").hidden = isTtt;
  if (!isTtt && !(gameState && gameState.kind === "party" && gameState.game === selectedGame)) {
    if ($("party-status")) $("party-status").textContent = programTitle(selectedGame);
    if ($("party-info")) $("party-info").textContent = t("party_idle");
    if ($("balls")) $("balls").innerHTML = "";
  }
  if ($("party-start")) $("party-start").hidden = state.running !== selectedGame;
  renderPartySettings();

  const driveBtn = $("btn-start-drive");
  if (driveBtn) driveBtn.disabled = state.running === "drive";
}

$("btn-start-show").onclick = () => startProgram(selectedShow);
$("btn-start-game").onclick = () => startProgram(selectedGame);

// ==========================================
// 6. Virtual Joystick
// ==========================================
let joystickHeading = 0;
let joystickSpeed = 0;
let activeBotIndex = 1;      // robot number driven from this browser
let joystickDragging = false;
let joystickAnimId = null;
let lastJoystickSend = 0;

const joyBase = $("joy-base");
const joyKnob = $("joy-knob");

function setKnobPosition(x, y) {
  if (joyKnob) joyKnob.style.transform = `translate(${x}px, ${y}px)`;
}

function updateJoystickHUD(headingDeg, speedPercent) {
  if ($("hud-heading")) $("hud-heading").textContent = `${Math.round(headingDeg)}°`;
  if ($("hud-speed")) $("hud-speed").textContent = `${Math.round(speedPercent)}%`;
}

function joystickRadius() {
  if (!joyBase || !joyKnob) return 65;
  return (joyBase.clientWidth - joyKnob.offsetWidth) / 2;
}

function handleJoystickMove(clientX, clientY) {
  if (!joyBase) return;
  const rect = joyBase.getBoundingClientRect();
  const dx = clientX - (rect.left + rect.width / 2);
  const dy = clientY - (rect.top + rect.height / 2);
  const dist = Math.hypot(dx, dy);
  const maxRadius = joystickRadius();
  const clampedDist = Math.min(dist, maxRadius);
  const heading = (Math.atan2(dx, -dy) * 180 / Math.PI + 360) % 360;   // 0 = up, clockwise

  setKnobPosition((dx / (dist || 1)) * clampedDist, (dy / (dist || 1)) * clampedDist);

  const speed = dist < maxRadius * 0.12 ? 0 : (clampedDist / maxRadius) * 100;
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
    const m = new DOMMatrixReadOnly(window.getComputedStyle(joyKnob).transform);
    startX = m.m41; startY = m.m42;
  }
  let startTime = null;
  function animateSnap(time) {
    if (!startTime) startTime = time;
    const progress = Math.min(1, (time - startTime) / 120);
    const ease = 1 - Math.pow(1 - progress, 3);
    setKnobPosition(startX * (1 - ease), startY * (1 - ease));
    if (progress < 1) joystickAnimId = requestAnimationFrame(animateSnap);
  }
  joystickAnimId = requestAnimationFrame(animateSnap);
}

function dispatchDrive(heading, speedPercent, force = false) {
  // 1. Simulation preview
  if (clientMode && clientRobots && clientRobots.length > 0) {
    const targetBot = clientRobots[activeBotIndex - 1] || clientRobots[0];
    if (targetBot) {
      targetBot.heading = (heading + calibOffset(activeBotIndex)) % 360;
      targetBot.speed = (speedPercent / 100) * 50;   // cm/s
      if (speedPercent > 5) targetBot.matrix = makeMatrix("Arrow", targetBot.baseColor);
    }
  }

  // 2. Throttled send (20 Hz), stops always go out immediately
  const now = Date.now();
  if (force || now - lastJoystickSend > 50 || speedPercent === 0) {
    lastJoystickSend = now;
    if (bleApiChar) {
      bleDrive(speedPercent, (heading + calibOffset(activeBotIndex)) % 360);
    } else if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: "joystick",
        heading: Math.round(heading),
        speed: Math.round((speedPercent / 100) * 255),
        robot: activeBotIndex,
      }));
    }
  }
}

// The drive program stops a robot that gets no command for 1 s, so a held
// stick (or held key) repeats its last command.
setInterval(() => {
  if ((joystickDragging || activeKeys.size > 0) && joystickSpeed > 0) {
    dispatchDrive(joystickHeading, joystickSpeed, true);
  }
}, 300);

if (joyBase) {
  joyBase.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    joystickDragging = true;
    joyBase.setPointerCapture(e.pointerId);
    handleJoystickMove(e.clientX, e.clientY);
  });
  joyBase.addEventListener("pointermove", (e) => {
    if (!joystickDragging) return;
    e.preventDefault();
    handleJoystickMove(e.clientX, e.clientY);
  });
  const pointerEnd = () => {
    if (!joystickDragging) return;
    joystickDragging = false;
    snapKnobToCenter();
  };
  joyBase.addEventListener("pointerup", pointerEnd);
  joyBase.addEventListener("pointercancel", pointerEnd);
  joyBase.addEventListener("lostpointercapture", pointerEnd);
}

// Robot selector for the host (phones always drive their own robot)
function renderBotSelector() {
  const box = $("bot-selector");
  if (!box) return;
  box.innerHTML = "";
  const colors = ["var(--r1)", "var(--r2)", "var(--r3)"];
  for (let n = 1; n <= 3; n++) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "seg" + (n === activeBotIndex ? " active" : "");
    b.style.setProperty("--c", colors[n - 1]);
    b.textContent = `BOLT ${n}`;
    b.onclick = () => { activeBotIndex = n; renderBotSelector(); renderCalib(); };
    box.appendChild(b);
  }
}

// ---------- Drive calibration ----------
// Robot number -> forward heading in degrees. Pushing the joystick up drives the
// robot at this heading, so "up" is away from the driver. Applied by the drive
// program on the server; in simulation and direct Bluetooth mode by this page.
let calibOffsets = {};
let calibDragging = false;
let lastCalibSend = 0;

function calibRobot() {
  return myRole === "controller" ? mySlot : activeBotIndex;
}

function calibOffset(robot = calibRobot()) {
  return Number(calibOffsets[robot] || 0);
}

function calibAvailable() {
  return clientMode || !!bleApiChar || state.running === "drive";
}

function renderCalib() {
  const slider = $("calib-slider");
  if (!slider) return;
  const off = calibOffset();
  const v = off > 180 ? off - 360 : off;
  if (!calibDragging) slider.value = String(v);
  $("calib-val").textContent = `${calibDragging ? slider.value : v}°`;
  $("calib-robot").textContent = myRole === "controller" ? "" : `· BOLT ${calibRobot()}`;
  const ok = calibAvailable();
  ["calib-slider", "calib-minus", "calib-plus", "calib-reset"].forEach((id) => { $(id).disabled = !ok; });
  $("calib-box").classList.toggle("disabled", !ok);
  $("calib-hint").textContent = t(ok ? "calib_hint" : "calib_off_hint");
}

function sendCalibration(value, force = false) {
  const robot = calibRobot();
  const offset = ((Math.round(value) % 360) + 360) % 360;
  calibOffsets[robot] = offset;
  $("calib-val").textContent = `${offset > 180 ? offset - 360 : offset}°`;
  const now = Date.now();
  if (!force && now - lastCalibSend < 120) return;
  lastCalibSend = now;
  if (ws && ws.readyState === WebSocket.OPEN && !clientMode) {
    ws.send(JSON.stringify({ type: "calibrate", robot, offset }));
  } else if (bleApiChar) {
    bleDrive(0, offset);                      // turn in place to the new forward
  } else if (clientRobots[robot - 1]) {
    const bot = clientRobots[robot - 1];
    bot.heading = offset;
    bot.matrix = makeMatrix("Arrow", bot.baseColor);
  }
}

$("calib-slider").addEventListener("input", (e) => { calibDragging = true; sendCalibration(Number(e.target.value)); });
$("calib-slider").addEventListener("change", (e) => {
  calibDragging = false;
  sendCalibration(Number(e.target.value), true);
  renderCalib();
});
$("calib-minus").onclick = () => { sendCalibration(calibOffset() - 15, true); renderCalib(); };
$("calib-plus").onclick = () => { sendCalibration(calibOffset() + 15, true); renderCalib(); };
$("calib-reset").onclick = () => { sendCalibration(0, true); renderCalib(); };

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
  if ($("arena-stats")) $("arena-stats").textContent = t("arena_stats", { n: arenaRobots.length });
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

let lowPowerMode = (typeof localStorage !== "undefined" && localStorage.getItem("sphero_low_power") === "1");
let lastArenaFrame = 0;
const ARENA_FPS_INTERVAL = 1000 / 60; // Solid 60 FPS cap for ultra-smooth rendering

function resolveRobotCollisions(robots) {
  if (!robots || robots.length < 2) return;
  const minDist = 7.3; // cm (matches physical ROBOT_DIAMETER = 7.3 cm, ROBOT_RADIUS = 3.65 cm)
  const minX = -80.0, maxX = 98.0, minY = -30.0, maxY = 135.0;

  for (let iter = 0; iter < 3; iter++) {
    for (let i = 0; i < robots.length; i++) {
      const a = robots[i];
      for (let j = i + 1; j < robots.length; j++) {
        const b = robots[j];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.hypot(dx, dy);
        if (dist < minDist) {
          const overlap = minDist - dist;
          const nx = dist > 0.001 ? dx / dist : Math.cos(i * 1.5 + j * 0.7);
          const ny = dist > 0.001 ? dy / dist : Math.sin(i * 1.5 + j * 0.7);
          a.x -= nx * overlap * 0.5;
          a.y -= ny * overlap * 0.5;
          b.x += nx * overlap * 0.5;
          b.y += ny * overlap * 0.5;
          if (iter === 0 && ((a.speed && a.speed > 3) || (b.speed && b.speed > 3))) {
            shakeWobble[a.name] = Date.now() + 250;
            shakeWobble[b.name] = Date.now() + 250;
          }
        }
      }
      // Strictly prevent escaping the visible arena boundary
      a.x = Math.max(minX, Math.min(maxX, a.x));
      a.y = Math.max(minY, Math.min(maxY, a.y));
    }
  }
}

function getRobotFleetInfo(r, idx) {
  let id = idx + 1;
  let rawName = r.name;
  if (currentRobots && currentRobots.length > 0) {
    const match = currentRobots.find((cr, i) =>
      (cr.raw_name && (cr.raw_name === r.name || cr.raw_name === r.raw_name)) ||
      (cr.name && (cr.name === r.name || cr.name === r.raw_name)) ||
      (cr.id && cr.id === (idx + 1))
    );
    if (match) {
      id = match.id || (idx + 1);
      rawName = match.raw_name || match.name || r.name;
    }
  }
  return { id, name: rawName };
}

let hoveredRobotName = null;

function getCanvasPointerRobot(clientX, clientY) {
  if (!canvas || !arenaRobots || !arenaRobots.length) return null;
  const rect = canvas.getBoundingClientRect();
  const mouseX = (clientX - rect.left) * (canvas.width / rect.width);
  const mouseY = (clientY - rect.top) * (canvas.height / rect.height);

  for (let idx = 0; idx < arenaRobots.length; idx++) {
    const r = arenaRobots[idx];
    const p = toCanvasCoords(r.x, r.y);
    const dist = Math.hypot(mouseX - p.cx, mouseY - p.cy);
    if (dist <= 22) {
      return { robot: r, index: idx, p, mouseX, mouseY };
    }
  }
  return null;
}

function renderArena(timestamp) {
  if (!canvas || !actx) return;
  requestAnimationFrame(renderArena);

  // Skip completely if canvas is hidden, off-screen or tab in background
  if (document.hidden || canvas.offsetParent === null) {
    return;
  }

  // Throttle render loop to 60 FPS (or 30 FPS in Eco mode)
  const targetInterval = lowPowerMode ? (1000 / 30) : ARENA_FPS_INTERVAL;
  if (timestamp && (timestamp - lastArenaFrame < targetInterval)) {
    return;
  }
  lastArenaFrame = timestamp || performance.now();

  // Prevent robots from hovering or overlapping each other in arena
  resolveRobotCollisions(arenaRobots);

  const w = canvas.width, h = canvas.height;
  actx.clearRect(0, 0, w, h);
  const dark = isDarkTheme();

  // 1. Grid lines (batched into a single path)
  const origin = toCanvasCoords(0, 0);
  actx.lineWidth = 1;
  actx.strokeStyle = dark ? "rgba(255, 255, 255, 0.05)" : "rgba(27, 32, 38, 0.07)";
  actx.beginPath();
  for (let cm = -200; cm <= 200; cm += 20) {
    const p = toCanvasCoords(cm, 0);
    actx.moveTo(p.cx, 0); actx.lineTo(p.cx, h);
  }
  for (let cm = -60; cm <= 240; cm += 20) {
    const p = toCanvasCoords(0, cm);
    actx.moveTo(0, p.cy); actx.lineTo(w, p.cy);
  }
  actx.stroke();

  // Major axes (batched)
  actx.strokeStyle = dark ? "rgba(255, 255, 255, 0.15)" : "rgba(27, 32, 38, 0.18)";
  actx.beginPath();
  actx.moveTo(origin.cx, 0); actx.lineTo(origin.cx, h);
  actx.moveTo(0, origin.cy); actx.lineTo(w, origin.cy);
  actx.stroke();

  // Coordinates labels
  actx.fillStyle = dark ? "rgba(255, 255, 255, 0.28)" : "rgba(27, 32, 38, 0.48)";
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
    { x: 0, y: 0, label: "BOLT 1", color: dark ? "#ff3b3b" : "#d93226" },
    { x: 15, y: 0, label: "BOLT 2", color: dark ? "#2ecc71" : "#16803c" },
    { x: 30, y: 0, label: "BOLT 3", color: dark ? "#3498db" : "#0077b8" },
  ];
  for (const sp of homeSpots) {
    const p = toCanvasCoords(sp.x, sp.y);
    actx.strokeStyle = sp.color;
    actx.setLineDash([3, 3]);
    actx.beginPath();
    actx.arc(p.cx, p.cy, 16, 0, Math.PI * 2);
    actx.stroke();
    actx.setLineDash([]);
    actx.fillStyle = sp.color;
    actx.font = "9px sans-serif";
    actx.fillText(sp.label, p.cx - 15, p.cy + 25);
  }

  // 2. Motion Trails
  if (showTrails) {
    const now = Date.now() / 1000;
    const effMaxAge = lowPowerMode ? 2.5 : maxTrailAge;
    for (const [name, pts] of Object.entries(trails)) {
      if (pts.length < 2) continue;
      const robot = arenaRobots.find(r => r.name === name);
      const defaultTrail = dark ? "#58a6ff" : "#0077b8";
      const baseCol = robot && robot.front_led !== "#000000" && (dark || robot.front_led !== "#ffffff") ? robot.front_led : defaultTrail;
      actx.lineWidth = lowPowerMode ? 1.5 : 2.0;
      actx.lineCap = "round";
      const startIdx = lowPowerMode ? Math.max(1, pts.length - 8) : 1;
      actx.beginPath();
      for (let i = startIdx; i < pts.length; i++) {
        const p1 = toCanvasCoords(pts[i - 1].x, pts[i - 1].y);
        const p2 = toCanvasCoords(pts[i].x, pts[i].y);
        const age = now - pts[i].t;
        if (age > effMaxAge) continue;
        actx.moveTo(p1.cx, p1.cy);
        actx.lineTo(p2.cx, p2.cy);
      }
      actx.strokeStyle = baseCol;
      actx.stroke();
    }
  }

  // 3. Robots
  const nowMs = Date.now();
  const isCrowded = arenaRobots.length > 5;
  let hoveredInfo = null;
  const hoverAccent = dark ? "#58a6ff" : "#0077b8";

  for (let idx = 0; idx < arenaRobots.length; idx++) {
    const r = arenaRobots[idx];
    const p = toCanvasCoords(r.x, r.y);
    let rx = p.cx, ry = p.cy;
    if (shakeWobble[r.name] && nowMs < shakeWobble[r.name]) {
      rx += (Math.random() - 0.5) * 8;
      ry += (Math.random() - 0.5) * 8;
    }
    const rad = 15;
    const isHovered = (hoveredRobotName === r.name);
    const info = getRobotFleetInfo(r, idx);

    if (isHovered) {
      hoveredInfo = { r, rx, ry, rad, info };
    }

    actx.save();
    actx.translate(rx, ry);

    // Subtle floor shadow in light mode
    if (!dark) {
      actx.fillStyle = "rgba(27, 32, 38, 0.16)";
      actx.beginPath();
      actx.arc(0, 2, rad + 1, 0, Math.PI * 2);
      actx.fill();
    }

    // Glowing locator pulse ring when hovered
    if (isHovered) {
      actx.strokeStyle = hoverAccent;
      actx.lineWidth = 2.5;
      actx.beginPath();
      actx.arc(0, 0, rad + 4, 0, Math.PI * 2);
      actx.stroke();
    }

    // Front headlight beam
    const headingRad = (r.heading * Math.PI) / 180;
    actx.rotate(headingRad);

    const beamGrad = actx.createRadialGradient(0, 0, rad, 0, -rad - 30, 40);
    beamGrad.addColorStop(0, dark ? "rgba(255, 255, 255, 0.35)" : "rgba(0, 119, 184, 0.26)");
    beamGrad.addColorStop(1, dark ? "rgba(255, 255, 255, 0.0)" : "rgba(0, 119, 184, 0.0)");
    actx.fillStyle = beamGrad;
    actx.beginPath();
    actx.moveTo(0, 0);
    actx.arc(0, 0, rad + 35, -Math.PI / 2 - 0.45, -Math.PI / 2 + 0.45);
    actx.closePath();
    actx.fill();

    // Tail light (blue dot at back - fast crisp render)
    if (r.back_led && r.back_led !== "#000000") {
      actx.fillStyle = r.back_led;
      actx.beginPath();
      actx.arc(0, rad - 2, 3, 0, Math.PI * 2);
      actx.fill();
    }

    // Outer spherical shell (smoked polycarbonate so 8x8 LEDs always pop)
    const ballGrad = actx.createRadialGradient(-rad * 0.3, -rad * 0.3, 2, 0, 0, rad);
    ballGrad.addColorStop(0, "rgba(255, 255, 255, 0.35)");
    ballGrad.addColorStop(0.7, "rgba(38, 48, 66, 0.85)");
    ballGrad.addColorStop(1, "rgba(18, 23, 33, 0.96)");
    actx.fillStyle = ballGrad;
    actx.beginPath();
    actx.arc(0, 0, rad, 0, Math.PI * 2);
    actx.fill();

    // Rim glow
    const rimDefault = dark ? "rgba(100, 150, 255, 0.4)" : "rgba(0, 119, 184, 0.55)";
    const rimFront = (r.front_led !== "#000000" && (dark || r.front_led !== "#ffffff")) ? r.front_led : rimDefault;
    actx.strokeStyle = isHovered ? hoverAccent : rimFront;
    actx.lineWidth = isHovered ? 2.2 : 1.8;
    actx.stroke();

    // 8x8 LED Matrix - batched for high performance
    if (r.matrix && r.matrix.length === 8) {
      const dotSize = 2.0;
      const dotSpacing = 2.5;
      const startX = -((7 * dotSpacing) / 2);
      const startY = -((7 * dotSpacing) / 2);

      // Fast matrix background grid
      actx.fillStyle = "rgba(255, 255, 255, 0.05)";
      actx.beginPath();
      for (let row = 0; row < 8; row++) {
        for (let col = 0; col < 8; col++) {
          const colHex = r.matrix[row][col];
          if (!colHex || colHex === "#000000") {
            const dx = startX + col * dotSpacing;
            const dy = startY + row * dotSpacing;
            actx.moveTo(dx + dotSize / 2, dy);
            actx.arc(dx, dy, dotSize / 2, 0, Math.PI * 2);
          }
        }
      }
      actx.fill();

      // Lit pixels (drawn directly without expensive software shadowBlur)
      for (let row = 0; row < 8; row++) {
        for (let col = 0; col < 8; col++) {
          const colHex = r.matrix[row][col];
          if (colHex && colHex !== "#000000") {
            actx.fillStyle = colHex;
            actx.beginPath();
            actx.arc(startX + col * dotSpacing, startY + row * dotSpacing, dotSize / 2, 0, Math.PI * 2);
            actx.fill();
          }
        }
      }
    }

    actx.restore();

    // Robot Name / ID Tag
    actx.fillStyle = isHovered ? hoverAccent : (dark ? "#ffffff" : "#1b2026");
    actx.font = "bold 10px sans-serif";
    actx.textAlign = "center";
    const stagger = isCrowded && (idx % 2 !== 0);
    const labelY = ry + rad + (stagger ? 24 : 12);
    actx.fillText(isCrowded ? `#${info.id} ${r.name}` : r.name, rx, labelY);

    if (!isCrowded) {
      actx.fillStyle = dark ? "rgba(255, 255, 255, 0.55)" : "rgba(27, 32, 38, 0.62)";
      actx.font = "9px monospace";
      actx.fillText(`(${Math.round(r.x)}, ${Math.round(r.y)}) ${Math.round(r.heading)}°`, rx, labelY + 10);
    }
  }

  // 4. Floating Tooltip above Hovered Robot
  if (hoveredInfo) {
    const { r, rx, ry, rad, info } = hoveredInfo;
    const text = `#${info.id} ${r.name} (${Math.round(r.x)}, ${Math.round(r.y)}) ${Math.round(r.heading)}°`;
    actx.font = "bold 11px sans-serif";
    const textWidth = actx.measureText(text).width;
    const pillW = textWidth + 18;
    const pillH = 22;
    const pillX = Math.max(10, Math.min(w - pillW - 10, rx - pillW / 2));
    const pillY = Math.max(10, ry - rad - 28);

    actx.fillStyle = dark ? "rgba(13, 17, 23, 0.94)" : "rgba(250, 247, 240, 0.96)";
    actx.strokeStyle = hoverAccent;
    actx.lineWidth = 1.5;
    actx.beginPath();
    if (actx.roundRect) {
      actx.roundRect(pillX, pillY, pillW, pillH, 6);
    } else {
      actx.rect(pillX, pillY, pillW, pillH);
    }
    actx.fill();
    actx.stroke();

    actx.fillStyle = hoverAccent;
    actx.textAlign = "center";
    actx.fillText(text, pillX + pillW / 2, pillY + 15);
  }
}

function handleCanvasPointer(clientX, clientY) {
  const hit = getCanvasPointerRobot(clientX, clientY);
  if (hit) {
    const { robot, index } = hit;
    const info = getRobotFleetInfo(robot, index);
    shakeWobble[robot.name] = Date.now() + 600;
    playPop();
    identifyRobot(info.id);

    let targetCell = info.id;
    if ((state.running === "tictactoe" || state.running === "simon" || state.running === "mole") && gameState && Array.isArray(gameState.cells)) {
      const cellIdx = gameState.cells.findIndex((c) => c && (c.robot === robot.name || c.robot === info.name || c.robot === `BOLT-${info.id}` || c.robot === `BOLT ${info.id}`));
      if (cellIdx >= 0) {
        targetCell = cellIdx + 1;
      }
    }
    sendShake(targetCell, robot.name);
  }
}

if (canvas) {
  canvas.addEventListener("click", (e) => handleCanvasPointer(e.clientX, e.clientY));
  canvas.addEventListener("touchstart", (e) => {
    if (e.touches && e.touches.length > 0) {
      handleCanvasPointer(e.touches[0].clientX, e.touches[0].clientY);
    }
  }, { passive: true });
  canvas.addEventListener("mousemove", (e) => {
    const hit = getCanvasPointerRobot(e.clientX, e.clientY);
    if (hit) {
      canvas.style.cursor = "pointer";
      if (hoveredRobotName !== hit.robot.name) {
        hoveredRobotName = hit.robot.name;
        document.querySelectorAll(".bot.hover-target").forEach((el) => el.classList.remove("hover-target"));
        const info = getRobotFleetInfo(hit.robot, hit.index);
        const card = document.querySelector(`.bot[data-robot="${info.id}"]`);
        if (card) {
          card.classList.add("hover-target");
          card.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" });
        }
      }
    } else {
      canvas.style.cursor = "default";
      if (hoveredRobotName !== null) {
        hoveredRobotName = null;
        document.querySelectorAll(".bot.hover-target").forEach((el) => el.classList.remove("hover-target"));
      }
    }
  });
  canvas.addEventListener("mouseleave", () => {
    canvas.style.cursor = "default";
    if (hoveredRobotName !== null) {
      hoveredRobotName = null;
      document.querySelectorAll(".bot.hover-target").forEach((el) => el.classList.remove("hover-target"));
    }
  });
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

const NEUMANN_COLOR = "#0077b8";
const DEFAULT_LETTER_CONFIG = {
  align: "compass",
  hand: false,
  heading: 0,
  letters: "NEUMANN".split("").map((letter) => ({ letter, rotation: 0, mirror: false, turn: 0 })),
};

let gameState = null;
let tttCfg = DEFAULT_TTT_CONFIG;
let letterCfg = DEFAULT_LETTER_CONFIG;

function initClientRobots(count = 3) {
  const configs = [
    { name: "BOLT 1", x: 0, y: 0, col: "#ff3b3b", matrixKey: "1" },
    { name: "BOLT 2", x: 18, y: 0, col: "#2ecc71", matrixKey: "2" },
    { name: "BOLT 3", x: 36, y: 0, col: "#3498db", matrixKey: "3" },
    { name: "BOLT 4", x: -50, y: 75, col: "#f1c40f", matrixKey: "4" },
    { name: "BOLT 5", x: -25, y: 75, col: "#e84393", matrixKey: "5" },
    { name: "BOLT 6", x: 0, y: 75, col: "#00cec9", matrixKey: "6" },
    { name: "BOLT 7", x: 25, y: 75, col: "#e67e22", matrixKey: "7" },
    { name: "BOLT 8", x: 50, y: 75, col: "#ffffff", matrixKey: "8" },
    { name: "BOLT 9", x: -50, y: 105, col: "#9b59b6", matrixKey: "9" },
    { name: "BOLT 10", x: -25, y: 105, col: "#fd79a8", matrixKey: "10" },
    { name: "BOLT 11", x: 0, y: 105, col: "#0984e3", matrixKey: "11" },
    { name: "BOLT 12", x: 25, y: 105, col: "#00b894", matrixKey: "12" },
    { name: "BOLT 13", x: 50, y: 105, col: "#ffeaa7", matrixKey: "13" },
    { name: "BOLT 14", x: -25, y: 125, col: "#6c5ce7", matrixKey: "14" },
    { name: "BOLT 15", x: 25, y: 125, col: "#d63031", matrixKey: "15" },
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

$("global-stop").onclick = stopProgram;

function startProgram(id) {
  toast(t("started_x", { name: programTitle(id) }));
  if (clientMode) {
    clientStart(id);
    return;
  }
  const body = partyConfig && partyConfig[id] ? JSON.stringify(partyConfig[id]) : null;
  const headers = body ? { "Content-Type": "application/json" } : {};
  fetch(`/api/start/${id}`, { method: "POST", headers, body })
    .then((r) => { if (!r.ok) clientStart(id); })
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
  initClientRobots(15);
  // Align all client dance robots in a single horizontal line
  const n = clientRobots.length;
  const spacing = Math.min(15.0, 140.0 / Math.max(1, n - 1));
  const startX = - (n - 1) * spacing / 2.0;
  clientRobots.forEach((r, idx) => {
    r.x = startX + idx * spacing;
    r.y = 30.0;
    r.homeX = r.x;
    r.homeY = r.y;
    r.heading = 0;
  });
  updateTelemetry({ robots: clientRobots });

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
      clientRobots.forEach(r => { r.y = 30.0 + progress * 20.0; r.heading = 0; });
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
    resolveRobotCollisions(clientRobots);
    updateTelemetry({ robots: clientRobots });
  }, 40);
}

// ------------------------------------------
// Neumann Formation
// ------------------------------------------
function runClientNeu() {
  // one letter per robot, robots 1-7 in a row left to right
  clientRobots = letterCfg.letters.map((item, i) => ({
    name: `BOLT ${i + 1}`,
    x: (i - (letterCfg.letters.length - 1) / 2) * 20, y: 25,
    heading: 0, speed: 0,
    front_led: "#ffffff", back_led: "#000000",
    matrix: makeMatrix("Arrow", NEUMANN_COLOR),
    homeX: (i - (letterCfg.letters.length - 1) / 2) * 20, homeY: 25,
    baseColor: NEUMANN_COLOR,
  }));
  let step = 0;
  clientLoopId = setInterval(() => {
    step++;
    if (step === 25) {
      clientRobots.forEach((r, i) => {
        const l = letterCfg.letters[i];
        r.heading = (letterCfg.heading + (l.turn || 0) + 360) % 360;
        r.matrix = makeMatrix(l.letter, NEUMANN_COLOR, l.rotation, l.mirror);
      });
    }
    updateTelemetry({ robots: clientRobots });
  }, 40);
}

// ------------------------------------------
// Autonomous Roam
// ------------------------------------------
function runClientRoam() {
  initClientRobots(15);
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
      r.x = Math.max(-80, Math.min(98, r.x + w.vx * 0.05));
      r.y = Math.max(-30, Math.min(135, r.y + w.vy * 0.05));
      const dist = Math.hypot(r.x - r.homeX, r.y - r.homeY);
      if (dist > 25) {
        w.vx += (r.homeX - r.x) * 0.1;
        w.vy += (r.homeY - r.y) * 0.1;
      }
      r.heading = (Math.atan2(w.vx, w.vy) * 180 / Math.PI + 360) % 360;
      r.matrix = makeMatrix("Arrow", r.baseColor);
    });
    resolveRobotCollisions(clientRobots);
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
        r.x = Math.max(-80, Math.min(98, r.x + Math.sin(rad) * r.speed * dt));
        r.y = Math.max(-30, Math.min(135, r.y + Math.cos(rad) * r.speed * dt));
      }
    });

    resolveRobotCollisions(clientRobots);
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
function isTypingTarget(e) {
  const tag = e.target && e.target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
}
window.addEventListener("blur", () => {
  if (activeKeys.size) { activeKeys.clear(); evalKeys(); }
});
window.addEventListener("keydown", (e) => {
  if (KEY_MAP[e.code] && !isTypingTarget(e) && !e.repeat) {
    if (e.code.startsWith("Arrow")) e.preventDefault();
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
function getPartyGamePositions(game, count = 9) {
  const cfg = (partyConfig && partyConfig[game]) || { layout: "3x3" };
  const n = count;
  if (cfg.layout === "random") {
    const coords = [];
    for (let i = 0; i < n; i++) {
      let placed = false;
      for (let attempt = 0; attempt < 120; attempt++) {
        const rx = Math.round((Math.random() * 100 - 50) * 10) / 10;
        const ry = Math.round((Math.random() * 58 + 14) * 10) / 10;
        if (coords.every(c => Math.hypot(rx - c.x, ry - c.y) >= 22)) {
          coords.push({ x: rx, y: ry });
          placed = true;
          break;
        }
      }
      if (!placed) {
        coords.push({ x: -45 + (i % 5) * 22, y: 15 + Math.floor(i / 5) * 25 });
      }
    }
    return coords;
  }
  // 3x3 layout
  if (n <= 4) {
    return [
      { x: -18, y: 50 }, { x: 18, y: 50 },
      { x: -18, y: 22 }, { x: 18, y: 22 },
    ].slice(0, n);
  }
  const xs = [-28, 0, 28];
  const ys = [66, 40, 14];
  const coords = [];
  for (const y of ys) {
    for (const x of xs) {
      coords.push({ x, y });
    }
  }
  return coords.slice(0, n);
}

function triggerClientDrift() {
  const game = selectedGame;
  const cfg = partyConfig && partyConfig[game];
  if (!cfg || !cfg.drift || !clientRobots || !clientRobots.length) return;
  const steps = 18;
  let step = 0;
  const deltas = clientRobots.map(r => {
    let angle = Math.random() * Math.PI * 2;
    const cx = 0, cy = 40;
    const dx = cx - r.x, dy = cy - r.y;
    if (Math.hypot(dx, dy) > 35) {
      angle = Math.atan2(dx, dy) + (Math.random() - 0.5) * 0.8;
    }
    const dist = (10.0 + Math.random() * 8.0) / steps;
    return {
      dx: Math.sin(angle) * dist,
      dy: Math.cos(angle) * dist,
      heading: Math.round(((angle * 180 / Math.PI) + 360) % 360),
    };
  });

  const driftTimer = setInterval(() => {
    step++;
    clientRobots.forEach((r, i) => {
      r.x += deltas[i].dx;
      r.y += deltas[i].dy;
      r.heading = deltas[i].heading;
      r.speed = 24;
    });
    resolveRobotCollisions(clientRobots);
    updateTelemetry({ robots: clientRobots });
    if (step >= steps) {
      clearInterval(driftTimer);
      clientRobots.forEach(r => r.speed = 0);
      updateTelemetry({ robots: clientRobots });
    }
  }, 25);
}

function runClientMole() {
  const positions = getPartyGamePositions("mole", 9);
  clientRobots = positions.map((p, i) => ({
    name: `BOLT ${i + 1}`,
    x: p.x,
    y: p.y,
    heading: 0,
    speed: 0,
    front_led: "#000000",
    back_led: "#0000ff",
    matrix: makeSolidMatrix("#000000"),
    homeX: p.x,
    homeY: p.y,
    baseColor: "#111111",
  }));

  const moleCfg = (partyConfig && partyConfig.mole) || { speed: "normal", layout: "3x3", drift: false };

  clientSimState = {
    score: 0,
    activeMole: -1,
    timeLeft: 60,
    moleTimeout: null,
    moleGapTimeout: null,
    speed: moleCfg.speed || "normal",
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

  function getMoleSpeedMs(speed, score) {
    switch (speed) {
      case "slow": return Math.max(1200, 2400 - score * 40);
      case "fast": return Math.max(450, 1050 - score * 50);
      case "insane": return Math.max(250, 600 - score * 30);
      case "normal":
      default: return Math.max(600, 1600 - score * 65);
    }
  }

  function getMoleGapMs(speed) {
    switch (speed) {
      case "slow": return 400;
      case "fast": return 160;
      case "insane": return 90;
      case "normal":
      default: return 250;
    }
  }

  function nextMole() {
    if (!state.running || state.running !== "mole") return;
    const moleIdx = Math.floor(Math.random() * clientRobots.length);
    clientSimState.activeMole = moleIdx;

    clientRobots.forEach((r, i) => {
      if (i === moleIdx) {
        r.matrix = makeSolidMatrix("#00ff44");
        r.front_led = "#00ff44";
        gameState.cells[i].color = "#00ff44";
        gameState.cells[i].label = "WHACK!";
      } else {
        r.matrix = makeSolidMatrix("#000000");
        r.front_led = "#000000";
        gameState.cells[i].color = "#111111";
        gameState.cells[i].label = "";
      }
    });

    renderParty();
    triggerClientDrift();
    updateTelemetry({ robots: clientRobots });
    playPop();

    const speedMs = getMoleSpeedMs(partyConfig.mole.speed, clientSimState.score);
    const gapMs = getMoleGapMs(partyConfig.mole.speed);
    clientSimState.moleTimeout = setTimeout(() => {
      if (clientSimState.activeMole === moleIdx) {
        clientSimState.activeMole = -1;
        clientRobots[moleIdx].matrix = makeSolidMatrix("#000000");
        clientRobots[moleIdx].front_led = "#000000";
        gameState.cells[moleIdx].color = "#111111";
        gameState.cells[moleIdx].label = "";
        renderParty();
        updateTelemetry({ robots: clientRobots });
        clientSimState.moleGapTimeout = setTimeout(nextMole, gapMs);
      }
    }, speedMs);
  }

  nextMole();

  clientLoopId = setInterval(() => {
    clientSimState.timeLeft--;
    if (clientSimState.timeLeft <= 0) {
      clearInterval(clientLoopId);
      clearTimeout(clientSimState.moleTimeout);
      clearTimeout(clientSimState.moleGapTimeout);
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
// Party Game 3: Memory Game
// ------------------------------------------
const SIMON_NOTES = [261.6, 293.7, 329.6, 349.2, 392.0, 440.0, 493.9, 523.2, 587.3];
const SIMON_COLORS = [
  "#ff0000", "#00ff00", "#003cff", "#ffc800",
  "#ff00c8", "#00e6e6", "#ff5a00", "#ffffff",
  "#8200ff"
];

function getSimonStepInterval(speed) {
  switch (speed) {
    case "slow": return 1050;
    case "fast": return 450;
    case "insane": return 260;
    case "normal":
    default: return 700;
  }
}

function runClientSimon() {
  const positions = getPartyGamePositions("simon", 9);
  clientRobots = positions.map((p, i) => ({
    name: `BOLT ${i + 1}`,
    x: p.x,
    y: p.y,
    heading: 0,
    speed: 0,
    front_led: SIMON_COLORS[i],
    back_led: "#0000ff",
    matrix: makeSolidMatrix(SIMON_COLORS[i]),
    homeX: p.x,
    homeY: p.y,
    baseColor: SIMON_COLORS[i],
  }));

  clientSimState = {
    sequence: [Math.floor(Math.random() * clientRobots.length)],
    playerIdx: 0,
    playingSeq: false,
    level: 1,
  };

  gameState = {
    kind: "party",
    game: "simon",
    title: "Memory game",
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
  const stepTime = getSimonStepInterval(partyConfig.simon ? partyConfig.simon.speed : "normal");
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
    triggerClientDrift();
    step++;
  }, stepTime);
}

function flashSimonBall(idx) {
  if (!clientRobots[idx]) return;
  const speed = partyConfig.simon ? partyConfig.simon.speed : "normal";
  const flashDur = speed === "insane" ? 140 : speed === "fast" ? 220 : speed === "slow" ? 480 : 350;
  playTone(SIMON_NOTES[idx] || 440, "triangle", flashDur / 1000, 0.25);
  shakeWobble[clientRobots[idx].name] = Date.now() + 400;
  clientRobots[idx].matrix = makeSolidMatrix("#ffffff");
  updateTelemetry({ robots: clientRobots });
  setTimeout(() => {
    if (clientRobots[idx]) {
      clientRobots[idx].matrix = makeSolidMatrix(SIMON_COLORS[idx]);
      updateTelemetry({ robots: clientRobots });
    }
  }, flashDur);
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
    front_led: "#ff3b3b",
    back_led: "#0000ff",
    matrix: makeMatrix(String(i + 1), "#c8c8c8", tttCfg ? tttCfg.rotation : 0, tttCfg ? tttCfg.mirror : false),
    homeX: pos.x,
    homeY: pos.y,
    baseColor: "#c8c8c8",
  }));

  gameState = {
    kind: "tictactoe",
    phase: "play",
    board: Array(9).fill(""),
    turn: "X",
    robots: 9,
    numbered: 9,
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
          const nextCol = gameState.turn === "X" ? "#ff3b3b" : "#3498db";
          clientRobots.forEach((r, i) => {
            if (!gameState.board[i]) {
              r.front_led = nextCol;
            }
          });
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
        r.front_led = "#ff3b3b";
      });
      renderGame();
      updateTelemetry({ robots: clientRobots });
    } else if (action === "recount") {
      gameState.phase = "numbering";
      gameState.board = Array(9).fill("");
      gameState.winner = null;
      gameState.line = null;
      gameState.numbered = 0;
      gameState.next = 1;
      clientRobots.forEach((r) => {
        r.matrix = makeMatrix("?", "#ffa000", tttCfg.rotation, tttCfg.mirror);
        r.front_led = "#ffa000";
      });
      renderGame();
      updateTelemetry({ robots: clientRobots });
    } else if (action === "tap" && gameState.phase === "numbering") {
      const idx = Math.max(0, Math.min(8, (body.cell || 1) - 1));
      const num = gameState.next || (gameState.numbered + 1);
      if (clientRobots[idx]) {
        clientRobots[idx].matrix = makeMatrix(String(num), "#c8c8c8", tttCfg.rotation, tttCfg.mirror);
        clientRobots[idx].front_led = "#000000";
      }
      gameState.numbered = num;
      gameState.next = num + 1;
      if (gameState.numbered >= 9) {
        handleClientGameAction({ action: "start" });
      } else {
        renderGame();
        updateTelemetry({ robots: clientRobots });
      }
    }
    return;
  }

  // Memory Game
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
          clientSimState.sequence.push(Math.floor(Math.random() * (clientRobots.length || 4)));
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
    if (action === "start") {
      runClientMole();
    } else if (action === "tap") {
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
      handleClientGameAction({ action: "tap", cell });
      return;
    }
    sendGameAction({ action: "play", cell });
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
  const game = gameState && gameState.kind !== "party" && gameState.kind !== "dance" ? gameState : null;
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
      $("ttt-status").textContent = t("ttt_idle");
    } else if (numbering) {
      $("ttt-status").textContent = t("ttt_numbering", { n: game.next, done: game.numbered });
    } else if (game.winner === "draw") {
      $("ttt-status").textContent = t("ttt_draw");
    } else if (game.winner) {
      $("ttt-status").textContent = t("ttt_win", { p: game.winner });
    } else {
      $("ttt-status").innerHTML = `${t("ttt_turn")} <span style="color:${game.turn === "X" ? "var(--r1)" : "var(--r3)"}">${game.turn}</span>`;
    }
  }

  for (let c = 0; c < 9; c++) {
    const b = document.createElement("button");
    const mark = running && !numbering ? game.board[c] : null;
    const cell = running ? game.cells[c] : null;
    b.className = "ttt-cell " + (mark || "num") + (running && game.line && game.line.includes(c) ? " win" : "");
    const label = numbering ? (cell && cell.connected ? cell.robot : (c + 1 === game.next ? t("ttt_shake_next") : ""))
      : cell ? (cell.connected ? cell.robot : t("ttt_tap")) : "";
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
  if (!g) return;
  renderPartySettings();

  if ($("party-status")) $("party-status").textContent = g.status || programTitle(g.game);
  if ($("party-info")) $("party-info").textContent = g.info || "";

  const box = $("balls");
  if (!box) return;
  const isGrid3x3 = (g.game === "simon" || g.game === "mole") &&
                    ((partyConfig[g.game] && partyConfig[g.game].layout === "3x3") || g.layout === "3x3") &&
                    g.cells.length === 9;
  box.classList.toggle("grid-3x3", isGrid3x3);

  if (box.childNodes.length !== g.cells.length) {
    box.innerHTML = "";
    g.cells.forEach((_, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "ball-btn";
      b.onclick = () => {
        playPop();
        sendGameAction({ action: "tap", cell: i + 1 });
      };
      box.appendChild(b);
    });
  }
  g.cells.forEach((c, i) => {
    const b = box.childNodes[i];
    if (!b) return;
    const col = c.color || "#000000";
    const [r, gr, bl] = [1, 3, 5].map((k) => parseInt(col.slice(k, k + 2), 16) || 0);
    const dark = 0.299 * r + 0.587 * gr + 0.114 * bl < 140;
    const off = col === "#000000";
    b.style.background = off ? "var(--panel-2)" : col;
    b.style.color = off ? "var(--text)" : dark ? "#fff" : "#111";
    b.innerHTML = `<span></span><small></small>`;
    b.querySelector("span").textContent = c.label || "";
    b.querySelector("small").textContent = c.robot || "";
  });
}
if ($("party-start")) {
  $("party-start").onclick = () => {
    const cfg = (partyConfig && partyConfig[selectedGame]) ? partyConfig[selectedGame] : undefined;
    sendGameAction({ action: "start", config: cfg });
  };
}

let partyConfig = {
  simon: { speed: "normal", layout: "3x3", drift: false },
  mole: { speed: "normal", layout: "3x3", drift: false },
};

function loadStoredPartyConfig() {
  try {
    const raw = localStorage.getItem("sphero_party_config");
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed.simon) partyConfig.simon = { ...partyConfig.simon, ...parsed.simon };
      if (parsed.mole) partyConfig.mole = { ...partyConfig.mole, ...parsed.mole };
    }
  } catch (e) {}
}

function saveAndSyncPartyConfig(gameId) {
  try {
    localStorage.setItem("sphero_party_config", JSON.stringify(partyConfig));
  } catch (e) {}
  if (!clientMode) {
    fetch("/api/minigames", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ game: gameId, config: partyConfig[gameId] }),
    }).catch(() => {});
  }
}

let partySaveTimer = null;
function savePartyPreferences() {
  const game = selectedGame;
  if (!["simon", "mole"].includes(game)) return;
  saveAndSyncPartyConfig(game);
  const hint = $("party-prefs-saved-hint");
  if (hint) {
    hint.hidden = false;
    clearTimeout(partySaveTimer);
    partySaveTimer = setTimeout(() => {
      hint.hidden = true;
    }, 2500);
  }
}

function renderPartySettings() {
  const box = $("party-difficulty-controls");
  if (!box) return;
  const isSupported = ["simon", "mole"].includes(selectedGame);
  box.hidden = !isSupported;
  if (!isSupported) return;

  const cfg = partyConfig[selectedGame] || { speed: "normal", layout: "3x3", drift: false };
  const speedSeg = $("party-speed-seg");
  if (speedSeg) {
    speedSeg.querySelectorAll("button").forEach(btn => {
      btn.classList.toggle("active", btn.dataset.speed === cfg.speed);
    });
  }
  const layoutSeg = $("party-layout-seg");
  if (layoutSeg) {
    layoutSeg.querySelectorAll("button").forEach(btn => {
      btn.classList.toggle("active", btn.dataset.layout === cfg.layout);
    });
  }
  const driftSeg = $("party-drift-seg");
  if (driftSeg) {
    driftSeg.querySelectorAll("button").forEach(btn => {
      btn.classList.toggle("active", (btn.dataset.drift === "on") === !!cfg.drift);
    });
  }
}

function initPartySettingsControls() {
  const saveBtn = $("btn-save-party-prefs");
  if (saveBtn) {
    saveBtn.onclick = () => savePartyPreferences();
  }
  const speedSeg = $("party-speed-seg");
  if (speedSeg) {
    speedSeg.querySelectorAll("button").forEach(btn => {
      btn.onclick = () => {
        if (!["simon", "mole"].includes(selectedGame)) return;
        partyConfig[selectedGame].speed = btn.dataset.speed;
        saveAndSyncPartyConfig(selectedGame);
        renderPartySettings();
      };
    });
  }
  const layoutSeg = $("party-layout-seg");
  if (layoutSeg) {
    layoutSeg.querySelectorAll("button").forEach(btn => {
      btn.onclick = () => {
        if (!["simon", "mole"].includes(selectedGame)) return;
        partyConfig[selectedGame].layout = btn.dataset.layout;
        saveAndSyncPartyConfig(selectedGame);
        renderPartySettings();
        if (clientMode && state.running === selectedGame) {
          if (selectedGame === "simon") runClientSimon();
          else if (selectedGame === "mole") runClientMole();
        }
      };
    });
  }
  const driftSeg = $("party-drift-seg");
  if (driftSeg) {
    driftSeg.querySelectorAll("button").forEach(btn => {
      btn.onclick = () => {
        if (!["simon", "mole"].includes(selectedGame)) return;
        partyConfig[selectedGame].drift = btn.dataset.drift === "on";
        saveAndSyncPartyConfig(selectedGame);
        renderPartySettings();
      };
    });
  }
}

// Dance show: robots left out, live phase and the Go / next part button
let danceCfg = { exclude: [] };

function renderDance() {
  const box = $("dance-robots");
  if (!box) return;
  const g = gameState && gameState.kind === "dance" && state.running === "dance" ? gameState : null;
  const numbers = currentRobots.length ? currentRobots.map((r, i) => r.id || i + 1)
    : Array.from({ length: 15 }, (_, i) => i + 1);
  const excluded = new Set(danceCfg.exclude || []);
  const skipped = new Set(g ? g.skipped || [] : []);
  const lost = new Set(g ? g.lost || [] : []);
  box.innerHTML = "";
  numbers.forEach((n) => {
    const robot = currentRobots.find((r) => r.id === n);
    const b = document.createElement("button");
    b.type = "button";
    b.className = "dance-robot" + (excluded.has(n) ? " out" : "") + (skipped.has(n) || lost.has(n) ? " busy" : "");
    b.style.setProperty("--c", (robot && robot.color && robot.color.hex) || "var(--accent)");
    b.textContent = n;
    b.title = excluded.has(n) ? t("dance_out") : skipped.has(n) ? t("dance_busy") : lost.has(n) ? t("dance_lost") : t("dance_in");
    b.onclick = () => toggleDanceRobot(n);
    box.appendChild(b);
  });

  const live = $("dance-live");
  if (!live) return;
  live.hidden = !g;
  if (!g) return;
  const phaseText = t(`dance_phase_${g.phase}`);
  $("dance-status").textContent = phaseText + (g.left ? ` · ${g.left} ${currentLang === "hu" ? "mp" : "s"}` : "")
    + (g.robots ? ` · ${g.robots.length} ${t("robots_unit")}` : "");
  const go = $("dance-go");
  go.hidden = !["setup", "rainbow", "rush", "chars", "home"].includes(g.phase);
  go.textContent = t(g.phase === "setup" ? "dance_go" : "dance_next");
}

function toggleDanceRobot(n) {
  if (clientMode) {
    const set = new Set(danceCfg.exclude || []);
    set.has(n) ? set.delete(n) : set.add(n);
    danceCfg = { exclude: [...set].sort((a, b) => a - b) };
    renderDance();
    return;
  }
  fetch("/api/dance", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ toggle: n }),
  }).then((r) => r.json()).then((cfg) => { danceCfg = cfg; renderDance(); }).catch(() => {});
}

$("dance-go").onclick = () => sendGameAction({ action: "start" });

// Letters Controls (Neumann formation)

function renderLetters() {
  if (!letterCfg) return;
  if ($("heading-slider") && document.activeElement !== $("heading-slider")) $("heading-slider").value = String(letterCfg.heading);
  if ($("heading-val")) $("heading-val").textContent = `${letterCfg.heading}°`;
  const align = letterCfg.align || "compass";
  const hand = !!letterCfg.hand;
  const lock = $("hand-lock");
  if (lock) {
    lock.classList.toggle("locked", hand);
    $("hand-lock-label").textContent = t(hand ? "hand_on" : "hand_off");
    $("hand-hint").textContent = t(hand ? "hand_on_hint" : "hand_off_hint");
  }
  document.querySelectorAll("#align-seg .seg").forEach((b) => { b.disabled = hand; });
  if ($("heading-slider")) $("heading-slider").disabled = hand;
  document.querySelectorAll("#align-seg .seg").forEach((b) => b.classList.toggle("active", b.dataset.align === align));
  if ($("align-hint")) $("align-hint").textContent = t(align === "compass" ? "align_compass_hint" : "align_aim_hint");

  const box = $("letter-rows");
  if (!box) return;
  box.innerHTML = "";
  const row = (target, big, color, who, stateText) => {
    const el = document.createElement("div");
    el.className = "letter-row";
    el.innerHTML = `<span class="letter-big" style="color:${color}"></span><span class="letter-who"></span>
      <span class="letter-state"></span>
      <span class="letter-group"><small></small>
        <button class="ghost sm" type="button" data-a="ccw">&#8634;</button>
        <button class="ghost sm" type="button" data-a="cw">&#8635;</button></span>
      <span class="letter-group"><small></small>
        <button class="ghost sm" type="button" data-a="left">&minus;15&deg;</button>
        <button class="ghost sm" type="button" data-a="right">+15&deg;</button></span>
      <button class="ghost sm" type="button" data-a="mirror"></button>
      <button class="ghost sm" type="button" data-a="reset"></button>`;
    el.querySelector(".letter-big").textContent = big;
    el.querySelector(".letter-who").textContent = who;
    el.querySelector(".letter-state").textContent = stateText;
    const groups = el.querySelectorAll(".letter-group small");
    groups[0].textContent = t("letter_word");
    groups[1].textContent = t("robot_word");
    el.querySelector('[data-a="ccw"]').title = t("letter_ccw");
    el.querySelector('[data-a="cw"]').title = t("letter_cw");
    el.querySelector('[data-a="left"]').title = t("robot_left");
    el.querySelector('[data-a="right"]').title = t("robot_right");
    el.querySelector('[data-a="mirror"]').textContent = t("mirror");
    el.querySelector('[data-a="reset"]').textContent = t("reset");
    el.querySelectorAll("button").forEach((b) => { b.onclick = () => changeLetters({ target, action: b.dataset.a }); });
    el.querySelectorAll('[data-a="left"], [data-a="right"]').forEach((b) => { b.disabled = !!letterCfg.hand; });
    box.appendChild(el);
  };
  letterCfg.letters.forEach((item, i) => {
    const turn = item.turn || 0;
    row(i, item.letter, NEUMANN_COLOR, `BOLT ${i + 1}`,
      `${item.rotation}°` + (turn ? ` · ${t("robot_word")} ${turn > 0 ? "+" : ""}${turn}°` : "")
      + (item.mirror ? ` · ${t("mirrored")}` : ""));
  });
  row("all", "*", "var(--muted)", t("all_three"), "");
}

document.querySelectorAll("#align-seg .seg").forEach((b) => {
  b.onclick = () => changeLetters({ align: b.dataset.align });
});
$("hand-lock").onclick = () => changeLetters({ hand: !(letterCfg && letterCfg.hand) });

function handleClientLetters(body) {
  if (body.heading !== undefined) letterCfg.heading = body.heading;
  if (body.align) letterCfg.align = body.align;
  if (body.hand !== undefined) letterCfg.hand = !!body.hand;
  if (body.target !== undefined && body.action) {
    const applyAction = (item) => {
      item.turn = item.turn || 0;
      if (body.action === "cw") item.rotation = (item.rotation + 90) % 360;
      if (body.action === "ccw") item.rotation = (item.rotation + 270) % 360;
      if (body.action === "mirror") item.mirror = !item.mirror;
      if (body.action === "left") item.turn = ((item.turn - 15 + 540) % 360) - 180;
      if (body.action === "right") item.turn = ((item.turn + 15 + 540) % 360) - 180;
      if (body.action === "reset") { item.rotation = 0; item.mirror = false; item.turn = 0; }
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
      if (l) {
        r.heading = (letterCfg.heading + (l.turn || 0) + 360) % 360;
        r.matrix = makeMatrix(l.letter, NEUMANN_COLOR, l.rotation, l.mirror);
      }
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
$("heading-slider").oninput = (e) => { $("heading-val").textContent = `${e.target.value}°`; };
$("heading-slider").onchange = (e) => changeLetters({ heading: Number(e.target.value) });

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
// 11. QR Code, Phones, Robot Fleet
// ==========================================
let connectedClients = [];
let maxClientSlots = 3;
let myRole = null;          // "host" | "controller" (from the server)
let mySlot = null;
let myColor = null;

async function initQRCode() {
  const box = $("qrcode-box");
  if (!box) return;
  let targetUrl = window.location.href;
  try {
    const res = await fetch("/api/info");
    if (res.ok) {
      const info = await res.json();
      if (info.url) targetUrl = info.url;
    }
  } catch (e) {}
  if ($("qr-url-text")) $("qr-url-text").textContent = targetUrl.replace(/^https?:\/\//, "");
  box.innerHTML = "";
  if (typeof QRCode !== "undefined") {
    new QRCode(box, {
      text: targetUrl, width: 264, height: 264,
      colorDark: "#181c20", colorLight: "#ffffff",
      correctLevel: QRCode.CorrectLevel.M,
    });
  }
}

const SLOT_COLORS = ["var(--r1)", "var(--r2)", "var(--r3)"];

function renderClients(clients, maxSlots) {
  connectedClients = clients || [];
  if (maxSlots) maxClientSlots = maxSlots;
  const n = connectedClients.length;
  if ($("slots-badge")) $("slots-badge").textContent = `${n} / ${maxClientSlots}`;
  if ($("phones-pill-text")) $("phones-pill-text").textContent = `${n} / ${maxClientSlots} ${t("phones_unit")}`;
  if ($("phones-pill")) $("phones-pill").className = "pill host-only" + (n > 0 ? " online" : "");

  const list = $("connected-devices-list");
  if (!list) return;
  list.innerHTML = "";
  if (n === 0) {
    list.innerHTML = `<div class="empty"></div>`;
    list.firstChild.textContent = t("no_devices_msg");
  }
  connectedClients.forEach((c, idx) => {
    const slot = c.slot || idx + 1;
    let idleStr;
    if (c.idle < 10) idleStr = t("active_now");
    else if (c.idle < 60) idleStr = t("idle_secs", { n: c.idle });
    else idleStr = t("idle_mins", { n: Math.floor(c.idle / 60) });

    const row = document.createElement("div");
    row.className = "device-row";
    row.innerHTML = `
      <span class="device-num" style="--c:${SLOT_COLORS[slot - 1] || "var(--accent)"}">${slot}</span>
      <span class="device-meta"><b></b><small></small></span>
      <button class="ghost sm" type="button"></button>`;
    row.querySelector("b").textContent = t("phone_n", { n: slot });
    row.querySelector("small").textContent = `${c.ip} · ${idleStr}`;
    const btn = row.querySelector("button");
    btn.textContent = t("disconnect_btn");
    btn.onclick = () => kickClient(c.id);
    list.appendChild(row);
  });
  renderDriveHint();
}

function renderDriveHint() {
  const hint = $("drive-hint");
  if (hint) hint.hidden = !(connectedClients.length > 0 && state.running !== "drive");
}

function kickClient(clientId) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "kick", client_id: clientId }));
  } else {
    fetch(`/api/clients/kick/${clientId}`, { method: "POST" }).catch(() => {});
  }
}

// ---------- Robot fleet ----------
let currentRobots = [];

function batteryClass(pct) {
  if (pct === null || pct === undefined) return "";
  return pct >= 70 ? "ok" : pct >= 30 ? "mid" : "low";
}

function renderRobotPool(robots) {
  if (robots) currentRobots = robots;
  const n = currentRobots.length;
  const low = currentRobots.filter((r) => typeof r.battery === "number" && r.battery < 30).length;

  if ($("robots-pill-text")) {
    $("robots-pill-text").textContent = `${n} ${t("robots_unit")}` + (low ? ` · ${t("low_batt", { n: low })}` : "");
  }
  if ($("robots-pill")) $("robots-pill").className = "pill host-only" + (low ? " warn" : n ? " online" : "");
  if ($("fleet-summary")) $("fleet-summary").textContent = n ? `${n}` + (low ? ` · ${t("low_batt", { n: low })}` : "") : "";

  const container = $("robot-pool-cards");
  if (!container) return;
  container.innerHTML = "";
  if (n === 0) {
    container.innerHTML = `<div class="empty"></div>`;
    container.firstChild.textContent = t("fleet_empty");
    return;
  }
  currentRobots.forEach((r, idx) => {
    const num = r.id || idx + 1;
    const color = (r.color && r.color.hex) || SLOT_COLORS[(num - 1) % 3];
    const hasBatt = typeof r.battery === "number";
    const assigned = !!r.slot;

    const b = document.createElement("button");
    b.type = "button";
    b.className = "bot" + (assigned ? " assigned" : "");
    b.dataset.robot = num;
    b.style.setProperty("--c", color);
    b.title = t("identify_title", { n: num }) + (assigned ? `\n${t("controlled_by", { n: r.slot })}` : "")
      + (hasBatt ? (r.voltage ? `\n${r.voltage} V` : "") : `\n${t("battery_unknown")}`);
    b.innerHTML = `
      <span class="bot-num">${num}</span>
      <span class="bot-meta">
        <span class="batt"><i class="bdot ${batteryClass(r.battery)}"></i>${hasBatt ? `${r.battery}%` : "&ndash;"}</span>
        <span class="bot-name"></span>
      </span>
      ${assigned ? `<span class="bot-phone"><svg class="icon"><use href="#i-phone"/></svg>${r.slot}</span>` : ""}`;
    b.querySelector(".bot-name").textContent = r.raw_name || r.name;
    b.onclick = () => identifyRobot(num);
    container.appendChild(b);
  });
}

function identifyRobot(id, quiet = false) {
  const card = document.querySelector(`.bot[data-robot="${id}"]`);
  if (card) {
    card.classList.remove("flash");
    void card.offsetWidth;
    card.classList.add("flash");
  }
  if (!quiet) toast(t("identify_sent", { n: id }));
  playTone(600, "sine", 0.08, 0.15);
  if (clientMode) {
    const bot = clientRobots[id - 1];
    if (bot) {
      shakeWobble[bot.name] = Date.now() + 600;
      bot.matrix = makeMatrix(String(id), bot.baseColor);
    }
    return Promise.resolve();
  }
  return fetch(`/api/robots/${id}/identify`, { method: "POST" }).catch(() => {});
}

$("btn-identify-all").onclick = async () => {
  toast(t("btn_identify_all"));
  const ids = currentRobots.length ? currentRobots.map((r, i) => r.id || i + 1) : [1, 2, 3];
  for (const id of ids) {
    identifyRobot(id, true);
    await new Promise((res) => setTimeout(res, 400));
  }
};

$("btn-refresh-robots").onclick = () => {
  const btn = $("btn-refresh-robots");
  btn.disabled = true;
  toast(t("refresh_started"));
  fetch("/api/robots/refresh", { method: "POST" })
    .then((r) => r.json())
    .then((d) => {
      if (d.robots) renderRobotPool(d.robots);
      if (d.ok) toast(t("refresh_done", { n: (d.robots || []).length }));
      else openLog();
    })
    .catch(() => {})
    .finally(() => { btn.disabled = false; });
};

// ---------- Phone controller view ----------
function handleSelfInfo(info) {
  if (!info) return;
  myRole = info.role;
  $("btn-admin-login").hidden = info.role !== "controller";
  $("btn-admin-logout").hidden = !info.remote_admin;
  if (info.role !== "controller") {
    document.body.classList.remove("role-controller");
    return;
  }
  mySlot = info.slot || 1;
  myColor = info.color || null;
  activeBotIndex = mySlot;
  document.body.classList.add("role-controller");
  switchTabForce("drive");
  renderAssignedBanner();
  renderControllerWait();
  renderCalib();
}

function switchTabForce(id) {
  document.querySelectorAll(".tab-page").forEach((page) => page.classList.toggle("active", page.id === `tab-${id}`));
}

function renderAssignedBanner() {
  const banner = $("mobile-assigned-banner");
  if (!banner || myRole !== "controller") return;
  const hex = (myColor && myColor.hex) || SLOT_COLORS[(mySlot - 1) % 3];
  const colorName = myColor ? (currentLang === "hu" ? myColor.name : myColor.en).toLowerCase() : "";
  banner.hidden = false;
  banner.style.setProperty("--c", hex);
  $("assigned-num").textContent = mySlot;
  $("assigned-slot-title").textContent = t("assigned_title", { n: mySlot });
  $("assigned-slot-desc").textContent = t("assigned_desc", { n: mySlot, color: colorName });
}

function renderControllerWait() {
  const el = $("controller-wait");
  if (el) el.hidden = !(myRole === "controller" && state.running !== "drive");
}

function handleControllerConnected(data) {
  const isAutoMap = store.get("auto_map_on_connect") !== "false";
  if (myRole === "controller" || !isAutoMap || (data && data.auto_map === false)) return;
  const arena = $("panel-arena");
  const target = arena && !arena.hidden ? arena : $("panel-phones");
  if (!target) return;
  target.classList.add("flash");
  setTimeout(() => target.classList.remove("flash"), 1800);
  target.scrollIntoView({ behavior: "smooth", block: "nearest" });
  if (data && data.slot) toast(t("phone_n", { n: data.slot }) + " +");
}

// ---------- Modals ----------
function showTimeoutModal(message) {
  const m = $("modal-timeout");
  if (!m) return;
  const desc = m.querySelector("[data-i18n='timeout_modal_desc']");
  if (desc) desc.textContent = message || t("timeout_modal_desc");
  m.hidden = false;
}

function showMaxClientsModal() {
  const m = $("modal-max-clients");
  if (m) m.hidden = false;
}

function closeMaxClientsModal() {
  const m = $("modal-max-clients");
  if (m) m.hidden = true;
}

function reconnectClient() {
  $("modal-timeout").hidden = true;
  $("modal-max-clients").hidden = true;
  suppressReconnect = false;
  wsRetry = 0;
  connect();
}

function openAdminModal() { $("modal-admin-settings").hidden = false; }
function closeAdminModal() { $("modal-admin-settings").hidden = true; }
$("btn-admin-settings").onclick = openAdminModal;
$("modal-admin-settings").onclick = (e) => { if (e.target.id === "modal-admin-settings") closeAdminModal(); };

// ---------- Admin login (phones) ----------
function openAdminLogin() {
  $("modal-admin-login").hidden = false;
  $("admin-login-error").hidden = true;
  $("admin-password").value = "";
  setTimeout(() => $("admin-password").focus(), 50);
}
function closeAdminLogin() { $("modal-admin-login").hidden = true; }

$("btn-admin-login").onclick = openAdminLogin;
$("admin-login-form").onsubmit = async (e) => {
  e.preventDefault();
  const err = $("admin-login-error");
  err.hidden = true;
  try {
    const r = await fetch("/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: $("admin-password").value }),
    });
    if (r.ok) {
      toast(t("admin_login_ok"));
      setTimeout(() => location.reload(), 400);   // reconnect as admin (frees the joystick slot)
      return;
    }
    err.textContent = t(r.status === 401 ? "admin_login_wrong" : "admin_login_failed");
  } catch (e2) {
    err.textContent = t("admin_login_failed");
  }
  err.hidden = false;
  $("admin-password").select();
};
$("btn-admin-logout").onclick = async () => {
  await fetch("/api/admin/logout", { method: "POST" }).catch(() => {});
  location.reload();
};

// An admin action refused by the server (phone not logged in, or password changed)
const _fetch = window.fetch.bind(window);
window.fetch = async (...args) => {
  const r = await _fetch(...args);
  if (r.status === 401 && String(args[0]).startsWith("/api/") && !String(args[0]).includes("/admin/")) {
    toast(t("admin_required"), true);
  }
  return r;
};

function onToggleAutoMap(checked) {
  store.set("auto_map_on_connect", checked ? "true" : "false");
  fetch("/api/settings/auto-map", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled: checked }),
  }).catch(() => {});
}

function onToggleLowPower(checked) {
  lowPowerMode = checked;
  store.set("sphero_low_power", checked ? "1" : "0");
  if ($("toggle-low-power")) $("toggle-low-power").checked = checked;
  fetch("/api/settings/low-power", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled: checked }),
  }).catch(() => {});
}

// Activity tracker: keeps a phone from timing out while it is being used
let lastActivityTime = 0;
function markUserActive() {
  const now = Date.now();
  if (now - lastActivityTime > 15000) {
    lastActivityTime = now;
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "ping" }));
  }
}
window.addEventListener("pointerdown", markUserActive);
window.addEventListener("keydown", markUserActive);

// ==========================================
// 12. Server Connection (WebSocket)
// ==========================================
function handleWsMessage(e) {
  const msg = JSON.parse(e.data);
  if (msg.type === "status") {
    state = msg;
    if (typeof msg.low_spec === "boolean" && store.get("sphero_low_power") === null) {
      lowPowerMode = msg.low_spec;
      if ($("toggle-low-power")) $("toggle-low-power").checked = lowPowerMode;
    }
    renderStatus();
  } else if (msg.type === "log") {
    addLine(msg.line);
    if (/collision!|BOOM!/i.test(msg.line)) playBoom();
    else if (/Passed!/i.test(msg.line)) playPop();
    else if (/Wrong ball/i.test(msg.line)) playBuzzer();
    else if (/Level \d+ done|wins the/i.test(msg.line)) playVictory();
  } else if (msg.type === "letters") {
    letterCfg = msg.config;
    renderLetters();
  } else if (msg.type === "game") {
    const prevPhase = gameState ? gameState.phase : null;
    gameState = msg.state;
    if (gameState && gameState.phase === "boom" && prevPhase !== "boom") playBoom();
    if (gameState && gameState.kind === "party" && gameState.game) selectedGame = gameState.game;
    else if (gameState && gameState.kind === "dance") selectedShow = "dance";
    else if (gameState) selectedGame = "tictactoe";
    renderProgramLists();
    renderGame();
    renderParty();
    renderDance();
  } else if (msg.type === "telemetry") {
    updateTelemetry(msg.data);
  } else if (msg.type === "history") {
    $("log").innerHTML = "";
    msg.lines.forEach((l) => addLine(l.line));
    unreadLog = 0; unreadErr = false;
    renderLogBadge();
  } else if (msg.type === "clients") {
    renderClients(msg.clients, msg.max || 3);
  } else if (msg.type === "robot_pool") {
    renderRobotPool(msg.robots);
    renderDance();
  } else if (msg.type === "self_info") {
    handleSelfInfo(msg);
  } else if (msg.type === "controller_connected") {
    handleControllerConnected(msg);
  } else if (msg.type === "dance") {
    danceCfg = msg.config || { exclude: [] };
    renderDance();
  } else if (msg.type === "minigames") {
    if (msg.config) {
      if (msg.config.simon) partyConfig.simon = { ...partyConfig.simon, ...msg.config.simon };
      if (msg.config.mole) partyConfig.mole = { ...partyConfig.mole, ...msg.config.mole };
      try {
        localStorage.setItem("sphero_party_config", JSON.stringify(partyConfig));
      } catch (e) {}
      renderPartySettings();
    }
  } else if (msg.type === "calibration") {
    calibOffsets = msg.offsets || {};
    renderCalib();
  } else if (msg.type === "settings") {
    if (typeof msg.auto_map === "boolean" && $("toggle-auto-map")) $("toggle-auto-map").checked = msg.auto_map;
    if (typeof msg.low_spec === "boolean") {
      lowPowerMode = msg.low_spec;
      if ($("toggle-low-power")) $("toggle-low-power").checked = msg.low_spec;
    }
  } else if (msg.type === "error" && msg.code === "MAX_CLIENTS") {
    suppressReconnect = true;
    showMaxClientsModal();
  } else if (msg.type === "timeout" || msg.type === "kicked") {
    suppressReconnect = true;
    showTimeoutModal(msg.message);
  }
}

function connectCustomServer(hostUrl) {
  const target = hostUrl.trim().replace(/^(https?|wss?):\/\//, "").replace(/\/+$/, "").replace(/\/ws$/, "");
  if (!target) return;
  const wsUrl = `ws://${target}/ws`;
  addLine(`Connecting to ${wsUrl}...`);
  if (ws) { try { ws.close(); } catch (e) {} }
  try {
    ws = new WebSocket(wsUrl);
    ws.onopen = () => {
      online = true;
      clientMode = false;
      connectedTarget = target;
      renderStatus();
      closeBluetoothModal();
      playVictory();
      addLine(`=== Connected to server: ${target} ===`);
    };
    ws.onerror = () => {
      toast(`${wsUrl}: connection failed`, true);
      addLine(`Connection to ${wsUrl} failed. Is the server running with --host 0.0.0.0 on the same Wi-Fi?`);
    };
    ws.onclose = () => {
      online = false;
      connectedTarget = null;
      renderStatus();
    };
    ws.onmessage = handleWsMessage;
  } catch (err) {
    toast(`${err.message || err}`, true);
  }
}

$("btn-connect-server").onclick = () => {
  const input = $("input-server-url");
  if (input && input.value.trim()) connectCustomServer(input.value.trim());
};
$("input-server-url").addEventListener("keydown", (e) => {
  if (e.key === "Enter") $("btn-connect-server").click();
});

let wsRetry = 0;
let suppressReconnect = false;

function connect() {
  const isStatic = location.protocol === "file:" ||
    location.hostname.endsWith("github.io") ||
    location.hostname.endsWith("vercel.app");

  if (isStatic) {
    enableClientMode();
    return;
  }

  try {
    ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
    ws.onopen = () => {
      online = true;
      clientMode = false;
      connectedTarget = null;
      wsRetry = 0;
      renderStatus();
      fetch("/api/letters").then((r) => (r.ok ? r.json() : null)).then((cfg) => {
        if (cfg) { letterCfg = cfg; renderLetters(); }
      }).catch(() => {});
    };
    ws.onclose = () => {
      online = false;
      connectedTarget = null;
      renderStatus();
      if (suppressReconnect) return;
      wsRetry++;
      if (wsRetry === 3) {
        enableClientMode();
        addLine(t("offline_sim"));
      }
      // keep retrying in the background so a restarted server is picked up again
      setTimeout(connect, Math.min(10000, 1500 * wsRetry));
    };
    ws.onmessage = handleWsMessage;
  } catch (e) {
    enableClientMode();
  }
}

// ==========================================
// 13. Startup
// ==========================================
function refreshAllViews() {
  updateSoundButton();
  renderStatus();
  renderClients(connectedClients);
  renderRobotPool();
  renderBotSelector();
  renderGame();
  renderParty();
  renderPartySettings();
  renderLetters();
  renderAssignedBanner();
  if ($("toggle-low-power")) $("toggle-low-power").checked = lowPowerMode;
  if ($("arena-stats")) $("arena-stats").textContent = t("arena_stats", { n: arenaRobots.length });
}

loadStoredPartyConfig();
initPartySettingsControls();
initClientRobots(3);
setLanguage(currentLang);
initQRCode();
connect();
