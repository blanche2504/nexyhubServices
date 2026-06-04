# sprints

agile plan for the nexyhub services project — training stage at esse-ti

sprint length: 2 weeks (adjustable)

---

## 1 environment & hello world

goal: set up dev environment and deploy a working container

tasks:

- install docker on dev machine
- connect to nexyhub air luci dashboard
- create minimal alpine dockerfile with ssh
- build, export, upload, and start the container
- verify ssh on port 222

acceptance criteria:

- developer can ssh into a running container on slot 1
- container logs are visible in luci

status: COMPLETE

---

## 2 can bus

goal: read and write can frames from a container

tasks:

- study socketcan api and iso 11898 frame format
- mount can0 in container
- implement can monitor with socketcan
- bring up interface at correct bitrate (500000)
- parse frame ids and log structured output
- test with bus stimulator

acceptance criteria:

- container reads and decodes can frames from can0
- logs visible in luci dashboard

status: COMPLETE

---

## 3 serial

goal: bidirectional serial communication over both serial ports

tasks:

- mount /dev/ttyLP6 and /dev/ttyLP2
- implement rs-232 echo (read bytes, echo back)
- handle uart config (baud rate, parity, stop bits)
- implement rs-485 echo with de gpio toggling
- implement minimal modbus rtu read
- validate exclusive peripheral ownership

acceptance criteria:

- container sends and receives over both serial interfaces
- modbus read returns valid register values

status: COMPLETE

---

## 4 BLE scanning

goal: scan for nearby ble devices and publish to shared memory

tasks:

- mount dbus socket (/run/dbus)
- integrate bleak library
- implement periodic scanning (every 10 s)
- write scan results as json to shared memory
- (optional) implement ble advertising

acceptance criteria:

- ble scanner container writes device list to shared memory
- a second container can read and parse the json

status: COMPLETE

---

## 5 inter-container ipc

goal: two containers exchange data through shared volume

tasks:

- understand dual-memory model (private vs shared)
- design file-based ipc protocol (json with atomic writes)
- implement producer (can monitor → shared memory)
- implement consumer (http rest api serving shared memory)
- validate private volume isolation

acceptance criteria:

- consumer correctly reflects data produced by the producer
- no shared filesystem side-effects on private volumes

status: COMPLETE

---

## 6 resilience & production readiness

goal: harden all containers for production deployment

tasks:

- verify restart:always behaviour (crash + auto-recovery)
- design for parallel boot (no startup order dependency)
- implement structured json logging to stdout
- add health-check logic in entrypoint
- document resource usage baselines (cpu, ram)
- write deployment runbook (build → export → upload → configure → rollback)

acceptance criteria:

- all containers restart automatically on crash
- services tolerate peer unavailability at boot
- deployment runbook is complete and tested

status: IN PROGRESS

---

## 6 ui and github pipeline

- ui dashboard with flask + plotly
- ci/cd pipeline with github actions
- final presentation
