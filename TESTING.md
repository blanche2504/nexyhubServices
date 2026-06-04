# Testing

run all tests

```
uv run pytest
```

## test files

| file | what it covers |
|------|----------------|
| tests/test_can_monitor.py | filter parsing, send/recv helpers, bus creation (mocked) |
| tests/test_serial.py | rs-232 echo, rs-485 echo + de gpio, modbus rtu import, wait_for_device (mocked) |
| tests/test_ble.py | device formatting, scan, write, main loop (mocked) |
| tests/test_ipc.py | shared mem atomic read/write, HTTP consumer endpoints |
| tests/serial_e2e_test.py | rs-232 + rs-485 echo over real pty via docker |
| tests/can_full_test.py | full can stack: message construction, filters, virtual bus, protocol, vcan |

## docker images

```
docker build -t nexyhub-hello -f Dockerfile .
docker build -t nexyhub-can -f Dockerfile.can .
docker build -t nexyhub-serial -f Dockerfile.serial .
docker build -t nexyhub-ble -f Dockerfile.ble .
docker build -t nexyhub-ipc -f Dockerfile.ipc .
```

## e2e tests

### can (real socketcan via vcan)

```
sudo modprobe vcan
sudo ip link add vcan0 type vcan
sudo ip link set vcan0 up
```

### serial (real pty via docker)

serial_e2e_test.py creates a pty pair and maps it into the container with `-v`

the response protocol expects `TEST232` / `TEST485` and replies with `ACK`
