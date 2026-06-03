def parse_filters(filter_str: str) -> list:
    if not filter_str or not filter_str.strip():
        return []

    filters = []
    for part in filter_str.split(","):
        part = part.strip()
        if not part:
            continue

        if "-" in part:
            lo_str, hi_str = part.split("-", 1)
            lo = int(lo_str.strip(), 0)
            hi = int(hi_str.strip(), 0)
            if lo > hi:
                lo, hi = hi, lo

            diff = lo ^ hi
            mask_bits = 0x7FF
            bit = 1
            while bit <= diff:
                mask_bits &= ~bit
                bit <<= 1
            filters.append((lo & mask_bits, mask_bits))
        else:
            can_id = int(part, 0)
            filters.append((can_id, 0x7FF))

    return filters
