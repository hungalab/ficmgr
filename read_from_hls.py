#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os.path
import os
import shutil
import sys, traceback
import subprocess
import struct
import binascii
import json
from collections import OrderedDict
import libficmgr

SWNUM = 4
PORTS = 5
TIM = 0xff80
MK1_WIDTH = 8
MK2_WIDTH = 16
RESULT_WIDTH = 8
MK1_LIST = ['fic00', 'fic01', 'fic02', 'fic03',
            'fic04', 'fic05', 'fic06', 'fic07',
            'fic08', 'fic09', 'fic10', 'fic11']
MK2_LIST = ['m2fic00', 'm2fic01', 'm2fic02', 'm2fic03',
            'm2fic04', 'm2fic05', 'm2fic06', 'm2fic07',
            'm2fic08', 'm2fic09', 'm2fic10', 'm2fic11']
FIC_LIST = MK1_LIST + MK2_LIST

class reader:
    def __init__(self, target, type, size, gpio_width):
        self.target = target
        self.type = type
        self.size = size
        self.gpio_width = gpio_width
        self.data = []
        self.converted_data = list()
        self.hex_data = list()
        self.data_bit_width = {'int': 32, 'uint': 32, 'float': 32}

    def hex_to_int(self, s):
        return format(-(int(s, 16) & (0x00000001 << (32 - 1))) | (int(s, 16) & ~(0x00000001 << (32 - 1))))
    
    def hex_to_uint(self, s):
        return format(int(s, 16))
    
    def hex_to_float(self, s):
        if s.startswith('0x'):
            s = s[2:]
        s = s.replace(' ', '')
        return format(struct.unpack('>f', binascii.unhexlify(s))[0], '.6f')

    def read_data(self):
        ficmgr = libficmgr.libficmgr()
        count = self.size * self.data_bit_width[self.type] // RESULT_WIDTH
        tmp = ficmgr.fic_hls_receive(self.target, count)
        if (tmp['return'] != 'success'):
            print(tmp)
        self.data = tmp['data']
    
    def convert_data(self):
        count = self.data_bit_width[self.type] // RESULT_WIDTH
        little_count = self.gpio_width // RESULT_WIDTH
        for i in range(0, self.size):
            val = 0
            for j in range(0, count//little_count):
                for k in range(0, little_count):
                    tmp = self.data[i * count + j * little_count + (little_count - k - 1)]
                    val = (val << RESULT_WIDTH) | tmp
            if self.data_bit_width[self.type] == 32:
                val_str = format(val, '#010x')
            self.hex_data.append(val_str)
            if self.type == 'int':
                self.converted_data.append(self.hex_to_int(val_str))
            elif self.type == 'uint':
                self.converted_data.append(self.hex_to_uint(val_str))
            elif self.type == 'float':
                self.converted_data.append(self.hex_to_float(val_str))

    def print_data(self):
        print('########' + self.target + '################')
        i = 0
        for val in self.converted_data:
            print('data[' + str(i) + ']: ' + val + ' (hex:' + self.hex_data[i] + ')')
            i = i + 1
        print()

class read_from_hls:
    def __init__(self):
        args = None

    def argparse(self):
        parser = argparse.ArgumentParser(description='Get timer')

        parser.add_argument('-t', help='target FPGA (name)', nargs='*', default=[])
        parser.add_argument('--tid', help='target FPGA (id)', nargs='*', default=[], type=int)
        parser.add_argument('-a', '--ALL', help='If you want to get data from all FPGAs, you can use this option instead of the -t option.', action='store_true')
        parser.add_argument('--type', help='data type', choices=['int', 'uint', 'float'], required=True)
        parser.add_argument('-s', '--size', help='# of data for each board', type=int, default=1)

        self.args = parser.parse_args()

        if self.args.t == [] and self.args.tid == [] and self.args.ALL == False:
            print('Error: please input target FPGA.', sys.stderr)
            sys.exit(1)
        
        if self.args.size <= 0:
            print('Invalid size: please input positive number.', sys.stderr)
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
        for target in targetlist:
            if target in MK1_LIST:
                actor = reader(target, self.args.type, self.args.size, MK1_WIDTH)
            else:
                actor = reader(target, self.args.type, self.args.size, MK2_WIDTH)
            actor.read_data()
            actor.convert_data()
            actor.print_data()

if __name__ == '__main__':
    obj = read_from_hls()
    obj.main()