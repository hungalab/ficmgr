#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
import os
import sys, traceback
import time
import base64
import requests
import json
import simplejson
import gzip
import getpass

import argparse
import pdb

#import http.server
#import socketserver
#import serial
#
#import math
#import struct
#import copy
#import re

from pprint import pprint
from multiprocessing import Process, Queue

#------------------------------------------------------------------------------
import libficmgr
mgr = libficmgr.libficmgr()

#------------------------------------------------------------------------------
VER_STR = 'ficmanager nyacom (C) December, 2018'
DDR_TRANSFER_BLOCK_SIZE = 1024*1024*8

#------------------------------------------------------------------------------
class ficmgr_cli:
    def __init__(self):
        self.args = None

    def argparse(self):
        parser = argparse.ArgumentParser(description = VER_STR)

        # Target
        parser.add_argument('-t', '--target', nargs='+', type=str, 
            metavar=('target1', 'target2'),
            help='Define command target FiC boards')

        # Action
        parser.add_argument('-l', '--list', action='store_true', help='Show FiC board status')
        parser.add_argument('-p', '--prog', nargs='+', type=str, 
            metavar=('for_target1', 'for_target2'),
            help='Program FPGA with *.bit file')

        parser.add_argument('-r', '--reset', action='store_true', help='Perform FPGA reset')
        #parser.add_argument('-d', '--deploy', nargs=1, type=str, help='Deploy fic configuration with json file')

        parser.add_argument('-hls', '--hlscmd', nargs=1, type=str, 
            metavar='[ start | reset ]', help='Control HLS')

        parser.add_argument('-hr', '--hlsrecv', nargs=1, type=str, 
            metavar='count', help='Receive count data from HLS')

        parser.add_argument('-hs', '--hlssend', nargs='+', type=str, 
            metavar=('for_target1', 'for_target2'),
            help='Send provided data file to HLS (CSV or value per line text file are supported)')

        parser.add_argument('-sw', '--switchset', nargs='+', type=str, 
            metavar=('for_target1', 'for_target2'),
            help='Set switch table with *.json file')

        parser.add_argument('-rr', '--regread', nargs=1, type=str, 
            metavar='ADDR',
            help='FiC register read from address')

        parser.add_argument('-rw', '--regwrite', nargs=2, type=str, 
            metavar=('ADDR', 'VALUE'),
            help='FiC register write to [address value]')

        parser.add_argument('-dr', '--ddrread', nargs=2, type=str, 
            metavar=('ADDR', 'SIZE'),
            help='Read SIZE byte data from DDR in ADDRess')

        parser.add_argument('-dw', '--ddrwrite', nargs=2, type=str, 
            metavar=('ADDR', 'FILE'),
            help='Write FILE data to DDR in ADDRess')

        parser.add_argument('-pm', '--progmode', nargs=1, type=str, 
            metavar='[ sm16 | sm16pr | sm8 | sm8pr ]',
            help='FPGA Program mode')

        parser.add_argument('-pmsg', '--message', nargs=1, type=str, 
            metavar='MESSAGE',
            help='Message/notes for this FPGA programing')

        parser.add_argument('--runcmd', nargs='+', type=str, 
            metavar=('cmdline_for_target1', 'cmdline_for_target2'),
            help='Run command on RPi3')

        parser.add_argument('--runcmdtimeout', nargs='?', type=int, 
            metavar='Timeout sec',
            help='Run command timeout in second (default is 5sec)')

        parser.add_argument('-f', '--conf', nargs=1, type=str, 
            metavar='FiCSW configuration setup file',
            help='Configure FiCSW with configuration setup file (.json)')

        #parser.add_argument('-o','--output', nargs=1, type=str)
        #parser.add_argument('infile', nargs=1, type=str)

        self.args = parser.parse_args()

    #------------------------------------------------------------------------------
    # Analyse target from cmdline argument
    # Note: self.args.url value priotize if it has set
    #------------------------------------------------------------------------------
    def get_target(self):
        if self.args.target != None:
            for t in self.args.target:
                if t not in mgr.board:
                    print("ERROR: board {0:s} is unknown".format(t), file=sys.stderr)
                    return None
            
            return self.args.target

        else:
            return mgr.board

    #------------------------------------------------------------------------------
    # Commandline parser
    #------------------------------------------------------------------------------
    def cmd_fic_status(self):
        stat = {}
        targets = self.get_target()

        procs = []
        q = Queue()
        def proc(q, target):
            ret = mgr.fic_get_status(target)
            q.put((target, ret))

        for t in targets:
            p = Process(target=proc, args=(q, t))
            procs.append(p)
            p.start()

        for p in procs:
            p.join()
            target, ret = q.get()
            stat[target] = ret
 
        for t in mgr.board:
            if t in stat.keys():
                if stat[t]['return'] == 'success':
                    brdst = stat[t]['status']
                    print("'{0:s}':\n".format(t), end='')
                    pprint(brdst, indent=4)
                    print('\n\n', end='')

                else:
                    print('{0:s}:\n'.format(t), end='')
                    print('ERROR: get status failed.\n\n')
                    return 1

        return 0

    #------------------------------------------------------------------------------
    def cmd_fic_reset(self):
        stat = {}
        target = self.get_target()

        for t in target:
            stat[t] = mgr.fic_reset(t)

        for t in mgr.board:
            if t in stat.keys():
                if stat[t]['return'] == 'success':
                    print('INFO: Reset FPGA on {0:s} is success'.format(t))

                else:
                    print('INFO: Reset FPGA on {0:s} is failed'.format(t))
                    return 1

        return 0

    #------------------------------------------------------------------------------
    def cmd_fic_read(self):
        if self.args.target is None:
            print("ERROR: You must specify target.", file=sys.stderr)
            return 1

        targets = self.get_target()
        addr = 0x0
        try:
            addr = int(self.args.regread[0], 0)

        except ValueError:
            print("ERROR: Invalid reg address.", file=sys.stderr)
            return 1

        if addr > 0xffff:
            print("ERROR: Invalid reg address 0x{0:x}.".format(addr), file=sys.stderr)
            return 1

        procs = []
        q = Queue()
        def proc(q, target, addr):
            ret = mgr.fic_read(target, addr)
            q.put((target, ret))

        for t in targets:
            p = Process(target=proc, args=(q, t, addr))
            procs.append(p)
            p.start()

        for p in procs:
            p.join()
            target, ret = q.get()

            if ret['return'] == 'success':
                print("INFO: {0:s} [0x{1:x}] = 0x{2:x}".format(target, addr, ret['data']))

            else:
                print("INFO: return from {0:s} is failed".format(target))
                return 1

        return 0
 
    #------------------------------------------------------------------------------
    def cmd_fic_write(self):
        if self.args.target is None:
            print("ERROR: You must specify target.", file=sys.stderr)
            return 1

        targets = self.get_target()
        addr = 0x0
        val = 0x0

        try:
            addr = int(self.args.regwrite[0], 0)
            val  = int(self.args.regwrite[1], 0)

        except ValueError:
            print("ERROR: Invalid addr/val value.", file=sys.stderr)
            return 1

        if addr > 0xffff:
            print("ERROR: Invalid reg address 0x{0:x}.".format(addr), file=sys.stderr)
            return 1

        if val > 0xff:
            print("ERROR: Invalid val 0x{0:x}.".format(val), file=sys.stderr)
            return 1

        procs = []
        q = Queue()
        def proc(q, target, addr, val):
            ret = mgr.fic_write(target, addr, val)
            q.put((target, ret))

        for t in targets:
            p = Process(target=proc, args=(q, t, addr, val))
            procs.append(p)
            p.start()

        for p in procs:
            p.join()
            target, ret = q.get()

            if ret['return'] == 'success':
                print("INFO: {0:s} [0x{1:x}] is write success".format(target, addr))

            else:
                print("INFO: {0:s} [0x{1:x}] is write failed".format(target, addr))
                return 1
        
        return 0

    #------------------------------------------------------------------------------
    def cmd_hls_ddr_read_exec(self, targets, addr, size):
        if addr < 0 or addr > 0xffffffff:
            print("ERROR: Invalid reg address 0x{0:x}.".format(addr), file=sys.stderr)
            return 1

        procs = []
        q = Queue()
        def proc(q, target, size, addr):

            ret = {'return': 'failed'}

            total_size = size
            rx_left  = size
            block_size = DDR_TRANSFER_BLOCK_SIZE
            dump_file  = '{0:s}_ddr.out'.format(target)

            with open(dump_file, 'wb') as f:
                for ar in range(addr, addr+total_size, block_size):
                    if rx_left < block_size:
                        ret = mgr.fic_hls_ddr_read(target, rx_left, addr)
                        rx_left -= rx_left

                    else:
                        ret = mgr.fic_hls_ddr_read(target, block_size, addr)
                        rx_left -= block_size

                    if ret['return'] == 'success':
                        #print(ret['data'])
                        f.write(ret['data'])
                        print("[{0:s}] DDR Read Transfer {1:d}/{2:d}".format(target, total_size - rx_left, total_size))

                    else:
                        print("ERROR: DDR Read Transfer", file=sys.stderr)
                        break

                ret = {'return': 'success'}

            q.put((target, ret))

        for t in targets:
            p = Process(target=proc, args=(q, t, size, addr))
            procs.append(p)
            p.start()

        for p in procs:
            p.join()
            target, ret = q.get()

        return 0
 
    #------------------------------------------------------------------------------
    def cmd_hls_ddr_read(self):
        if self.args.target is None:
            print("ERROR: You must specify target.", file=sys.stderr)
            return 1

        targets = self.get_target()

        # Check address
        try:
            addr = int(self.args.ddrread[0], 0)
            size = int(self.args.ddrread[1], 0)

        except ValueError:
            print("ERROR: Invalid reg address.", file=sys.stderr)
            return 1

        return self.cmd_hls_ddr_read_exec(targets, addr, size)

    #------------------------------------------------------------------------------
    def cmd_hls_ddr_write_exec(self, targets, addr, files):
        if addr < 0 or addr > 0xffffffff:
            print("ERROR: Invalid reg address 0x{0:x}.".format(addr), file=sys.stderr)
            return 1

        #------------------------------------------------------------------------------
        procs = []
        q = Queue()
        def proc(q, target, addr, file):
            ret = {'return': 'failed'}

            total_size = os.path.getsize(file)
            block_size = DDR_TRANSFER_BLOCK_SIZE
            tx_size = 0

            with open(file, 'rb') as f:
                for ar in range(addr, addr+total_size, block_size):
                    buf = f.read(block_size)
                    ret = mgr.fic_hls_ddr_write(target, buf, ar)
                    tx_size += len(buf)
                    print("[{0:s}] DDR Write Transfer {1:d}/{2:d}".format(target, tx_size, total_size))

                    if ret['return'] == 'failed':
                        print("ERROR: DDR Write Transfer", file=sys.stderr)
                        break

            q.put((target, ret))
        #------------------------------------------------------------------------------

        if len(files) > 1:  # multiple files to multiple FPGAs
            for file, t in zip(files, targets):
                p = Process(target=proc, args=(q, t, addr, file))
                procs.append(p)
                p.start()

        else:
            file = files[0]
            for t in targets:
                p = Process(target=proc, args=(q, t, addr, file))
                procs.append(p)
                p.start()

        for p in procs:
            p.join()
            target, ret = q.get()

            if ret['return'] == 'success':
                print("INFO: {0:s} [0x{1:x}] is write success".format(target, addr))

            else:
                print("INFO: {0:s} [0x{1:x}] is write failed".format(target, addr))
                return 1

        return 0
 
    #------------------------------------------------------------------------------
    def cmd_hls_ddr_write(self):
        if self.args.target is None:
            print("ERROR: You must specify target.", file=sys.stderr)
            return 1

        targets = self.get_target()

        # Address
        addr = 0x0
        try:
            addr = int(self.args.ddrwrite[0], 0)

        except ValueError:
            print("ERROR: Invalid addr/val value.", file=sys.stderr)
            return 1

        # File
        file = self.args.ddrwrite[1]
        if os.path.exists(file) == False:
            print("ERROR: Can't open file {0:s}.".format(file), file=sys.stderr)
            return 1

        return self.cmd_hls_ddr_write_exec(targets, addr, [file])

    #------------------------------------------------------------------------------
    def cmd_fic_prog_exec(self, targets, pr_mode, memo, bs_files):

        #------------------------------------------------------------------------------
        procs = []
        q = Queue()
        def proc(q, target, pr_mode, bs_file, msg):
            ret = mgr.fic_prog(target, pr_mode, True, bs_file, msg)
            q.put((target, ret))

        #------------------------------------------------------------------------------

        if len(bs_files) > 1:   # Multiple files to multiple FPGAs
            if len(bs_files) != len(targets):
                print("ERROR: Unmatch number of *.bit files and targets.", file=sys.stderr)
                return 1

            for bs, t in zip(bs_files, targets):
                p = Process(target=proc, args=(q, t, pr_mode, bs,  memo))
                procs.append(p)
                p.start()

        else:   # Single file to multiple FPGAs
            bs = bs_files[0]
            for t in targets:
                p = Process(target=proc, args=(q, t, pr_mode, bs, memo))
                procs.append(p)
                p.start()

        for p in procs:
            p.join()
            target, ret = q.get()
            if ret['return'] == 'success':
                print("INFO: FPGA configuration on {0:s} is success".format(target))

            else:
                print("INFO: FPGA configuration on {0:s} is failed".format(target))
                return 1

        return 0

    #------------------------------------------------------------------------------
    def cmd_fic_prog(self):
        if self.args.prog is None:
            print("ERROR: You must specify bitfile.", file=sys.stderr)
            return 1

        bs_files = self.args.prog

        if self.args.target is None:
            print("ERROR: You must specify target.", file=sys.stderr)
            return 1

        targets = self.get_target()

        pr_mode = 'sm16'
        if self.args.progmode != None:
            pr_mode = self.args.progmode[0]
            if pr_mode not in ['sm16', 'sm16pr', 'sm8', 'sm8pr']:
                print("ERROR: The program mode {0:s} is unknown".format(pm), file=sys.stderr)
                return 1
        
        memo = 'Configure via ficmanager by {0:s}@{1:s}'.format(getpass.getuser(), os.uname()[1])
        if self.args.message != None:
            memo = self.args.message[0]

        return self.cmd_fic_prog_exec(targets, pr_mode, memo, bs_files)

    #------------------------------------------------------------------------------
    def cmd_hls_cmd_exec(self, targets, cmd):
        procs = []
        q = Queue()
        def proc(q, target, cmd):
            ret = mgr.fic_hls_cmd(target, cmd)
            q.put((target, ret))

        for t in targets:
            p = Process(target=proc, args=(q, t, cmd))
            procs.append(p)
            p.start()

        for p in procs:
            p.join()
            target, ret = q.get()
            if ret['return'] == 'success':
                print("INFO: HLS send command on {0:s} success".format(target))

            else:
                print("INFO: HLS send command on {0:s} failed".format(target))
                return 1

        #procs = []
        #for t in target:
        #    p = Process(target=self.fic_hls_cmd, args=(t, cmd))
        #    procs.append(p)
        #    p.start

        #for p in procs:
        #    print(p.join())
        return 0

    def cmd_hls_cmd(self):
        if self.args.target is None:
            print("ERROR: You must specify target.", file=sys.stderr)
            return 1

        targets = self.get_target()

        cmd = self.args.hlscmd[0]
        if cmd not in ['start', 'reset']:
            print("ERROR: Unknown command {0:s}.".format(cmd), file=sys.stderr)
            return 1

        return self.cmd_hls_cmd_exec(targets, cmd)

    #------------------------------------------------------------------------------
    def cmd_hls_recv(self):
        if self.args.target is None:
            print("ERROR: You must specify target.", file=sys.stderr)
            return 1

        targets = self.get_target()
        arg1 = self.args.hlsrecv[0]

        count = 0
        try:
            count = int(arg1)

        except ValueError:
            print("ERROR: Invalid number.", file=sys.stderr)
            return 1

        if count <= 0:
            print("ERROR: Invalid number.", file=sys.stderr)
            return 1

        procs = []
        q = Queue()
        def proc(q, target, count):
            ret = mgr.fic_hls_receive(target, count)
            q.put((target, ret))

        for t in targets:
            p = Process(target=proc, args=(q, t, count))
            procs.append(p)
            p.start()

        for p in procs:
            p.join()
            target, ret = q.get()
            if ret['return'] == 'success':
                print(ret)

            else:
                print("INFO: HLS data receive failed on {0:s}".format(target))
                return 1

        #procs = []
        #for t in target:
        #    p = Process(target=self.fic_hls_recv, args=(t, count))
        #    procs.append(p)
        #    p.start

        #for p in procs:
        #    p.join()

        return 0

    #------------------------------------------------------------------------------
    def cmd_hls_send(self):
        if self.args.target is None:
            print("ERROR: You must specify target.", file=sys.stderr)
            return 1

        targets = self.get_target()
        dat_files = self.args.hlssend

        if len(dat_files) > 1:   # Multiple files to multiple FPGAs
            if len(dat_files) != len(targets):
                print("ERROR: Unmatch number of *.dat files and targets.", file=sys.stderr)
                return 1

            procs = []
            q = Queue()
            def proc(q, target, data):
                ret = mgr.fic_hls_send(target, data)
                q.put((target, ret))

            for df, t in zip(dat_files, targets):
                with open(df, 'rt') as f:
                    data = mgr.parse_datafile(f.read())
                    f.close()

                p = Process(target=proc, args=(q, t, data))
                procs.append(p)
                p.start()

            for p in procs:
                p.join()
                target, ret = q.get()
                if ret['return'] == 'success':
                    print("INFO: Sending data to HLS on {0:s} is success".format(target))

                else:
                    print("INFO: Sending data to HLS on {0:s} is failed".format(target))
                    return 1

        else:   # Single file to multiple FPGAs
            filename = os.path.basename(dat_files[0])
            with open(dat_files[0], 'rt') as f:
                data = mgr.parse_datafile(f.read())
                f.close()

                procs = []
                q = Queue()
                def proc(q, target, data):
                    ret = mgr.fic_hls_send(target, data)
                    q.put((target, ret))

                for t in targets:
                    p = Process(target=proc, args=(q, t, data))
                    procs.append(p)
                    p.start()

                for p in procs:
                    p.join()
                    target, ret = q.get()

                    if ret['return'] == 'success':
                        print("INFO: Sending data to HLS on {0:s} is success".format(target))

                    else:
                        print("INFO: Sending data to HLS on {0:s} is failed".format(target))
                        return 1

        return 0

    #------------------------------------------------------------------------------
    def cmd_fic_switchset_exec(self, targets, sw_files):
        if len(sw_files) > 1:   # Multiple files to multiple FPGAs
            if len(sw_files) != len(targets):
                print("ERROR: Unmatch number of *.json files and targets.", file=sys.stderr)
                return 1

            procs = []
            q = Queue()
            def proc(q, target, data):
                ret = mgr.fic_set_switch(target, data)
                q.put((target, ret))

            for df, t in zip(sw_files, targets):
                with open(df, 'rt') as f:
                    data = mgr.parse_switchconfig(f.read())
                    f.close()

                if data is None:
                    return 1

                p = Process(target=proc, args=(q, t, data))
                procs.append(p)
                p.start()

            for p in procs:
                p.join()
                target, ret = q.get()
                if ret['return'] == 'success':
                    print("INFO: Set table on {0:s} is success".format(target))

                else:
                    print("INFO: Set table on {0:s} is failed".format(target))
                    return 1

        else:   # Single file to multiple FPGAs
            filename = os.path.basename(sw_files[0])
            with open(sw_files[0], 'rt') as f:
                data = mgr.parse_switchconfig(f.read())
                f.close()

                if data is None:
                    return 1

                procs = []
                q = Queue()
                def proc(q, target, data):
                    ret = mgr.fic_set_switch(target, data)
                    q.put((target, ret))

                for t in targets:
                    p = Process(target=proc, args=(q, t, data))
                    procs.append(p)
                    p.start()

                for p in procs:
                    p.join()
                    target, ret = q.get()

                    if ret['return'] == 'success':
                        print("INFO: Set table on {0:s} is success".format(target))

                    else:
                        print("INFO: Set table on {0:s} is failed".format(target))
                        return 1

        return 0


    #------------------------------------------------------------------------------
    def cmd_fic_switchset(self):
        if self.args.target is None:
            print("ERROR: You must specify target.", file=sys.stderr)
            return 1

        targets  = self.get_target()
        sw_files = self.args.switchset

        return self.cmd_fic_switchset_exec(targets, sw_files)

    #------------------------------------------------------------------------------
    def cmd_fic_runcmd_exec(self, targets, cmdlines, timeout):
        #--------------------------------------------------------------------------
        def sub_proc(q, target, cmd, tout):
            ret = mgr.fic_runcmd(target, cmd, tout)
            q.put((target, ret))
        #--------------------------------------------------------------------------

        if len(cmdlines) > 1:   # Multiple cmd to multiple FiCs
            if len(cmdlines) != len(targets):
                print("ERROR: Unmatch number of cmdlines and targets. Aren't you forget cmdline quoted?", file=sys.stderr)
                return 1

            procs = []
            q = Queue()
            for cmdline, t in zip(cmdlines, targets):
                p = Process(target=sub_proc, args=(q, t, cmdline, timeout))
                procs.append(p)
                p.start()

            for p in procs:
                p.join()
                target, ret = q.get()

                if ret['return'] == 'success':
                    print("INFO: Run command on {0:s} is success".format(target))
                    print("----")
                    print("Stdout output:\n{0:s}".format(ret['stdout']))
                    print("Stderr output:\n{0:s}".format(ret['stderr']))

                else:
                    print("INFO: Run command on {0:s} is failed".format(target))
                    print("INFO: {0:s}".format(ret['error']))
                    print("----")
                    print("Stdout output:\n{0:s}".format(ret['stdout']))
                    print("Stderr output:\n{0:s}".format(ret['stderr']))
                    return 1

        else:   # Single cmdline to multiple FiCs
            cmdline = cmdlines[0]

            procs = []
            q = Queue()
            for t in targets:
                p = Process(target=sub_proc, args=(q, t, cmdline, timeout))
                procs.append(p)
                p.start()

            for p in procs:
                p.join()
                target, ret = q.get()

                stdout = ret['stdout']
                stderr = ret['stderr']

                if stdout is None:
                    stdout = ""

                if stderr is None:
                    stderr = ""


                if ret['return'] == 'success':
                    print("INFO: Run command on {0:s} is success".format(target))
                    print("----")
                    print("Stdout output:\n{0:s}".format(stdout))
                    print("Stderr output:\n{0:s}".format(stderr))

                else:
                    print("INFO: Run command on {0:s} is failed".format(target))
                    print("INFO: {0:s}".format(ret['error']))
                    print("----")
                    print("Stdout output:\n{0:s}".format(stdout))
                    print("Stderr output:\n{0:s}".format(stderr))
                    return 1

        return 0

    #------------------------------------------------------------------------------
    def cmd_fic_runcmd(self):
        if self.args.target is None:
            print("ERROR: You must specify target.", file=sys.stderr)
            return 1

        targets  = self.get_target()
        cmdlines = self.args.runcmd
        timeout  = self.args.runcmdtimeout

        return self.cmd_fic_runcmd_exec(targets, cmdlines, timeout)

    #------------------------------------------------------------------------------
    def cmd_fic_setup(self):
        conf_file = self.args.conf[0]
        with open(conf_file, 'rt') as f:
            data = mgr.parse_setupfile(f.read())
            f.close()

            if data is None:
                return 1

            procs = []
            q = Queue()
            #------------------------------------------------------------------
            def proc(q, target, conf):
                # config FPGA
                if 'fpga' in conf:
                    print('INFO: FPGA setup on {0}'.format(target))
                    fpga = conf['fpga']
                    bs_file = fpga['bitstream']
                    pr_mode = fpga['progmode']
                    msg = ''
                    if 'msg' in fpga.keys():
                        msg = fpga['msg']

                    ret = self.cmd_fic_prog_exec([target], pr_mode, msg, [bs_file])
                    if ret > 0:
                        q.put((target, {'return': 'failed'}))
                        return

