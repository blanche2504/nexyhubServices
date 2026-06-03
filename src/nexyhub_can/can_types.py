import struct

CAN_MTU = 16
CAN_FMT = "<IB3x8s"

CAN_EFF_FLAG = 0x80000000
CAN_RTR_FLAG = 0x40000000
CAN_ERR_FLAG = 0x20000000
CAN_ERR_MASK = 0x1FFFFFFF

CAN_ERR_TX_TIMEOUT = 0x00000001
CAN_ERR_BUSOFF = 0x00000040
CAN_ERR_BUSERROR = 0x00000080
CAN_ERR_RESTARTED = 0x00000100


def parse_frame(data: bytes) -> dict:
    raw_id, dlc, payload = struct.unpack(CAN_FMT, data)
    return {
        "id": raw_id & CAN_ERR_MASK,
        "dlc": dlc,
        "data": payload[:dlc],
        "is_error": bool(raw_id & CAN_ERR_FLAG),
        "is_rtr": bool(raw_id & CAN_RTR_FLAG),
        "is_extended": bool(raw_id & CAN_EFF_FLAG),
        "error_flags": raw_id if raw_id & CAN_ERR_FLAG else 0,
    }


def describe_error_flags(flags: int) -> str:
    errors = []
    if flags & CAN_ERR_BUSOFF:
        errors.append("BUS-OFF")
    if flags & CAN_ERR_BUSERROR:
        errors.append("BUS-ERROR")
    if flags & CAN_ERR_TX_TIMEOUT:
        errors.append("TX-TIMEOUT")
    if flags & CAN_ERR_RESTARTED:
        errors.append("RESTARTED")
    return ", ".join(errors) if errors else f"ERROR(0x{flags:08X})"
