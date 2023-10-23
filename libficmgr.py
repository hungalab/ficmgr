#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#------------------------------------------------------------------------------
# libficmgr
# FiC Manager library  nyacom (C) 2018-2020
#------------------------------------------------------------------------------

import os
import sys, traceback
import time
import base64
from typing import Type
import requests
import json
import simplejson
import gzip
import getpass

import argparse
import pdb

from pprint import pprint
from multiprocessing import Process, Queue, Value

#------------------------------------------------------------------------------
VER_STR = 'ficmanager nyacom (C) December, 2018'

#------------------------------------------------------------------------------
class libficmgr:
    def __init__(self):
        # Define board and board uri
        # self.base_uri = 'http://polaris.am.ics.keio.ac.jp'
        self.base_uri = 'http://192.168.71.12'

        # Define boards
        self.board = [
            'fic00', 'fic01', 'fic02', 'fic03',
            'fic04', 'fic05', 'fic06', 'fic07',
            'fic08', 'fic09', 'fic10', 'fic11',
            'fic12', 'fic13',
            'm2fic00', 'm2fic01', 'm2fic02', 'm2fic03',
            'm2fic04', 'm2fic05', 'm2fic06', 'm2fic07',
            'm2fic08', 'm2fic09', 'm2fic10', 'm2fic11',
        ]

        # Define urls
        self.board_url = {}
        for b in self.board:
            self.board_url[b] = "{0:s}/{1:s}".format(self.base_uri, b)

    #------------------------------------------------------------------------------
    # Parsing HLS datafile
    #------------------------------------------------------------------------------
    def parse_datafile(self, buf):
        for line, h in enumerate(buf.split('\n')):
            h = h.strip()
            for v in h.split(','):
                if len(v) > 0:
                    try:
                        val = int(v, 0)
                        ret.append(val)
                    except ValueError:
                        raise ValueError("ERROR: in data file line {0:d}".format(line))

    #------------------------------------------------------------------------------
    # Parse switch config json
    #------------------------------------------------------------------------------
    def check_switch_json(self, conf):
        # If tablefile is specified, file input is prioritize
        if 'tablefile' in conf.keys():
            tblf = conf['tablefile']
            with open(tblf, 'rt') as f:
                j = json.loads(f.read())
                self.check_switch_json(j)
                return

        else:
            if 'ports' not in conf.keys():
                raise ValueError("ERROR: Not number of ports defined")

            if 'slots' not in conf.keys():
                raise ValueError("ERROR: Not number of slots defined")

            if 'switches' not in conf.keys():
                raise ValueError("ERROR: No switches defined")

            if 'table' not in conf.keys():
                raise ValueError("ERROR: No table is defined")

        print(conf)
        tbl = conf['table']
        try:
            num_slots = conf['slots']
            num_ports = conf['ports']
            num_switches = conf['switches']
        
        except ValueError:
            raise ValueError("ERROR: Invalid port/slot or switches number")

        if len(tbl) != num_switches:
            raise ValueError("ERROR: Insufficient number of outputs defined in the table")

        for out in tbl:
            ports = tbl[out]
            if len(ports) != num_ports:
                raise ValueError("ERROR: Insufficient number of ports defined in the {0}".format(out))

            for port in ports:
                slots = ports[port]
                if len(slots) != num_slots:
                    raise ValueError("ERROR: Insufficient number of slots defined in the table")

                for s, v in slots.items():
                    if type(v) is not int:
                        raise TypeError("ERROR: Value in Output {0} Port {1} Slot {2} is invalid".format(out, port, s))

        return

    def parse_switchconfig(self, buf):
        j = json.loads(buf)
        self.check_switch_json(j)
        return j

    #------------------------------------------------------------------------------
    # Parsing FiCSW configuration setup JSON
    #------------------------------------------------------------------------------
    def check_setup_json(self, conf):
        # check target name)
        for target, attrs in conf.items():
            if target not in self.board:
                raise ValueError("ERROR: {0} is unknown target".format(target))

            # check 'fpga' if exist
            if 'fpga' in attrs:
                fpga = attrs['fpga']
                if 'bitstream' not in fpga.keys():
                    raise ValueError("ERROR: For {0}, must specify bitstream".format(target))

                if os.path.exists(fpga['bitstream']) == False:
                    raise ValueError("ERROR: {0} is not exist".format(fpga['bitstream']))

                if 'progmode' not in fpga.keys():
                    raise ValueError("ERROR: For {0}, must specify progmode".format(target))
                
                if fpga['progmode'] not in ['sm16', 'sm16pr', 'sm8', 'sm8pr']:
                    raise ValueError("ERROR: progmode {0} is invalid".format(fpga['progmode']))

            # check 'dram' if exist
            if 'dram' in attrs:
                dram = attrs['dram']
                if 'command' not in dram.keys():
                    raise ValueError("ERROR: For {0}, must specify dram command".format(target))

                if dram['command'] not in ['read', 'write']:
                    raise ValueError("ERROR: dram command {0} is invalid".format(dram['command']))

                if dram['command'] == 'read':
                    if 'address' not in dram.keys():
                        raise ValueError("ERROR: dram address is required")

                    if 'size' not in dram.keys():
                        raise ValueError("ERROR: dram size is required")

                    if type(dram['address']) is not int:
                        raise ValueError("ERROR: dram address is not integer")

                    if type(dram['size']) is not int:
                        raise ValueError("ERROR: dram address is not integer")

                if dram['command'] == 'write':
                    if 'address' not in dram.keys():
                        raise ValueError("ERROR: dram address is required")

                    if type(dram['address']) is not int:
                        raise ValueError("ERROR: dram address is not integer")

                    if 'file' not in dram.keys():
                        raise ValueError("ERROR: dram file is required")

                    if os.path.exists(dram['file']) == False:
                        raise ValueError("ERROR: {0} is not exist".format(dram['file']))

            # check 'switch' if exist
            if 'switch' in attrs:
                switch = attrs['switch']
                self.check_switch_json(switch)

            # check 'option' if exist
            if 'option' in attrs:
                option = attrs['option']
                if "auto_hls_reset_start" in option.keys():
                    if option["auto_hls_reset_start"] not in {True, False}:
                        raise ValueError("ERROR: Value in auto_hls_reset_start {0} is invalid".format(
                            option["auto_hls_reset_start"]))

                if "auto_runcmd" in option.keys():
                    if type(option["auto_runcmd"]) is not str:
                        raise ValueError("ERROR: Value in auto_runcmd {0} is invalid".format(
                            option["auto_runcmd"]))

        return

    def parse_setupfile(self, buf):
        j = json.loads(buf)
        self.check_setup_json(j)
        return j

    #------------------------------------------------------------------------------
    # HTTP request handler
    #------------------------------------------------------------------------------
    def rest_post(self, url, data):
        try:
            resp = requests.post(url, data=data, headers={'Content-Type': 'application/json'})
            return resp.json()

        except simplejson.JSONDecodeError:
            raise IOError("ERROR: {0:s} is not respond".format(url))

    #------------------------------------------------------------------------------
    def rest_get(self, url):
        try:
            resp = requests.get(url, headers={'Content-Type': 'application/json'})
            return resp.json()

        except simplejson.JSONDecodeError:
            raise IOError("ERROR: {0:s} is not respond".format(url))

    #------------------------------------------------------------------------------
    def rest_delete(self, url):
        try:
            resp = requests.delete(url, headers={'Content-Type': 'application/json'})
            return resp.json()

        except simplejson.JSONDecodeError:
            raise IOError("ERROR: {0:s} is not respond".format(url))
    
    #------------------------------------------------------------------------------
    # FiC Methods
    #------------------------------------------------------------------------------
    def fic_prog(self, target, pr_mode, compress, bs_file, memo):
        if target not in self.board:
            raise ValueError("ERROR: board {0:s} is not found".format(target))

        url =  self.board_url[target] + '/fpga'

        bitname = os.path.basename(bs_file)
        with open(bs_file, 'rb') as f:
            if compress:
                b64 = base64.b64encode(gzip.compress(f.read()))

            else:
                b64 = base64.b64encode(f.read())

        j = json.dumps({
            'mode'     : pr_mode,
            'bitname'  : bitname,
            'compress' : compress,
            'memo'     : memo,
            'bitstream': b64.decode(encoding='utf-8')
        })

        print("INFO: Select FPGA configuration mode: {0:s}".format(pr_mode))
        print("INFO: Send FPGA configuration {0:s} to {1:s}".format(bitname, target))
        print("INFO: Awaiting response from {0:s}... be patient ... ".format(target))

        return self.rest_post(url, j)

    #------------------------------------------------------------------------------
    def fic_get_status(self, target):
        if target not in self.board:
            raise ValueError("ERROR: board {0:s} is not found".format(target))

        url = self.board_url[target] + '/status'
        return self.rest_get(url)

    #------------------------------------------------------------------------------
    def fic_reset(self, target):
        if target not in self.board:
            raise ValueError("ERROR: board {0:s} is not found".format(target))

        url = self.board_url[target] + '/fpga'
        print("INFO: Send FPGA reset to {0:s}".format(target))

        return self.rest_delete(url)

    #------------------------------------------------------------------------------
    def fic_hls_cmd(self, target, cmd):
        if cmd not in ['start', 'reset']:
            raise ValueError("ERROR: Unknown command {0:s}".format(cmd))

        if target not in self.board:
            print("ERROR: board {0:s} is not found".format(target), file=sys.stderr)

        url = self.board_url[target] + '/hls'
        print("INFO: Send HLS command to {0:s}".format(target))

        j = json.dumps({
            'command': cmd,
        })

        return self.rest_post(url, j)

    #------------------------------------------------------------------------------
    def fic_hls_send(self, target, data):
        if type(data) is not list:
            raise TypeError("ERROR: Invalid data type")

        if target not in self.board:
            raise ValueError("ERROR: board {0:s} is not found".format(target))

        url = self.board_url[target] + '/hls'
        print("INFO: Send HLS command to {0:s}".format(target))

        j = json.dumps({
            'command': 'send',
            'data': data,
        })

        return self.rest_post(url, j)

    #------------------------------------------------------------------------------
    def fic_hls_receive(self, target, count):
        if type(count) is not int:
            raise TypeError("ERROR: Count is invalid type")

        if count <= 0:
            raise ValueError("ERROR: Invalid count")

        if target not in self.board:
            raise ValueError("ERROR: board {0:s} is not found".format(target))

        url = self.board_url[target] + '/hls'
        print("INFO: Send HLS command to {0:s}".format(target))

        j = json.dumps({
            'command': 'receive',
            'count': count,
        })

        return self.rest_post(url, j)

    #------------------------------------------------------------------------------
    def fic_hls_ddr_write(self, target, data, addr):
        if type(data) is not bytes:
            raise TypeError("ERROR: Data is invalid type")

        if len(data) < 4:
            raise ValueError("ERROR: Data length is too short (less than 4B)")

        if (len(data) % 4) != 0:
            print("WARN: Data length is aligned to 4B", file=sys.stderr)

        if addr < 0 or addr > 0xffffffff:
            raise ValueError("ERROR: Address range is invalid")
 
        if target not in self.board:
            raise ValueError("ERROR: board {0:s} is not found".format(target))

        print("INFO: Start DDR write to {0:s} address={1:d}".format(target, addr))

        url = self.board_url[target] + '/hls_ddr'
        b64 = base64.b64encode(data)

        j = json.dumps({
            'command'  : 'write',
            'data'     : b64.decode('utf-8'),
            'address'  : addr,
        })

        return self.rest_post(url, j)

    #------------------------------------------------------------------------------
    def fic_hls_ddr_read(self, target, size, addr):
        if size <= 0:
            raise ValueError("ERROR: Invalid size {0:d}".format(size))

        if target not in self.board:
            raise ValueError("ERROR: board {0:s} is not found".format(target))

        print("INFO: Start DDR read from {0:s} address={1:d} size={2:d}".format(target, addr, size))

        url = self.board_url[target] + '/hls_ddr'

        j = json.dumps({
            'command': 'read',
            'address': addr,
            'size'   : size,
        })

        rcv = self.rest_post(url, j)

        if rcv['return'] == 'success':
            bs = base64.b64decode(rcv['data'])
            return {"return": "success", "data": bs}

        return {"return": "failed"}

    #------------------------------------------------------------------------------
    def fic_read(self, target, addr):
        if addr < 0 or addr > 0xffff:
            raise ValueError("ERROR: Invalid address")

        if target not in self.board:
            raise ValueError("ERROR: board {0:s} is not found".format(target))

        url = self.board_url[target] + '/regread'

        j = json.dumps({
            'address': addr,
        })

        return self.rest_post(url, j)

    #------------------------------------------------------------------------------
    def fic_write(self, target, addr, val):
        if addr < 0 or addr > 0xffff:
            raise ValueError("ERROR: Invalid address")

        if val > 0xff:
            raise ValueError("ERROR: Invalid value")

        if target not in self.board:
            raise ValueError("ERROR: board {0:s} is not found".format(target))

        url = self.board_url[target] + '/regwrite'

        j = json.dumps({
            'address': addr,
            'data': val,
        })

        return self.rest_post(url, j)

    #------------------------------------------------------------------------------
    def fic_set_switch(self, target, table):
        self.check_switch_json(table)

        if target not in self.board:
            raise ValueError("ERROR: board {0:s} is not found".format(target))

        url = self.board_url[target] + '/switch'

        if 'tablefile' in table.keys():
            tblf = table['tablefile']
            with open(tblf, 'rt') as f:
                j = json.dumps(json.loads(f.read()))

        else:
            j = json.dumps(table)

        return self.rest_post(url, j)

    #------------------------------------------------------------------------------
    def fic_runcmd(self, target, cmdline, timeout):
        if target not in self.board:
            raise ValueError("ERROR: board {0:s} is not found".format(target))

        url = self.board_url[target] + '/runcmd'

        j = json.dumps({
            'command': cmdline,
            'timeout': timeout 
            })

        return self.rest_post(url, j)

    #------------------------------------------------------------------------------
