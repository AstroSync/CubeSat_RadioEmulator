
import random
from pydantic import BaseModel
from cubesat_simradio.models import (SX127x_BW, SX127x_CR, SX127x_HeaderMode,
                                                                       SX127x_Modulation)


class RadioConfig(BaseModel):
    mode: SX127x_Modulation
    bandwidth: SX127x_BW
    coding_rate: SX127x_CR
    header_mode: SX127x_HeaderMode
    frequency: int
    ldro: bool
    crc_mode: bool
    spread_factor: int
    sync_word: int
    tle: str = ''


NORBI_CONFIG = RadioConfig(mode=random.choice([SX127x_Modulation.LORA, SX127x_Modulation.FSK]),
                           bandwidth=SX127x_BW.BW250,
                           coding_rate=SX127x_CR.CR5,
                           header_mode=SX127x_HeaderMode.EXPLICIT,
                           frequency=436_700_000,
                           ldro=True,
                           crc_mode=True,
                           spread_factor=10,
                           sync_word=0x12,
                           tle = """NORBI
1 46494U 20068J   23221.70148323  .00006361  00000+0  39361-3 0  9991
2 46494  97.7712 171.1476 0014154 305.4906  54.5001 15.10096344157192""")


NORBI2_CONFIG = RadioConfig(mode=random.choice([SX127x_Modulation.LORA, SX127x_Modulation.FSK]),
                            bandwidth=SX127x_BW.BW250,
                            coding_rate=SX127x_CR.CR5,
                            header_mode=SX127x_HeaderMode.EXPLICIT,
                            frequency=436_500_000,
                            ldro=True,
                            crc_mode=True,
                            spread_factor=10,
                            sync_word=0x12,
                            tle = """NORBI-2
1 57181U 23091R   23222.07973288  .00003409  00000+0  25467-3 0  9994
2 57181  97.6629 272.3469 0020660 103.3794 256.9737 15.03318062  6539""")


STRATOSAT_CONFIG = RadioConfig(mode=random.choice([SX127x_Modulation.LORA, SX127x_Modulation.FSK]),
                               bandwidth=SX127x_BW.BW250,
                               coding_rate=SX127x_CR.CR5,
                               header_mode=SX127x_HeaderMode.IMPLICIT,
                               frequency=436_260_000,
                               ldro=False,
                               crc_mode=False,
                               spread_factor=10,
                               sync_word=0x12,
                               tle="""STRATOSAT-TK 1 (RS52S)
1 57167U 23091B   23222.13867123  .00008911  00000+0  64967-3 0  9996
2 57167  97.6626 272.4215 0020149 103.4161 256.9312 15.03796479  6543""")


DEFAULT_CONFIG = RadioConfig(mode=SX127x_Modulation.FSK,
                             bandwidth=SX127x_BW.BW250,
                             coding_rate=SX127x_CR.CR5,
                             header_mode=SX127x_HeaderMode.EXPLICIT,
                             frequency=-1,
                             ldro=False,
                             crc_mode=False,
                             spread_factor=-1,
                             sync_word=0x12,
                             tle="")