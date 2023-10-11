from cubesat_simradio.models import LoRaRxPacket
from cubesat_simradio.radio_mock import RadioMock

def on_received(data: LoRaRxPacket):
    print(data)


def main():
    radio = RadioMock(name='NORBI2')
    radio.received.connect(on_received)
    radio.frequency = 436_500_000
    print(radio.read_config())
    radio.init()
    print('after init')
    print(radio.read_config())

    radio.user_cli()

if __name__ == '__main__':
    main()