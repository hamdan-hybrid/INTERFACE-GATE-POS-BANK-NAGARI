#!/usr/bin/env python3
"""Serial monitor ESP32 (DTR/RTS mati agar board tidak ter-reset).
Tanpa dependensi (tidak perlu pyserial), khusus Linux.
Pakai: python3 monitor.py [port] [baud]  - ketik teks + Enter untuk kirim ke ESP, Ctrl+C keluar
"""
import fcntl
import os
import select
import struct
import sys
import termios

port = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB0"
baud = int(sys.argv[2]) if len(sys.argv) > 2 else 115200
speed = getattr(termios, f"B{baud}")

fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)

# Matikan DTR/RTS supaya ESP32 tidak reset / masuk mode boot
TIOCM_DTR, TIOCM_RTS = 0x002, 0x004
fcntl.ioctl(fd, termios.TIOCMBIC, struct.pack("I", TIOCM_DTR | TIOCM_RTS))

# Mode raw 8N1
attr = termios.tcgetattr(fd)
attr[0] = 0                                   # iflag
attr[1] = 0                                   # oflag
attr[2] = termios.CS8 | termios.CREAD | termios.CLOCAL  # cflag (tanpa HUPCL)
attr[3] = 0                                   # lflag
attr[4] = attr[5] = speed
termios.tcsetattr(fd, termios.TCSANOW, attr)

print(f"Monitor {port} @ {baud} - ketik lalu Enter untuk kirim, Ctrl+C untuk keluar")

try:
    while True:
        r, _, _ = select.select([fd, sys.stdin], [], [])
        if fd in r:
            try:
                data = os.read(fd, 256)
            except BlockingIOError:
                data = b""
            if data:
                sys.stdout.write(data.decode(errors="replace"))
                sys.stdout.flush()
        if sys.stdin in r:
            line = sys.stdin.readline()
            if not line:
                break
            os.write(fd, line.encode())
except KeyboardInterrupt:
    pass
finally:
    os.close(fd)
