from __future__ import annotations

from ast import literal_eval
from datetime import datetime
from enum import Enum
from queue import Empty, Queue
import threading
import time
import random
from typing import Callable
from loguru import logger
from pytz import utc
from cubesat_simradio.models import (RadioModel, LoRaRxPacket, LoRaTxPacket, SX127x_BW, SX127x_CR, SX127x_HeaderMode,
                                     SX127x_Modulation)
from cubesat_simradio.utils import Signal
from cubesat_simradio.emusat import EMUSAT
from cubesat_simradio.sat_path import SatellitePath


class InterfaceMock:
    connection_status: bool = True

class RadioMock:
    transmited: Signal = Signal(LoRaTxPacket)
    received: Signal = Signal(LoRaRxPacket)
    tx_timeout: Signal = Signal(str)
    on_rx_timeout: Signal = Signal(str)

    def __init__(self, interference_level: int = 0, **kwargs) -> None:
        self.modulation: SX127x_Modulation = kwargs.get('modulation', SX127x_Modulation.LORA)
        self.coding_rate: SX127x_CR = kwargs.get('ecr', SX127x_CR.CR5)  # error coding rate
        self.bandwidth: SX127x_BW = kwargs.get('bw', SX127x_BW.BW250)  # bandwidth  BW250
        self.spread_factor: int = kwargs.get('sf', 10)  # spreading factor  SF10
        self.frequency: int = kwargs.get('frequency', 436_700_000)   # 436700000
        self.crc_mode: bool = kwargs.get('crc_mode', True)  # check crc
        self.tx_power: int = kwargs.get('tx_power', 12)  # dBm
        self.sync_word: int = kwargs.get('sync_word', 0x12)
        self.preamble_length: int = kwargs.get('preamble_length', 8)
        self.auto_gain_control: bool = kwargs.get('agc', True)  # auto gain control
        self.payload_length: int = kwargs.get('payload_size', 10)  # for implicit mode
        self.low_noize_amplifier: int = kwargs.get('low_noize_amplifier', 5)  # 1 - min; 6 - max
        self.lna_boost: bool = kwargs.get('lna_boost', False)  # 150% LNA current
        self.header_mode: SX127x_HeaderMode = kwargs.get('header_mode', SX127x_HeaderMode.EXPLICIT) # fixed payload size
        self.low_data_rate_optimize: bool = kwargs.get('low_data_rate_optimize', True)

        self.interface: InterfaceMock = InterfaceMock()

        self.__rx_thread = threading.Thread(name='rx_thread', target=self._rx_routine, daemon=True)
        self.__stop_rx_routine_flag: bool = False
        self.__rx_timeout_sec: int = 3
        self.__rx_buffer: list[LoRaRxPacket] = []
        self.__tx_buffer: list[LoRaTxPacket] = []
        self.__lock = threading.Lock()
        self.__waiting_answer: bool = False

        self.interference_level: int = interference_level

        self.sat_path: SatellitePath | None = None

        self.rx_queue: Queue[bytes] = Queue(1)
        self.__last_model: RadioModel = self.__to_model()

        self.satellite = EMUSAT(**kwargs)
        self.satellite.transmited.connect(lambda data: self.rx_queue.put(data, timeout=0.5))
        self.connect()

    def __to_model(self) -> RadioModel:
        return RadioModel(mode=self.modulation.name, frequency=self.frequency, spreading_factor=self.spread_factor,
                          bandwidth=self.bandwidth.name, check_crc=self.crc_mode, sync_word=self.sync_word,
                          coding_rate=self.coding_rate.name, tx_power=self.tx_power, lna_boost=self.lna_boost,
                          lna_gain=self.low_noize_amplifier, header_mode=self.header_mode.name,
                          autogain_control=self.auto_gain_control, ldro=self.low_data_rate_optimize,
                          op_mode='RXCONT')

    def read_config(self) -> RadioModel:
        return self.__last_model

    def clear_subscribers(self) -> None:
        self.received.listeners[:] = self.received.listeners[:2]
        self.transmited.listeners[:] = self.transmited.listeners[:2]
        self.on_rx_timeout.listeners.clear()
        self.tx_timeout.listeners.clear()

    def init(self) -> None:
        time.sleep(1)
        self.__last_model = self.__to_model()

    def start_rx_thread(self) -> None:
        if not self.__rx_thread.is_alive():
            logger.debug('Start Rx thread')
            self.__stop_rx_routine_flag = False
            self.__rx_thread = threading.Thread(name='radio_rx_thread', target=self._rx_routine, daemon=True)
            self.__rx_thread.start()

    def stop_rx_thread(self) -> None:
        self.__stop_rx_routine_flag = True
        self.__rx_thread.join(timeout=0.8)

    def set_rx_timeout(self, sec: int) -> None:
        if 10 > sec > 0:
            self.__rx_timeout_sec = sec

    def connect(self) -> bool:

        logger.success('Radio connected.\nStart initialization...')
        self.init()
        logger.success('Radio inited.')
        self.satellite.power_on()

        self.start_rx_thread()
        return True

    def disconnect(self) -> bool:
        self.satellite.power_off()
        self.stop_rx_thread()
        return True

    def _is_implicit_header(self) -> bool:
        return self.header_mode == SX127x_HeaderMode.IMPLICIT

    def calculate_freq_error(self) -> int:
        if self.sat_path:
            light_speed = 299_792_458  # m/s
            range_rate = int(self.sat_path.find_nearest(self.sat_path.dist_rate, datetime.now().astimezone(utc)) * 1000)
            return self.frequency - int((1 + range_rate / light_speed) * self.frequency)
        return 0

    def calculate_packet(self, packet: list[int] | bytes, force_optimization=True) -> LoRaTxPacket:
        sf: int = self.spread_factor
        bw: int | float = literal_eval(self.bandwidth.name.replace('BW', '').replace('_', '.'))
        cr: int = self.coding_rate.value >> 1
        if self.header_mode == SX127x_HeaderMode.IMPLICIT:
            payload_size = self.payload_length
        else:
            payload_size: int = len(packet)
        t_sym: float = 2 ** sf / bw
        optimization_flag: bool = True if force_optimization else t_sym > 16
        preamble_time: float = (self.preamble_length + 4.25) * t_sym
        tmp_poly: int = max((8 * payload_size - 4 * sf + 28 + 16 * self.crc_mode - 20 * self.header_mode.value), 0)
        payload_symbol_nb: float = 8 + (tmp_poly / (4 * (sf - 2 * optimization_flag))) * (4 + cr)
        payload_time: float = payload_symbol_nb * t_sym
        packet_time: float = payload_time + preamble_time
        timestamp: datetime = datetime.now().astimezone(utc)

        return LoRaTxPacket(timestamp.isoformat(' ', 'seconds'),
                            bytes(packet).hex(' ').upper(), len(packet),
                            self.calculate_freq_error(), packet_time, optimization_flag)

    def send_single(self, data: list[int] | bytes) -> LoRaTxPacket:
        if not isinstance(data, (list, bytes)):
            raise ValueError('Incorrect data type. Possible types: list[int] or bytes')
        if not self.__stop_rx_routine_flag:
            self.stop_rx_thread()
        buffer_size: int = 255
        tx_pkt: LoRaTxPacket = self.calculate_packet(data)
        self.__tx_buffer.append(tx_pkt)
        logger.debug(tx_pkt)
        if len(data) > buffer_size:
            chunks: list[list[int] | bytes] = [data[i:i + buffer_size] for i in range(0, len(data), buffer_size)]
            logger.debug(f'big parcel: {len(data)=}')
            for chunk in chunks:
                tx_chunk: LoRaTxPacket = self.calculate_packet(chunk)
                logger.debug(tx_chunk)
                time.sleep((tx_chunk.Tpkt + 10) / 1000)
                self.satellite.receive_data(chunk, self.__to_model())

        else:
            time.sleep((tx_pkt.Tpkt) / 1000)
            self.satellite.receive_data(data, self.__to_model())

        with self.__lock:
            self.transmited.emit(tx_pkt)

        if self.__stop_rx_routine_flag:
            self.start_rx_thread()
        return tx_pkt

    def get_rssi_packet(self) -> int:
        return random.randint(-115, -112)

    def get_rssi_value(self) -> int:
        return random.randint(-115, -112)

    def get_snr(self) -> int:
        return random.randint(42, 52)

    def get_snr_and_rssi(self) -> tuple[int, int]:
        return self.get_snr(), self.get_rssi_packet()

    def wait_read(self, timeout_sec: float | None = None) -> LoRaRxPacket | None:
        if timeout_sec is None:
            timeout_sec = self.__rx_timeout_sec
        start_time: float = time.perf_counter()
        self.__waiting_answer = True
        while self.__waiting_answer:
            current_time: float = time.perf_counter()
            if current_time - start_time > timeout_sec:
                self.on_rx_timeout.emit('radio rx timeout')
                logger.debug('rx_timeout')
                return None
            time.sleep(0.01)
        return self.get_rx_buffer()[-1]

    def send_repeat(self, data: list[int] | bytes,
                    period_sec: float,
                    *handler_args,
                    untill_answer: bool = True,
                    max_retries: int = 50,
                    answer_handler: Callable[[LoRaRxPacket, tuple], bool] | None = None) -> LoRaRxPacket | None:
        last_rx_packet: LoRaRxPacket | None = None
        # retries: int = max_retries if max_retries > 0 else 99999
        while max_retries:
            tx_packet: LoRaTxPacket = self.send_single(data)
            rx_packet: LoRaRxPacket | None = self.wait_read(period_sec - tx_packet.Tpkt / 1000)
            if rx_packet:
                last_rx_packet = rx_packet
            if rx_packet and not rx_packet.is_crc_error and untill_answer:
                if answer_handler:
                    if answer_handler(rx_packet, *handler_args):
                        break
                else:
                    break
            max_retries -= 1
        return last_rx_packet

    @staticmethod
    def __compare_models(val1, val2):
        if isinstance(val1, Enum):
            return val1.name == val2
        return val1 == val2

    def check_rx_input(self) -> LoRaRxPacket | None:
        try:
            data: bytes = self.rx_queue.get(timeout=0.5)
        except Empty:
            return None
        diff_items: dict = {k: self.read_config().model_dump()[k] for k in self.read_config().model_dump()
                            if k in self.satellite.radio_config.model_dump()
                            and not self.__compare_models(self.satellite.radio_config.model_dump()[k],
                                                            self.read_config().model_dump()[k])}
        if len(diff_items) != 0:
            print(f'gs got data from sat but radio config is incorrect. Different attributes: {diff_items}')
            return None
        dice: float = random.random()
        crc_error: bool = 0 < dice < self.interference_level / 100 if self.crc_mode else True
        freq_error: int = self.calculate_freq_error()
        timestamp: str = datetime.now().astimezone(utc).isoformat(' ', 'seconds')
        return LoRaRxPacket(timestamp, ' '.join(f'{val:02X}' for val in data), len(data), freq_error,
                            *self.get_snr_and_rssi(), crc_error)

    def clear_buffers(self) -> None:
        self.__rx_buffer.clear()
        self.__tx_buffer.clear()

    def clear(self) -> None:
        self.clear_buffers()
        self.sat_path = None
        self.clear_subscribers()

    def get_tx_buffer(self) -> list[LoRaTxPacket]:
        return self.__tx_buffer

    def get_rx_buffer(self) -> list[LoRaRxPacket]:
        return self.__rx_buffer

    def _rx_routine(self) -> None:
        while not self.__stop_rx_routine_flag:
            pkt: LoRaRxPacket | None = self.check_rx_input()
            if pkt is not None:
                time.sleep(0.3)
                if len(pkt.data) > 0:
                    logger.debug(pkt)
                    self.__rx_buffer.append(pkt)
                with self.__lock:
                    self.__waiting_answer = False
                    self.received.emit(pkt)
            time.sleep(0.5)

    def user_cli(self) -> None:
        try:
            while True:
                data = literal_eval(input('> '))
                if isinstance(data, tuple):
                    data = list(data)
                if isinstance(data, (list, bytes)):
                    self.send_single(data)
                else:
                    logger.warning('Incorrect data format. You can send list[int] or bytes.')
        except KeyboardInterrupt:
            self.disconnect()
            logger.debug('Shutdown radio driver')


if __name__ == '__main__':
    radio = RadioMock(name='NORBI2')
    radio.user_cli()
