'''RCT System States
'''
from enum import IntEnum, Enum


class GPS_STATES(IntEnum):
	get_tty = 0
	get_msg = 1
	wait_recycle = 2
	rdy = 3
	fail = 4

class SDR_INIT_STATES(IntEnum):
	find_devices = 0
	wait_recycle = 1
	usrp_probe = 2
	rdy = 3
	fail = 4

class OUTPUT_DIR_STATES(IntEnum):
	get_output_dir = 0
	check_output_dir = 1
	check_space = 2
	wait_recycle = 3
	rdy = 4
	fail = 5

class RCT_STATES(Enum):
	init		=	0
	wait_init	=	1
	wait_start	=	2
	start		=	3
	wait_end	=	4
	finish		=	5
	fail		=	6
