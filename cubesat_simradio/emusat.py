from __future__ import annotations
from ast import literal_eval
from datetime import datetime, timedelta
from enum import Enum
from queue import Empty, Queue
import time
import threading
import random
from loguru import logger
import numpy as np
from skyfield.toposlib import GeographicPosition

from cubesat_simradio.models import RadioModel, SessionModel, SX127x_Modulation
from cubesat_simradio.emusats_configs import NORBI_CONFIG, NORBI2_CONFIG, STRATOSAT_CONFIG, DEFAULT_CONFIG, RadioConfig
from cubesat_simradio.utils import Signal
from cubesat_simradio.sat_path import SatellitePath, angle_points
from cubesat_simradio.radio_packet import RadioPacket

class EMUSAT:
    transmited = Signal(bytes)

    BEACON_PERIOD = 60

    session: SessionModel
    path: SatellitePath
    def __init__(self, name: str = 'NORBI', **kwargs) -> None:
        self.name: str = name
        self.update_config(name)
        self.transaction_id: int = random.randint(0, 0xFFFF)
        self.onboard_time: float = time.time()
        self.frame_num: int = random.randint(28853, 38543)

        self._routine_flag = False

        self._next_beacon_timestamp: float = 0
        self._rx_queue: Queue[bytes] = Queue(1)

        self.tx_loss_level: int = kwargs.get('tx_loss_level', 0)  # 0 to 100
        self.rx_loss_level: int = kwargs.get('rx_loss_level', 0)  # 0 to 100
        # self.start_t_index = 0
        # self.finish_t_index = -1

    def update_config(self, sat_name: str):
        self.name = sat_name
        if self.name.upper() == 'NORBI':
            self.radio_config: RadioConfig = NORBI_CONFIG
            self.addresses: tuple = (bytes([10, 6, 1, 201]), bytes([10, 6, 1, 202]))
        elif self.name.upper() in ['NORBI2', 'NORBI-2', 'NORBY2', 'NORBY-2']:
            self.name = 'NORBI-2'
            self.radio_config = NORBI2_CONFIG
            self.addresses: tuple = (bytes([10, 6, 1, 203]), bytes([10, 6, 1, 204]))
        elif self.name.upper() == 'STRATOSAT-TK 1 (RS52S)':
            self.radio_config = STRATOSAT_CONFIG
        else:
            self.radio_config = DEFAULT_CONFIG
        # if hasattr(self, 'path'):
        #     self.start_t_index = int(self.path.altitude.shape[0] * 0.85)
        #     self.finish_t_index = int(self.path.altitude.shape[0] * 0.15)
        logger.success(f'config is updated: {self.name}\n{self.radio_config}')

    def recalcute_path(self, gs_position: GeographicPosition):
        norbi_path: SatellitePath = angle_points(NORBI_CONFIG.tle, 'NORBI', gs_position, self.session.start,
                                                 self.session.finish)
        norbi2_path: SatellitePath = angle_points(NORBI2_CONFIG.tle, 'NORBI-2', gs_position, self.session.start,
                                                  self.session.finish)
        stratosat_path: SatellitePath = angle_points(STRATOSAT_CONFIG.tle, 'STRATOSAT-TK 1 (RS52S)', gs_position,
                                                     self.session.start, self.session.finish)
        logger.debug(f'{norbi_path=}\n{norbi2_path=}\n{stratosat_path=}')

    def get_actual_start_finish(self, path: SatellitePath):
        start = np.argmax(path.altitude > 0)
        finish = np.argmax(path.altitude[::-1] > 0)
        if 0 < start < path.altitude.shape[0] // 2 and 0 < finish < path.altitude.shape[0]:
            return path.t_points[start], path.t_points[finish]
        return None

    def get_norbi2_time(self):
        d0 = datetime(2000, 1, 1, 0, 0, 0, 0).timestamp()
        d1 = (datetime.now() - timedelta(8568, 8, minutes=55, hours=8)).timestamp()
        return int(d1 - d0)

    def get_norbi_time(self):
        d0 = datetime(2000, 1, 1, 0, 0, 0, 0).timestamp()
        d1 = (datetime.now() - timedelta(8135, 56, minutes=13, hours=14)).timestamp()
        return int(d1 - d0)

    def power_on(self) -> None:
        self.radio_config.mode = random.choice([SX127x_Modulation.LORA, SX127x_Modulation.FSK])
        logger.debug(f'start emulator session with {self.name}')
        self._next_beacon_timestamp = random.randint(10, self.BEACON_PERIOD) + time.time()
        self._routine_flag = True
        self._routine_thread = threading.Thread(target=self._sat_process, name='NORBI process', daemon=True)
        self._routine_thread.start()

    def power_off(self) -> None:
        self._routine_flag = False
        self._routine_thread.join(0.5)

    def _sat_process(self) -> None:
        logger.debug('start sat process')
        while self._routine_flag:
            if self.is_time_for_beacon():
                self.change_state()
            try:
                data: bytes = self._rx_queue.get(timeout=0.5)
                self._cmd_handler(data)
            except Empty:
                pass
            time.sleep(0.2)

    def change_state(self) -> None:
        self.refresh_beacon_timer()
        if self.radio_config.mode == SX127x_Modulation.LORA:
            self.radio_config.mode = SX127x_Modulation.FSK
            logger.debug('fsk beacon')
        elif self.radio_config.mode == SX127x_Modulation.FSK:
            self.radio_config.mode = SX127x_Modulation.LORA
            logger.debug('lora beacon')
            if self.name == 'STRATOSAT-TK 1 (RS52S)':
                beacon = self.get_stratosat_beacon()
            else:
                beacon = self.get_beacon()
            self.send_data(beacon)
        else:
            raise RuntimeError(f'incorrect Norbi modulation: {self.radio_config.mode}')

    @staticmethod
    def __compare_models(val1, val2):
        if isinstance(val1, Enum):
            return val1.name == val2
        return val1 == val2

    def receive_data(self, data: bytes | list[int], radio_parameters: RadioModel | None = None) -> None:
        if 0 < random.random() < 1 - self.rx_loss_level / 100:
            if not radio_parameters:
                self._rx_queue.put(bytes(data) + b'\xff\xff', timeout=0.5)
            if radio_parameters:
                diff_items: dict = {k: radio_parameters.model_dump()[k] for k in radio_parameters.model_dump()
                                    if k in self.radio_config.model_dump()
                                    and not self.__compare_models(self.radio_config.model_dump()[k],
                                                                  radio_parameters.model_dump()[k])}
                if len(diff_items) == 0:
                    self._rx_queue.put(bytes(data) + b'\xff\xff', timeout=0.5)
                else:
                    logger.warning(f'different attributes: {diff_items}')
            return None

    def _cmd_handler(self, data: bytes) -> None:
        if len(data) < 15:
            logger.error(f'got incorrect message len: {data}')
            return None
        radio_packet = RadioPacket(bytes(data))
        if radio_packet.packet_length != (len(data) - 3):
            logger.error(f'got incorrect message packet length: {data}')
            return None
        if radio_packet.rx_addr not in self.addresses:
            logger.error(f'got incorrect message address: {data}')
            return None
        if self.name in ['NORBI', 'NORBI-2']:
            if radio_packet.msg_id in [1, 3, 5, 7, 9]:
                self.send_data(self.generate_answer_tmi((radio_packet.msg_id - 1) // 2))
            elif radio_packet.msg[:-2] == bytes.fromhex('90 04 00 35 80 00 00 00 00'):
                self.send_data(self.generate_answer_pss_tmi(0))
            elif radio_packet.msg[:-2] == bytes.fromhex('30 0A 00 35 80 00 00 00 00'):
                self.send_data(self.generate_answer_pss_tmi(1))
            elif radio_packet.msg[:-2] == bytes.fromhex('D0 0F 00 35 80 00 00 00 00'):
                self.send_data(self.generate_answer_pss_tmi(2))
            elif radio_packet.msg[:-2] == bytes.fromhex('70 15 00 35 80 00 00 00 00'):
                self.send_data(self.generate_answer_pss_tmi(3))
            else:
                logger.error(f'got unknown cmd: {radio_packet.msg.hex(" ")}')
        else:
            logger.error(f'trying to send data to incorrect sat {self.name}')
        self.refresh_beacon_timer()
        logger.debug(data)
        return None

    def refresh_beacon_timer(self) -> None:
        self._next_beacon_timestamp = time.time() + self.BEACON_PERIOD

    def is_time_for_beacon(self) -> bool:
        return self._next_beacon_timestamp - time.time() < 0

    def send_data(self, data: bytes) -> None:
        self.frame_num += 1
        # if not hasattr(self, 'path'):
        #     return None
        # if self.path.t_points[self.start_t_index] < datetime.now(utc) < self.path.t_points[self.finish_t_index]:
        if 0 < random.random() < 1 - self.tx_loss_level / 100:
            time.sleep(0.5)
            self.transmited.emit(data)

    def generate_answer_tmi(self, tmi_num: int) -> bytes:
        tmi_list: list[str] = [
            '8E 05 00 00 0F 0A 06 01 C9 00 05 00 01 00 02 F1 0F 00 00 6B EA BE 21 7F 02 42 52 4B 20 4D 57 20 56 45 52 '\
            '3A 30 35 61 5F 30 31 00 00 00 00 00 0E 01 00 FD 07 00 00 00 02 12 00 08 DD 0A 82 F1 E5 00 00 00 00 00 00 '\
            '00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 2D 00 B6 00 07 00 F9 FC 00 00 00 00 00 00 0B 04 04 '\
            '0F 0F 0F 0F 0F 0F 00 0A 0C A7 6C 92 60 0A B3 38 0E 0C 00 0C 00 00 1B 09 E6 13 4B 05 0A 0D 08 00 60 10 8A '\
            '20 A8 A1',
            '8E 05 00 00 0F 0A 06 01 C9 09 1A 00 00 00 04 F1 0F 01 00 B4 13 D0 F7 1C 28 00 00 00 00 EC 07 00 00 00 02 '\
            '14 0F 00 00 DB 0A 89 00 00 00 00 00 ED 16 00 00 00 00 00 00 D7 9B 00 00 00 00 00 00 00 00 00 00 ED 07 '\
            '00 00 15 15 00 00 87 00 00 00 00 00 00 00 00 00 00 00 82 00 00 00 00 00 00 00 00 0E 07 35 01 02 00 02 '\
            '00 07 00 01 00 84 00 84 02 04 FF 00 FF 01 60 60 63 BA 00 00 00 B1 15 36 14 D9 2F 4C 06 4B 06 F3 0F 00 '\
            '00 00 00 00 AC 81',
            '8E 05 00 00 0F 0A 06 01 C9 09 1B 00 00 00 06 F1 0F 02 00 8A 10 D3 F7 1C 28 91 00 00 00 00 00 00 00 00 00'\
            ' 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 14 00 00 00 D3 01 00 00 00 00 00 00 00 00'\
            ' 00 00 00 00 00 00 00 00 00 00 E0 DB E8 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 EC DA E1'\
            ' 00 00 00 00 00 00 00 00 00 00 0F 00 00 00 00 00 00 0C 04 04 0F 0F 0F 0F 0F 0F 7A A6 FE 01 00 00 00 00'\
            ' 00 00 00 13 3B 34',
            '8E 05 00 00 0F 0A 06 01 C9 09 1C 00 00 00 08 F1 0F 03 00 67 10 D6 F7 1C 28 00 00 6F 00 6F 00 BB 00 B6 00'\
            ' 22 01 25 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00'\
            ' 00 00 00 00 00 00 31 B2 FE 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00'\
            ' 00 00 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00'\
            ' 00 00 00 13 9A 19',
            '8E 05 00 00 0F 0A 06 01 C9 09 1D 00 00 00 0A F1 0F 04 00 9B 16 D9 F7 1C 28 39 00 2D 00 2D 00 4F 00 20 03'\
            ' EC 00 9B 20 9A 20 97 20 9A 20 9C 20 9B 20 09 0A 09 7F 7F 12 B7 6C 92 60 0A 52 CE 0A 00 00 D3 0A D2 0A'\
            ' CF 0A E8 0A 2A 36 43 07 07 06 05 06 04 05 04 0E 0C 00 0C 00 6A 00 00 00 2C 00 2C 00 00 00 00 00 7D 20'\
            ' 7D 20 61 00 63 00 00 37 00 E4 0C BE 21 3C 29 C4 0C 09 0D 07 00 60 10 7D 20 F0 21 00 00 F1 21 00 00 01'\
            ' 01 00 00 00 B1 07',
            '8E 05 00 00 0F 0A 06 01 C9 09 1E 00 00 00 18 F1 0F 05 00 01 04 DD F7 1C 28 00 00 00 80 11 FD 55 41 00 00'\
            ' 00 60 59 9B 7E 41 00 00 00 80 0B A1 90 41 00 00 00 A0 7D 54 27 41 00 00 00 00 00 D6 E0 40 00 00 00 00'\
            ' 00 00 00 00 15 04 1D 04 33 35 00 9F 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00'\
            ' 00 00 00 00 00 00 00 00 00 00 00 00 00 00 75 FF 9B 01 1A 00 0F 0C 0C 10 06 CA FE 01 00 00 00 00 00 00'\
            ' 00 00 00 13 0B 86',
            '8E 05 00 00 0F 0A 06 01 C9 09 1F 00 00 00 1A F1 0F 06 00 22 15 E0 F7 1C 28 00 00 00 00 00 00 00 00 00 00'\
            ' 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 FE FF F3 FF F9 FF 00 00'\
            ' 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00'\
            ' 3E FB 89 F9 B3 FC 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 BF D5 FE 01'\
            ' 00 00 00 13 A4 84',
            '8E 05 00 00 0F 0A 06 01 C9 09 20 00 00 00 1C F1 0F 07 00 C1 06 E3 F7 1C 28 F3 00 00 00 D1 00 C8 00 CF 00'\
            ' CB 00 3B 10 3B 10 00 00 00 00 31 10 3B 10 3B 10 36 10 31 10 36 10 31 10 3B 10 64 00 64 64 64 64 7B 20'\
            ' 00 00 7E 20 7D 20 00 00 00 00 FF 93 7F 00 00 90 00 00 00 00 00 00 00 03 00 03 03 00 00 00 00 8F 61 30'\
            ' 00 00 00 BF 82 15 8F 62 00 8F 62 2B FF 80 01 8F 62 2D 8F 62 27 FF 00 00 02 00 55 05 48 12 00 00 00 00'\
            ' 37 00 00 00 80 FA',
            '8E 05 00 00 0F 0A 06 01 C9 09 22 00 00 00 1E F1 0F 82 60 00 00 E8 F7 1C 28 00 82 00 00 00 BA 60 03 11 00'\
            ' C0 04 36 14 4B 06 FE FE 00 00 00 00 00 00 24 00 00 00 A0 FF 0F 0F FE FE FE FE 00 00 00 00 00 00 24 00'\
            ' 00 00 F0 00 0F 0F FE FE FE FE 00 00 00 00 00 00 7A 00 00 00 20 FF 03 0F FE FE FE FE 00 00 00 00 00 00'\
            ' 17 00 00 00 80 01 00 0F FE FE FE FE 0E 07 44 02 03 77 4C 08 02 00 49 08 28 00 EE 6B FE FE B1 15 D9 2F'\
            ' 4C 06 F3 0F 46 A4',
        ]
        data = bytearray(bytes.fromhex(tmi_list[tmi_num]))
        data[-2:] = random.randint(0x2334, 0xFEDA).to_bytes(2, 'little')
        data[19:21] = self.frame_num.to_bytes(2, 'little')
        data[21:25] = self.get_norbi_time().to_bytes(4, 'little')
        return bytes(data)

    def generate_answer_pss_tmi(self, tmi_num: int) -> bytes:
        tmi_pss: list[str] = [
            '8E 01 01 01 01 0A 06 01 CB 0B A8 00 00 00 0E F1 0F 02 00 00 30 00 00 6B 68 0E 00 02 00 00 00 00 00 02 43'\
            ' 00 00 00 00 00 00 00 3D 00 00 00 48 00 00 00 76 20 74 20 74 20 72 20 00 00 00 00 00 00 00 00 36 00 E4 0C'\
            ' 76 20 E8 0A FD 01 FE 93 05 01 F0 00 00 00 00 00 00 00 01 01 01 01 01 00 00 00 00 73 20 77 20 00 00 00 00'\
            ' FF FF FF FF 71 20 75 20 FF FF 00 00 00 00 00 00 1F 00 1E 00 00 00 00 00 00 00 00 00 2E 00 1D 00 00 00 00'\
            ' 00 89 A4',
            '8E 01 01 01 01 0A 06 01 CB 0B AD 00 00 00 0E F1 0F 02 00 01 30 00 00 72 68 0E 00 02 00 63 21 FD 00 00 00'\
            ' 00 00 00 00 07 06 0D 07 07 35 00 91 20 9B 00 8A 20 A3 00 72 20 8F 20 09 00 00 00 05 00 00 00 1A 00 D8 03'\
            ' 00 00 00 00 00 00 00 00 08 00 0C 00 E2 DC DE E4 F1 F3 F7 F3 0A 10 0F 08 F9 FA FC FD F2 F2 00 00 FD FD 00'\
            ' 00 E0 F3 0C FB F2 FD 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00'\
            ' 00 B8 9B',
            '8E 01 01 01 01 0A 06 01 CB 00 8C 00 00 00 0E F1 0F 02 00 02 30 00 00 B7 5D 03 00 02 00 EF 0E 00 00 30 5E'\
            ' 61 FF FF FF 00 FF 00 00 00 00 00 00 00 00 00 00 0C 00 0C 00 0C 00 0C 00 0C 00 0C 00 0C 00 0C 64 64 64 63'\
            ' 63 63 64 63 C4 0B C3 0B B5 0B E8 0B C2 0B C0 0B BD 0B CD 0B 33 00 33 00 33 00 56 00 38 00 38 00 34 00 37'\
            ' 00 03 03 02 03 03 02 03 03 03 03 03 03 07 08 06 08 08 06 07 08 06 08 08 06 00 00 00 00 00 00 00 00 00 00'\
            ' 00 4C 81',
            '8E 01 01 01 01 0A 06 01 CB 00 08 00 00 00 0E F1 0F 02 00 03 30 00 00 2E 46 03 00 02 00 E0 0F F5 0F E7 0F'\
            ' EE 0F E8 0F EA 0F E7 0F EC 0F E6 0F E8 0F E7 0F E7 0F E1 0F EB 0F EB 0F E9 0F E0 01 98 FE 18 01 D0 FD 18'\
            ' 01 98 FE E0 01 A8 FD F0 00 A8 FD F0 00 C0 FE F0 00 C0 FE 18 01 98 FE 64 0F 64 0F 64 0F 60 09 64 0F 64 0F'\
            ' 64 0F 64 0F 0F 01 0E 01 0F 01 0E 01 0F 01 0E 01 0F 01 0E 01 73 73 73 74 73 73 73 73 7F 7F 7F 7F 7F 7F 7F'\
            ' 7F EF 46',
        ]
        data = bytearray(bytes.fromhex(tmi_pss[tmi_num]))
        data[-2:] = random.randint(0x2334, 0xFEDA).to_bytes(2, 'little')
        data[23:27] = self.get_norbi2_time().to_bytes(4, 'little')
        return bytes(data)

    def get_beacon(self) -> bytes:
        beacon: str = '8E FF FF FF FF 0A 06 01 CB 4C B5 00 00 00 00 F1 0F 00 00 66 6E 22 87 12 00 42 52 4B 20 4D 57' \
                      '20 56 45 52 3A 30 37 5F 30 31 00 00 00 00 00 00 0E 00 00 AE 00 00 00 00 06 0A 00 02 25 0B 84' \
                      'F8 2C 02 00 12 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00' \
                      '00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00' \
                      '00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 8E CA'
        data = bytearray(bytes.fromhex(beacon))
        data[-2:] = random.randint(0x2334, 0xFEDA).to_bytes(2, 'little')
        if self.name == 'NORBI':
            data[21:25] = self.get_norbi_time().to_bytes(4, 'little')
        elif self.name == 'NORBI-2':
            data[21:25] = self.get_norbi2_time().to_bytes(4, 'little')
        return bytes(data)

    def get_stratosat_beacon(self) -> bytes:
        data = bytearray(bytes.fromhex('99 FC 2E 22 6A 4D FE BF D2 4F 56 AD 40 CE 2C 10 C1 BE B6 34 3C BA 2E 49 8D 07'\
                                       'C8 15 D8 F2 A5 51 8F 02 D4 13 83 71 AF 5C 99 6F CF 9C 08 55 EC 96 C8 8E 0D 1A'\
                                       '24 1D B8 45 CF 95 02 98 D8 F0 A1 0F E7 46 37 C3 BD 7D ED D7 8E A1 84 17 0E A1'\
                                       '84 06 3C D5 6C D7 9F 82 C2 8B 37 D3 70 FF EE 89 42 C9 5B 67 C4 9C 59 67'))
        data[-2:] = random.randint(0x2334, 0xFEDA).to_bytes(2, 'little')
        return bytes(data)


if __name__ == '__main__':
    sat = EMUSAT()
    sat.power_on()
    try:
        while True:
            input_data = literal_eval(input('> '))
            if isinstance(input_data, (bytes, list)):
                sat.receive_data(input_data)
            else:
                print('incorrect data format')

    except KeyboardInterrupt:
        print('shutdown')