
crc_table: list[int] = [0x00000000, 0x04C11DB7, 0x09823B6E, 0x0D4326D9, 0x130476DC, 0x17C56B6B, 0x1A864DB2, 0x1E475005,
                        0x2608EDB8, 0x22C9F00F, 0x2F8AD6D6, 0x2B4BCB61,  0x350C9B64, 0x31CD86D3, 0x3C8EA00A, 0x384FBDBD]


def calculate_crc(crc: int, data: list[int]):
    for word in data:
        crc = (crc ^ word) & 0xffffffff
        # print(f'CRC: {crc=:#04x} data: {word:#04x}')
        for _ in range(8):
            crc = ((crc << 4) ^ crc_table[crc >> 28]) & 0xffffffff
    return crc


def init_crc(board_time: int) -> int:
    crc: int = (-1 ^ (board_time ^ 0x01041964)) & 0xffffffff
    for _ in range(8):
        crc = ((crc << 4) ^ crc_table[crc >> 28]) & 0xffffffff
    return crc


class BRK_VAR_ID:
    def __init__(self, *args):
        self.dev_id: int = args[0]
        self.var_id: int = args[1]
        self.offset: int = args[2]

    def to_bytes(self) -> bytes:
        return ((self.dev_id << 28) + (self.var_id << 24) + (self.offset << 3)).to_bytes(4, 'little')

    def __str__(self) -> str:
        return ' '.join([f'{val:02X}' for val in self.to_bytes()])  # self.to_bytes().hex(' ')


def write_registers_message(data_list: list[tuple[BRK_VAR_ID, int | bytes]], board_time: int) -> bytes:
    """data_list: [(BRK_Radio_Frame_VarID, value)], board_time: time from beacon in little endian format"""
    msg: bytes = b''
    for data in data_list:
        msg += data[0].to_bytes()
        if isinstance(data[1], int):
            value_length: int = (data[1].bit_length() + 7) // 8
            msg += value_length.to_bytes(1, 'little')
            msg += data[1].to_bytes(value_length, 'little')
        elif isinstance(data[1], bytes):
            msg += len(data[1]).to_bytes(1, 'little')
            msg += data[1]
        else:
            raise TypeError('Incorrect type for data_list second argument. Possible types: int or bytes.')
    msg += bytes(4)  # end_term
    pad_count: int = len(msg) % 4
    if pad_count > 0:
        msg += bytes(4 - pad_count)

    words: list[int] = [int.from_bytes(reversed(msg[i:i+4]), 'big') for i in range(0, len(msg), 4)]
    crc: int = calculate_crc(init_crc(board_time), words)
    msg += crc.to_bytes(4, 'little')
    return msg


def read_registers_message(data_list: list[tuple[BRK_VAR_ID, int]]) -> bytes:
    """data_list: [(BRK_Radio_Frame_VarID, length)]"""
    msg: bytes = b''
    for data in data_list:
        msg += data[0].to_bytes() + data[1].to_bytes(1, 'little')
    msg += bytes(4)  # end_term
    return msg


def generate_radio_frame(tx_address: bytes | int, rx_address: bytes | int, transaction_id: int, msg_id: int,
                         data: bytes | None = None) -> bytes:
    if data:
        packet_len: int = 14 + len(data)
    else:
        packet_len = 14
    radio_frame: bytes = b''
    radio_frame += packet_len.to_bytes(1, byteorder='big')
    radio_frame += rx_address.to_bytes(4, byteorder='big') if isinstance(rx_address, int) else rx_address
    radio_frame += tx_address.to_bytes(4, byteorder='big') if isinstance(tx_address, int) else tx_address
    radio_frame += transaction_id.to_bytes(2, byteorder='big')  # must be different from previous request
    radio_frame += bytes(2)
    radio_frame += msg_id.to_bytes(2, byteorder='big')
    if data is not None:
        radio_frame += data
    return radio_frame


def read_register(tx_address: bytes | int, rx_address: bytes | int, transaction_id: int,
                  data: list[tuple[int, int, int, int]]) -> bytes:
    """data:  [(dev_id: int, var_id: int, offset: int, length: int), (dev_id, var_id, offset, length), ...] """
    msg: bytes = read_registers_message([(BRK_VAR_ID(*args[:3]), args[3]) for args in data])
    radio_frame: bytes = generate_radio_frame(tx_address, rx_address, transaction_id=transaction_id, msg_id=13,
                                              data=msg)
    return radio_frame


def write_register(tx_address: bytes | int, rx_address: bytes | int, transaction_id: int,
                   data: list[tuple[int, int, int, int | bytes]], btime: int):
    """data:  [(dev_id: int, var_id: int, offset: int, data: int | bytes), (dev_id, var_id, offset, data), ...] """
    msg: bytes = write_registers_message([(BRK_VAR_ID(*args[:3]), args[3]) for args in data], btime)
    radio_frame: bytes = generate_radio_frame(tx_address, rx_address, transaction_id=transaction_id, msg_id=15,
                                              data=msg)
    return radio_frame

