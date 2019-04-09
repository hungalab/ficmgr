from __future__ import print_function
import unittest
import os 
import base64
from ficmgr import ficmanage

# change these
bs_files = ['/home/asap/hunga/demo3/virt4x4/fic_top.bin']
targets = ['fic07']
pr_mode = 'sm8'
test_ficmgr = ficmanage()

class FicmgrTest(unittest.TestCase):
    '''
    these tests should be done sequentially
    '''
    def test_prog(self):
        for bs, t in zip(bs_files, targets):
            bitname = os.path.basename(bs)
            with open(bs, 'rb') as f:
                b64 = base64.b64encode(f.read())
                f.close()
            status = test_ficmgr.fic_prog(t, pr_mode, bitname, b64, 'testing ficprog')
            self.assertEqual(status['return'], 'success')

    def test_reset_and_start(self):
        commands = ['reset', 'start']
        for c in commands:
            print("testing command: ", c)
            for t in targets:
                status = test_ficmgr.fic_hls_cmd(t, c)
                self.assertEqual(status['return'], 'success')


if __name__ == '__main__':
    unittest.main()