# FiC manager CLI utility

* A CLI utility for manage fic boards via REST interface

## Usage

```
nyacom@gekko:~/project/fic/ficmgr$ ./ficmgr.py -h
usage: ficmgr.py [-h] [-t target1 [target2 ...]] [-l]
                 [-p for_target1 [for_target2 ...]] [-r]
                 [-hls [start | reset]] [-hr count]
                 [-hs for_target1 [for_target2 ...]]
                 [-sw for_target1 [for_target2 ...]] [-rr ADDR]
                 [-rw ADDR VALUE] [-pm [sm16 | sm16pr | sm8 | sm8pr]]
                 [-pmsg MESSAGE]
                 [--runcmd cmdline_for_target1 [cmdline_for_target2 ...]]

ficmanager nyacom (C) December, 2018

optional arguments:
  -h, --help            show this help message and exit
  -t target1 [target2 ...], --target target1 [target2 ...]
                        Define command target FiC boards
  -l, --list            Show FiC board status
  -p for_target1 [for_target2 ...], --prog for_target1 [for_target2 ...]
                        Program FPGA with *.bit file
  -r, --reset           Perform FPGA reset
  -hls [ start | reset ], --hlscmd [ start | reset ]
                        Control HLS
  -hr count, --hlsrecv count
                        Receive count data from HLS
  -hs for_target1 [for_target2 ...], --hlssend for_target1 [for_target2 ...]
                        Send provided data file to HLS (CSV or value per line
                        text file are supported)
  -sw for_target1 [for_target2 ...], --switchset for_target1 [for_target2 ...]
                        Set switch table with *.json file
  -rr ADDR, --regread ADDR
                        FiC register read from address
  -rw ADDR VALUE, --regwrite ADDR VALUE
                        FiC register write to [address value]
  -pm [ sm16 | sm16pr | sm8 | sm8pr ], --progmode [ sm16 | sm16pr | sm8 | sm8pr ]
                        FPGA Program mode
  -pmsg MESSAGE, --message MESSAGE
                        Message/notes for this FPGA programing
  --runcmd cmdline_for_target1 [cmdline_for_target2 ...]
                        Run command on RPi3

```

### Get board status

```
    ./ficmgr.py -l -t fic01 fic02

    'fic02':
    {   'board': {'dipsw': 1, 'done': 1, 'led': 0, 'link': 255, 'power': 1},
        'fpga': {   'bitname': 'ring.bin',
                    'conftime': 'Sat, 22 Dec 2018 23:23:21 GMT',
                    'done': 1,
                    'ifbit': 4,
                    'memo': 'Configure via ficdeploy by nyacom@polaris',
                    'mode': 'sm8'},
        'hls': {'status': 'stop'},
        'last_update': 1545952489.2381828,
        'switch': {   'outputs': {   'o0': {'s0': 0, 's1': 0, 's2': 0, 's3': 0},
                                    'o1': {'s0': 0, 's1': 0, 's2': 0, 's3': 0},
                                    'o2': {'s0': 0, 's1': 0, 's2': 0, 's3': 0},
                                    'o3': {'s0': 0, 's1': 0, 's2': 0, 's3': 0}},
                    'ports': 4,
                    'slots': 4}}


    'fic01':
    {   'board': {'dipsw': 0, 'done': 1, 'led': 1, 'link': 255, 'power': 1},
        'fpga': {   'bitname': 'ring.bin',
                    'conftime': 'Fri, 28 Dec 2018 20:23:19 GMT',
                    'done': 1,
                    'ifbit': 4,
                    'memo': 'Configure via ficdeploy by nyacom@polaris',
                    'mode': 'sm8'},
        'hls': {'status': 'stop'},
        'last_update': 1546395288.8909626,
        'switch': {   'outputs': {   'o0': {'s0': 0, 's1': 0, 's2': 0, 's3': 0},
                                    'o1': {'s0': 0, 's1': 0, 's2': 0, 's3': 0},
                                    'o2': {'s0': 0, 's1': 0, 's2': 0, 's3': 0},
                                    'o3': {'s0': 0, 's1': 0, 's2': 0, 's3': 0}},
                    'ports': 4,
                    'slots': 4}}
```

### Program FPGA

* use -p to specify FPGA bit file
* use -pm to specify FPGA program mode
* use -t to target board

* when you set multiple file with -p like '-p ring1.bin ring2.bin. ...' then with '-t fic01 fic02 ...', it will be program FPGA with given configuration according to arguments.


```
    nyacom@gekko:~/project/fic/ficmgr$ ./ficmgr.py -p ../ring/ring.bin -pm sm16 -t fic01 fic02
    ficmanager nyacom (C) December, 2018
    
    INFO: Send FPGA configuration ring.bin to fic02
    INFO: Awaiting response from fic02... be patience ...
    INFO: Send FPGA configuration ring.bin to fic01
    INFO: Awaiting response from fic01... be patience ...
    INFO: FPGA configuration on fic01 is success
    INFO: FPGA configuration on fic02 is success
```

### Run command on RPi3

* with --runcmd can invoke run command on RPi on the target FiC board
* The command line will be executing under www-data user
* Intractive shell is unsupported (like sudo)
* You must make every command in single line


### Use from python

* import ficmgr.py from your python script and call functions:

  * fic_prog(self, target, pr_mode, bitname, b64, memo)
  * fic_status(self, target)
  * fic_reset(self, target)
  * fic_hls_cmd(self, target, cmd)
  * fic_hls_send(self, target, data)
  * fic_hls_recv(self, target, count)
  * fic_regread(self, target, addr)
  * fic_regwrite(self, target, addr, val)
  * fic_setsw(self, target, table)

## Disclaimer
* I am okay if any fic member does not understand what I said, what I effort to do the eco system becoming better, how system deployment is harder. F*** y**.
