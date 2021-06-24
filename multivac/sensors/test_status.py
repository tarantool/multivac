#!/usr/bin/env python

import os
import sys
import re
import json
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


def get_cache_filepath(log_filepath):
    return '{}.test_status.cache.json'.format(log_filepath)


def test_status_iter(log_fh, cache_filepath=None):
    if cache_filepath:
        if os.path.isfile(cache_filepath):
            with open(cache_filepath, 'r') as cache_fh:
                data = json.load(cache_fh)
            for test_status in data:
                yield tuple(test_status)
            return

        cache = []

    for line in log_fh:
        m = TEST_STATUS_LINE_RE.match(line)
        if m:
            status = m.group('status') or 'fail'
            res = (m['test'], m['conf'], status)
            if cache_filepath:
                cache.append(res)
            yield res

    if cache_filepath:
        with open(cache_filepath, 'w') as cache_fh:
            json.dump(cache, cache_fh, indent=2)


def test_smart_status_iter(log_fh, cache_filepath=None):
    tmp = OrderedDict()
    for test, conf, status in test_status_iter(log_fh, cache_filepath):
        key = (test, conf)
        if status == 'pass' and tmp.get(key) == 'fail':
            status = 'transient fail'
        tmp[key] = status
    for key, status in tmp.items():
        test, conf = key
        yield test, conf, status


def execute(log_filepath):
    cache_filepath = get_cache_filepath(log_filepath)
    with open(log_filepath, 'r') as log_fh:
        for test, conf, status in test_smart_status_iter(
                log_fh, cache_filepath):
            yield {
                'event': 'test status',
                'test': test,
                'conf': conf,
                'status': status,
            }


if __name__ == '__main__':
    log_filepath = sys.argv[1]
    cache_filepath = get_cache_filepath(log_filepath)
    with open(log_filepath, 'r') as log_fh:
        for test, conf, status in test_smart_status_iter(
                log_fh, cache_filepath):
            print('event: test status; test: {}; conf: {}; status: {}'.format(
                test, conf or 'null', status))
