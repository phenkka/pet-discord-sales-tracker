import os
from dotenv import load_dotenv

load_dotenv()


TOKEN = os.getenv("DISCORD_TOKEN")
SALES_CHANNELS = [
    int(os.getenv("TEST_1")),
    int(os.getenv("TEST_2"))
]
CLOCK_CHANNEL = int(os.getenv("TEST_3"))


# SALES_CHANNELS = [
#     int(os.getenv("F2F_TA_09_JOWISSA")),
#     int(os.getenv("F2F_TA_09_RIAD")),
#     int(os.getenv("F2F_TA_09_GENNA")),
#     int(os.getenv("F2F_TA_09_GLYDEL")),
#     int(os.getenv("F2F_TA_010_GENNA")),
#     int(os.getenv("F2F_TA_010_PATRIC")),
#     int(os.getenv("F2F_TA_011_GENNA")),
#     int(os.getenv("F2F_TA_012_GLYDEL")),
#     int(os.getenv("F2F_TA_012_GENNA")),
#     int(os.getenv("F2F_TA_013_IVY"))
# ]

# CLOCK_CHANNEL = int(os.getenv("CLOCK_CHANNEL"))