# TallyPi

ATEM to Smartview tally bridge for Raspberry Pi.

Listens for program/preview changes from a Blackmagic ATEM switcher and sends tally border commands to a Blackmagic Smartview monitor.

## Features

- Uses the simple Videohub protocol (TCP port 9990) for reliable ATEM communication
- Real-time tally updates when switching sources
- Red border for program, green border for preview
- Auto-reconnect on connection loss
- Runs as a systemd service

## Hardware

- Raspberry Pi (tested on Pi Zero 2W)
- Blackmagic ATEM switcher (tested on ATEM Mini Pro ISO)
- Blackmagic Smartview monitor (tested on Smartview Duo 2)

## Configuration

Edit `tallypi.py` to set your device IPs:

```python
ATEM_IP = "192.168.1.XX2"
SMARTVIEW_IP = "192.168.1.XX1"
```

Configure input-to-monitor mapping:

```python
INPUT_TO_MONITOR = {
    1: (0, False),  # Camera 1 -> Monitor A
    2: (1, False),  # Camera 2 -> Monitor B
}
```

## Installation

1. Copy `tallypi.py` to `/home/pi/tallypi/`
2. Copy `tallypi.service` to `/etc/systemd/system/`
3. Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable tallypi
sudo systemctl start tallypi
```

## Usage

```bash
# Check status
sudo systemctl status tallypi

# View logs
journalctl -u tallypi -f

# Restart after config changes
sudo systemctl restart tallypi
```

