#!/usr/bin/env python

import sys
import re

def failed_tests():
    RE = re.compile(r'\[\d+\] +(?P<test>[^ ]+/[^ ]+) +(?P<conf>[^ ]+)? +\[ (?P<status>[^ ]+) \]')
    with open(sys.argv[1], 'r') as f:
        for line in f:
            m = RE.search(line)
            if m and m['status'] == 'fail':
                yield m['test'], m['conf']

for test, conf in failed_tests():
    if conf:
        print('event: fail; test: {}; conf: {}'.format(test, conf))
    else:
        print('event: fail; test: {}'.format(test))
