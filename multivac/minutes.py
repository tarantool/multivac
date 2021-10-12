#!/usr/bin/env python

import math
import os
import glob
import re
import json
from datetime import datetime, timedelta
import argparse


parser = argparse.ArgumentParser(description='Machine time spent in jobs')
parser.add_argument('--short', action='store_true',
                    help="Coalesce 'runs-on' labels by a first word")
args = parser.parse_args()


workflow_runs_dir = 'workflow_runs'
workflow_run_jobs_dir = 'workflow_run_jobs'


def timestamp(timestamp_from_github):
    timestamp_str = timestamp_from_github.rstrip('Z') + '+00:00'
    return datetime.fromisoformat(timestamp_str)


def add_minutes(acc, k1, k2, value):
    """ Helper to update minutes_per_*. """
    if k1 not in acc:
        acc[k1] = {}
    if k2 not in acc[k1]:
        acc[k1][k2] = 0
    acc[k1][k2] += value


def print_minutes(header, acc, k2_list):
    """ Helper to print minutes_per_*. """
    print(header + ' ' + ' '.join(k2_list))
    for k1, summary in sorted(acc.items()):
        summary_sorted = []
        for k2 in k2_list:
            val = math.ceil(summary.get(k2, 0))
            summary_sorted.append(str(val).rjust(len(k2)))
        summary_str = ' '.join(summary_sorted)
        print('{} {}'.format(k1, summary_str))


JOB_META_PATH_RE = re.compile(r'^{}/[0-9]+.json$'.format(
    workflow_run_jobs_dir))

# Splitted by day / week / month, then by 'runs-on'.
minutes_per_day = dict()
minutes_per_week = dict()
minutes_per_month = dict()

known_runs_on = set()

for job_meta_path in glob.glob(os.path.join(workflow_run_jobs_dir, '*.json')):
    # Skip everything except workflow run job meta:
    # say, *.log.test_status.cache.json files.
    if not JOB_META_PATH_RE.match(job_meta_path):
        continue

    # Load job meta.
    with open(job_meta_path, 'r') as f:
        job = json.load(f)

    # Load workflow run meta.
    run_id = str(job['run_id'])
    run_meta_path = os.path.join(workflow_runs_dir, run_id + '.json')
    with open(run_meta_path, 'r') as f:
        run = json.load(f)

    if job['conclusion'] == 'skipped':
        continue

    started_at = timestamp(job['started_at'])
    completed_at = timestamp(job['completed_at'])
    # I hope GitHub does not count 1.5 minutes job as 2 minutes.
    minutes = (completed_at - started_at) / timedelta(minutes=1)

    day = started_at.strftime('%Y-%m-%d')
    week = started_at.strftime('%Y-W%W')
    month = started_at.strftime('%Y-%m-*')

    # The idea of the --short option is that a user may not be
    # interested in separate minutes for, say, ubuntu-18.04 and
    # ubuntu-20.04. So we can just cut off everything after '-'.
    labels = job['labels']
    if args.short:
        labels = [label.split('-', 1)[0] for label in labels]
    runs_on = ','.join(labels)
    known_runs_on.add(runs_on)

    add_minutes(minutes_per_day, day, runs_on, minutes)
    add_minutes(minutes_per_week, week, runs_on, minutes)
    add_minutes(minutes_per_month, month, runs_on, minutes)

known_runs_on = sorted(known_runs_on)

print('Minutes per day:')
print_minutes('YYYY-MM-DD', minutes_per_day, known_runs_on)
print('')

print('Minutes per week:')
print_minutes('YYYY-.WW', minutes_per_week, known_runs_on)
print('')

print('Minutes per month:')
print_minutes('YYYY-MM-*', minutes_per_month, known_runs_on)
