Architecture
============

Project Structure
-----------------

::

    iplist/
    ├── main.py            FastAPI application and API routes
    ├── database.py        SQLite setup and queries
    ├── scanner.py         nmap wrapper and ARP table parsing
    ├── static/
    │   └── index.html     Single-page frontend (vanilla JS)
    ├── requirements.txt   Python dependencies
    └── devices.db         SQLite database (created at runtime)

Backend
-------

The backend is a Python FastAPI application with three modules:

**main.py** -- the FastAPI app. Serves the static frontend and exposes the REST
API. The ``/api/scan`` endpoint returns a Server-Sent Events stream.

**scanner.py** -- wraps nmap and the system ARP table. The ``scan_network_stream``
generator yields devices one at a time as nmap discovers them. It uses a
pseudo-tty (``pty`` module) so that nmap flushes its output per-host instead of
buffering everything until the scan completes.

**database.py** -- manages the SQLite database. Uses MAC address as the primary
key since it's the only stable device identifier when IPs change via DHCP.

Data Model
----------

The ``devices`` table:

===========  =======  ==========================================
Column       Type     Description
===========  =======  ==========================================
mac          TEXT     Primary key -- device MAC address
ip           TEXT     Last known IP address
hostname     TEXT     Hostname from nmap / reverse DNS
description  TEXT     User-provided label
last_seen    TEXT     ISO 8601 timestamp of last scan detection
is_online    INTEGER  1 if found in most recent scan, else 0
===========  =======  ==========================================

Network Scanning
----------------

The scanning process:

1. Auto-detects the local /24 subnet from the default network interface
2. Pre-fetches the system ARP table (``arp -an``) for MAC address lookups
3. Marks all existing devices as offline
4. Runs ``nmap -sn --unprivileged <subnet>`` via a pseudo-tty
5. Parses stdout line-by-line, yielding each device as it appears
6. Enriches devices with MAC addresses from the ARP table
7. Upserts each device into SQLite and marks it online

Frontend
--------

The frontend is a single HTML file with embedded CSS and vanilla JavaScript.
It uses ``EventSource`` (SSE) to consume the scan stream and updates the table
in real-time as devices are discovered. No build step or framework required.
