import datetime
import struct
import os
import pandas as pd
import numpy as np

from cubesat_simradio.radio_packet import RadioPacket

class FrameFormats:
    def __init__(self) -> None:
        self.norbi1_tmi: list[pd.DataFrame] = [pd.read_csv(os.path.join(os.path.dirname(__file__),
                                                                        'NORBI_TMI_formats', f'tmi{i}.csv'))
                                               for i in range(9)]
        self.norbi2_tmi: list[pd.DataFrame] = [pd.read_csv(os.path.join(os.path.dirname(__file__),
                                                                        'NORBI2_TMI_formats', f'tmi_pss{i}.csv'))
                                               for i in range(4)]

tmi_formats: FrameFormats = FrameFormats()


def convert_glonass_time(glonass_seconds: int) -> str:
    return (datetime.datetime(2000, 1, 1, 0, 0, 0) + datetime.timedelta(seconds=glonass_seconds)).isoformat(' ',
                                                                                                            'seconds')


def struct_time(data: bytes) -> str:
    return datetime.datetime(2000 + data[0], *data[1:]).isoformat(' ', 'seconds')  # type: ignore


def field_format(field_name: str, field_type: str, field_size: int, value: bytes):
    if value is np.nan:
        return value
    if field_type is np.nan:
        field_type = 'hex'
    if field_type.startswith('uint'):
        if 'время' in field_name.lower():
            return convert_glonass_time(int.from_bytes(value, 'little'))
        return int.from_bytes(value, 'little')
    if field_type.startswith('int'):
        if field_size == 1:
            return np.frombuffer(value, 'int8')[0]
        if field_size == 2:
            return np.frombuffer(value, 'int16')[0]
        if field_size == 4:
            return int.from_bytes(value, byteorder='little', signed=True)
    if '*' in field_type:
        return np.frombuffer(value, field_type.split(' * ')[1].rstrip('_t')).tolist()
    if field_type == 'double':
        return struct.unpack('d', value)[0]
    if field_type == 'string':
        try:
            return value.decode("ascii")
        except UnicodeDecodeError:
            return f"0x{''.join(f'{val:02X}' for val in value)}"
    if field_type == 'struct time_t':
        return struct_time(value)
    return f"0x{''.join(f'{val:02X}' for val in value)}"


def frame_parser(data: bytes, sat_name: str = 'NORBI'):
    radio_frame = RadioPacket(data)
    if sat_name == 'NORBI':
        tmi_num: int = int.from_bytes(radio_frame.msg[2:4], 'little')
        try:
            tmi = tmi_formats.norbi1_tmi[tmi_num]
        except IndexError as err:
            raise IndexError(f'frame parser error: you try do get tmi{tmi_num} but norbi1_tmi length=4') from err
        new_header_name: str = f'Параметры Норби ТМИ {tmi_num}'
    elif sat_name == 'NORBI-2':
        tmi_num: int = int.from_bytes(radio_frame.msg[4:5], 'little')
        if tmi_num > 4:
            tmi_num = int.from_bytes(radio_frame.msg[2:4], 'little')
            try:
                tmi = tmi_formats.norbi1_tmi[tmi_num]
            except IndexError as err:
                raise IndexError(f'frame parser error: you try do get tmi{tmi_num} but norbi2_tmi length=4') from err
        else:
            try:
                tmi: pd.DataFrame = tmi_formats.norbi2_tmi[tmi_num]
            except IndexError as err:
                raise IndexError(f'frame parser error: you try do get tmi{tmi_num} but norbi2_tmi length=4') from err
        new_header_name = f'Параметры Норби2 ТМИ {tmi_num}'
    else:
        tmi_num: int = int.from_bytes(radio_frame.msg[2:4], 'little')
        try:
            tmi = tmi_formats.norbi1_tmi[tmi_num]
        except IndexError as err:
            raise IndexError(f'frame parser error: you try do get tmi{tmi_num} but norbi1_tmi length=4') from err
        new_header_name: str = f'Параметры Норби ТМИ {tmi_num}'

    tmi_frame: pd.DataFrame = tmi.rename(columns={'Параметр': new_header_name})
    msg_data: list[bytes] = split_data_by_sizes(radio_frame.msg, tmi['Размер Байт'].astype('int').tolist())
    tmi_frame['Значения'] = pd.Series(msg_data)  # add column
    for index, row in tmi_frame.iterrows():
        tmi_frame.at[index, 'Значения'] = field_format(row[0], row['Тип данных'], row['Размер Байт'], row['Значения'])
    tmi_frame.at[len(tmi_frame) - 1, 'Значения'] = f"0x{''.join(f'{val:02X}' for val in radio_frame.crc16)}"
    return radio_frame, tmi_frame#[[new_header_name, 'Размерность', 'Значения']]


def split_data_by_sizes(msg: bytes, field_sizes: list[int]) -> list[bytes]:
    return [msg[sum(field_sizes[:i]):sum(field_sizes[:i]) + field_size] for i, field_size in enumerate(field_sizes)]

