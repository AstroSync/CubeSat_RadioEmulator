from dataclasses import dataclass
from datetime import datetime
from enum import Enum
# from hashlib import _Hash, sha1
from uuid import UUID
from pydantic import BaseModel, Field

@dataclass
class LoRaPacket:
    timestamp: str
    data: str
    data_len: int
    freq_error_hz: int

    def to_bytes(self) -> bytes:
        return bytes.fromhex(self.data)

@dataclass
class LoRaRxPacket(LoRaPacket):
    snr: int
    rssi_pkt: int
    is_crc_error: bool

    def __str__(self) -> str:
        currepted_string: str = '(CORRUPTED)' if self.is_crc_error else ''
        return f"{self.timestamp} {currepted_string} freq error: {self.freq_error_hz} rssi: {self.rssi_pkt} "\
               f"rx < {self.data}"


@dataclass
class LoRaTxPacket(LoRaPacket):
    Tpkt: float
    low_datarate_opt_flag: bool

    def __str__(self) -> str:
        return f"{self.timestamp} tx > {self.data} (Tpkt: {self.Tpkt})"

class SessionModel(BaseModel):
    time_range_id: UUID = Field(alias='_id')
    user_id: UUID
    username: str
    script_id: UUID | None
    sat_name: str
    is_user_tle: bool
    station: str
    registration_time: datetime
    priority: int
    start: datetime
    duration_sec: int
    finish: datetime
    parts: int
    max_elevation: float
    initial_start: datetime
    initial_duration_sec: int
    class Config:
        json_encoders = {
            # custom output conversion for datetime
            datetime: lambda dt: dt.isoformat(' ', 'seconds')
        }

class RadioModel(BaseModel):
    mode: str
    op_mode: str
    frequency: int
    spreading_factor: int
    coding_rate: str
    bandwidth: str
    check_crc: bool
    sync_word: int
    tx_power: float
    autogain_control: bool
    lna_gain: int
    lna_boost: bool
    header_mode: str
    ldro: bool

    def __str__(self) -> str:
        return super().__str__().replace(' ', '\n')


class SX127x_Modulation(Enum):
    LORA = 0x80
    FSK = 0

class SX127x_HeaderMode(Enum):
    EXPLICIT = 0
    IMPLICIT = 1

class SX127x_BW(Enum):
    BW7_8 = 0
    BW10_4 = 1 << 4
    BW15_6 = 2 << 4
    BW20_8 = 3 << 4
    BW31_25 = 4 << 4
    BW41_7 = 5 << 4
    BW62_5 = 6 << 4
    BW125 = 7 << 4
    BW250 = 8 << 4
    BW500 = 9 << 4

class SX127x_CR(Enum):
    CR5 = 1 << 1
    CR6 = 2 << 1
    CR7 = 3 << 1
    CR8 = 4 << 1