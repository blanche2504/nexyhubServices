import can


def create_bus(ifname: str, filters: list) -> can.Bus:
    bus = can.Bus(interface="socketcan", channel=ifname, receive_own_messages=False)
    if filters:
        bus.set_filters(filters)
    return bus


def send_message(bus: can.Bus, arb_id: int, data: bytes) -> bool:
    msg = can.Message(
        arbitration_id=arb_id,
        data=data,
        is_extended_id=bool(arb_id > 0x7FF),
    )
    try:
        bus.send(msg)
        return True
    except (OSError, can.CanError):
        return False


def recv_message(bus: can.Bus) -> can.Message | None:
    try:
        return bus.recv(timeout=1.0)
    except Exception:
        return None
