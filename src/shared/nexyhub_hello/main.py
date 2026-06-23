import time


def main():
    print("Hello from NexyHub!")
    i = 0
    while True:
        time.sleep(10)
        i += 1
        print(f"[heartbeat] NexyHub Hello running... ({i * 10}s)")


if __name__ == "__main__":
    main()
