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
BASE_URI = 'http://zeus.am.ics.keio.ac.jp'
#BASE_URI = 'http://172.20.2.2'
#------------------------------------------------------------------------------
BOARDS = {
    'fic00' : { 'url' : BASE_URI + '/fic00' },
    'fic01' : { 'url' : BASE_URI + '/fic01' },
    'fic02' : { 'url' : BASE_URI + '/fic02' },
    'fic03' : { 'url' : BASE_URI + '/fic03' },
    'fic04' : { 'url' : BASE_URI + '/fic04' },
    'fic05' : { 'url' : BASE_URI + '/fic05' },
    'fic06' : { 'url' : BASE_URI + '/fic06' },
    'fic07' : { 'url' : BASE_URI + '/fic07' },
    'fic08' : { 'url' : BASE_URI + '/fic08' },
    'fic09' : { 'url' : BASE_URI + '/fic09' },
    'fic10' : { 'url' : BASE_URI + '/fic10' },
    'fic11' : { 'url' : BASE_URI + '/fic11' },
    'fic12' : { 'url' : BASE_URI + '/fic12' },
    'fic13' : { 'url' : BASE_URI + '/fic13' },
    'm2fic00' : { 'url' : BASE_URI + '/m2fic00' },
    'm2fic01' : { 'url' : BASE_URI + '/m2fic01' },
    'm2fic02' : { 'url' : BASE_URI + '/m2fic02' },
    'm2fic03' : { 'url' : BASE_URI + '/m2fic03' },
    'm2fic04' : { 'url' : BASE_URI + '/m2fic04' },
    'm2fic05' : { 'url' : BASE_URI + '/m2fic05' },
    'm2fic06' : { 'url' : BASE_URI + '/m2fic06' },
    'm2fic07' : { 'url' : BASE_URI + '/m2fic07' },
    'm2fic08' : { 'url' : BASE_URI + '/m2fic08' },
    'm2fic09' : { 'url' : BASE_URI + '/m2fic09' },
    'm2fic10' : { 'url' : BASE_URI + '/m2fic10' },
    'm2fic11' : { 'url' : BASE_URI + '/m2fic11' },
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
        # If tablefile is specified, file input is priotize
        if 'tablefile' in conf.keys():
            tblf = conf['tablefile']
            with open(tblf, 'rt') as f:
                try:
                    j = json.loads(f.read())

                except json.JSONDecodeError as e:
                    print("ERROR: JSON error", file=sys.stderr)
                    print(e, file=sys.stderr)
                    return -1 

                if self.check_swconfig(j) < 0:
                    return -1 

            return 0

        else:
            if 'ports' not in conf.keys():
                print("ERROR: Not number of ports defined", file=sys.stderr)
                return -1

            if 'slots' not in conf.keys():
                print("ERROR: Not number of slots defined", file=sys.stderr)
                return -1

            if 'outputs' not in conf.keys():
                print("ERROR: No outputs defined", file=sys.stderr)
                return -1

        print(conf)
        tbl = conf['table']
        try:
            num_slots = conf['slots']
            num_ports = conf['ports']
            num_outs = conf['outputs']
        
        except ValueError:
            print("ERROR: Invalid port/slot or outputs number", file=sys.stderr)
            return -1

        if len(tbl) != num_outs:
            print("ERROR: Insufficient number of outputs defined in the table", file=sys.stderr)
            return -1

        for out in tbl:
            ports = tbl[out]
            if len(ports) != num_ports:
                print("ERROR: Insufficient number of ports defined in the {0}".format(out), file=sys.stderr)
                return -1

            for port in ports:
                slots = ports[port]
                if len(slots) != num_slots:
                    print("ERROR: Insufficient number of slots defined in the table", file=sys.stderr)
                    return -1

                for s, v in slots.items():
                    if type(v) is not int:
                        print("ERROR: Value in Output {0} Port {1} Slot {2} is invalid".format(out, port, s), file=sys.stderr)
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
    # Parsing FiCSW configuration setup JSON
    #------------------------------------------------------------------------------
    def check_setupconfig(self, conf):
        # check target name)
        for target, attrs in conf.items():
            if target not in BOARDS:
                print("ERROR: {0} is unknown target".format(target), file=sys.stderr)
                return -1

            # check 'fpga' if exist
            if 'fpga' in attrs:
                fpga = attrs['fpga']
                if 'bitstream' not in fpga.keys():
                    print("ERROR: For {0}, must specify bitstream".format(target), file=sys.stderr)
                    return -1

                if os.path.exists(fpga['bitstream']) == False:
                    print("ERROR: {0} is not exist".format(fpga['bitstream']), file=sys.stderr)
                    return -1

                if 'progmode' not in fpga.keys():
                    print("ERROR: For {0}, must specify progmode".format(target), file=sys.stderr)
                    return -1
                
                if fpga['progmode'] not in ['sm16', 'sm16pr', 'sm8', 'sm8pr']:
                    print("ERROR: progmode {0} is invalid".format(fpga['progmode']), file=sys.stderr)
                    return -1

            # check 'switch' if exist
            if 'switch' in attrs:
                switch = attrs['switch']
                if self.check_swconfig(switch) < 0:
                    return -1

            # check 'option' if exist
            if 'option' in attrs:
                option = attrs['option']
                if "auto_hls_reset_start" in option.keys():
                    if option["auto_hls_reset_start"] not in {True, False}:
                        print("ERROR: Value in auto_hls_reset_start {0} is invalid".format(
                            option["auto_hls_reset_start"]), file=sys.stderr)
                        return -1

                if "auto_runcmd" in option.keys():
                    if type(option["auto_runcmd"]) is not str:
                        print("ERROR: Value in auto_runcmd {0} is invalid".format(
                            option["auto_runcmd"]), file=sys.stderr)
                        return -1

        return 0

    def parse_setupconfigfile(self, buf):
        try:
            j = json.loads(buf)

        except json.JSONDecodeError as e:
            print("ERROR: JSON error", file=sys.stderr)
            print(e, file=sys.stderr)
            return None

        if self.check_setupconfig(j) < 0:
            return None

        return j

    #------------------------------------------------------------------------------
    # HTTP request handler
    #------------------------------------------------------------------------------
    def rest_post(self, url, data):
        ret = {'return': 'failed'}
        try:
            resp = requests.post(url, data=data, headers={'Content-Type': 'application/json'})
            ret = resp.json()

        except simplejson.JSONDecodeError:
            print("ERROR: {0:s} is not respond".format(url), file=sys.stderr)

        return ret

    #------------------------------------------------------------------------------
    def rest_get(self, url):
        ret = {'return': 'failed'}
        try:
            resp = requests.get(url, headers={'Content-Type': 'application/json'})
            ret = resp.json()

        except simplejson.JSONDecodeError:
            print("ERROR: {0:s} is not respond".format(url), file=sys.stderr)

        return ret

    #------------------------------------------------------------------------------
    def rest_delete(self, url):
        ret = {'return': 'failed'}
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
                    print('ERROR: get status failed.\n\n')

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
        memo = 'Configure via ficmanager by {0:s}@{1:s}'.format(os.getlogin(), os.uname()[1])

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

        targets = self.get_target()

        cmd = self.args.hlscmd[0]
        if cmd not in ['start', 'reset']:
            print("ERROR: Unknown command {0:s}.".format(cmd), file=sys.stderr)
            return -1

        procs = []
        q = Queue()
        def proc(q, target, cmd):
            ret = self.fic_hls_cmd(target, cmd)
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

        targets = self.get_target()
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
        def proc(q, target, count):
            ret = self.fic_hls_recv(target, count)
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

            print("INFO: Select FPGA configuration mode: {0:s}".format(pr_mode))
            print("INFO: Send FPGA configuration {0:s} to {1:s}".format(bitname, target))
            print("INFO: Awaiting response from {0:s}... be patient ... ".format(target))

            ret = self.rest_post(url, j)

        else:
            print("ERROR: board {0:s} is not found".format(target), file=sys.stderr)

        return ret

    #------------------------------------------------------------------------------
    def fic_status(self, target):
        ret = {'return': 'failed'}
        if target in BOARDS.keys():
            url = BOARDS[target]['url'] + '/status'
            ret = self.rest_get(url)

        else:
            print("ERROR: board {0:s} is not found".format(target), file=sys.stderr)

        return ret

    #------------------------------------------------------------------------------
    def fic_reset(self, target):
        ret = {'return': 'failed'}
        if target in BOARDS.keys():
            url =  BOARDS[target]['url'] + '/fpga'
            print("INFO: Send FPGA reset to {0:s}".format(target))

            ret = self.rest_delete(url)

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

            j = json.dumps({
                'command': cmd,
            })

            ret = self.rest_post(url, j)

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

            j = json.dumps({
                'command': 'send',
                'data': data,
            })

            ret = self.rest_post(url, j)

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

            j = json.dumps({
                'command': 'receive',
                'count': count,
            })

            ret = self.rest_post(url, j)

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

            ret = self.rest_post(url, j)

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

            ret = self.rest_post(url, j)

        else:
            print("ERROR: board {0:s} is not found".format(target), file=sys.stderr)

        return ret

    #------------------------------------------------------------------------------
    def fic_setsw(self, target, table):
        ret = {'return': 'failed'}

        if self.check_swconfig(table) < 0:
            return ret

        if target in BOARDS.keys():
            url = BOARDS[target]['url'] + '/switch'

            if 'tablefile' in table.keys():
                tblf = table['tablefile']
                with open(tblf, 'rt') as f:
                    j = json.loads(f.read())

            else:
                j = json.dumps(table)

            ret = self.rest_post(url, j)

        else:
            print("ERROR: board {0:s} is not found".format(target), file=sys.stderr)

        return ret

    #------------------------------------------------------------------------------
    def fic_runcmd(self, target, cmdline, timeout):
        ret = {'return': 'failed'}

        if target in BOARDS.keys():
            url = BOARDS[target]['url'] + '/runcmd'

            j = json.dumps({
                'command': cmdline,
                'timeout': timeout 
                })

            ret = self.rest_post(url, j)

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

        elif self.args.runcmd:         # Run command
            self.cmd_fic_runcmd()

        elif self.args.conf:
            self.cmd_fic_setup()       # Setup with configuration file

    #------------------------------------------------------------------------------
    def cmd_fic_setup(self):
        conf_file = self.args.conf[0]
        with open(conf_file, 'rt') as f:
            data = self.parse_setupconfigfile(f.read())
            f.close()

            if data is None:
                return -1

            procs = []
            q = Queue()
            #------------------------------------------------------------------
            def proc(q, target, conf):
                # config FPGA
                if 'fpga' in conf:
                    print('INFO: FPGA config on {0}'.format(target))
                    fpga = conf['fpga']
                    bs_file = fpga['bitstream']
                    pr_mode = fpga['progmode']
                    msg = ''
                    if 'msg' in fpga.keys():
                        msg = fpga['msg']

                    bitname = os.path.basename(bs_file)
                    with open(bs_file, 'rb') as f:
                        b64 = base64.b64encode(f.read())
                        f.close()
                        ret = self.fic_prog(target, pr_mode, bitname, b64, msg)
                        if ret['return'] != 'success':
                            q.put((target, ret))
                            return

                # config TABLE
                if 'switch' in conf:
                    print('INFO: Switch config on {0}'.format(target))
                    switch = conf['switch']
                    ret = self.fic_setsw(target, switch)
                    if ret['return'] != 'success':
                        q.put((target, ret))
                        return

                # config OPTION
                if 'option' in conf:
                    print('INFO: Option setting on {0}'.format(target))
                    option = conf['option']
                    if 'auto_hls_reset_start' in option.keys():
                        ret = self.fic_hls_cmd(target, 'reset')
                        ret = self.fic_hls_cmd(target, 'start')
                        if ret['return'] != 'success':
                            q.put((target, ret))
                            return

                    if 'auto_runcmd' in option.keys():
                        ret = self.fic_runcmd(target, option['auto_runcmd'], 5)
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

                    q.put((target, {'return': 'success'}))
                    return 0

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
    def cmd_fic_runcmd(self):

        #--------------------------------------------------------------------------
        def sub_proc(q, target, cmd, tout):
            ret = self.fic_runcmd(target, cmd, tout)
            q.put((target, ret))
        #--------------------------------------------------------------------------

        if self.args.target is None:
            print("ERROR: You must specify target.", file=sys.stderr)
            return -1

        targets  = self.get_target()
        cmdlines = self.args.runcmd
        timeout  = self.args.runcmdtimeout

        if len(cmdlines) > 1:   # Multiple cmd to multiple FiCs
            if len(cmdlines) != len(targets):
                print("ERROR: Unmatch number of cmdlines and targets. Aren't you forget cmdline quoted?", file=sys.stderr)
                return -1

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

        return 0

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
