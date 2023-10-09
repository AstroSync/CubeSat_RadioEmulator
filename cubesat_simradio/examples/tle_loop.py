
import time
from cubesat_simradio.examples.frame_parser import frame_parser
from cubesat_simradio.models import SX127x_HeaderMode
from cubesat_simradio.radio_mock import RadioMock
import cubesat_simradio.examples.register_commands as brk_commands

radio = RadioMock()


def get_sat_name():
    return radio.satellite.name

delay = lambda x: time.sleep(x)



board_time = 0
transaction_id = 0
sat_name = get_sat_name()
#
print(f'satellite {sat_name}')
radio.low_data_rate_optimize = True
radio.header_mode = SX127x_HeaderMode.EXPLICIT
if sat_name == 'NORBI':
    radio.frequency = 436_700_000
elif sat_name == 'NORBI-2':
    radio.frequency = 436_500_000
radio.init()
#
print(radio.read_config())
#
def receive_handler(packet):
    try:
        if not packet.is_crc_error:
            radio_packet, dataframe = frame_parser(packet.to_bytes(), sat_name)
            global transaction_id
            transaction_id += 1
            print(dataframe.to_string())
            if radio_packet.rx_addr == 0xFFFFFFFF.to_bytes(4, 'big'):
                global board_time
                board_time = int.from_bytes(radio_packet.msg[6:10], "little")
            # save_report('pss_tle', dataframe)
        else:
            print('got corrupted packet')
    except Exception as err:
        print(err, packet)


radio.received.connect(receive_handler)

station_address = 0x01010101
station_address_list = list(station_address.to_bytes(4, 'big'))
norbi2_address = 0x0A0601CB
norbi2_address_list = list(norbi2_address.to_bytes(4, 'big'))
norbi_address = 0x0A0601C9
norbi_address_list = list(norbi_address.to_bytes(4, 'big'))
tmi_offsets = [146, 326, 506, 686]

while board_time == 0:
    delay(1)

while True:
    if sat_name == 'NORBI':
        for tmi_num in range(1, 10, 2):
            radio.send_repeat([14, *norbi_address_list, *station_address_list, 0, transaction_id, 0, 0, 0, tmi_num], period_sec=3, max_retries=10)
    elif sat_name == 'NORBI-2':
        for tmi_offset in tmi_offsets:
            radio.send_repeat(brk_commands.read_register(station_address, norbi2_address, transaction_id, [(3, 5, tmi_offset, 128)]), period_sec=3, max_retries=10)
            transaction_id += 1
    else:
        print(f'incorrect sat: {sat_name}')
        delay(60)