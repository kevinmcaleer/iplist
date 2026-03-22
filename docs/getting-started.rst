Getting Started
===============

Prerequisites
-------------

- Python 3.11+
- nmap (network scanner)

Install nmap on macOS::

    brew install nmap

Install nmap on Debian/Ubuntu::

    sudo apt install nmap

Installation
------------

Clone the repository and install dependencies::

    git clone https://github.com/kevinmcaleer/iplist.git
    cd iplist
    pip install -r requirements.txt

Running
-------

Start the server::

    uvicorn main:app --reload --host 0.0.0.0

Then open http://localhost:8000 in your browser.

The ``--host 0.0.0.0`` flag makes the server accessible from other devices on
your LAN, so you can check it from your phone or another computer.

Running with sudo
^^^^^^^^^^^^^^^^^

Without sudo, nmap uses TCP ping and relies on the system ARP cache for MAC
addresses. With sudo, nmap can send ARP requests directly and will discover
more devices::

    sudo uvicorn main:app --reload --host 0.0.0.0
