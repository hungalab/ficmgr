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
VER_STR = 'ficmanager nyacom (C) December, 2018'

#------------------------------------------------------------------------------
# Define board and board uri
BASE_URI = 'http://zeus.am.ics.keio.ac.jp/'
#BASE_URI = 'http://172.20.2.2'
#------------------------------------------------------------------------------
BOARDS = {
    'fic01' : { 'url' : BASE_URI + '/fic01' },
    'fic02' : { 'url' : BASE_URI + '/fic02' },
    'fic03' : { 'url' : BASE_URI + '/fic03' },
    'fic04' : { 'url' : BASE_URI + '/fic04' },
    'fic05' : { 'url' : BASE_URI + '/fic05' },
    'fic06' : { 'url' : BASE_URI + '/fic06' },
    'fic07' : { 'url' : BASE_URI + '/fic07' },
    'fic08' : { 'url' : BASE_URI + '/fic08' },
}

#------------------------------------------------------------------------------
class ficmanage:
    def __init__(self):
        args = None

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

        parser.add_argument('-pm', '--progmode', nargs=1, type=str, 
            metavar='[ sm16 | sm16pr | sm8 | sm8pr ]',
            help='FPGA Program mode')

        parser.add_argument('-pmsg', '--message', nargs=1, type=str, 
            metavar='MESSAGE',
            help='Message/notes for this FPGA programing')

        #parser.add_argument('-o','--output', nargs=1, type=str)
        #parser.add_argument('infile', nargs=1, type=str)

        self.args = parser.parse_args()

    #------------------------------------------------------------------------------
    # Analyse target from cmdline argument
    #------------------------------------------------------------------------------
    def get_target(self):
        if self.args.target != None:
            for t in self.args.target:
                if t not in BOARDS.keys():
                    print("ERROR: board {0:s} is unknown".format(t), file=sys.stderr)
                    return None
            
            return self.args.target

        else:
            return BOARDS.keys()

    #------------------------------------------------------------------------------
    # Parsing HLS datafile
    #------------------------------------------------------------------------------
    def parse_datafile(self, buf):
        ret = []
        for line, h in enumerate(buf.split('\n')):
            h = h.strip()
            for v in h.split(','):
                if len(v) > 0:
                    try:
                        val = int(v, 0)
                        ret.append(val)
                    except ValueError:
                        print("ERROR: in data file line {0:d}".format(line), file=sys.stderr)
                        return None

        return ret

    #------------------------------------------------------------------------------
    # Parsing HLS datafile
    #------------------------------------------------------------------------------
    def check_swconfig(self, conf):
        if 'ports' not in conf.keys():
            print("ERROR: Not number of ports defined", file=sys.stderr)
            return -1

        if 'slots' not in conf.keys():
            print("ERROR: Not number of slots defined", file=sys.stderr)
            return -1

        if 'outputs' not in conf.keys():
            print("ERROR: No outputs defined", file=sys.stderr)
            return -1

        tbl = conf['outputs']

        try:
            slots = conf['slots']
            ports = conf['ports']
        
        except ValueError:
            print("ERROR: Invalid port/slot number", file=sys.stderr)
            return -1

        if len(tbl) != ports:
            print("ERROR: Insufficient number of ports defined in the table", file=sys.stderr)
            return -1

        for p in tbl:
            output = tbl[p]
            if len(output) != slots:
                print("ERROR: Insufficient number of slots defined in the table", file=sys.stderr)
                return -1

            for s, v in output.items():
                if type(v) is not int:
                    print("ERROR: Value in Port {0:s} Slot {1:s} is invalid".format(p, s), file=sys.stderr)
                    return -1

        return 0

    def parse_swconfigfile(self, buf):
        try:
            j = json.loads(buf)

        except json.JSONDecodeError as e:
            print("ERROR: JSON error", file=sys.stderr)
            print(e, file=sys.stderr)
            return None

        if self.check_swconfig(j) < 0:
            return None

        return j

    #------------------------------------------------------------------------------
    # HTTP request handler
    #------------------------------------------------------------------------------
    def post2fic(self, url, data):
        ret = {'return', 'failed'}
        try:
            resp = requests.post(url, data=data, headers={'Content-Type': 'application/json'})
            ret = resp.json()

        except simplejson.JSONDecodeError:
            print("ERROR: {0:s} is not respond".format(url), file=sys.stderr)

        return ret

    #------------------------------------------------------------------------------
    def get2fic(self, url):
        ret = {'return', 'failed'}
        try:
            resp = requests.get(url, headers={'Content-Type': 'application/json'})
            ret = resp.json()

        except simplejson.JSONDecodeError:
            print("ERROR: {0:s} is not respond".format(url), file=sys.stderr)

        return ret

    #------------------------------------------------------------------------------
    def delete2fic(self, url):
        ret = {'return', 'failed'}
        try:
            resp = requests.delete(url, headers={'Content-Type': 'application/json'})
            ret = resp.json()

        except simplejson.JSONDecodeError:
            print("ERROR: {0:s} is not respond".format(url), file=sys.stderr)

        return ret
    
    #------------------------------------------------------------------------------
    # Commandline parser
    #------------------------------------------------------------------------------
    def cmd_fic_status(self):
        stat = {}
        targets = self.get_target()

        procs = []
        q = Queue()
        def proc(q, target):
            ret = self.fic_status(target)
            q.put((target, ret))

        for t in targets:
            p = Process(target=proc, args=(q, t))
            procs.append(p)
            p.start()

        for p in procs:
            p.join()
            target, ret = q.get()
            stat[target] = ret
 
        for t in BOARDS.keys():
            if t in stat.keys():
                if stat[t]['return'] == 'success':
                    brdst = stat[t]['status']
                    print("'{0:s}':\n".format(t), end='')
                    pprint(brdst, indent=4)
                    print('\n\n', end='')

                else:
                    print('{0:s}:\n'.format(t), end='')
                    print('    get status failed.\n\n')

    #------------------------------------------------------------------------------
    def cmd_fic_reset(self):
        stat = {}
        target = self.get_target()

        for t in target:
            stat[t] = self.fic_reset(t)

        for t in BOARDS.keys():
            if t in stat.keys():
                if stat[t]['return'] == 'success':
                    print('INFO: Reset FPGA on {0:s} is success'.format(t))

                else:
                    print('INFO: Reset FPGA on {0:s} is failed'.format(t))

    #------------------------------------------------------------------------------
    def cmd_fic_regread(self):
        if self.args.target is None:
            print("ERROR: You must specify target.", file=sys.stderr)
            return -1

        targets = self.get_target()
        addr = 0x0
        try:
            addr = int(self.args.regread[0], 0)

        except ValueError:
            print("ERROR: Invalid reg address.", file=sys.stderr)
            return -1

        if addr > 0xffff:
            print("ERROR: Invalid reg address 0x{0:x}.".format(addr), file=sys.stderr)
            return -1

        procs = []
        q = Queue()
        def proc(q, target, addr):
            ret = self.fic_regread(target, addr)
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
 
    #------------------------------------------------------------------------------
    def cmd_fic_regwrite(self):
        if self.args.target is None:
            print("ERROR: You must specify target.", file=sys.stderr)
            return -1

        targets = self.get_target()
        addr = 0x0
        val = 0x0

        try:
            addr = int(self.args.regwrite[0], 0)
            val = int(self.args.regwrite[1], 0)

        except ValueError:
            print("ERROR: Invalid addr/val value.", file=sys.stderr)
            return -1

        if addr > 0xffff:
            print("ERROR: Invalid reg address 0x{0:x}.".format(addr), file=sys.stderr)
            return -1

        if val > 0xff:
            print("ERROR: Invalid val 0x{0:x}.".format(val), file=sys.stderr)

        procs = []
        q = Queue()
        def proc(q, target, addr, val):
            ret = self.fic_regwrite(target, addr, val)
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
 
    #------------------------------------------------------------------------------
    def cmd_fic_prog(self):
        bs_files = self.args.prog

        if self.args.target is None:
            print("ERROR: You must specify target.", file=sys.stderr)
            return -1

        targets = self.get_target()

        pr_mode = 'sm16'
        memo = 'Configure via ficdeploy by {0:s}@{1:s}'.format(os.getlogin(), os.uname()[1])

        if self.args.progmode != None:
            pr_mode = self.args.progmode[0]
            if pr_mode not in ['sm16', 'sm16pr', 'sm8', 'sm8pr']:
                print("ERROR: The program mode {0:s} is unknown".format(pm), file=sys.stderr)
                return -1
        
        if self.args.message != None:
            memo = self.args.message[0]

        if len(bs_files) > 1:   # Multiple files to multiple FPGAs
            if len(bs_files) != len(targets):
                print("ERROR: Unmatch number of *.bit files and targets.", file=sys.stderr)
                return -1

            procs = []
            q = Queue()
            def proc(q, target, pr_mode, bitname, b64, msg):
                ret = self.fic_prog(target, pr_mode, bitname, b64, msg)
                q.put((target, ret))

            for bs, t in zip(bs_files, targets):
                bitname = os.path.basename(bs)
                with open(bs, 'rb') as f:
                    b64 = base64.b64encode(f.read())
                    f.close()

                    p = Process(target=proc, args=(q, t, pr_mode, bitname, b64, memo))
                    procs.append(p)
                    p.start()

            for p in procs:
                p.join()
                target, ret = q.get()
                if ret['return'] == 'success':
                    print("INFO: FPGA configuration on {0:s} is success".format(target))

                else:
                    print("INFO: FPGA configuration on {0:s} is failed".format(target))


        else:   # Single file to multiple FPGAs
            bitname = os.path.basename(bs_files[0])
            with open(bs_files[0], 'rb') as f:
                b64 = base64.b64encode(f.read())
                f.close()

                procs = []
                q = Queue()
                def proc(q, target, pr_mode, bitname, b64, msg):
                    ret = self.fic_prog(target, pr_mode, bitname, b64, msg)
                    q.put((target, ret))

                for t in targets:
                    p = Process(target=proc, args=(q, t, pr_mode, bitname, b64, memo))
                    procs.append(p)
                    p.start()

                for p in procs:
                    p.join()
                    target, ret = q.get()
                    if ret['return'] == 'success':
                        print("INFO: FPGA configuration on {0:s} is success".format(target))

                    else:
                        print("INFO: FPGA configuration on {0:s} is failed".format(target))

        return 0


    #------------------------------------------------------------------------------
    def cmd_hls_cmd(self):
        if self.args.target is None:
            print("ERROR: You must specify target.", file=sys.stderr)
            return -1

        target = self.get_target()

        cmd = self.args.hlscmd[0]
        if cmd not in ['start', 'reset']:
            print("ERROR: Unknown command {0:s}.".format(cmd), file=sys.stderr)
            return -1

        procs = []
        q = Queue()
        def proc(q, cmd):
            ret = self.fic_hls_cmd(cmd)
            q.put((target, ret))

        for t in targets:
            p = Process(target=proc, args=(q, cmd))
            procs.append(p)
            p.start()

        for p in procs:
            p.join()
            target, ret = q.get()
            if ret['return'] == 'success':
                print("INFO: HLS send command on {0:s} success".format(target))

            else:
                print("INFO: HLS send command on {0:s} failed".format(target))

        #procs = []
        #for t in target:
        #    p = Process(target=self.fic_hls_cmd, args=(t, cmd))
        #    procs.append(p)
        #    p.start

        #for p in procs:
        #    print(p.join())

     #------------------------------------------------------------------------------
    def cmd_hls_recv(self):
        if self.args.target is None:
            print("ERROR: You must specify target.", file=sys.stderr)
            return -1

        target = self.get_target()
        arg1 = self.args.hlsrecv[0]

        count = 0
        try:
            count = int(arg1)

        except ValueError:
            print("ERROR: Invalid number.", file=sys.stderr)
            return -1

        if count <= 0:
            print("ERROR: Invalid number.", file=sys.stderr)
            return -1

        procs = []
        q = Queue()
        def proc(q, cmd):
            ret = self.fic_hls_recv(count)
            q.put((target, ret))

        for t in targets:
            p = Process(target=proc, args=(q, count))
            procs.append(p)
            p.start()

        for p in procs:
            p.join()
            target, ret = q.get()
            if ret['return'] == 'success':
                print(ret)

            else:
                print("INFO: HLS data receive failed on {0:s}".format(target))

        #procs = []
        #for t in target:
        #    p = Process(target=self.fic_hls_recv, args=(t, count))
        #    procs.append(p)
        #    p.start

        #for p in procs:
        #    p.join()

    #------------------------------------------------------------------------------
    def cmd_hls_send(self):
        if self.args.target is None:
            print("ERROR: You must specify target.", file=sys.stderr)
            return -1

        targets = self.get_target()
        dat_files = self.args.hlssend

        if len(dat_files) > 1:   # Multiple files to multiple FPGAs
            if len(dat_files) != len(targets):
                print("ERROR: Unmatch number of *.dat files and targets.", file=sys.stderr)
                return -1

            procs = []
            q = Queue()
            def proc(q, target, data):
                ret = self.fic_hls_send(target, data)
                q.put((target, ret))

            for df, t in zip(dat_files, targets):
                with open(df, 'rt') as f:
                    data = self.parse_datafile(f.read())
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

        else:   # Single file to multiple FPGAs
            filename = os.path.basename(dat_files[0])
            with open(dat_files[0], 'rt') as f:
                data = self.parse_datafile(f.read())
                f.close()

                procs = []
                q = Queue()
                def proc(q, target, data):
                    ret = self.fic_hls_send(target, data)
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
        return 0

    #------------------------------------------------------------------------------
    def cmd_fic_switchset(self):
        if self.args.target is None:
            print("ERROR: You must specify target.", file=sys.stderr)
            return -1

        targets = self.get_target()
        sw_files = self.args.switchset

        if len(sw_files) > 1:   # Multiple files to multiple FPGAs
            if len(sw_files) != len(targets):
                print("ERROR: Unmatch number of *.json files and targets.", file=sys.stderr)
                return -1

            procs = []
            q = Queue()
            def proc(q, target, data):
                ret = self.fic_setsw(target, data)
                q.put((target, ret))

            for df, t in zip(sw_files, targets):
                with open(df, 'rt') as f:
                    data = self.parse_swconfigfile(f.read())
                    f.close()

                if data is None:
                    return -1

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

        else:   # Single file to multiple FPGAs
            filename = os.path.basename(sw_files[0])
            with open(sw_files[0], 'rt') as f:
                data = self.parse_swconfigfile(f.read())
                f.close()

                if data is None:
                    return -1

                procs = []
                q = Queue()
                def proc(q, target, data):
                    ret = self.fic_setsw(target, data)
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

        return 0

    #------------------------------------------------------------------------------
    def fic_prog(self, target, pr_mode, bitname, b64, memo):
        ret = {'return': 'failed'}
        if target in BOARDS.keys():
            url =  BOARDS[target]['url'] + '/fpga'
            j = json.dumps({
                'mode': pr_mode,
                'bitname': bitname,
                'memo': memo,
                'bitstream': b64.decode(encoding='utf-8')
            })

            print("INFO: Send FPGA configuration {0:s} to {1:s}".format(bitname, target))
            print("INFO: Awaiting response from {0:s}... be patience ... ".format(target))

            ret = self.post2fic(url, j)

        else:
            print("ERROR: board {0:s} is not found".format(target), file=sys.stderr)

        return ret

    #------------------------------------------------------------------------------
    def fic_status(self, target):
        ret = {'return': 'failed'}
        if target in BOARDS.keys():
            url = BOARDS[target]['url'] + '/status'
            ret = self.get2fic(url)

        else:
            print("ERROR: board {0:s} is not found".format(target), file=sys.stderr)

        return ret

    #------------------------------------------------------------------------------
    def fic_reset(self, target):
        ret = {'return': 'failed'}
        if target in BOARDS.keys():
            url =  BOARDS[target]['url'] + '/fpga'
            print("INFO: Send FPGA reset to {0:s}".format(target))

            ret = self.delete2fic(url)

        else:
            print("ERROR: board {0:s} is not found".format(target), file=sys.stderr)

        return ret

    #------------------------------------------------------------------------------
    def fic_hls_cmd(self, target, cmd):
        ret = {'return': 'failed'}

        if cmd not in ['start', 'reset']:
            print("ERROR: Unknown command {0:s}".format(cmd))
            return ret

        if target in BOARDS.keys():
            url =  BOARDS[target]['url'] + '/hls'
            print("INFO: Send HLS command to {0:s}".format(target))

            j = json.dump({
                'command': cmd,
            })

            ret = self.post2fic(url, j)

        else:
            print("ERROR: board {0:s} is not found".format(target), file=sys.stderr)

        return ret

    #------------------------------------------------------------------------------
    def fic_hls_send(self, target, data):
        ret = {'return': 'failed'}

        if type(data) is not list:
            print("ERROR: Invalid data type")
            return ret

        if target in BOARDS.keys():
            url =  BOARDS[target]['url'] + '/hls'
            print("INFO: Send HLS command to {0:s}".format(target))

            j = json.dump({
                'command': 'send4',
                'data': data,
            })

            ret = self.post2fic(url, j)

        else:
            print("ERROR: board {0:s} is not found".format(target), file=sys.stderr)

        return ret

    #------------------------------------------------------------------------------
    def fic_hls_recv(self, target, count):
        ret = {'return': 'failed'}
        
        if type(count) is not int:
            print("ERROR: Invalid count")
            return ret

        if count <= 0:
            print("ERROR: Invalid count")
            return ret

        if target in BOARDS.keys():
            url =  BOARDS[target]['url'] + '/hls'
            print("INFO: Send HLS command to {0:s}".format(target))

            j = json.dump({
                'command': 'receive4',
                'count': count,
            })

            ret = self.post2fic(url, j)

        else:
            print("ERROR: board {0:s} is not found".format(target), file=sys.stderr)

        return ret

    #------------------------------------------------------------------------------
    def fic_regread(self, target, addr):
        ret = {'return': 'failed'}

        if addr < 0:
            print("ERROR: Invalid address")
            return ret

        if target in BOARDS.keys():
            url = BOARDS[target]['url'] + '/regread'

            j = json.dumps({
                'address': addr,
            })

            ret = self.post2fic(url, j)

        else:
            print("ERROR: board {0:s} is not found".format(target), file=sys.stderr)

        return ret

    #------------------------------------------------------------------------------
    def fic_regwrite(self, target, addr, val):
        ret = {'return': 'failed'}

        if addr < 0:
            print("ERROR: Invalid address", file=sys.stderr)
            return ret

        if val > 0xff:
            print("ERROR: Invalid value", file=sys.stderr)
            return ret

        if target in BOARDS.keys():
            url = BOARDS[target]['url'] + '/regwrite'

            j = json.dumps({
                'address': addr,
                'data': val,
            })

            ret = self.post2fic(url, j)

        else:
            print("ERROR: board {0:s} is not found".format(target), file=sys.stderr)

        return ret

    #------------------------------------------------------------------------------
    def fic_setsw(self, target, table):
        ret = {'return': 'failed'}

        if self.check_swconfig(table) < 0:
            print(table)
            return ret

        if target in BOARDS.keys():
            url = BOARDS[target]['url'] + '/switch'

            j = json.dumps(table)

            ret = self.post2fic(url, j)

        else:
            print("ERROR: board {0:s} is not found".format(target), file=sys.stderr)

        return ret

    #------------------------------------------------------------------------------
    def main(self):
        self.argparse()
        print(self.args)

        print(VER_STR, end='\n\n')
        
        #------------------------------------------------------------------------------
        # parse command 
        #------------------------------------------------------------------------------
        if self.args.list:
            self.cmd_fic_status()       # List boards (-l)

        elif self.args.reset:           # FPGA reset (-r)
            self.cmd_fic_reset()

        elif self.args.hlscmd:          # send to HLS command (-hls)
            self.cmd_hls_cmd()

        elif self.args.hlsrecv:         # receive from HLS
            self.cmd_hls_recv()

        elif self.args.hlssend:         # receive from HLS
            self.cmd_hls_send()

        elif self.args.regread:         # read FiC register
            self.cmd_fic_regread()

        elif self.args.regwrite:        # write FiC register
            self.cmd_fic_regwrite()

        elif self.args.switchset:       # set switch
            self.cmd_fic_switchset()

        elif self.args.prog:            # FPGA program (-p)
            self.cmd_fic_prog()


