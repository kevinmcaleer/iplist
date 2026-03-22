API Reference
=============

All endpoints are served from the FastAPI application on port 8000 by default.

List Devices
------------

.. code-block:: text

    GET /api/devices?online_only=false

Returns all known devices as a JSON array.

**Query parameters:**

- ``online_only`` (bool, optional) -- if ``true``, only return devices that were
  found in the most recent scan. Default: ``false``.

**Response:**

.. code-block:: json

    [
        {
            "mac": "AA:BB:CC:DD:EE:FF",
            "ip": "192.168.1.100",
            "hostname": "mydevice.lan",
            "description": "Living room TV",
            "last_seen": "2026-03-22T08:00:00+00:00",
            "is_online": 1
        }
    ]

Scan Network (SSE)
------------------

.. code-block:: text

    GET /api/scan

Triggers a network scan and streams results as Server-Sent Events. Each event
contains a single discovered device. The final event signals scan completion.

**Device event:**

.. code-block:: text

    data: {"mac": "AA:BB:CC:DD:EE:FF", "ip": "192.168.1.100", "hostname": "mydevice.lan", "is_online": 1, "last_seen": "..."}

**Completion event:**

.. code-block:: text

    data: {"done": true, "scanned": 16}

Update Device
-------------

.. code-block:: text

    PUT /api/devices/{mac}

Update a device's description or hostname.

**Request body:**

.. code-block:: json

    {
        "description": "Living room TV",
        "hostname": "custom-name"
    }

Both fields are optional -- only include the fields you want to change.

**Response:**

.. code-block:: json

    {"ok": true}

Delete Device
-------------

.. code-block:: text

    DELETE /api/devices/{mac}

Remove a device from the database.

**Response:**

.. code-block:: json

    {"ok": true}
