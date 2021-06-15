#!/usr/bin/env python

import os
import sys
import re
import glob
from datetime import datetime
import json
import csv


# from subprocess import PIPE
# from subprocess import Popen


# SEP_RE = r'; '
# EVENT_RE = r'event: (?P<event>[^;]+)'
# TEST_RE = r'test: (?P<test>[^;]+)'
# CONF_RE = r'conf: (?P<conf>[^;]+)'
# STATUS_RE = r'status: (?P<status>[^;]+)'
# RE = re.compile(
#     '^' +
#     EVENT_RE + SEP_RE +
#     TEST_RE + SEP_RE +
#     CONF_RE + SEP_RE +
#     STATUS_RE +
#     '$')


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_DIR)
from multivac.sensors import test_status  # noqa: E402


def fails(log):
    # cmd = ['multivac/sensors/test_status.py', log]
    # with Popen(cmd, stdout=PIPE, encoding='utf-8') as process:
    #     for line in process.stdout:
    #         m = RE.match(line.rstrip())
    #         if m and m['event'] == 'test status' and \
    #                 m['status'] in ('fail', 'transient fail'):
    #             conf = None if m['conf'] == 'null' else m['conf']
    #             yield m['test'], conf, m['status']
    for event in test_status.execute(log):
        if event['event'] != 'test status':
            continue
        status = event['status']
        if status in ('fail', 'transient fail'):
            yield event['test'], event['conf'], status


res = dict()
for log in glob.glob('runs/*.log'):
    meta_path = log.split('.', 1)[0] + '.json'
    with open(meta_path, 'r') as f:
        run = json.load(f)
    branch = run['head_branch']
    timestamp = datetime.fromisoformat(run['created_at'].rstrip('Z'))

    if branch != 'master' and not re.match(r'^\d+\.\d+$', branch):
        continue

    for test, conf, status in fails(log):
        key = (test, conf)
        if key not in res or res[key][0] < timestamp:
            res[key] = (timestamp, branch, status, log)

res = sorted(res.items(), key=lambda kv: kv[1][0], reverse=True)
w = csv.writer(sys.stdout)
for key, value in res:
    test, conf = key
    timestamp, branch, status, log = value
    w.writerow([timestamp, test, conf, branch, status, log])
