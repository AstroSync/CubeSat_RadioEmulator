

from cubesat_simradio.examples.frame_parser import frame_parser


tmi_0_to_8: list[str] = ['8E FF FF FF FF 0A 06 01 C9 8A 79 00 00 00 00 F1 0F 00 00 98 8A CB F7 1C 28 42 52 4B 20 4D 57 20 56 45 52 3A 30 32 5F 31 32 00 00 00 00 00 00 0E 00 00 EC 07 00 00 00 02 14 00 00 DD 0A 89 00 80 07 00 00 82 20 20 04 60 C7 E8 57 00 69 AE DF 01 9A B7 2C 04 D7 F7 1C 28 38 00 FE FF F2 FF F9 FF 00 00 00 00 00 00 0C 04 04 0F 0F 0F 0F 0F 0F 00 09 09 B7 6C 92 60 0A 26 36 0E 0C 00 0C 00 00 25 26 6D 2A C2 0C 09 0D 07 00 60 10 7E 20 B2 B0',
                         '8E 05 00 00 0F 0A 06 01 C9 09 1A 00 00 00 04 F1 0F 01 00 B4 13 D0 F7 1C 28 00 00 00 00 EC 07 00 00 00 02 14 0F 00 00 DB 0A 89 00 00 00 00 00 ED 16 00 00 00 00 00 00 D7 9B 00 00 00 00 00 00 00 00 00 00 ED 07 00 00 15 15 00 00 87 00 00 00 00 00 00 00 00 00 00 00 82 00 00 00 00 00 00 00 00 0E 07 35 01 02 00 02 00 07 00 01 00 84 00 84 02 04 FF 00 FF 01 60 60 63 BA 00 00 00 B1 15 36 14 D9 2F 4C 06 4B 06 F3 0F 00 00 00 00 00 AC 81',
                         '8E 05 00 00 0F 0A 06 01 C9 09 1B 00 00 00 06 F1 0F 02 00 8A 10 D3 F7 1C 28 91 EE 57 00 7D B2 E4 01 51 83 2A 04 51 AA 0B 00 BA 86 00 00 00 00 00 00 E0 F7 1C 28 9F 00 14 00 00 00 D3 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 E0 DB E8 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 EC DA E1 00 00 00 00 00 00 00 00 00 00 0F 00 00 00 00 00 00 0C 04 04 0F 0F 0F 0F 0F 0F 7A A6 FE 01 00 00 00 00 00 00 00 13 3B 34',
                         '8E 05 00 00 0F 0A 06 01 C9 09 1C 00 00 00 08 F1 0F 03 00 67 10 D6 F7 1C 28 00 00 6F 00 6F 00 BB 00 B6 00 22 01 25 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 31 B2 FE 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 13 9A 19',
                         '8E 05 00 00 0F 0A 06 01 C9 09 1D 00 00 00 0A F1 0F 04 00 9B 16 D9 F7 1C 28 39 00 2D 00 2D 00 4F 00 20 03 EC 00 9B 20 9A 20 97 20 9A 20 9C 20 9B 20 09 0A 09 7F 7F 12 B7 6C 92 60 0A 52 CE 0A 00 00 D3 0A D2 0A CF 0A E8 0A 2A 36 43 07 07 06 05 06 04 05 04 0E 0C 00 0C 00 6A 00 00 00 2C 00 2C 00 00 00 00 00 7D 20 7D 20 61 00 63 00 00 37 00 E4 0C BE 21 3C 29 C4 0C 09 0D 07 00 60 10 7D 20 F0 21 00 00 F1 21 00 00 01 01 00 00 00 B1 07',
                         '8E 05 00 00 0F 0A 06 01 C9 09 1E 00 00 00 18 F1 0F 05 00 01 04 DD F7 1C 28 00 00 00 80 11 FD 55 41 00 00 00 60 59 9B 7E 41 00 00 00 80 0B A1 90 41 00 00 00 A0 7D 54 27 41 00 00 00 00 00 D6 E0 40 00 00 00 00 00 00 00 00 15 04 1D 04 33 35 00 9F 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 75 FF 9B 01 1A 00 0F 0C 0C 10 06 CA FE 01 00 00 00 00 00 00 00 00 00 13 0B 86',
                         '8E 05 00 00 0F 0A 06 01 C9 09 1F 00 00 00 1A F1 0F 06 00 22 15 E0 F7 1C 28 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 FE FF F3 FF F9 FF 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 3E FB 89 F9 B3 FC 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 BF D5 FE 01 00 00 00 13 A4 84',
                         '8E 05 00 00 0F 0A 06 01 C9 09 20 00 00 00 1C F1 0F 07 00 C1 06 E3 F7 1C 28 F3 00 00 00 D1 00 C8 00 CF 00 CB 00 3B 10 3B 10 00 00 00 00 31 10 3B 10 3B 10 36 10 31 10 36 10 31 10 3B 10 64 00 64 64 64 64 7B 20 00 00 7E 20 7D 20 00 00 00 00 FF 93 7F 00 00 90 00 00 00 00 00 00 00 03 00 03 03 00 00 00 00 8F 61 30 00 00 00 BF 82 15 8F 62 00 8F 62 2B FF 80 01 8F 62 2D 8F 62 27 FF 00 00 02 00 55 05 48 12 00 00 00 00 37 00 00 00 80 FA',
                        #  '8E 05 00 00 0F 0A 06 01 C9 09 22 00 00 00 1E F1 0F 82 60 00 00 E8 F7 1C 28 00 82 00 00 00 BA 60 03 11 00 C0 04 36 14 4B 06 FE FE 00 00 00 00 00 00 24 00 00 00 A0 FF 0F 0F FE FE FE FE 00 00 00 00 00 00 24 00 00 00 F0 00 0F 0F FE FE FE FE 00 00 00 00 00 00 7A 00 00 00 20 FF 03 0F FE FE FE FE 00 00 00 00 00 00 17 00 00 00 80 01 00 0F FE FE FE FE 0E 07 44 02 03 77 4C 08 02 00 49 08 28 00 EE 6B FE FE B1 15 D9 2F 4C 06 F3 0F 46 A4'
                         ]

for i, tmi in enumerate(tmi_0_to_8):
    df = frame_parser(bytes.fromhex(tmi), 'NORBI')[1]
    print(i, df.to_string())