# Configuration

all services read config from a yaml file at `/etc/nexyhub/config.yaml`.
the path can be overridden with the `NEXYHUB_CONFIG` env var.

if the file does not exist, sensible (hopefully) defaults are used for everything.

## example

```yaml
can:
    interface: can0
    bitrate: 500000
    filters:
        - id: "0x100"
          name: "sensor_temp"
          fields:
              - offset: 0
                length: 2
                name: "temperature"
                unit: "C"

serial:
    rs232:
        port: /dev/ttyLP6
        baudrate: 9600
        parity: N
        stopbits: 1
    rs485:
        port: /dev/ttyLP2
        baudrate: 9600

ble:
    adapter: hci0
    scan_sec: 10
    poll_sec: 10

alarms:
    - name: "high_temperature"
      source: "can.sensor_temp.temperature"
      max: 80.0
      hysteresis: 2.0
      severity: "critical"
    - name: "low_temperature"
      source: "can.sensor_temp.temperature"
      min: -10.0
      severity: "warning"

logging:
    db_path: /mnt/shared/nexyhub.db
    retention_days: 30
    batch_interval: 10
```

## sections

### can

| key       | default | description                            |
| --------- | ------- | -------------------------------------- |
| interface | can0    | socketcan interface name               |
| bitrate   | 500000  | bus bitrate                            |
| filters   | []      | list of can id definitions for parsing |

each filter entry:

- `id` - can id hex string (e.g. "0x100")
- `name` (optional) - human-readable label
- `fields` (optional) - byte field definitions for extracting values

### Serial

| key            | default     | description        |
| -------------- | ----------- | ------------------ |
| rs232.port     | /dev/ttyLP6 | rs-232 device path |
| rs232.baudrate | 9600        | baud rate          |
| rs232.parity   | N           | parity (N/E/O)     |
| rs232.stopbits | 1           | stop bits          |
| rs485.port     | /dev/ttyLP2 | rs-485 device path |
| rs485.baudrate | 9600        | baud rate          |

### BLE

| key      | default | description              |
| -------- | ------- | ------------------------ |
| adapter  | hci0    | bluetooth adapter        |
| scan_sec | 10      | scan duration in seconds |
| poll_sec | 10      | interval between scans   |

### Alarms

list of alarm rules. each rule:

| key        | required | description                                                           |
| ---------- | -------- | --------------------------------------------------------------------- |
| name       | yes      | unique alarm identifier                                               |
| source     | yes      | dotted path to the value in data (e.g. "can.sensor_temp.temperature") |
| min        | no       | lower threshold (null = no lower bound)                               |
| max        | no       | upper threshold (null = no upper bound)                               |
| hysteresis | no       | deadband for clearing (default 0)                                     |
| severity   | no       | "warning" or "critical" (default "warning")                           |

an alarm triggers when the value exceeds max or drops below min.
it clears when the value returns within range by at least the hysteresis amount.

### Logging

| key            | default                | description                     |
| -------------- | ---------------------- | ------------------------------- |
| db_path        | /mnt/shared/nexyhub.db | sqlite database path            |
| retention_days | 30                     | delete readings older than this |
| batch_interval | 10                     | seconds between batch writes    |

## defaults only

if no config file exists, all services work with built-in defaults
(can0 @ 500k, /dev/ttyLP6 @ 9600, hci0, no alarms, db at /mnt/shared/nexyhub.db).