#                    bitname = os.path.basename(bs_file)
#                    with open(bs_file, 'rb') as f:
#                        b64 = base64.b64encode(gzip.compress(f.read()))
#                        f.close()
#                        ret = mgr.fic_prog(target, pr_mode, True, bitname, b64, msg)
#                        if ret['return'] != 'success':
#                            q.put((target, ret))
#                            return

                # config TABLE
                if 'switch' in conf:
                    print('INFO: Switch setup on {0}'.format(target))
                    switch = conf['switch']
                    ret = mgr.fic_set_switch(target, switch)

                    if ret['return'] != 'success':
                        q.put((target, ret))
                        return

                # config OPTION
                if 'option' in conf:
                    print('INFO: Option setting on {0}'.format(target))
                    option = conf['option']

                    if 'auto_hls_reset_start' in option.keys():
                        ret = mgr.fic_hls_cmd(target, 'reset')
                        ret = mgr.fic_hls_cmd(target, 'start')

                        if ret['return'] != 'success':
                            q.put((target, ret))
                            return

                    if 'auto_runcmd' in option.keys():
                        ret = mgr.fic_runcmd(target, option['auto_runcmd'], 5)
                        stdout = ret['stdout']
                        stderr = ret['stderr']

                        if stdout is None:
                            stdout = ""

                        if stderr is None:
                            stderr = ""

                        if ret['return'] == 'success':
                            print("INFO: Run command on {0:s} is success".format(target))
                            print("----")
                            print("Stdout output:\n{0:s}".format(stdout))
                            print("Stderr output:\n{0:s}".format(stderr))

                        else:
                            print("INFO: Run command on {0:s} is failed".format(target))
                            print("INFO: {0:s}".format(ret['error']))
                            print("----")
                            print("Stdout output:\n{0:s}".format(stdout))
                            print("Stderr output:\n{0:s}".format(stderr))

                # config DRAM
                if 'dram' in conf:
                    print('INFO: Dram setup on {0}'.format(target))
                    dram = conf['dram']
                    if dram['command'] == 'read':
                        addr = int(dram['address'])
                        size = int(dram['size'])

                        ret = self.cmd_hls_ddr_read_exec([target], addr, size)
                        if ret > 0:
                            q.put((target, {'return': 'failed'}))
                            return

                    elif dram['command'] == 'write':
                        file = dram['file']
                        addr = int(dram['address'])

                        ret = self.cmd_hls_ddr_write_exec([target], addr, [file])
                        if ret > 0:
                            q.put((target, {'return': 'failed'}))
                            return

                # Normal exit
                q.put((target, {'return': 'success'}))
                return

            #------------------------------------------------------------------
            for t, v in data.items():
                p = Process(target=proc, args=(q, t, v))
                procs.append(p)
                p.start()

            for p in procs:
                p.join()
                target, ret = q.get()
                if ret['return'] == 'success':
                    print("INFO: Setup on {0:s} is success".format(target))

                else:
                    print("INFO: Setup on {0:s} is failed".format(target))


    #------------------------------------------------------------------------------
    def main(self):
        self.argparse()
        print(self.args)

        print(VER_STR, end='\n\n')
        
        #------------------------------------------------------------------------------
        # parse command 
        #------------------------------------------------------------------------------
        if self.args.list:
            return self.cmd_fic_status()       # List boards (-l)

        elif self.args.reset:               # FPGA reset (-r)
            return self.cmd_fic_reset()

        elif self.args.hlscmd:          # send to HLS command (-hls)
            return self.cmd_hls_cmd()

        elif self.args.hlsrecv:         # receive from HLS
            return self.cmd_hls_recv()

        elif self.args.hlssend:         # receive from HLS
            return self.cmd_hls_send()

        elif self.args.regread:         # read FiC register
            return self.cmd_fic_read()

        elif self.args.regwrite:        # write FiC register
            return self.cmd_fic_write()

        elif self.args.ddrread:         # Read DDR
            return self.cmd_hls_ddr_read()

        elif self.args.ddrwrite:        # Write DDR
            return self.cmd_hls_ddr_write()

        elif self.args.switchset:       # set switch
            return self.cmd_fic_switchset()

        elif self.args.prog:            # FPGA program (-p)
            return self.cmd_fic_prog()

        elif self.args.runcmd:          # Run command
            return self.cmd_fic_runcmd()

        elif self.args.conf:
            return self.cmd_fic_setup() # Setup with configuration file


#------------------------------------------------------------------------------
if __name__ == '__main__':
    obj = ficmgr_cli()
    ret = obj.main()
    exit(ret)
