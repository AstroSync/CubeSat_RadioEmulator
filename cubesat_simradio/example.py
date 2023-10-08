from cubesat_simradio.models import LoRaRxPacket
from cubesat_simradio.radio_mock import RadioMock

def on_received(data: LoRaRxPacket):
    print(data)

if __name__ == '__main__':
    gs_radio = RadioMock()
    gs_radio.received.connect(on_received)
    gs_radio.user_cli()