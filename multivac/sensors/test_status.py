#!/usr/bin/env python

import os
import sys
import re
import json
from collections import OrderedDict


SEP_RE = r' +'
TIMESTAMP_RE = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d+Z'
WORKER_ID_RE = r'(?P<wid>\[\d+\])'
TEST_RE = r'(?P<test>[^ ]+/[^ ]+(.test.lua|.test.sql|.test.py|.test|>))'
CONF_RE = r'((?P<conf>[^ []+)|)'
STATUS_RE = r'((Test timeout of \d+ secs reached\t)?\[ (?P<status>[^ ]+) \]|)'
RESULT_RE = r'(?P<result>[^ ]+/[^ ]+\.result)'

TEST_STATUS_LINE_RE = re.compile(
    '^' +
    TIMESTAMP_RE + SEP_RE +
    WORKER_ID_RE + SEP_RE +
    TEST_RE + SEP_RE +
    CONF_RE + SEP_RE +
    STATUS_RE +
    '$')
TEST_HANG_RE = re.compile(
    '^' +
    TIMESTAMP_RE + SEP_RE +
    r'Test hung! Result content mismatch:' +
    '$')
HANG_RESULT_RE = re.compile(
    '^' +
    TIMESTAMP_RE + SEP_RE +
    r'--- ' + RESULT_RE + r'\b')

# match lines with late test result: [ <worker_id> ] [ <result> ]
LATE_STATUS = re.compile(r'.*(?P<wid>\[\d+\]) \[ (?P<res>[a-z]+) ]')


def get_cache_filepath(log_filepath):
    return '{}.test_status.cache.json'.format(log_filepath)


def test_status_iter(log_fh, cache_filepath=None):
    """ Iterator generator, which accepts a log file handle
        (which contains an output of a CI job) and yields
        (test, conf, status) tuples.

        Caches result in the 'cache_filepath' file when its name
        is provided. Reuses the existing cache on next
        invocations.
    """
    if cache_filepath:
        if os.path.isfile(cache_filepath):
            with open(cache_filepath, 'r') as cache_fh:
                data = json.load(cache_fh)
            for test_status in data:
                yield tuple(test_status)
            return

        cache = []

    hang_detected = False

    awaiting_tests = {}
    for line in log_fh:
        m = TEST_STATUS_LINE_RE.match(line)

        if m:
            if not m.group('status'):
                awaiting_tests.update({m['wid']: (m['test'], m['conf'])})
                continue
            status = m.group('status')
            res = (m['test'], m['conf'], status)
            if cache_filepath:
                cache.append(res)
            yield res
            continue
        elif awaiting_tests:
            status_match = LATE_STATUS.match(line)
            if status_match:
                matched_test = awaiting_tests.pop(status_match.group('wid'))
                res = (matched_test[0],
                       matched_test[1],
                       status_match.group('res'))
                yield res

        m = TEST_HANG_RE.match(line)
        if m:
            hang_detected = True
            continue

        if hang_detected:
            hang_detected = False
            m = HANG_RESULT_RE.match(line)
            if m:
                result = m['result']
                # Assume .result -> .test.lua as most common test
                # kind.
                #
                # In fact, we don't know, whether it is .test.lua,
                # .test.sql, .test.py, .test.sql or just .test.
                test = result.split('.', 1)[0] + '.test.lua'
                # We don't know a configuration, assume None.
                res = (test, None, 'hang')
                if cache_filepath:
                    cache.append(res)
                yield res
                continue

    # if there are tests with no result, save them as failed.
    for wid in awaiting_tests:
        res = awaiting_tests.get(wid)  # get tuple (test name, test conf)
        yield (res[0], res[1], 'fail')

    if cache_filepath:
        with open(cache_filepath, 'w') as cache_fh:
            json.dump(cache, cache_fh, indent=2)


def test_smart_status_iter(log_fh, cache_filepath=None):
    """ Iterator generator that yields (test, conf, status)
        tuples.

        The difference from `test_status_iter()` is that this
        iterator squashes duplicates and reports 'transient fail'
        status for a test, which fails, run again and succeeds.
    """
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
    """ External API for the smart test status iterator.

        The result format is designed to provide some level of
        unification between different sensors. The event
        dictionary for the 'test status' event contains `test`,
        `conf` and `status` fields (except common `event` field).
    """
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
    """ Command line API for the smart test status iterator.

        Accepts a CI log file name as the command line argument,
        prints test statuses in a simple format that may be
        grepped or parsed from arbitrary language.
    """
    log_filepath = sys.argv[1]
    cache_filepath = get_cache_filepath(log_filepath)
    with open(log_filepath, 'r') as log_fh:
        for test, conf, status in test_smart_status_iter(
                log_fh, cache_filepath):
            print('event: test status; test: {}; conf: {}; status: {}'.format(
                test, conf or 'null', status))
