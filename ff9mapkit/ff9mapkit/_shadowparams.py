"""Auto-generated per-model field BLOB SHADOW -- ``(size, intensity)`` = the modal MapConfigData
``shadowR`` / ``shadowI`` real fields apply to each model (``fldmcf.ff9fieldMCFService``), one vote
per (field, model) over 818 shipping fields. :mod:`ff9mapkit.content.shadow` emits them as
``SetShadowSize(size, size)`` + ``SetShadowAmplifier(intensity << 3)`` -- the same two engine calls.
``STOCK_CASTS`` is the script half: whether stock lets a model's shadow show at all (its free-standing
objects' Inits ``DisableShadow`` it on every path, or not) -- what a ``[[prop]]`` follows.

DO NOT EDIT BY HAND. Regenerate with:  python -m ff9mapkit._regen_shadowparams
Provenance: derived metadata (model ids + small ints), no Square-Enix bytes.
"""
# generated-from: install by _regen_shadowparams.py

# a model no shipping field shows (minted / custom): the modal pair over every vote
DEFAULT = (11, 4)

# model id: (size, intensity)    # name, field votes  (under 5 votes the intensity is DEFAULT's)
SHADOW_PARAMS = {
    2: (30, 4),    # GEO_MON_F0_ZZZ, 1
    3: (11, 4),    # GEO_ACC_F0_FEL, 3
    4: (8, 4),    # GEO_MON_F0_SDR, 5
    6: (11, 4),    # GEO_ACC_F0_FLR, 1
    8: (10, 4),    # GEO_MAIN_F0_VIV, 240
    10: (8, 4),    # GEO_NPC_F1_BBA, 8
    11: (12, 4),    # GEO_NPC_F1_TCK, 2
    12: (11, 4),    # GEO_NPC_F2_BBA, 2
    13: (13, 4),    # GEO_NPC_F3_BBA, 4
    15: (8, 4),    # GEO_ACC_F0_IFE, 3
    16: (11, 4),    # GEO_ACC_F0_BTN, 1
    17: (9, 3),    # GEO_NPC_F2_APM, 6
    18: (9, 4),    # GEO_NPC_F1_TMM, 1
    19: (12, 4),    # GEO_NPC_F1_TMF, 1
    20: (9, 3),    # GEO_NPC_F1_OFF, 9
    21: (11, 5),    # GEO_NPC_F2_OSC, 5
    22: (10, 4),    # GEO_ACC_F0_LDD, 4
    23: (1, 1),    # GEO_ACC_F0_TSM, 5
    24: (10, 3),    # GEO_NPC_F0_APF, 11
    25: (11, 3),    # GEO_NPC_F2_G17, 5
    26: (8, 4),    # GEO_NPC_F2_G20, 2
    27: (8, 4),    # GEO_NPC_F2_TBY, 1
    31: (3, 4),    # GEO_ACC_F0_DGR, 4
    32: (8, 8),    # GEO_NPC_F0_TBY, 21
    33: (27, 4),    # GEO_MON_F0_EFM, 1
    34: (7, 3),    # GEO_NPC_F3_TBY, 8
    35: (3, 4),    # GEO_ACC_F0_DBR, 2
    40: (6, 4),    # GEO_NPC_F2_TGR, 1
    48: (10, 4),    # GEO_SUB_F0_RBY, 12
    49: (8, 4),    # GEO_NPC_F0_DAC, 5
    50: (8, 4),    # GEO_NPC_F0_DAL, 11
    51: (7, 3),    # GEO_NPC_F0_HUF, 9
    52: (10, 5),    # GEO_NPC_F0_KAC, 11
    53: (13, 8),    # GEO_NPC_F1_BMG, 22
    54: (13, 8),    # GEO_NPC_F2_BMG, 16
    55: (8, 4),    # GEO_NPC_F0_DAF, 5
    56: (10, 4),    # GEO_NPC_F0_G17, 8
    61: (8, 4),    # GEO_NPC_F3_TGR, 9
    62: (9, 8),    # GEO_SUB_F0_NTA, 10
    63: (5, 3),    # GEO_NPC_F0_CCB, 20
    64: (11, 6),    # GEO_NPC_F0_DAW, 6
    65: (10, 4),    # GEO_NPC_F0_ORC, 2
    66: (11, 3),    # GEO_NPC_F0_RAS, 25
    67: (8, 4),    # GEO_NPC_F0_TRF, 6
    68: (12, 4),    # GEO_NPC_F1_BAR, 1
    69: (1, 1),    # GEO_NPC_F1_CCB, 5
    70: (9, 3),    # GEO_NPC_F1_CSA, 12
    71: (9, 2),    # GEO_NPC_F1_CSO, 17
    72: (10, 3),    # GEO_NPC_F2_HUF, 11
    73: (10, 3),    # GEO_NPC_F3_CSA, 8
    74: (8, 3),    # GEO_NPC_F4_CSA, 11
    75: (10, 4),    # GEO_ACC_F0_TBX, 112
    76: (7, 4),    # GEO_MAIN_F1_GRN, 1
    91: (11, 4),    # GEO_ACC_F1_TBX, 26
    98: (9, 4),    # GEO_MAIN_F0_ZDN, 701
    99: (7, 4),    # GEO_NPC_F1_HUF, 2
    100: (0, 1),    # GEO_NPC_F1_CHO, 5
    101: (10, 1),    # GEO_NPC_F3_APM, 7
    102: (9, 5),    # GEO_NPC_F4_JJY, 6
    103: (10, 3),    # GEO_NPC_F1_WRK, 6
    104: (8, 2),    # GEO_NPC_F2_HTH, 5
    106: (25, 4),    # GEO_SUB_F0_BRN, 17
    107: (10, 5),    # GEO_SUB_F0_CNA, 24
    108: (9, 3),    # GEO_NPC_F2_HUM, 6
    109: (11, 4),    # GEO_SUB_F0_MRC, 41
    110: (8, 3),    # GEO_NPC_F1_HUM, 16
    111: (9, 3),    # GEO_NPC_F0_APM, 11
    112: (11, 5),    # GEO_NPC_F0_BBA, 7
    113: (8, 4),    # GEO_NPC_F0_BND, 4
    114: (2, 7),    # GEO_NPC_F0_BRI, 6
    115: (8, 3),    # GEO_NPC_F0_CAT, 8
    116: (8, 4),    # GEO_NPC_F0_HEK, 14
    117: (10, 6),    # GEO_NPC_F0_JJY, 15
    118: (9, 4),    # GEO_NPC_F0_OFF, 55
    119: (8, 4),    # GEO_NPC_F0_RMF, 6
    120: (8, 4),    # GEO_NPC_F0_RMM, 7
    121: (8, 7),    # GEO_NPC_F0_RTC, 10
    122: (11, 4),    # GEO_NPC_F0_TCK, 2
    123: (14, 6),    # GEO_NPC_F0_TMF, 8
    124: (12, 5),    # GEO_NPC_F0_TMM, 6
    126: (12, 4),    # GEO_NPC_F0_WRK, 5
    127: (8, 4),    # GEO_NPC_F1_BND, 4
    128: (3, 4),    # GEO_NPC_F1_BRI, 2
    129: (7, 3),    # GEO_NPC_F1_MOG, 12
    130: (8, 4),    # GEO_NPC_F2_BND, 4
    131: (9, 4),    # GEO_NPC_F3_BND, 2
    132: (8, 4),    # GEO_NPC_F4_BND, 2
    133: (11, 3),    # GEO_ACC_F0_MGR, 58
    134: (4, 1),    # GEO_ACC_F0_MGP, 56
    167: (8, 4),    # GEO_SUB_F0_BW3, 3
    168: (18, 4),    # GEO_SUB_F0_BW2, 1
    169: (18, 4),    # GEO_SUB_F0_BW1, 1
    170: (13, 4),    # GEO_SUB_F0_CDW, 6
    171: (11, 3),    # GEO_SUB_F0_TOT, 19
    172: (8, 2),    # GEO_SUB_F0_ZON, 23
    173: (8, 4),    # GEO_NPC_F0_BAR, 4
    174: (6, 2),    # GEO_NPC_F0_FRC, 9
    175: (6, 2),    # GEO_NPC_F0_FRF, 9
    176: (6, 2),    # GEO_NPC_F0_FRM, 11
    177: (12, 4),    # GEO_NPC_F0_G16, 8
    178: (1, 1),    # GEO_NPC_F0_TAD, 8
    179: (8, 5),    # GEO_NPC_F1_DAL, 8
    180: (8, 4),    # GEO_NPC_F1_DAC, 3
    181: (10, 4),    # GEO_NPC_F1_RAS, 5
    182: (10, 4),    # GEO_NPC_F4_CSO, 16
    183: (9, 3),    # GEO_NPC_F4_APM, 9
    185: (8, 4),    # GEO_MAIN_F0_GRN, 232
    186: (14, 4),    # GEO_SUB_F2_BAK, 1
    187: (9, 4),    # GEO_NPC_F0_OSC, 11
    188: (10, 3),    # GEO_NPC_F1_CSM, 10
    189: (9, 4),    # GEO_NPC_F2_CSM, 4
    190: (8, 5),    # GEO_SUB_F1_BLN, 6
    191: (5, 4),    # GEO_SUB_F2_CID, 13
    192: (11, 4),    # GEO_MAIN_F0_FRJ, 114
    193: (11, 4),    # GEO_NPC_F0_DOG, 12
    194: (9, 4),    # GEO_NPC_F0_CSA, 6
    195: (13, 4),    # GEO_NPC_F0_GUD, 3
    196: (7, 4),    # GEO_NPC_F2_MOG, 3
    197: (11, 3),    # GEO_NPC_F3_CSM, 6
    198: (5, 4),    # GEO_NPC_F4_MOG, 15
    199: (7, 4),    # GEO_NPC_F5_MOG, 2
    200: (2, 16),    # GEO_ACC_F0_V10, 12
    201: (11, 4),    # GEO_MON_F2_EFM, 1
    202: (7, 4),    # GEO_MAIN_F3_GRN, 12
    203: (8, 4),    # GEO_MAIN_F1_ZDN, 2
    204: (9, 3),    # GEO_SUB_F0_BTX, 34
    205: (6, 4),    # GEO_MAIN_F4_GRN, 2
    206: (7, 8),    # GEO_NPC_F0_BUC, 10
    207: (11, 4),    # GEO_SUB_F1_BW3, 1
    208: (11, 2),    # GEO_NPC_F0_CSM, 10
    209: (13, 4),    # GEO_NPC_F0_FUK, 3
    210: (9, 4),    # GEO_NPC_F0_STR, 4
    211: (9, 4),    # GEO_NPC_F2_CSA, 4
    212: (8, 3),    # GEO_NPC_F3_MOG, 12
    213: (8, 4),    # GEO_NPC_F0_G20, 7
    214: (10, 4),    # GEO_SUB_F0_KUW, 2
    215: (12, 5),    # GEO_SUB_F0_KUT, 7
    216: (10, 2),    # GEO_NPC_F0_BUF, 15
    217: (9, 3),    # GEO_NPC_F0_CSO, 28
    218: (10, 3),    # GEO_NPC_F2_CSO, 17
    219: (10, 3),    # GEO_NPC_F3_CSO, 16
    220: (6, 2),    # GEO_NPC_F0_MOG, 81
    222: (11, 6),    # GEO_ACC_F0_TKT, 5
    223: (3, 4),    # GEO_ACC_F0_GRS, 3
    224: (10, 4),    # GEO_ACC_F0_ROP, 2
    225: (11, 4),    # GEO_ACC_F0_TNT, 66
    226: (11, 6),    # GEO_ACC_F0_BLL, 6
    227: (2, 4),    # GEO_ACC_F0_BIN, 4
    228: (1, 4),    # GEO_ACC_F0_MAP, 3
    229: (11, 4),    # GEO_ACC_F0_V03, 1
    230: (11, 4),    # GEO_ACC_F0_V02, 2
    231: (11, 4),    # GEO_ACC_F0_V01, 3
    232: (11, 4),    # GEO_ACC_F0_BOT, 3
    233: (1, 1),    # GEO_ACC_F0_OPB, 5
    234: (3, 4),    # GEO_ACC_F0_CUP, 4
    235: (11, 4),    # GEO_ACC_F0_SUP, 3
    236: (8, 3),    # GEO_ACC_F1_SUP, 7
    237: (11, 4),    # GEO_ACC_F2_SUP, 2
    238: (10, 4),    # GEO_ACC_F0_BBX, 3
    239: (8, 4),    # GEO_ACC_F0_SSH, 1
    240: (10, 4),    # GEO_ACC_F0_BBT, 3
    241: (11, 5),    # GEO_ACC_F0_CSK, 9
    242: (12, 4),    # GEO_ACC_F0_ELV, 1
    243: (10, 4),    # GEO_ACC_F0_SWD, 10
    245: (24, 4),    # GEO_MON_F0_BFF, 2
    246: (22, 4),    # GEO_MON_F0_BAN, 4
    247: (14, 5),    # GEO_MON_F0_FFG, 5
    248: (11, 6),    # GEO_MON_F0_MUU, 5
    249: (11, 5),    # GEO_MON_F0_TBL, 7
    250: (11, 4),    # GEO_MON_F0_TOM, 1
    251: (11, 4),    # GEO_MON_F1_TOM, 2
    252: (17, 4),    # GEO_MON_F0_AMD, 2
    253: (9, 4),    # GEO_NPC_F2_APF, 4
    254: (40, 4),    # GEO_MON_F0_GRI, 1
    255: (32, 4),    # GEO_MON_F0_KAT, 1
    256: (64, 4),    # GEO_MON_F0_MOS, 1
    257: (10, 4),    # GEO_ACC_F0_HOD, 1
    258: (11, 4),    # GEO_ACC_F0_LTT, 63
    259: (0, 1),    # GEO_NPC_F0_CHO, 12
    260: (0, 4),    # GEO_NPC_F0_CHC, 3
    262: (10, 4),    # GEO_ACC_F0_CBH, 2
    267: (12, 3),    # GEO_SUB_F0_KJA, 15
    268: (11, 4),    # GEO_NPC_F0_DOK, 2
    269: (10, 8),    # GEO_NPC_F0_FLS, 16
    270: (10, 3),    # GEO_SUB_F0_CID, 10
    272: (14, 4),    # GEO_NPC_F0_CLD, 2
    273: (16, 4),    # GEO_MAIN_F0_KUI, 99
    274: (8, 2),    # GEO_SUB_F1_ZON, 23
    275: (11, 4),    # GEO_ACC_F0_HDB, 4
    277: (5, 4),    # GEO_ACC_F0_TUR, 4
    279: (1, 4),    # GEO_ACC_F0_FIS, 3
    282: (10, 4),    # GEO_NPC_F4_CSM, 3
    294: (11, 8),    # GEO_ACC_F0_GRG, 7
    306: (11, 3),    # GEO_ACC_F1_GRG, 19
    360: (9, 4),    # GEO_NPC_F5_CSM, 2
    365: (31, 4),    # GEO_ACC_F0_CRS, 1
    368: (10, 2),    # GEO_SUB_F0_SBW, 6
    376: (10, 4),    # GEO_NPC_F2_JJY, 7
    377: (7, 4),    # GEO_ACC_F0_LNW, 3
    380: (12, 4),    # GEO_SUB_F0_FLT, 4
    381: (6, 4),    # GEO_MAIN_F9_GRN, 1
    382: (14, 4),    # GEO_SUB_F0_GRL, 10
    395: (1, 4),    # GEO_ACC_F0_CER, 4
    406: (11, 4),    # GEO_ACC_F0_GAB, 1
    407: (1, 4),    # GEO_ACC_F0_LIF, 1
    408: (11, 4),    # GEO_ACC_F0_LEV, 1
    409: (11, 4),    # GEO_ACC_F0_MAK, 1
    411: (10, 4),    # GEO_ACC_F0_BON, 1
    412: (15, 2),    # GEO_NPC_F0_HTH, 9
    414: (1, 4),    # GEO_ACC_F0_DLF, 1
    415: (11, 4),    # GEO_ACC_F0_NEP, 4
    417: (11, 4),    # GEO_NPC_F0_G19, 3
    418: (8, 8),    # GEO_NPC_F1_TGR, 6
    419: (9, 4),    # GEO_MAIN_F5_GRN, 5
    420: (11, 3),    # GEO_NPC_F0_DOC, 7
    421: (11, 4),    # GEO_NPC_F0_DOF, 4
    422: (8, 4),    # GEO_NPC_F0_DOM, 4
    423: (6, 4),    # GEO_NPC_F1_FRM, 4
    424: (8, 3),    # GEO_NPC_F1_TBY, 8
    425: (8, 4),    # GEO_SUB_F1_CID, 13
    426: (9, 4),    # GEO_SUB_F4_SSB, 5
    431: (11, 4),    # GEO_NPC_F0_NAN, 2
    432: (10, 4),    # GEO_MAIN_F2_ZDN, 2
    433: (4, 4),    # GEO_ACC_F0_DAG, 2
    434: (1, 4),    # GEO_ACC_F0_HKG, 2
    435: (1, 4),    # GEO_ACC_F0_KOR, 2
    436: (11, 4),    # GEO_ACC_F0_TRK, 8
    437: (9, 4),    # GEO_ACC_F0_BLK, 1
    438: (1, 4),    # GEO_ACC_F0_KOS, 1
    439: (4, 4),    # GEO_ACC_F0_KOM, 4
    442: (11, 4),    # GEO_MON_F0_CLB, 1
    443: (8, 4),    # GEO_MAIN_F0_EIK, 112
    447: (9, 8),    # GEO_NPC_F0_CLM, 11
    487: (11, 4),    # GEO_ACC_F0_ORD, 1
    488: (11, 16),    # GEO_ACC_F0_V11, 6
    489: (11, 4),    # GEO_ACC_F0_WRE, 1
    490: (11, 4),    # GEO_ACC_F0_ZBR, 2
    508: (9, 4),    # GEO_ACC_F0_WEA, 1
    509: (13, 4),    # GEO_MAIN_F0_SLM, 61
    523: (12, 4),    # GEO_ACC_F0_YIB, 1
    524: (13, 4),    # GEO_MON_F1_EFM, 4
    526: (11, 4),    # GEO_MAIN_F0_STD, 2
    528: (11, 4),    # GEO_MON_F0_DRA, 1
    529: (11, 4),    # GEO_MON_F0_EEE, 2
    530: (30, 4),    # GEO_MON_F0_FFF, 1
    531: (11, 4),    # GEO_SUB_F0_KJG, 3
    532: (10, 1),    # GEO_MAIN_F0_ZDD, 7
    533: (50, 4),    # GEO_MON_F0_DAH, 1
    534: (11, 5),    # GEO_MON_F0_RAM, 6
    535: (11, 4),    # GEO_MON_F0_WWW, 1
    536: (9, 4),    # GEO_ACC_F0_EGG, 2
    537: (8, 4),    # GEO_ACC_F0_GAS, 18
    538: (10, 4),    # GEO_ACC_F0_KGG, 2
    539: (9, 6),    # GEO_SUB_F0_NTC, 18
    540: (9, 6),    # GEO_SUB_F0_NTB, 10
    541: (8, 8),    # GEO_SUB_F0_NTD, 10
    542: (19, 4),    # GEO_NPC_F0_CHD, 3
    543: (12, 4),    # GEO_NPC_F1_G17, 2
    544: (8, 4),    # GEO_NPC_F1_OSC, 1
    547: (9, 4),    # GEO_NPC_F1_HTH, 3
    549: (9, 4),    # GEO_NPC_F1_DOC, 1
    550: (11, 4),    # GEO_NPC_F1_DOF, 4
    551: (11, 4),    # GEO_NPC_F1_DOM, 4
    555: (11, 3),    # GEO_ACC_F0_STQ, 9
    559: (10, 4),    # GEO_NPC_F1_APM, 3
    564: (11, 4),    # GEO_NPC_F1_DOK, 2
    574: (30, 4),    # GEO_MON_F0_MKM, 6
    575: (1, 4),    # GEO_MON_F0_HHP, 1
    577: (10, 4),    # GEO_ACC_F1_BLL, 2
    578: (11, 4),    # GEO_ACC_F2_BLL, 1
    579: (10, 4),    # GEO_ACC_F3_BLL, 2
    586: (11, 4),    # GEO_ACC_F0_ISB, 4
    587: (1, 4),    # GEO_ACC_F1_ISB, 1
    588: (5, 4),    # GEO_ACC_F0_FS3, 4
    589: (5, 2),    # GEO_ACC_F0_FS2, 5
    590: (5, 2),    # GEO_ACC_F0_FS1, 5
    596: (1, 1),    # GEO_ACC_F0_ELE, 6
    597: (9, 3),    # GEO_NPC_F3_HUF, 7
    598: (14, 4),    # GEO_NPC_F1_GUD, 2
    599: (11, 4),    # GEO_NPC_F3_JJY, 4
    600: (10, 2),    # GEO_NPC_F7_CSM, 7
    603: (11, 4),    # GEO_NPC_F2_DAL, 4
    604: (7, 4),    # GEO_NPC_F1_DAF, 2
    609: (1, 4),    # GEO_ACC_F0_TKE, 1
    612: (8, 4),    # GEO_NPC_F1_G20, 4
    613: (0, 1),    # GEO_NPC_F2_CHO, 5
    614: (0, 1),    # GEO_NPC_F3_CHO, 5
    615: (0, 1),    # GEO_NPC_F4_CHO, 6
    616: (11, 4),    # GEO_MON_F0_CDR, 4
    617: (32, 4),    # GEO_MON_F0_AMS, 1
    622: (8, 4),    # GEO_ACC_F0_DLB, 1
    624: (8, 5),    # GEO_NPC_F1_CAT, 13
    625: (1, 4),    # GEO_ACC_F0_TNB, 3
    626: (1, 4),    # GEO_ACC_F0_WT0, 2
    627: (10, 4),    # GEO_ACC_F0_LG2, 1
    628: (10, 4),    # GEO_ACC_F0_LG1, 3
    630: (1, 4),    # GEO_ACC_F0_WT3, 2
    631: (1, 4),    # GEO_ACC_F0_WT2, 2
    632: (1, 4),    # GEO_ACC_F0_WT1, 2
    633: (11, 4),    # GEO_ACC_F1_HKG, 1
    634: (11, 4),    # GEO_ACC_F2_HKG, 1
    635: (11, 4),    # GEO_ACC_F3_HKG, 1
    636: (11, 4),    # GEO_ACC_F0_IRF, 2
    637: (11, 4),    # GEO_ACC_F0_EYE, 1
    638: (5, 4),    # GEO_ACC_F0_GNT, 1
    640: (11, 4),    # GEO_ACC_F0_YRI, 1
    641: (1, 4),    # GEO_ACC_F0_HSK, 3
    642: (1, 4),    # GEO_ACC_F0_RBN, 2
    643: (6, 4),    # GEO_NPC_F2_DAC, 4
    646: (8, 4),    # GEO_NPC_F1_APF, 5
    647: (10, 4),    # GEO_NPC_F1_JJY, 10
    658: (12, 5),    # GEO_MAIN_F1_STN, 33
    659: (10, 4),    # GEO_SUB_F7_BLN, 1
    660: (10, 4),    # GEO_SUB_F7_MRC, 3
    661: (10, 4),    # GEO_SUB_F7_CNA, 1
    662: (10, 4),    # GEO_MAIN_F7_VIV, 2
    665: (10, 4),    # GEO_SUB_F0_MOM, 1
    666: (8, 4),    # GEO_MAIN_F8_GRN, 1
    667: (10, 4),    # GEO_SUB_F3_KJA, 3
    668: (10, 4),    # GEO_MAIN_F3_ZDN, 1
    669: (10, 4),    # GEO_MAIN_F4_ZDN, 1
    670: (10, 4),    # GEO_MAIN_F5_ZDN, 1
    674: (9, 4),    # GEO_NPC_F5_CSA, 1
    675: (8, 4),    # GEO_NPC_F6_CSA, 1
    677: (10, 4),    # GEO_NPC_F1_KAC, 1
    678: (11, 4),    # GEO_NPC_F2_KAC, 1
    679: (1, 4),    # GEO_ACC_F1_MGP, 2
    680: (1, 4),    # GEO_ACC_F2_LTT, 2
    681: (9, 4),    # GEO_ACC_F1_SWD, 2
    701: (8, 3),    # GEO_ACC_F2_TBX, 5
    702: (8, 4),    # GEO_ACC_F3_TBX, 6
    5464: (14, 4),    # GEO_SUB_F0_BAK, 24
    5467: (8, 4),    # GEO_SUB_F0_BLN, 35
    5468: (13, 8),    # GEO_NPC_F0_BMG, 37
    5474: (7, 3),    # GEO_NPC_F0_COK, 10
    5476: (10, 4),    # GEO_NPC_F0_G18, 8
    5478: (9, 4),    # GEO_NPC_F0_HUM, 13
    5488: (8, 3),    # GEO_SUB_F0_SSB, 23
    5489: (11, 3),    # GEO_MAIN_F0_STN, 154
    5492: (8, 4),    # GEO_NPC_F0_TGR, 19
    5500: (10, 4),    # GEO_SUB_F0_ZNR, 13
    5501: (22, 4),    # GEO_SUB_F1_BAK, 8
    5505: (8, 4),    # GEO_SUB_F1_SSB, 3
    5509: (10, 3),    # GEO_SUB_F2_SSB, 11
    5511: (8, 4),    # GEO_SUB_F3_SSB, 2
}

