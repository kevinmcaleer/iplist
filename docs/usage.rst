Usage
=====

Scanning the Network
--------------------

Click the **Scan Network** button to start a network scan. Devices appear in the
table as they are discovered -- you don't need to wait for the full scan to
complete.

The scan:

1. Runs ``nmap -sn`` (ping sweep) on your local /24 subnet (plus any extra subnets)
2. Reads the system ARP table to resolve MAC addresses
3. Streams each discovered device to the browser via SSE
4. Saves results to the SQLite database

Previously known devices that are not found during a scan are marked as offline.

Multiple Subnets
^^^^^^^^^^^^^^^^

By default the scanner auto-detects your local /24 subnet. If your network spans
additional subnets, add them to the ``.env`` file in the project root::

    EXTRA_SUBNETS=192.168.2.0/24

Multiple extra subnets can be comma-separated::

    EXTRA_SUBNETS=192.168.2.0/24,10.0.0.0/24

The status bar shows which subnets are being scanned during a scan.

Managing Devices
----------------

Descriptions
^^^^^^^^^^^^

Click the description field next to any device to add a label (e.g. "Living room
TV", "Printer", "Raspberry Pi"). Descriptions are saved automatically when you
press Enter or click away.

Descriptions persist across scans -- when a device's IP changes due to DHCP, the
description stays attached to its MAC address.

Filtering
^^^^^^^^^

Use the **Filter devices** search box to filter the table by any field: IP
address, MAC address, hostname, or description. The filter updates as you type.

Clickable Hostnames
^^^^^^^^^^^^^^^^^^^

When a device is online and has a resolved hostname, the hostname is displayed as
a clickable link. Clicking it opens ``http://<device-ip>`` in a new browser tab,
which is handy for quickly accessing routers, printers, and other devices that
expose a web interface.

Copying IP Addresses
^^^^^^^^^^^^^^^^^^^^

Click any IP address in the table to copy it to your clipboard. A toast
notification confirms the copy.

Removing Devices
^^^^^^^^^^^^^^^^

Click the **x** button on any row to remove a device from the database. This is
useful for cleaning up devices that are no longer on your network.

Backup & Restore
----------------

The ``backup.py`` script lets you export the entire device database as a SQL
script and restore it later. This is useful for migrating to a new machine or
keeping periodic snapshots.

Creating a Backup
^^^^^^^^^^^^^^^^^

Print the backup SQL to the terminal::

    python backup.py

Save the backup to a file::

    python backup.py -o backup.sql

You can also redirect stdout::

    python backup.py > backup.sql

Restoring from a Backup
^^^^^^^^^^^^^^^^^^^^^^^^

Restore a previously saved backup::

    python backup.py --restore backup.sql

This replaces the contents of the database with the data in the backup file.

Using a Custom Database Path
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Both backup and restore accept ``--db`` to specify an alternate database file::

    python backup.py --db /path/to/devices.db -o backup.sql
    python backup.py --db /path/to/devices.db --restore backup.sql
