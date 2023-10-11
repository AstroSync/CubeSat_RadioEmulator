class RadioPacket:
    """ NORBI radio packet of transport layer

    | Packet length | RX ADDR | TX ADDR | Transaction number |   Res   | Message ID |   Payload   |  CRC16  |
    |:-------------:|:-------:|:-------:|:------------------:|:-------:|:----------:|:-----------:|:-------:|
    |     1 byte    | 4 bytes | 4 bytes |       2 bytes      | 2 bytes |   2 bytes  | < 240 bytes | 2 bytes |
    """
    sizes: list[int] = [1, 4, 4, 2, 2, 2, 0, 2]

    def __init__(self, raw_data: bytes) -> None:
        self.raw_data: bytes = raw_data
        fields: list[bytes] = self.split_by_sizes(raw_data)
        self.raw_data_length: int = len(raw_data)
        self.packet_length: int = fields[0][0]
        self.rx_addr: bytes = fields[1]
        self.tx_addr: bytes = fields[2]
        self.transaction_num: int = int.from_bytes(fields[3], 'big')
        self.__res: bytes = fields[4]
        self.msg_id: int = int.from_bytes(fields[5], 'big')
        self.msg: bytes = raw_data[sum(self.sizes[:-2]):-2]
        self.crc16: bytes = raw_data[-self.sizes[-1]:]

    def split_by_sizes(self, buffer: bytes) -> list[bytes]:
        return [buffer[sum(self.sizes[:i]):sum(self.sizes[:i]) + s] for i, s in enumerate(self.sizes[:-2])]

    @staticmethod
    def address_to_string(address: bytes) -> str:
        return f'{address[0]}.{address[1]}.{address[2]}.{address[3]}'

    def __repr__(self) -> str:
        return f'Frame length: {self.packet_length}\n'\
               f'TX Address: {self.address_to_string(self.tx_addr)}\n' \
               f'RX Address: {self.address_to_string(self.rx_addr)}\n'\
               f'Transaction number: {self.transaction_num}\n' \
               f'Msg ID: {self.msg_id}\n'\
               f'Msg: {" ".join(f"{val:02X}" for val in self.msg)}\n'\
               f'CRC16: 0x{int.from_bytes(self.crc16, "big"):02X}\n'