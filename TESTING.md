# Testing

run all tests

```bash
uv run pytest
```

## docker images

```bash
bash run.sh build
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
