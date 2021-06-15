#!/usr/bin/env python

import os
import sys
import re
import glob
from datetime import datetime
import json
import csv
import argparse


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


parser = argparse.ArgumentParser(
    description='Search for fails and sort by last occurence')
parser.add_argument('--branch', type=str, action='append',
                    help='branch (may be passed several times)')
args = parser.parse_args()
branch_list = args.branch


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


timestamps_min = dict()
timestamps_max = dict()
res = dict()
for log in glob.glob('runs/*.log'):
    meta_path = log.split('.', 1)[0] + '.json'
    with open(meta_path, 'r') as f:
        run = json.load(f)
    branch = run['head_branch']

    if branch not in branch_list:
        continue

    timestamp = datetime.fromisoformat(run['created_at'].rstrip('Z'))
    if branch not in timestamps_min or timestamps_min[branch] > timestamp:
        timestamps_min[branch] = timestamp
    if branch not in timestamps_max or timestamps_max[branch] < timestamp:
        timestamps_max[branch] = timestamp

    for test, conf, status in fails(log):
        key = (test, conf, status)
        if key not in res:
            res[key] = (timestamp, branch, 1, log)
        elif res[key][0] < timestamp:
            res[key] = (timestamp, branch, res[key][2] + 1, log)
        else:
            res[key] = (res[key][0], res[key][1], res[key][2] + 1, res[key][3])

print('Statistics for the following log intervals\n', file=sys.stderr)
for branch in branch_list:
    timestamp_min = timestamps_min[branch].isoformat()
    timestamp_max = timestamps_max[branch].isoformat()
    print('{}: [{}, {}]'.format(branch, timestamp_min, timestamp_max),
          file=sys.stderr)
print('', file=sys.stderr)

res = sorted(res.items(), key=lambda kv: (kv[1][0], kv[1][2]), reverse=True)
w = csv.writer(sys.stdout)
print('timestamp,test,conf,branch,status,count,log')
for key, value in res:
    test, conf, status = key
    timestamp, branch, count, log = value
    w.writerow([timestamp, test, conf, branch, status, count, log])
