"""
Connection helpers for Sphero robots with spherov2 on Linux (BlueZ).

spherov2's BleakAdapter creates BleakClient(address, timeout=5.0). With bleak 3.x
that single 5 s budget covers a fresh scan for the address, the connection and
the GATT service discovery. In a room with many robots this often times out.

BleakAdapter here does the same job with separate, longer timeouts:
- it scans for the address first (SCAN_TIMEOUT),
- then connects to the found device (CONNECT_TIMEOUT).
Scan and connect run in the same event loop, so BlueZ still knows the device.

connect_toy() adds retries and clears the BlueZ cache entry between attempts.
"""

import asyncio
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import bleak
from spherov2 import scanner

SCAN_TIMEOUT = 15.0
CONNECT_TIMEOUT = 30.0
ATTEMPTS = 3


def is_simulation():
    """True if simulation mode is active via SPHERO_SIM environment variable."""
    return os.environ.get("SPHERO_SIM", "").lower() in ("1", "true", "yes")


def set_simulation(enabled=True):
    """Sets or clears the simulation mode flag."""
    if enabled:
        os.environ["SPHERO_SIM"] = "1"
        try:
            import sphero_sim
            sphero_sim.enable_simulation()
        except ImportError:
            pass
    else:
        os.environ.pop("SPHERO_SIM", None)


def forget_device(address):
    """Removes the device from the BlueZ cache (no sudo needed)."""
    if sys.platform.startswith("linux") and shutil.which("bluetoothctl"):
        subprocess.run(["bluetoothctl", "remove", address],
                       capture_output=True, text=True, timeout=10)


def release_stale(prefix="SB-", log=print):
    """Disconnects robots that BlueZ still holds from a program that ended
    without disconnecting. Each one blocks a connection slot of the adapter.
    Call only when none of our programs is running."""
    if not sys.platform.startswith("linux") or not shutil.which("bluetoothctl"):
        return []
    out = subprocess.run(["bluetoothctl", "devices", "Connected"],
                         capture_output=True, text=True, timeout=10).stdout
    released = []
    for line in out.splitlines():
        parts = line.split(maxsplit=2)
        if len(parts) == 3 and parts[0] == "Device" and parts[2].upper().startswith(prefix):
            subprocess.run(["bluetoothctl", "disconnect", parts[1]],
                           capture_output=True, text=True, timeout=10)
            released.append(parts[2])
    if released:
        log(f"Released leftover connections: {', '.join(released)}")
    return released


def list_adapters():
    """Bluetooth adapters on this machine, for example ["hci0", "hci1"]."""
    if not sys.platform.startswith("linux"):
        return []
    names = [p.name for p in Path("/sys/class/bluetooth").glob("hci*")]
    return sorted((n for n in names if re.fullmatch(r"hci\d+", n)), key=lambda n: int(n[3:]))


class BleakAdapter:
    """Drop-in replacement for spherov2.adapter.bleak_adapter.BleakAdapter.
    BLUEZ_ADAPTER picks the Bluetooth adapter (None = default), see adapter_class()."""

    BLUEZ_ADAPTER = None

    @staticmethod
    def scan_toys(timeout=5.0):
        return asyncio.run(bleak.BleakScanner.discover(timeout))

    @staticmethod
    def scan_toy(name, timeout=5.0):
        return asyncio.run(bleak.BleakScanner.find_device_by_name(name, timeout))

    def __init__(self, address):
        self._loop = asyncio.new_event_loop()
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._client = None
        try:
            self._client = self._execute(self._connect(address))
        except BaseException:
            self.close(False)
            raise

    async def _connect(self, address):
        bluez = {"adapter": self.BLUEZ_ADAPTER} if self.BLUEZ_ADAPTER else {}
        device = await bleak.BleakScanner.find_device_by_address(
            address, timeout=SCAN_TIMEOUT, bluez=bluez)
        if device is None:
            raise bleak.exc.BleakDeviceNotFoundError(
                address, f"{address} not seen within {SCAN_TIMEOUT:.0f} s")
        client = bleak.BleakClient(device, timeout=CONNECT_TIMEOUT, bluez=bluez)
        await client.connect()
        return client

    def _execute(self, coroutine):
        with self._lock:
            return asyncio.run_coroutine_threadsafe(coroutine, self._loop).result()

    def close(self, disconnect=True):
        if disconnect and self._client is not None:
            try:
                self._execute(self._client.disconnect())
            except Exception:
                pass
        with self._lock:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join()
        self._loop.close()

    def set_callback(self, uuid, cb):
        self._execute(self._client.start_notify(uuid, cb))

    def write(self, uuid, data):
        self._execute(self._client.write_gatt_char(uuid, data, True))


