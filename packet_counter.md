# ficmgr_tool
Tools that use ficmgr (only compatible with FiC (not MKUBOS)) <br>
Note: you have to put libficmgr.py ([ficmgr](https://github.com/hungalab/ficmgr)) in the directory or make a symbolic link to libficmgr.py.
```
/--
  |-- fft_checker.py
  |-- libficmgr.py
  |-- ...
```

## packet_monitor.py
You can get the packet counter.
### Usage
```
usage: packet_monitor.py [-h] [-t [T [T ...]]] [--tid [TID [TID ...]]] [-a] [-m] [--radix {5,6}]

Get packet counter

optional arguments:
  -h, --help            show this help message and exit
  -t [T [T ...]]        target FPGA (name)
  --tid [TID [TID ...]]
                        target FPGA (id)
  -a, --ALL             If you want to get packet counter from all FPGAs, you can use this option instead of the -t
                        option.
  -m                    use multi-ejection switches
  --radix {5,6}         radix of the switch
```
### Example
```
$ python3 packet_monitor.py -t m2fic00 m2fic01 m2fic02 m2fic03 --radix 5
(or $ python3 packet_monitor.py --tid 12 13 14 15 --radix 5)
########m2fic00################
----lane0----
from_hls(in0):2049, in1:2048, in2:4096, in3:0, in4:0
to_hls(out0):6144, out1:4097, out2:2049, out3:0, out4:0
----lane1----
from_hls(in0):2049, in1:2048, in2:4096, in3:0, in4:0
to_hls(out0):6144, out1:4097, out2:2049, out3:0, out4:0
----lane2----
from_hls(in0):2049, in1:2048, in2:4096, in3:0, in4:0
to_hls(out0):6144, out1:4097, out2:2049, out3:0, out4:0
----lane3----
from_hls(in0):2049, in1:2048, in2:4096, in3:0, in4:0
to_hls(out0):6144, out1:4097, out2:2049, out3:0, out4:0
```

## read_from_hls.py
You can read data from HLS.
### Usage
```
usage: read_from_hls.py [-h] [-t [T [T ...]]] [--tid [TID [TID ...]]] [-a] --type {int,uint,float} [-s SIZE]

Read date from HLS

optional arguments:
  -h, --help            show this help message and exit
  -t [T [T ...]]        target FPGA (name)
  --tid [TID [TID ...]]
                        target FPGA (id)
  -a, --ALL             If you want to get data from all FPGAs, you can use this option instead of the -t option.
  --type {int,uint,float}
                        data type
  -s SIZE, --size SIZE  # of data for each board
```
### Example
```
$ python3 read_from_hls.py -t m2fic00 m2fic01 m2fic02 m2fic03 --type float -s 2048
(or $ python3 read_from_hls.py --tid 12 13 14 15 --type float -s 2048)
INFO: Send HLS command to m2fic00
########m2fic00################
data[0]: 0.000351 (hex:0x39b82066)
data[1]: 0.000358 (hex:0x39bbb90c)
data[2]: 0.000329 (hex:0x39acb674)
data[3]: 0.000389 (hex:0x39cc2aa2)
data[4]: 0.000420 (hex:0x39dc47b1)
data[5]: 0.000474 (hex:0x39f86e52)
data[6]: 0.000489 (hex:0x3a002996)
data[7]: 0.000692 (hex:0x3a356b3a)
data[8]: 0.000982 (hex:0x3a80a8d6)
data[9]: 0.001859 (hex:0x3af3b36c)
data[10]: 4095.999023 (hex:0x457ffffc)
data[11]: -0.001671 (hex:0xbadb1118)
data[12]: -0.000804 (hex:0xba52b35c)
data[13]: -0.000511 (hex:0xba060393)
...
data[2039]: 0.000001 (hex:0x3555e292)
data[2040]: 0.000000 (hex:0x34241d90)
data[2041]: -0.000006 (hex:0xb6bf3346)
data[2042]: 0.000008 (hex:0x3702f065)
data[2043]: -0.000006 (hex:0xb6c15c84)
data[2044]: 0.000003 (hex:0x3629140f)
data[2045]: -0.000003 (hex:0xb65ca5f8)
data[2046]: 0.000010 (hex:0x3728882a)
data[2047]: -0.000007 (hex:0xb6df6350)

INFO: Send HLS command to m2fic01
########m2fic01################
data[0]: 0.000002 (hex:0x35fef643)
data[1]: -0.000000 (hex:0xb33f02c0)
data[2]: 0.000003 (hex:0x36472ff8)
data[3]: -0.000005 (hex:0xb6abc5ce)
data[4]: 0.000002 (hex:0x35cd2cb2)
...
```

## time_monitor.py
You can get the timer.
### Usage
```
usage: time_monitor.py [-h] [-t [T [T ...]]] [--tid [TID [TID ...]]] [-a]

Get timer

optional arguments:
  -h, --help            show this help message and exit
  -t [T [T ...]]        target FPGA (name)
  --tid [TID [TID ...]]
                        target FPGA (id)
  -a, --ALL             If you want to get timer from all FPGAs, you can use this option instead of the -t option.
```
### Example
```
$ python3 time_monitor.py -t m2fic00 m2fic01 m2fic02 m2fic03
(or $ python3 time_monitor.py --tid 12 13 14 15)
########m2fic00################
timer: 18440

########m2fic01################
timer: 18430

########m2fic02################
timer: 18424

########m2fic03################
timer: 18418
```
