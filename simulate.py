#!/usr/bin/env python3
# simulate elevator field data for testing
# sends realistic CAN frames + serial data

import os
import time
import struct
import random
import signal
import threading

running = True
CAN_CHANNEL = os.environ.get("CAN_INTERFACE", "vcan0")
SERIAL_DEV = os.environ.get("SERIAL_DEV", "")


def log(msg):
    print(f"[sim] {msg}", flush=True)


def signal_handler(sig, frame):
    global running
    log("shutting down...")
    running = False


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def simulate_can():
    try:
        import can
    except ImportError:
        log("python-can not installed, skipping CAN")
        return

    log(f"CAN on {CAN_CHANNEL}")
    floor = 1
    dir_mult = 1

    while running:
        try:
            bus = can.Bus(interface="socketcan", channel=CAN_CHANNEL, receive_own_messages=False)
        except OSError as e:
            log(f"Cannot open {CAN_CHANNEL}: {e}")
            time.sleep(3)
            continue

        while running:
            try:
                # floor position (ID 0x100)
                bus.send(can.Message(arbitration_id=0x100, data=struct.pack("B", floor)))
                log(f"0x100 floor={floor}")

                # status (ID 0x200): byte0=dir (0=down,1=up), byte1=door
                dir_byte = 1 if dir_mult == 1 else 0
                door = 1 if floor % 3 == 0 else 0
                bus.send(can.Message(arbitration_id=0x200, data=struct.pack("BB", dir_byte, door)))
                log(f"0x200 dir={dir_byte} door={door}")

                # movement
                floor += dir_mult
                if floor >= 8:
                    dir_mult = -1
                elif floor <= 1:
                    dir_mult = 1

                # random fault
                if random.random() < 0.05:
                    fault = random.choice([0x01, 0x02, 0x04, 0x08])
                    bus.send(can.Message(arbitration_id=0x300, data=struct.pack("B", fault)))
                    log(f"0x300 fault=0x{fault:02x}")

            except Exception as e:
                log(f"CAN send error: {e}")

            for _ in range(3):
                if not running:
                    break
                time.sleep(1)

        bus.shutdown()


def simulate_serial():
    if not SERIAL_DEV:
        log("SERIAL_DEV not set, skipping serial")
        return

    import serial

    log(f"serial on {SERIAL_DEV}")

    while running:
        try:
            if not os.path.exists(SERIAL_DEV):
                time.sleep(2)
                continue

            ser = serial.Serial(SERIAL_DEV, baudrate=9600, timeout=1)
            log(f"opened {SERIAL_DEV}")
        except Exception as e:
            log(f"serial open error: {e}")
            time.sleep(3)
            continue

        while running:
            cmd = random.choice([b"TEST232\n", b"TEST485\n", b"HELLO\n"])
            try:
                ser.write(cmd)
                echo = ser.readline()
                log(f"TX {cmd.strip().decode()} -> RX {echo.strip().decode()}")
            except Exception as e:
                log(f"serial error: {e}")
                break

            for _ in range(2):
                if not running:
                    break
                time.sleep(1)

        try:
            ser.close()
        except Exception:
            pass


def main():
    log("elevator simulator starting")

    threads = []
    t = threading.Thread(target=simulate_can, daemon=True)
    t.start()
    threads.append(t)

    if SERIAL_DEV:
        t = threading.Thread(target=simulate_serial, daemon=True)
        t.start()
        threads.append(t)

    try:
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    log("done")


if __name__ == "__main__":
    main()
