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
MK1_PKT = 0xfc00 #this macro is used by 6x6 mk2 switch
MK2_PKT = 0xff00
MK1_WIDTH = 8
MK2_WIDTH = 16
MK1_LIST = ['fic00', 'fic01', 'fic02', 'fic03',
            'fic04', 'fic05', 'fic06', 'fic07',
            'fic08', 'fic09', 'fic10', 'fic11']
MK2_LIST = ['m2fic00', 'm2fic01', 'm2fic02', 'm2fic03',
            'm2fic04', 'm2fic05', 'm2fic06', 'm2fic07',
            'm2fic08', 'm2fic09', 'm2fic10', 'm2fic11']
FIC_LIST = MK1_LIST + MK2_LIST

class packet_counter:
    def __init__(self, target, radix):
        self.target = target
        self.radix = radix
        self.packet_counter_list = list()

    def mk1_get_packet_counter_5x5(self):
        ficmgr = libficmgr.libficmgr()
        for i in range(0, SWNUM):
            for j in range(0, self.radix*2):
                count = 0
                for k_index in range(0, 4):
                    k = 3 - k_index
                    tmp = ficmgr.fic_read(self.target, MK1_PKT + ((i^2) << 8) + (j << 2) + k)
                    count = (count << 8) | tmp['data']
                self.packet_counter_list.append(count)

    def mk1_get_packet_counter_for_multi_ejection_5x5(self):
        ficmgr = libficmgr.libficmgr()
        for i in range(0, SWNUM):
            for j in range(0, self.radix*2+3):
                count = 0
                for k_index in range(0, 4):
                    k = 3 - k_index
                    tmp = ficmgr.fic_read(self.target, MK1_PKT + ((i^2) << 8) + (j << 2) + k)
                    count = (count << 8) | tmp['data']
                self.packet_counter_list.append(count)

    def mk2_get_packet_counter_5x5(self):
        ficmgr = libficmgr.libficmgr()
        for i in range(0, SWNUM):
            for j in range(0, self.radix*2):
                tmp = ficmgr.fic_read(self.target, MK2_PKT + (i << 5) + j * 2)
                count = tmp['data']
                tmp = ficmgr.fic_read(self.target, MK2_PKT + (i << 5) + j * 2 + 1)
                count = (count << 16) | tmp['data']
                self.packet_counter_list.append(count)
    
    def mk2_get_packet_counter_for_multi_ejection_5x5(self):
        ficmgr = libficmgr.libficmgr()
        for i in range(0, SWNUM):
            for j in range(0, self.radix*2+3):
                tmp = ficmgr.fic_read(self.target, MK2_PKT + (i << 5) + j * 2)
                count = tmp['data']
                tmp = ficmgr.fic_read(self.target, MK2_PKT + (i << 5) + j * 2 + 1)
                count = (count << 16) | tmp['data']
                self.packet_counter_list.append(count)

    def get_packet_counter_6x6(self, gpio_width):
        ficmgr = libficmgr.libficmgr()
        for i in range(0, SWNUM):
            for j in range(0, self.radix*2):
                count = 0
                for k_index in range(0, 32//gpio_width):
                    k = (32//gpio_width) - k_index - 1
                    tmp = ficmgr.fic_read(self.target, MK1_PKT + (i << 8) + j * 32//gpio_width + k)
                    count = (count << gpio_width) | tmp['data']
                self.packet_counter_list.append(count)

    def print_packet_counter_5x5(self):
        print('########' + self.target + '################')
        for i in range(0, SWNUM):
            print('----lane' + str(i) + '----')
            print('from_hls(in0):' + str(self.packet_counter_list[i*self.radix*2+0]) + ', in1:' + str(self.packet_counter_list[i*self.radix*2+1]) + ', in2:' + str(self.packet_counter_list[i*self.radix*2+2]) + ', in3:' + str(self.packet_counter_list[i*self.radix*2+3]) + ', in4:' + str(self.packet_counter_list[i*self.radix*2+4]))
            print('to_hls(out0):' + str(self.packet_counter_list[i*self.radix*2+5]) + ', out1:' + str(self.packet_counter_list[i*self.radix*2+6]) + ', out2:' + str(self.packet_counter_list[i*self.radix*2+7]) + ', out3:' + str(self.packet_counter_list[i*self.radix*2+8]) + ', out4:' + str(self.packet_counter_list[i*self.radix*2+9]))
        print()
        print()
    
    def print_packet_counter_for_multi_ejection_5x5(self):
        print('########' + self.target + '################')
        for i in range(0, SWNUM):
            print('----lane' + str(i) + '----')
            print('from_hls(in0):' + str(self.packet_counter_list[i*(self.radix*2+3)+0]) + ', in1:' + str(self.packet_counter_list[i*(self.radix*2+3)+1]) + ', in2:' + str(self.packet_counter_list[i*(self.radix*2+3)+2]) + ', in3:' + str(self.packet_counter_list[i*(self.radix*2+3)+3]) + ', in4:' + str(self.packet_counter_list[i*(self.radix*2+3)+4]))
            print('to_hls(out0):(' + str(self.packet_counter_list[i*(self.radix*2+3)+5]) + ', ' + str(self.packet_counter_list[i*(self.radix*2+3)+10]) + ', ' + str(self.packet_counter_list[i*(self.radix*2+3)+11]) + ', ' + str(self.packet_counter_list[i*(self.radix*2+3)+12]) + '), out1:' + str(self.packet_counter_list[i*(self.radix*2+3)+6]) + ', out2:' + str(self.packet_counter_list[i*(self.radix*2+3)+7]) + ', out3:' + str(self.packet_counter_list[i*(self.radix*2+3)+8]) + ', out4:' + str(self.packet_counter_list[i*(self.radix*2+3)+9]))
        print()
        print()

    def print_packet_counter_6x6(self):
        print('########' + self.target + '################')
        for i in range(0, SWNUM):
            print('----lane' + str(i) + '----')
            print('from_hls(in0):' + str(self.packet_counter_list[i*self.radix*2+0]) + ', in1:' + str(self.packet_counter_list[i*self.radix*2+1]) + ', in2:' + str(self.packet_counter_list[i*self.radix*2+2]) + ', in3:' + str(self.packet_counter_list[i*self.radix*2+3]) + ', in4:' + str(self.packet_counter_list[i*self.radix*2+4]) + ', in5:' + str(self.packet_counter_list[i*self.radix*2+5]))
            print('to_hls(out0):' + str(self.packet_counter_list[i*self.radix*2+6]) + ', out1:' + str(self.packet_counter_list[i*self.radix*2+7]) + ', out2:' + str(self.packet_counter_list[i*self.radix*2+8]) + ', out3:' + str(self.packet_counter_list[i*self.radix*2+9]) + ', out4:' + str(self.packet_counter_list[i*self.radix*2+10]) + ', out5:' + str(self.packet_counter_list[i*self.radix*2+11]))
        print()
        print()

class packet_monitor:
    def __init__(self):
        args = None

    def argparse(self):
        parser = argparse.ArgumentParser(description='Get packet counter')

        parser.add_argument('-t', help='target FPGA (name)', nargs='*', default=[])
        parser.add_argument('--tid', help='target FPGA (id)', nargs='*', default=[], type=int)
        parser.add_argument('-a', '--ALL', help='If you want to get packet counter from all FPGAs, you can use this option instead of the -t option.', action='store_true')
        parser.add_argument('-m', help='use multi-ejection switches', action='store_true')
        parser.add_argument('--radix', help='radix of the switch', type=int, choices=[5, 6], default=6)

        self.args = parser.parse_args()

        if self.args.t == [] and self.args.tid == [] and self.args.ALL == False:
            print('Error: please input target FPGA.', sys.stderr)
            sys.exit(1)

        if self.args.m and self.args.radix == 6:
            print('Error: the multi-ejection switch whose radix is 6 is not supported.', sys.stderr)
            sys.exit(2)

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
        if (not self.args.m) and self.args.radix == 5:
            for target in targetlist:
                actor = packet_counter(target, self.args.radix)
                if target in MK1_LIST:
                    actor.mk1_get_packet_counter_5x5()
                else:
                    actor.mk2_get_packet_counter_5x5()
                actor.print_packet_counter_5x5()
        elif self.args.m and self.args.radix == 5:
            for target in targetlist:
                actor = packet_counter(target, self.args.radix)
                if target in MK1_LIST:
                    actor.mk1_get_packet_counter_for_multi_ejection_5x5()
                else:
                    actor.mk2_get_packet_counter_for_multi_ejection_5x5()
                actor.print_packet_counter_for_multi_ejection_5x5()
        elif (not self.args.m) and self.args.radix == 6:
            for target in targetlist:
                actor = packet_counter(target, self.args.radix)
                if target in MK1_LIST:
                    actor.get_packet_counter_6x6(MK1_WIDTH)
                else:
                    actor.get_packet_counter_6x6(MK2_WIDTH)
                actor.print_packet_counter_6x6()

if __name__ == '__main__':
    obj = packet_monitor()
    obj.main()
