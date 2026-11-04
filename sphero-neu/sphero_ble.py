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
import re
import subprocess
import threading
import time
from pathlib import Path

import bleak
from spherov2 import scanner

SCAN_TIMEOUT = 15.0
CONNECT_TIMEOUT = 30.0
ATTEMPTS = 3


def forget_device(address):
    """Removes the device from the BlueZ cache (no sudo needed)."""
    subprocess.run(["bluetoothctl", "remove", address],
                   capture_output=True, text=True, timeout=10)


def release_stale(prefix="SB-", log=print):
    """Disconnects robots that BlueZ still holds from a program that ended
    without disconnecting. Each one blocks a connection slot of the adapter.
    Call only when none of our programs is running."""
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
    async def scan():
        return await bleak.BleakScanner.discover(timeout, return_adv=True)
    found = {}
    for device, adv in asyncio.run(scan()).values():
        name = adv.local_name or device.name
        if name and name.upper().startswith(prefix):
            found[name.upper()] = (name.upper(), device.address, adv.rssi)
    return sorted(found.values(), key=lambda t: -t[2])


def find_toy(name, timeout=SCAN_TIMEOUT, toy_type=scanner.BOLT, adapter=None):
    """Scans for one robot by name. Returns a spherov2 toy using our adapter
    (through Bluetooth adapter `adapter`, None = default)."""
    toys = scanner.find_toys(timeout=timeout, toy_types=[toy_type],
                             toy_names=[name], adapter=adapter_class(adapter))
    if not toys:
        raise scanner.ToyNotFoundError(f"{name} not found within {timeout:.0f} s")
    return toys[0]


def connect_toy(name, enter, attempts=ATTEMPTS, log=print, adapter=None):
    """
    Finds robot `name` and enters a context on it, with retries.

    `enter(toy)` must return the entered context (for example
    stack.enter_context(SpheroEduAPI(toy))). A fresh scan runs before every
    attempt, and the BlueZ cache entry is removed after a failed attempt.
    """
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
            time.sleep(2)
    raise ConnectionError(f"{name}: no connection after {attempts} attempts") from last