# a [[prop]] whose model no stock object shows standing free (minted / custom / only ever held): the
# verdict of stock's set-dressing models -- 16 of 84 GEO_ACC_* models cast one
PROP_DEFAULT_CASTS = False

# model id: does stock let its shadow show?    # name, free-standing objects casting / disabled
STOCK_CASTS = {
    2: True,    # GEO_MON_F0_ZZZ, 1 / 0
    3: False,    # GEO_ACC_F0_FEL, 0 / 3
    4: False,    # GEO_MON_F0_SDR, 0 / 5
    6: False,    # GEO_ACC_F0_FLR, 0 / 8
    8: True,    # GEO_MAIN_F0_VIV, 238 / 1
    10: True,    # GEO_NPC_F1_BBA, 7 / 1
    11: True,    # GEO_NPC_F1_TCK, 2 / 0
    12: True,    # GEO_NPC_F2_BBA, 2 / 0
    13: True,    # GEO_NPC_F3_BBA, 4 / 0
    15: False,    # GEO_ACC_F0_IFE, 0 / 3
    16: False,    # GEO_ACC_F0_BTN, 0 / 3
    17: True,    # GEO_NPC_F2_APM, 6 / 0
    18: True,    # GEO_NPC_F1_TMM, 1 / 0
    19: True,    # GEO_NPC_F1_TMF, 1 / 0
    20: True,    # GEO_NPC_F1_OFF, 15 / 0
    21: True,    # GEO_NPC_F2_OSC, 5 / 0
    22: False,    # GEO_ACC_F0_LDD, 0 / 4
    23: False,    # GEO_ACC_F0_TSM, 2 / 2
    24: True,    # GEO_NPC_F0_APF, 11 / 0
    25: True,    # GEO_NPC_F2_G17, 5 / 0
    26: True,    # GEO_NPC_F2_G20, 2 / 0
    27: True,    # GEO_NPC_F2_TBY, 1 / 0
    31: False,    # GEO_ACC_F0_DGR, 0 / 1
    32: True,    # GEO_NPC_F0_TBY, 22 / 0
    33: True,    # GEO_MON_F0_EFM, 1 / 0
    34: True,    # GEO_NPC_F3_TBY, 8 / 0
    40: True,    # GEO_NPC_F2_TGR, 1 / 0
    48: True,    # GEO_SUB_F0_RBY, 12 / 0
    49: True,    # GEO_NPC_F0_DAC, 7 / 0
    50: True,    # GEO_NPC_F0_DAL, 15 / 0
    51: True,    # GEO_NPC_F0_HUF, 10 / 0
    52: True,    # GEO_NPC_F0_KAC, 11 / 0
    53: True,    # GEO_NPC_F1_BMG, 25 / 13
    54: True,    # GEO_NPC_F2_BMG, 21 / 0
    55: True,    # GEO_NPC_F0_DAF, 4 / 2
    56: True,    # GEO_NPC_F0_G17, 8 / 0
    61: True,    # GEO_NPC_F3_TGR, 9 / 0
    62: True,    # GEO_SUB_F0_NTA, 14 / 0
    63: False,    # GEO_NPC_F0_CCB, 11 / 32
    64: True,    # GEO_NPC_F0_DAW, 6 / 0
    65: True,    # GEO_NPC_F0_ORC, 2 / 0
    66: True,    # GEO_NPC_F0_RAS, 30 / 0
    67: True,    # GEO_NPC_F0_TRF, 6 / 0
    68: True,    # GEO_NPC_F1_BAR, 1 / 0
    69: False,    # GEO_NPC_F1_CCB, 2 / 10
    70: True,    # GEO_NPC_F1_CSA, 14 / 0
    71: True,    # GEO_NPC_F1_CSO, 20 / 1
    72: True,    # GEO_NPC_F2_HUF, 11 / 1
    73: True,    # GEO_NPC_F3_CSA, 8 / 0
    74: True,    # GEO_NPC_F4_CSA, 12 / 0
    75: True,    # GEO_ACC_F0_TBX, 172 / 3
    76: True,    # GEO_MAIN_F1_GRN, 1 / 0
    91: True,    # GEO_ACC_F1_TBX, 38 / 0
    98: True,    # GEO_MAIN_F0_ZDN, 665 / 16
    99: True,    # GEO_NPC_F1_HUF, 2 / 0
    100: True,    # GEO_NPC_F1_CHO, 5 / 1
    101: True,    # GEO_NPC_F3_APM, 7 / 0
    102: False,    # GEO_NPC_F4_JJY, 4 / 6
    103: True,    # GEO_NPC_F1_WRK, 5 / 1
    104: True,    # GEO_NPC_F2_HTH, 6 / 0
    106: True,    # GEO_SUB_F0_BRN, 17 / 0
    107: True,    # GEO_SUB_F0_CNA, 23 / 1
    108: True,    # GEO_NPC_F2_HUM, 6 / 0
    109: True,    # GEO_SUB_F0_MRC, 38 / 3
    110: True,    # GEO_NPC_F1_HUM, 16 / 0
    111: True,    # GEO_NPC_F0_APM, 10 / 1
    112: True,    # GEO_NPC_F0_BBA, 8 / 0
    113: True,    # GEO_NPC_F0_BND, 3 / 1
    114: True,    # GEO_NPC_F0_BRI, 6 / 3
    115: True,    # GEO_NPC_F0_CAT, 11 / 0
    116: True,    # GEO_NPC_F0_HEK, 15 / 0
    117: True,    # GEO_NPC_F0_JJY, 16 / 0
    118: True,    # GEO_NPC_F0_OFF, 105 / 0
    119: True,    # GEO_NPC_F0_RMF, 6 / 0
    120: True,    # GEO_NPC_F0_RMM, 7 / 0
    121: True,    # GEO_NPC_F0_RTC, 9 / 1
    122: True,    # GEO_NPC_F0_TCK, 2 / 0
    123: True,    # GEO_NPC_F0_TMF, 8 / 0
    124: True,    # GEO_NPC_F0_TMM, 6 / 0
    126: True,    # GEO_NPC_F0_WRK, 5 / 0
    127: True,    # GEO_NPC_F1_BND, 4 / 0
    128: False,    # GEO_NPC_F1_BRI, 0 / 3
    129: True,    # GEO_NPC_F1_MOG, 13 / 0
    130: True,    # GEO_NPC_F2_BND, 4 / 0
    131: True,    # GEO_NPC_F3_BND, 2 / 0
    132: True,    # GEO_NPC_F4_BND, 2 / 0
    133: False,    # GEO_ACC_F0_MGR, 0 / 58
    134: False,    # GEO_ACC_F0_MGP, 0 / 56
    167: False,    # GEO_SUB_F0_BW3, 1 / 2
    168: True,    # GEO_SUB_F0_BW2, 1 / 0
    169: True,    # GEO_SUB_F0_BW1, 1 / 0
    170: True,    # GEO_SUB_F0_CDW, 6 / 0
    171: True,    # GEO_SUB_F0_TOT, 19 / 1
    172: True,    # GEO_SUB_F0_ZON, 24 / 0
    173: True,    # GEO_NPC_F0_BAR, 4 / 0
    174: False,    # GEO_NPC_F0_FRC, 0 / 9
    175: False,    # GEO_NPC_F0_FRF, 0 / 9
    176: False,    # GEO_NPC_F0_FRM, 4 / 9
    177: True,    # GEO_NPC_F0_G16, 8 / 0
    178: False,    # GEO_NPC_F0_TAD, 0 / 8
    179: True,    # GEO_NPC_F1_DAL, 9 / 1
    180: True,    # GEO_NPC_F1_DAC, 5 / 0
    181: True,    # GEO_NPC_F1_RAS, 6 / 0
    182: True,    # GEO_NPC_F4_CSO, 22 / 0
    183: True,    # GEO_NPC_F4_APM, 9 / 0
    185: True,    # GEO_MAIN_F0_GRN, 217 / 14
    186: False,    # GEO_SUB_F2_BAK, 0 / 1
    187: True,    # GEO_NPC_F0_OSC, 21 / 0
    188: True,    # GEO_NPC_F1_CSM, 10 / 0
    189: True,    # GEO_NPC_F2_CSM, 4 / 0
    190: True,    # GEO_SUB_F1_BLN, 6 / 0
    191: True,    # GEO_SUB_F2_CID, 15 / 0
    192: True,    # GEO_MAIN_F0_FRJ, 114 / 0
    193: True,    # GEO_NPC_F0_DOG, 12 / 0
    194: True,    # GEO_NPC_F0_CSA, 6 / 0
    195: True,    # GEO_NPC_F0_GUD, 3 / 0
    196: True,    # GEO_NPC_F2_MOG, 8 / 0
    197: True,    # GEO_NPC_F3_CSM, 6 / 0
    198: True,    # GEO_NPC_F4_MOG, 11 / 5
    199: True,    # GEO_NPC_F5_MOG, 3 / 1
    200: True,    # GEO_ACC_F0_V10, 11 / 2
    201: True,    # GEO_MON_F2_EFM, 1 / 0
    202: True,    # GEO_MAIN_F3_GRN, 11 / 1
    203: True,    # GEO_MAIN_F1_ZDN, 2 / 0
    204: True,    # GEO_SUB_F0_BTX, 33 / 1
    205: False,    # GEO_MAIN_F4_GRN, 1 / 1
    206: True,    # GEO_NPC_F0_BUC, 23 / 0
    207: True,    # GEO_SUB_F1_BW3, 1 / 0
    208: True,    # GEO_NPC_F0_CSM, 15 / 0
    209: True,    # GEO_NPC_F0_FUK, 2 / 1
    210: True,    # GEO_NPC_F0_STR, 4 / 0
    211: True,    # GEO_NPC_F2_CSA, 4 / 0
    212: True,    # GEO_NPC_F3_MOG, 13 / 0
    213: True,    # GEO_NPC_F0_G20, 7 / 0
    214: True,    # GEO_SUB_F0_KUW, 2 / 0
    215: True,    # GEO_SUB_F0_KUT, 8 / 0
    216: True,    # GEO_NPC_F0_BUF, 18 / 0
    217: True,    # GEO_NPC_F0_CSO, 45 / 3
    218: True,    # GEO_NPC_F2_CSO, 22 / 0
    219: True,    # GEO_NPC_F3_CSO, 16 / 0
    220: True,    # GEO_NPC_F0_MOG, 98 / 4
    222: False,    # GEO_ACC_F0_TKT, 1 / 1
    223: False,    # GEO_ACC_F0_GRS, 0 / 1
    224: False,    # GEO_ACC_F0_ROP, 0 / 2
    225: False,    # GEO_ACC_F0_TNT, 1 / 66
    226: False,    # GEO_ACC_F0_BLL, 0 / 1
    229: False,    # GEO_ACC_F0_V03, 0 / 1
    230: False,    # GEO_ACC_F0_V02, 0 / 2
    231: False,    # GEO_ACC_F0_V01, 0 / 3
    232: False,    # GEO_ACC_F0_BOT, 0 / 3
    233: False,    # GEO_ACC_F0_OPB, 0 / 5
    234: False,    # GEO_ACC_F0_CUP, 0 / 1
    235: False,    # GEO_ACC_F0_SUP, 0 / 4
    236: False,    # GEO_ACC_F1_SUP, 0 / 8
    237: False,    # GEO_ACC_F2_SUP, 0 / 9
    238: False,    # GEO_ACC_F0_BBX, 0 / 3
    239: False,    # GEO_ACC_F0_SSH, 0 / 1
    240: False,    # GEO_ACC_F0_BBT, 0 / 4
    241: True,    # GEO_ACC_F0_CSK, 19 / 0
    242: True,    # GEO_ACC_F0_ELV, 2 / 0
    245: True,    # GEO_MON_F0_BFF, 2 / 0
    246: True,    # GEO_MON_F0_BAN, 6 / 0
    247: True,    # GEO_MON_F0_FFG, 10 / 0
    248: True,    # GEO_MON_F0_MUU, 9 / 0
    249: False,    # GEO_MON_F0_TBL, 4 / 5
    250: False,    # GEO_MON_F0_TOM, 0 / 1
    251: False,    # GEO_MON_F1_TOM, 0 / 2
    252: True,    # GEO_MON_F0_AMD, 2 / 0
    253: True,    # GEO_NPC_F2_APF, 4 / 0
    254: True,    # GEO_MON_F0_GRI, 1 / 0
    255: True,    # GEO_MON_F0_KAT, 1 / 0
    256: True,    # GEO_MON_F0_MOS, 1 / 0
    257: False,    # GEO_ACC_F0_HOD, 0 / 1
    258: False,    # GEO_ACC_F0_LTT, 0 / 57
    259: True,    # GEO_NPC_F0_CHO, 10 / 5
    260: True,    # GEO_NPC_F0_CHC, 3 / 0
    262: False,    # GEO_ACC_F0_CBH, 0 / 2
    267: True,    # GEO_SUB_F0_KJA, 12 / 3
    268: True,    # GEO_NPC_F0_DOK, 4 / 0
    269: True,    # GEO_NPC_F0_FLS, 35 / 0
    270: True,    # GEO_SUB_F0_CID, 9 / 1
    272: True,    # GEO_NPC_F0_CLD, 2 / 0
    273: True,    # GEO_MAIN_F0_KUI, 99 / 0
    274: True,    # GEO_SUB_F1_ZON, 24 / 0
    279: False,    # GEO_ACC_F0_FIS, 0 / 3
    282: True,    # GEO_NPC_F4_CSM, 3 / 0
    294: False,    # GEO_ACC_F0_GRG, 2 / 5
    306: False,    # GEO_ACC_F1_GRG, 0 / 19
    360: True,    # GEO_NPC_F5_CSM, 2 / 0
    365: False,    # GEO_ACC_F0_CRS, 0 / 1
    368: True,    # GEO_SUB_F0_SBW, 5 / 1
    376: True,    # GEO_NPC_F2_JJY, 6 / 1
    380: True,    # GEO_SUB_F0_FLT, 3 / 1
    381: True,    # GEO_MAIN_F9_GRN, 1 / 0
    382: True,    # GEO_SUB_F0_GRL, 7 / 3
    395: False,    # GEO_ACC_F0_CER, 0 / 15
    406: True,    # GEO_ACC_F0_GAB, 2 / 0
    407: False,    # GEO_ACC_F0_LIF, 0 / 1
    408: False,    # GEO_ACC_F0_LEV, 0 / 1
    409: True,    # GEO_ACC_F0_MAK, 1 / 0
    412: True,    # GEO_NPC_F0_HTH, 9 / 0
    414: False,    # GEO_ACC_F0_DLF, 0 / 3
    415: False,    # GEO_ACC_F0_NEP, 0 / 6
    417: True,    # GEO_NPC_F0_G19, 3 / 0
    418: True,    # GEO_NPC_F1_TGR, 6 / 0
    419: True,    # GEO_MAIN_F5_GRN, 5 / 0
    420: True,    # GEO_NPC_F0_DOC, 7 / 0
    421: True,    # GEO_NPC_F0_DOF, 5 / 0
    422: True,    # GEO_NPC_F0_DOM, 6 / 0
    423: False,    # GEO_NPC_F1_FRM, 0 / 4
    424: True,    # GEO_NPC_F1_TBY, 8 / 0
    425: True,    # GEO_SUB_F1_CID, 12 / 0
    426: True,    # GEO_SUB_F4_SSB, 9 / 0
    431: True,    # GEO_NPC_F0_NAN, 2 / 0
    432: True,    # GEO_MAIN_F2_ZDN, 2 / 0
    434: False,    # GEO_ACC_F0_HKG, 1 / 1
    435: False,    # GEO_ACC_F0_KOR, 0 / 2
    436: True,    # GEO_ACC_F0_TRK, 10 / 0
    437: True,    # GEO_ACC_F0_BLK, 1 / 0
    438: False,    # GEO_ACC_F0_KOS, 0 / 2
    439: False,    # GEO_ACC_F0_KOM, 3 / 6
    442: True,    # GEO_MON_F0_CLB, 1 / 0
    443: True,    # GEO_MAIN_F0_EIK, 104 / 7
    447: True,    # GEO_NPC_F0_CLM, 22 / 0
    488: False,    # GEO_ACC_F0_V11, 1 / 10
    508: False,    # GEO_ACC_F0_WEA, 0 / 1
    509: True,    # GEO_MAIN_F0_SLM, 60 / 1
    523: False,    # GEO_ACC_F0_YIB, 0 / 3
    524: True,    # GEO_MON_F1_EFM, 8 / 3
    526: True,    # GEO_MAIN_F0_STD, 2 / 0
    528: True,    # GEO_MON_F0_DRA, 1 / 0
    529: False,    # GEO_MON_F0_EEE, 0 / 2
    530: False,    # GEO_MON_F0_FFF, 0 / 1
    531: False,    # GEO_SUB_F0_KJG, 1 / 2
    532: True,    # GEO_MAIN_F0_ZDD, 7 / 0
    533: True,    # GEO_MON_F0_DAH, 1 / 0
    534: False,    # GEO_MON_F0_RAM, 2 / 4
    535: True,    # GEO_MON_F0_WWW, 1 / 0
    536: False,    # GEO_ACC_F0_EGG, 1 / 2
    537: False,    # GEO_ACC_F0_GAS, 0 / 30
    538: False,    # GEO_ACC_F0_KGG, 0 / 2
    539: True,    # GEO_SUB_F0_NTC, 18 / 0
    540: True,    # GEO_SUB_F0_NTB, 13 / 0
    541: True,    # GEO_SUB_F0_NTD, 11 / 0
    542: True,    # GEO_NPC_F0_CHD, 3 / 0
    543: True,    # GEO_NPC_F1_G17, 2 / 0
    544: True,    # GEO_NPC_F1_OSC, 1 / 0
    547: True,    # GEO_NPC_F1_HTH, 3 / 0
    549: True,    # GEO_NPC_F1_DOC, 1 / 0
    550: True,    # GEO_NPC_F1_DOF, 5 / 0
    551: True,    # GEO_NPC_F1_DOM, 7 / 0
    559: True,    # GEO_NPC_F1_APM, 3 / 0
    564: True,    # GEO_NPC_F1_DOK, 2 / 0
    574: True,    # GEO_MON_F0_MKM, 7 / 1
    575: True,    # GEO_MON_F0_HHP, 1 / 0
    577: False,    # GEO_ACC_F1_BLL, 0 / 2
    578: False,    # GEO_ACC_F2_BLL, 0 / 1
    579: False,    # GEO_ACC_F3_BLL, 0 / 1
    586: True,    # GEO_ACC_F0_ISB, 3 / 2
    587: False,    # GEO_ACC_F1_ISB, 0 / 2
    588: False,    # GEO_ACC_F0_FS3, 2 / 2
    589: True,    # GEO_ACC_F0_FS2, 6 / 1
    590: True,    # GEO_ACC_F0_FS1, 5 / 1
    596: False,    # GEO_ACC_F0_ELE, 0 / 7
    597: True,    # GEO_NPC_F3_HUF, 8 / 0
    598: True,    # GEO_NPC_F1_GUD, 2 / 0
    599: True,    # GEO_NPC_F3_JJY, 4 / 0
    600: True,    # GEO_NPC_F7_CSM, 7 / 0
    603: True,    # GEO_NPC_F2_DAL, 4 / 0
    604: True,    # GEO_NPC_F1_DAF, 2 / 1
    609: False,    # GEO_ACC_F0_TKE, 0 / 1
    612: True,    # GEO_NPC_F1_G20, 4 / 0
    613: True,    # GEO_NPC_F2_CHO, 5 / 1
    614: True,    # GEO_NPC_F3_CHO, 5 / 1
    615: True,    # GEO_NPC_F4_CHO, 8 / 2
    616: False,    # GEO_MON_F0_CDR, 0 / 4
    617: True,    # GEO_MON_F0_AMS, 1 / 0
    622: False,    # GEO_ACC_F0_DLB, 0 / 1
    624: True,    # GEO_NPC_F1_CAT, 13 / 0
    625: True,    # GEO_ACC_F0_TNB, 3 / 0
    626: False,    # GEO_ACC_F0_WT0, 0 / 1
    627: False,    # GEO_ACC_F0_LG2, 0 / 11
    628: False,    # GEO_ACC_F0_LG1, 1 / 1
    630: False,    # GEO_ACC_F0_WT3, 0 / 1
    631: False,    # GEO_ACC_F0_WT2, 0 / 1
    632: False,    # GEO_ACC_F0_WT1, 0 / 1
    636: False,    # GEO_ACC_F0_IRF, 0 / 2
    637: False,    # GEO_ACC_F0_EYE, 0 / 2
    641: False,    # GEO_ACC_F0_HSK, 1 / 1
    642: False,    # GEO_ACC_F0_RBN, 0 / 2
    643: True,    # GEO_NPC_F2_DAC, 4 / 0
    646: True,    # GEO_NPC_F1_APF, 5 / 0
    647: True,    # GEO_NPC_F1_JJY, 9 / 1
    658: True,    # GEO_MAIN_F1_STN, 33 / 0
    659: True,    # GEO_SUB_F7_BLN, 1 / 0
    660: True,    # GEO_SUB_F7_MRC, 3 / 0
    661: True,    # GEO_SUB_F7_CNA, 1 / 0
    662: True,    # GEO_MAIN_F7_VIV, 7 / 0
    665: True,    # GEO_SUB_F0_MOM, 1 / 0
    666: True,    # GEO_MAIN_F8_GRN, 1 / 0
    667: True,    # GEO_SUB_F3_KJA, 3 / 0
    668: False,    # GEO_MAIN_F3_ZDN, 0 / 1
    669: False,    # GEO_MAIN_F4_ZDN, 0 / 1
    670: False,    # GEO_MAIN_F5_ZDN, 0 / 1
    674: True,    # GEO_NPC_F5_CSA, 1 / 0
    675: True,    # GEO_NPC_F6_CSA, 1 / 0
    677: True,    # GEO_NPC_F1_KAC, 1 / 0
    678: True,    # GEO_NPC_F2_KAC, 1 / 0
    679: False,    # GEO_ACC_F1_MGP, 0 / 2
    680: False,    # GEO_ACC_F2_LTT, 0 / 2
    681: True,    # GEO_ACC_F1_SWD, 1 / 0
    701: True,    # GEO_ACC_F2_TBX, 5 / 0
    702: True,    # GEO_ACC_F3_TBX, 6 / 0
    5464: True,    # GEO_SUB_F0_BAK, 24 / 0
    5467: True,    # GEO_SUB_F0_BLN, 36 / 0
    5468: True,    # GEO_NPC_F0_BMG, 52 / 7
    5474: True,    # GEO_NPC_F0_COK, 24 / 0
    5476: True,    # GEO_NPC_F0_G18, 8 / 0
    5478: True,    # GEO_NPC_F0_HUM, 13 / 0
    5488: True,    # GEO_SUB_F0_SSB, 35 / 2
    5489: True,    # GEO_MAIN_F0_STN, 152 / 2
    5492: True,    # GEO_NPC_F0_TGR, 26 / 0
    5500: True,    # GEO_SUB_F0_ZNR, 27 / 0
    5501: True,    # GEO_SUB_F1_BAK, 8 / 0
    5505: True,    # GEO_SUB_F1_SSB, 3 / 0
    5509: True,    # GEO_SUB_F2_SSB, 11 / 0
    5511: True,    # GEO_SUB_F3_SSB, 2 / 0
}