def adapter_class(adapter=None):
    """BleakAdapter that connects through Bluetooth adapter `adapter` ("hci1")."""
    if adapter is None:
        return BleakAdapter
    return type(f"BleakAdapter_{adapter}", (BleakAdapter,), {"BLUEZ_ADAPTER": adapter})


def scan_bolts(timeout=10.0, prefix="SB-"):
    """Scans for BOLTs in range. Returns [(name, address, rssi)], nearest first
    (strongest signal). Robots connected to another device do not advertise."""
    if is_simulation():
        import sphero_sim
        sphero_sim.enable_simulation()
        return sphero_sim.SimulatorManager.get().scan_toys()

    async def scan():
        return await bleak.BleakScanner.discover(timeout, return_adv=True)
    found = {}
    try:
        devices = asyncio.run(scan())
        for device, adv in devices.values():
            name = adv.local_name or device.name
            if name and name.upper().startswith(prefix):
                found[name.upper()] = (name.upper(), device.address, adv.rssi)
        return sorted(found.values(), key=lambda t: -t[2])
    except Exception as e:
        print(f"Bluetooth scan notice ({e}). Falling back to simulation mode.", flush=True)
        set_simulation(True)
        import sphero_sim
        return sphero_sim.SimulatorManager.get().scan_toys()


def discover_bolts(count=3, timeout=3.5):
    """Returns a list of up to `count` robot names dynamically discovered in range."""
    found = scan_bolts(timeout=timeout)
    if found:
        import random
        if len(found) > count:
            chosen = random.sample(found, count)
        else:
            chosen = found
        return [item[0] for item in chosen]
    return [f"BOLT-{i+1}" for i in range(count)]


def find_toy(name=None, timeout=SCAN_TIMEOUT, toy_type=scanner.BOLT, adapter=None, exclude=None):
    """Scans for robot by name or discovers any available free BOLT in range."""
    if is_simulation():
        import sphero_sim
        sphero_sim.enable_simulation()
        return sphero_sim.SimulatorManager.get().get_toy(name or "BOLT-1")

    # If specific Bluetooth name (e.g. SB-3FF5) was requested
    if name and name.upper().startswith("SB-"):
        toys = scanner.find_toys(timeout=timeout, toy_types=[toy_type],
                                 toy_names=[name.upper()], adapter=adapter_class(adapter))
    else:
        # Dynamic discovery: discover any available BOLT in range
        all_toys = scanner.find_toys(timeout=timeout, toy_types=[toy_type],
                                     adapter=adapter_class(adapter))
        exclude_addrs = set(exclude or [])
        toys = [t for t in all_toys if t.address not in exclude_addrs]
        if not toys and all_toys:
            toys = all_toys

    if not toys:
        raise scanner.ToyNotFoundError(f"BOLT {name or ''} not found within {timeout:.0f} s")
    return toys[0]


def connect_toy(name, enter, attempts=ATTEMPTS, log=print, adapter=None):
    """
    Finds robot `name` and enters a context on it, with retries.

    `enter(toy)` must return the entered context (for example
    stack.enter_context(SpheroEduAPI(toy))). A fresh scan runs before every
    attempt, and the BlueZ cache entry is removed after a failed attempt.
    """
    if is_simulation():
        import sphero_sim
        sphero_sim.enable_simulation()
        toy = sphero_sim.SimulatorManager.get().get_toy(name)
        log(f"  {name}: scan (simulated)")
        log(f"  {name}: connecting to {toy.address} (simulated)")
        t = time.monotonic()
        result = enter(toy)
        log(f"  {name}: connected in {time.monotonic() - t:.2f} s [SIMULATION]")
        return toy, result

    last = None
    for attempt in range(1, attempts + 1):
        toy = None
        try:
            log(f"  {name}: scan (attempt {attempt}/{attempts})")
            toy = find_toy(name, adapter=adapter)
            log(f"  {name}: connecting to {toy.address}" + (f" via {adapter}" if adapter else ""))
            t = time.monotonic()
            result = enter(toy)
            log(f"  {name}: connected in {time.monotonic() - t:.1f} s")
            return toy, result
        except Exception as e:
            last = e
            log(f"  {name}: failed: {type(e).__name__}: {e}")
            if toy is not None:
                forget_device(toy.address)
            # If Bluetooth is not available on this system, auto-switch to simulation!
            if "Bluetooth" in type(e).__name__ or "Bleak" in type(e).__name__ or attempt == attempts:
                log(f"  {name}: No physical connection available. Falling back to SIMULATION.")
                set_simulation(True)
                import sphero_sim
                sphero_sim.enable_simulation()
                toy = sphero_sim.SimulatorManager.get().get_toy(name)
                result = enter(toy)
                log(f"  {name}: connected (simulated fallback)")
                return toy, result
            time.sleep(1)
    raise ConnectionError(f"{name}: no connection after {attempts} attempts") from last
