#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os.path
import os
import shutil
import sys, traceback
import subprocess
import json
from collections import OrderedDict
import libficmgr

SWNUM = 4
PORTS = 5
TIM = 0xff80
MK1_LIST = ['fic00', 'fic01', 'fic02', 'fic03',
            'fic04', 'fic05', 'fic06', 'fic07',
            'fic08', 'fic09', 'fic10', 'fic11']
MK2_LIST = ['m2fic00', 'm2fic01', 'm2fic02', 'm2fic03',
            'm2fic04', 'm2fic05', 'm2fic06', 'm2fic07',
            'm2fic08', 'm2fic09', 'm2fic10', 'm2fic11']
FIC_LIST = MK1_LIST + MK2_LIST

class timer:
    def __init__(self, target):
        self.target = target
        self.time = 0

    def mk1_get_timer(self):
        ficmgr = libficmgr.libficmgr()
        count = 0
        for k_index in range(0, 4):
            k = 3 - k_index
            tmp = ficmgr.fic_read(self.target, TIM + k)
            count = (count << 8) | tmp['data']
        self.time = count

    def mk2_get_timer(self):
        ficmgr = libficmgr.libficmgr()
        tmp = ficmgr.fic_read(self.target, TIM)
        count = tmp['data']
        tmp = ficmgr.fic_read(self.target, TIM + 1)
        count = (count << 16) | tmp['data']
        self.time = count

    def print_timer(self):
        print('########' + self.target + '################')
        print('timer: ' + str(self.time))
        print()

class time_monitor:
    def __init__(self):
        args = None

    def argparse(self):
        parser = argparse.ArgumentParser(description='Get timer')

        parser.add_argument('-t', help='target FPGA (name)', nargs='*', default=[])
        parser.add_argument('--tid', help='target FPGA (id)', nargs='*', default=[], type=int)
        parser.add_argument('-a', '--ALL', help='If you want to get timer from all FPGAs, you can use this option instead of the -t option.', action='store_true')

        self.args = parser.parse_args()

        if self.args.t == [] and self.args.tid == [] and self.args.ALL == False:
            print('Error: please input target FPGA.', sys.stderr)
            sys.exit(1)

    def main(self):
        self.argparse()
        targetlist = []
        if self.args.ALL:
            targetlist = FIC_LIST
        elif self.args.t != []: 
            targetlist = self.args.t
        else: 
            for tid in self.args.tid:
                targetlist.append(FIC_LIST[tid])
        for target in targetlist:
            actor = timer(target)
            if target in MK1_LIST:
                actor.mk1_get_timer()
            else:
                actor.mk2_get_timer()
            actor.print_timer()

if __name__ == '__main__':
    obj = time_monitor()
    obj.main()
