# developer-serial — Contenitore Seriale NexyHub Air

Contenitore Docker per la comunicazione seriale su **NexyHub Air**:

- **RS-232** su `/dev/ttyLP6` — echo `TEST232` con risposta `ACK`
- **RS-485** su `/dev/ttyLP2` — echo `TEST485` con risposta `ACK` e controllo GPIO DE
- **Modbus RTU** su `/dev/ttyLP2` — polling registri holding

## Dipendenze

- `pyserial` — comunicazione seriale
- `pymodbus` — client Modbus RTU
- `pyyaml` — parsing configurazione
- `nexyhub_config` — loader configurazione condiviso
- `nexyhub_db` — database logging condiviso
- `nexyhub_alarms` — motore allarmi condiviso

## Build

```bash
docker build -t nexyhub/developer-serial:1.0 \
  -f developer-serial-1.0/Dockerfile \
  developer-serial-1.0/
```

## Esecuzione

### RS-232 echo (default)

```bash
docker run --rm -it \
  --device /dev/ttyLP6 \
  -e SSH_ROOT_PASSWORD=secret \
  -e SERIAL_PORT=/dev/ttyLP6 \
  nexyhub/developer-serial:1.0
```

### RS-485 echo

```bash
docker run --rm -it \
  --device /dev/ttyLP2 \
  --device /dev/gpiochip1 \
  -e SSH_ROOT_PASSWORD=secret \
  -e SERIAL_PORT=/dev/ttyLP2 \
  nexyhub/developer-serial:1.0 \
  python3 -m nexyhub_serial.rs485_echo
```

### Modbus RTU

```bash
docker run --rm -it \
  --device /dev/ttyLP2 \
  -e SSH_ROOT_PASSWORD=secret \
  -e MODBUS_PORT=/dev/ttyLP2 \
  nexyhub/developer-serial:1.0 \
  python3 -m nexyhub_serial.modbus_rtu
```
