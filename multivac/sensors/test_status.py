#!/usr/bin/env python

import sys
import re
from collections import OrderedDict


SEP_RE = r' +'
TIMESTAMP_RE = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d+Z'
WORKER_ID_RE = r'\[\d+\]'
TEST_RE = r'(?P<test>[^ ]+/[^ ]+(.test.lua|.test.sql|.test.py|.test|>))'
CONF_RE = r'((?P<conf>[^ []+)|)'
STATUS_RE = r'((Test timeout of \d+ secs reached\t)?\[ (?P<status>[^ ]+) \]|)'

TEST_STATUS_LINE_RE = re.compile(
    '^' +
    TIMESTAMP_RE + SEP_RE +
    WORKER_ID_RE + SEP_RE +
    TEST_RE + SEP_RE +
    CONF_RE + SEP_RE +
    STATUS_RE +
    '$')


def test_status_iter(f):
    for line in f:
        m = TEST_STATUS_LINE_RE.match(line)
        if m:
            status = m.group('status') or 'fail'
            yield m['test'], m['conf'], status


def test_smart_status_iter(f):
    tmp = OrderedDict()
    for test, conf, status in test_status_iter(f):
        key = (test, conf)
        if status == 'pass' and tmp.get(key) == 'fail':
            status = 'transient fail'
        tmp[key] = status
    for key, status in tmp.items():
        test, conf = key
        yield test, conf, status


def execute(log_filepath):
    with open(log_filepath, 'r') as f:
        for test, conf, status in test_smart_status_iter(f):
            yield {
                'event': 'test status',
                'test': test,
                'conf': conf,
                'status': status,
            }


if __name__ == '__main__':
    with open(sys.argv[1], 'r') as f:
        for test, conf, status in test_smart_status_iter(f):
            print('event: test status; test: {}; conf: {}; status: {}'.format(
                test, conf or 'null', status))
