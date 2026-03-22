import os
import pty
import subprocess
import re
from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from database import upsert_device, mark_all_offline

load_dotenv(Path(__file__).parent / ".env")


def get_local_subnet() -> str:
    """Auto-detect the local /24 subnet (e.g. 192.168.1.0/24) from default route interface."""
    try:
        # macOS: get default interface
        route = subprocess.run(
            ["route", "-n", "get", "default"],
            capture_output=True, text=True, timeout=5,
        )
        iface = None
        for line in route.stdout.splitlines():
            if "interface:" in line:
                iface = line.split(":")[1].strip()
                break

        if not iface:
            return "192.168.1.0/24"

        # Get IP from ifconfig
        ifconfig = subprocess.run(
            ["ifconfig", iface],
            capture_output=True, text=True, timeout=5,
        )
        for line in ifconfig.stdout.splitlines():
            m = re.search(r"inet (\d+\.\d+\.\d+)\.\d+", line)
            if m:
                # Always use /24 — home LANs are virtually always /24
                return f"{m.group(1)}.0/24"
    except Exception:
        pass

    return "192.168.1.0/24"


def get_arp_table() -> dict[str, str]:
    """Read the system ARP table. Returns {ip: mac}."""
    arp_map = {}
    try:
        result = subprocess.run(
            ["arp", "-an"],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.splitlines():
            # macOS: ? (192.168.1.1) at aa:bb:cc:dd:ee:ff on en0 ...
            m = re.search(r"\((\d+\.\d+\.\d+\.\d+)\) at ([0-9a-f:]+)", line, re.IGNORECASE)
            if m and m.group(2) != "(incomplete)":
                mac = normalize_mac(m.group(2))
                if mac:
                    arp_map[m.group(1)] = mac
    except Exception:
        pass
    return arp_map


def normalize_mac(mac: str) -> str | None:
    """Normalize MAC to uppercase AA:BB:CC:DD:EE:FF format."""
    parts = mac.split(":")
    if len(parts) != 6:
        return None
    try:
        return ":".join(p.upper().zfill(2) for p in parts)
    except Exception:
        return None


def get_subnets() -> list[str]:
    """Return list of subnets to scan: auto-detected + any extra from EXTRA_SUBNETS env var."""
    subnets = [get_local_subnet()]
    extra = os.environ.get("EXTRA_SUBNETS", "")
    if extra:
        for s in extra.split(","):
            s = s.strip()
            if s and s not in subnets:
                subnets.append(s)
    return subnets


def _scan_single_subnet(
    subnet: str, arp_table: dict[str, str], now: str
) -> Generator[dict, None, None]:
    """Scan one subnet with nmap and yield devices as they're discovered."""
    primary_fd, replica_fd = pty.openpty()

    proc = subprocess.Popen(
        ["nmap", "-sn", "--unprivileged", subnet],
        stdout=replica_fd,
        stderr=subprocess.DEVNULL,
        text=False,
    )
    os.close(replica_fd)  # close child side in parent

    stdout_file = os.fdopen(primary_fd, "r", encoding="utf-8", errors="replace")

    current_ip = None
    current_hostname = None
    current_mac = None

    while True:
        try:
            line = stdout_file.readline()
        except OSError:
            break
        if not line:
            break
        line = line.rstrip()

        # Match: Nmap scan report for hostname (ip) or just ip
        report = re.match(
            r"Nmap scan report for (?:(.+?) \()?(\d+\.\d+\.\d+\.\d+)\)?", line
        )
        if report:
            device = _finalize_device(current_ip, current_mac, current_hostname, arp_table, now)
            if device:
                yield device

            current_hostname = report.group(1) or ""
            current_ip = report.group(2)
            current_mac = None
            continue

        # Match: MAC Address: AA:BB:CC:DD:EE:FF (Vendor)
        mac_match = re.match(r"MAC Address: ([0-9A-F:]{17})", line)
        if mac_match:
            current_mac = mac_match.group(1).upper()

    # Emit the last device
    device = _finalize_device(current_ip, current_mac, current_hostname, arp_table, now)
    if device:
        yield device

    stdout_file.close()
    proc.wait()


def scan_network_stream(subnets: list[str] | None = None) -> Generator[dict, None, None]:
    """Stream devices from one or more subnets as nmap discovers them."""
    if subnets is None:
        subnets = get_subnets()

    # Pre-fetch ARP table so we can enrich results immediately
    arp_table = get_arp_table()
    now = datetime.now(timezone.utc).isoformat()

    mark_all_offline()

    for subnet in subnets:
        yield from _scan_single_subnet(subnet, arp_table, now)


def _finalize_device(
    ip: str | None,
    mac: str | None,
    hostname: str | None,
    arp_table: dict[str, str],
    now: str,
) -> dict | None:
    """Resolve MAC via ARP if needed, upsert to DB, return device dict or None."""
    if not ip:
        return None

    # Try ARP table if nmap didn't report a MAC (non-sudo mode)
    if not mac and ip in arp_table:
        mac = arp_table[ip]

    if not mac:
        return None

    hostname = hostname or ""
    upsert_device(mac=mac, ip=ip, hostname=hostname, last_seen=now)

    return {"mac": mac, "ip": ip, "hostname": hostname, "is_online": 1, "last_seen": now}
