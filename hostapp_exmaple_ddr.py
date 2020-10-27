#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# Host application example using libficmgr
#------------------------------------------------------------------------------
import os
import sys, traceback
import libficmgr

#------------------------------------------------------------------------------
MK1_FPGA_BITSTREAM = '/home/hlab/nyacom/project/fic/ficmgr/mk1_ficbd_ddr4_20201017.bin'
SAMPLE_FILE        = '/home/hlab/nyacom/project/fic/libfic2/1G'

#------------------------------------------------------------------------------
if __name__ == '__main__':
    ficmgr = libficmgr.libficmgr()

    # Configure target FPGA
    print('TEST: Prog FPGA')
    ficmgr.fic_prog('fic11', 'sm8', True, MK1_FPGA_BITSTREAM, "Host app example")

    # Reset Start HLS
    print('TEST: HLS reset start')
    ficmgr.fic_hls_cmd('fic11', 'reset')
    ficmgr.fic_hls_cmd('fic11', 'start')

    # Read data file and transfer to DDR
    print('TEST: DDR write')
    with open(SAMPLE_FILE, 'rb') as f:
        buf = f.read(1024*1024*10)    # Read 10MB
        ficmgr.fic_hls_ddr_write('fic11', buf, 0)

    print('TEST: DDR read')
    ret = ficmgr.fic_hls_ddr_read('fic11', 1024*1024*1, 0)  # Readout 1MB
    print(len(ret['data']))