#    def fic_setup(self, config_json):
#
#        if config_json is None:
#            raise ValueError("ERROR: json is invalid")
#
#        # Syntax check
#
#        #------------------------------------------------------------------
#        def proc(q, target, conf):
#            # config FPGA
#            if 'fpga' in conf:
#                print('INFO: FPGA setup on {0}'.format(target))
#                fpga = conf['fpga']
#                bs_file = fpga['bitstream']
#                pr_mode = fpga['progmode']
#                msg = ''
#                if 'msg' in fpga.keys():
#                    msg = fpga['msg']
#
#                bitname = os.path.basename(bs_file)
#                with open(bs_file, 'rb') as f:
#                    b64 = base64.b64encode(gzip.compress(f.read()))
#                    f.close()
#                    ret = self.fic_prog(target, pr_mode, True, bitname, b64, msg)
#                    if ret['return'] != 'success':
#                        q.put((target, ret))
#                        return
#
#            # config TABLE
#            if 'switch' in conf:
#                print('INFO: Switch setup on {0}'.format(target))
#                switch = conf['switch']
#                ret = self.fic_set_switch(target, switch)
#                if ret['return'] != 'success':
#                    q.put((target, ret))
#                    return
#
#            # config dram
#            if 'dram' in config:
#                print('INFO: Dram setup on {0}'.format(target))
#                dram = conf['dram']
#                if 'command' == 'read':
#                    addr = dram['address']
#                    size = dram['size']
#                    ret = self.fic_hls_ddr_read(target, size, addr)
#                    if ret['return'] != 'success':
#                        q.put((target, ret))
#                        return
#
#                elif 'command' == 'write':
#                    file = dram['file']
#                    addr = dram['address']
#                    with open(file, 'rb') as f:
#
#                    ret = self.fic_hls_ddr_write(target, )
#
#
#
#            # config OPTION
#            if 'option' in conf:
#                print('INFO: Option setting on {0}'.format(target))
#                option = conf['option']
#                if 'auto_hls_reset_start' in option.keys():
#                    ret = self.fic_hls_cmd(target, 'reset')
#                    ret = self.fic_hls_cmd(target, 'start')
#                    if ret['return'] != 'success':
#                        q.put((target, ret))
#                        return
#
#                if 'auto_runcmd' in option.keys():
#                    ret = self.fic_runcmd(target, option['auto_runcmd'], 5)
#                    stdout = ret['stdout']
#                    stderr = ret['stderr']
#
#                    if stdout is None:
#                        stdout = ""
#
#                    if stderr is None:
#                        stderr = ""
#
#                    if ret['return'] == 'success':
#                        print("INFO: Run command on {0:s} is success".format(target))
#                        print("----")
#                        print("Stdout output:\n{0:s}".format(stdout))
#                        print("Stderr output:\n{0:s}".format(stderr))
#
#                    else:
#                        print("INFO: Run command on {0:s} is failed".format(target))
#                        print("INFO: {0:s}".format(ret['error']))
#                        print("----")
#                        print("Stdout output:\n{0:s}".format(stdout))
#                        print("Stderr output:\n{0:s}".format(stderr))
#
#            # Normal exit
#            q.put((target, {'return': 'success'}))
#            return
#
#        #------------------------------------------------------------------
#        ret = {}
#        procs = []
#        q = Queue()
#
#        for t, v in config_json.items():
#            p = Process(target=proc, args=(q, t, v))
#            procs.append((t, p))
#            p.start()
#
#        for t, p in procs:
#            p.join()
#            target, ret = q.get()
#            if ret['return'] == 'success':
#                print("INFO: Setup on {0:s} is success".format(target))
#                ret[t] = 'success'
#
#            else:
#                print("INFO: Setup on {0:s} is failed".format(target))
#                ret[t] = 'failed'
#
#        return ret

##------------------------------------------------------------------------------
#if __name__ == '__main__':
#    obj = ficmanage()
#    ret = obj.main()
#    exit(ret)
