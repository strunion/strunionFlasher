def crc211(buf):
    crc = 211
    for byte in buf:
        crc += byte * 211
        crc &= 0xFFFF
        crc ^= crc >> 8
    return crc & 0xFF


def crc16(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc