iplist - LAN Device Manager
===========================

A web-based tool for tracking devices on your home LAN. Scans the network using
nmap, enriches results with ARP table lookups, and streams discovered devices to
the browser in real-time via Server-Sent Events (SSE).

Devices are identified by MAC address (stable across DHCP reassignments) and
stored in a local SQLite database. You can label each device with a description
to quickly find and connect to it later.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   getting-started
   usage
   architecture
   api