#    #------------------------------------------------------------------------------
#    def test_switch():
#        print("DEBUG: test_switch")
#
#        url = BASE_URI + '/switch'
#        j = json.dumps({
#            "ports": "4",
#            "slots": "4",
#            "outputs" : {
#                "o0": {
#                    's0': 0,
#                    's1': 0,
#                    's2': 0,
#                    's3': 0,
#                },
#                "o1": {
#                    's0': 0,
#                    's1': 0,
#                    's2': 0,
#                    's3': 0,
#                },
#                "o2": {
#                    's0': 0,
#                    's1': 0,
#                    's2': 0,
#                    's3': 0,
#                },
#                "o3": {
#                    's0': 0,
#                    's1': 0,
#                    's2': 0,
#                    's3': 0,
#                },
#            },
#        })
#
#        resp = requests.post(url, j, headers={'Content-Type': 'application/json'})
#        print(resp.json())
#
#    #------------------------------------------------------------------------------
#    def test_hls():
#        print("DEBUG: test_hls")
#        url = BASE_URI + '/hls'
#
#        j = json.dumps({
#            "type": "command",
#            "command": "reset",
#        })
#
#        resp = requests.post(url, j, headers={'Content-Type': 'application/json'})
#        print(resp.json())
#
#        j = json.dumps({
#            "type": "command",
#            "command": "start",
#        })
#
#        resp = requests.post(url, j, headers={'Content-Type': 'application/json'})
#        print(resp.json())
#
#        #j = json.dumps({
#        #    "type": "data",
#        #    "data": [0xa, 0xb, 0xc, 0xd, 0x0, 0x1, 0x2, 0x3],
#        #})
#
#        #resp = requests.post(url, j, headers={'Content-Type': 'application/json'})
#        #print(resp.json())

#------------------------------------------------------------------------------
if __name__ == '__main__':
    obj = ficmanage()
    obj.main()

#    test_fpga()
#    test_status()

#    test_switch()
#    test_hls()
