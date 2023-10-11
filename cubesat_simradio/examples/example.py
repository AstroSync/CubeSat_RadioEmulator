from cubesat_simradio.examples.register_commands import generate_radio_frame
from cubesat_simradio.models import LoRaRxPacket
from cubesat_simradio.radio_mock import RadioMock

def on_received(data: LoRaRxPacket):
    print(data)


def main():
    radio = RadioMock(name='NORBI2')
    msg_data = b'hello'
    test_msg = generate_radio_frame(bytes([10, 6, 1, 4]), bytes([10, 6, 1, 203]), 1, 25, msg_data)
    print(test_msg)
    radio.satellite.add_route(msg_data, b'world')

    radio.received.connect(on_received)
    radio.frequency = 436_500_000
    print(radio.read_config())
    radio.init()
    print('after init')
    print(radio.read_config())

    radio.user_cli()

if __name__ == '__main__':
    main()