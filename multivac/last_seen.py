#!/usr/bin/env python

import os
import sys
import glob
from datetime import datetime
import json
import csv
import argparse
import importlib.resources as pkg_resources

# secret.LOG_STORAGE_BUCKET_URL
bucket_url_unstripped = os.environ.get('LOG_STORAGE_BUCKET_URL')
if not bucket_url_unstripped:
    print('LOG_STORAGE_BUCKET_URL not set')
    exit(1)
bucket_url = bucket_url_unstripped.strip("'")

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_DIR)
from multivac.sensors import test_status  # noqa: E402

parser = argparse.ArgumentParser(description="""
    Search for fails and sort by last occurence.
    The resulting report is stored in the output/ directory.
    """)
parser.add_argument('--branch', type=str, action='append',
                    help='branch (may be passed several times)')
parser.add_argument('--format', choices=['csv', 'html'], default='csv',
                    help='result format')
parser.add_argument('--short', action='store_true',
                    help="Coalesce 'runs-on' labels by a first word")
parser.add_argument('--repo-path', type=str, default='tarantool/tarantool',
                    help='owner/repository')
args = parser.parse_args()
branch_list = args.branch
result_format = args.format

output_dir = 'output'
workflow_runs_dir = f'{args.repo_path}/workflow_runs'
workflow_run_jobs_dir = f'{args.repo_path}/workflow_run_jobs'
org_repo = args.repo_path


def fails(log):
    for event in test_status.execute(log):
        if event['event'] != 'test status':
            continue
        status = event['status']
        if status in ('fail', 'transient fail', 'hang'):
            yield event['test'], event['conf'], status


timestamps_min = dict()
timestamps_max = dict()
res = dict()
for log in glob.glob(os.path.join(workflow_run_jobs_dir, '*.log')):
    # Load job meta.
    job_meta_path = log.split('.', 1)[0] + '.json'
    with open(job_meta_path, 'r') as f:
        job = json.load(f)

    # Load workflow run meta.
    run_id = str(job['run_id'])
    run_meta_path = os.path.join(workflow_runs_dir, run_id + '.json')
    with open(run_meta_path, 'r') as f:
        run = json.load(f)

    # Skip branches, which were not requested.
    branch = run['head_branch']
    if branch not in branch_list:
        continue

    timestamp_str = job['started_at'].rstrip('Z') + '+00:00'
    timestamp = datetime.fromisoformat(timestamp_str)
    if branch not in timestamps_min or timestamps_min[branch] > timestamp:
        timestamps_min[branch] = timestamp
    if branch not in timestamps_max or timestamps_max[branch] < timestamp:
        timestamps_max[branch] = timestamp

    job_id = job['id']
    run_id = job['run_id']
    # The idea of the --short option is that a user may not be
    # interested in separate results for, say, ubuntu-18.04 and
    # ubuntu-20.04. So we can just cut off everything after '-'.
    labels = job['labels']
    if args.short:
        labels = [label.split('-', 1)[0] for label in labels]
    runs_on = ','.join(labels)

    for test, conf, status in fails(log):
        key = (test, conf, status, runs_on)
        if key not in res:
            res[key] = (timestamp, branch, 1, job_id, run_id)
        elif res[key][0] < timestamp:
            res[key] = (timestamp, branch, res[key][2] + 1, job_id, run_id)
        else:
            res[key] = (res[key][0], res[key][1], res[key][2] + 1, res[key][3], res[key][4])

res = sorted(res.items(), key=lambda kv: (kv[1][0], kv[1][2], kv[1][3]),
             reverse=True)

output_fh = None


def write_line(line):
    global output_fh
    print(line, file=output_fh)


def write_csv():
    global output_fh

    print('Statistics for the following log intervals\n', file=sys.stderr)
    for branch in branch_list:
        if branch not in timestamps_min or branch not in timestamps_max:
            continue
        timestamp_min = timestamps_min[branch].isoformat()
        timestamp_max = timestamps_max[branch].isoformat()
        print('{}: [{}, {}]'.format(branch, timestamp_min, timestamp_max),
              file=sys.stderr)

    w = csv.writer(output_fh)
    write_line('timestamp,test,conf,branch,status,count,runs_on,'
               'url,job_json,job_log,run_json')
    for key, value in res:
        test, conf, status, runs_on = key
        timestamp, branch, count, job_id, run_id = value
        url = f"https://github.com/{org_repo}/runs/{job_id}?check_suite_focus=true"
        job_json = f'{bucket_url}/{org_repo}/workflow_run_jobs/{job_id}.json'
        job_log = f'{bucket_url}/{org_repo}/workflow_run_jobs/{job_id}.log'
        run_json = f'{bucket_url}/{org_repo}/workflow_runs/{run_id}.json'
        w.writerow([timestamp, test, conf, branch, status, count, runs_on,
                    url, job_json, job_log, run_json, ])


def write_html_header():
    write_line('<!DOCTYPE html>')
    write_line('<html>')
    write_line('  <head>')
    write_line('    <meta http-equiv="Content-Type" content="text/html; ' +
               'charset=utf-8">')
    write_line('    <title>Last seen fails in CI</title>')
    write_line('    <link rel="stylesheet" type="text/css" href="main.css">')
    write_line('  </head>')
    write_line('  <body>')


def write_html_footer():
    write_line('  </body>')
    write_line('</html>')


def write_html():
    write_html_header()
    write_line('    <h1>Last seen fails in CI</h1>')

    write_line('    <table class="log_intervals">')
    write_line('      <caption>Log intervals</caption>')
    write_line('      <tr>')
    write_line('        <th>Timestamp</th>')
    write_line('        <th>Starting from</th>')
    write_line('        <th>Ending at</th>')
    write_line('      </tr>')
    write_line('      <tr>')
    for branch in branch_list:
        if branch not in timestamps_min or branch not in timestamps_max:
            continue
        timestamp_min = timestamps_min[branch].isoformat()
        timestamp_max = timestamps_max[branch].isoformat()
        write_line('        <td class="branch">{}</td>'.format(branch))
        write_line('        <td class="timestamp_min">{}</td>'.format(
            timestamp_min))
        write_line('        <td class="timestamp_max">{}</td>'.format(
            timestamp_max))
        write_line('      </tr>')
    write_line('    </table>')

    write_line('    <table class="last_seen">')
    write_line('      <caption>Last seen fails in CI</caption>')
    write_line('      <tr>')
    write_line('        <th>Timestamp</th>')
    write_line('        <th>Test</th>')
    write_line('        <th>Conf</th>')
    write_line('        <th>Branch</th>')
    write_line('        <th>Status</th>')
    write_line('        <th>Count</th>')
    write_line('        <th>URL</th>')
    write_line('        <th>Runs on</th>')
    write_line('      </tr>')
    for key, value in res:
        test, conf, status, runs_on = key
        timestamp, branch, count, url = value
        write_line('      <tr>')
        write_line('        <td class="timestamp">{}</td>'.format(timestamp))
        write_line('        <td class="test">{}</td>'.format(test))
        write_line('        <td class="conf">{}</td>'.format(conf or ''))
        write_line('        <td class="branch">{}</td>'.format(branch))
        write_line('        <td class="status">{}</td>'.format(status))
        write_line('        <td class="count">{}</td>'.format(count))
        write_line('        <td class="url"><a href="{}">[log]</a></td>'.
                   format(url))
        write_line('        <td class="runs_on">{}</td>'.format(runs_on))
        write_line('      </tr>')
    write_line('    </table>')

    write_html_footer()


if not os.path.isdir(output_dir):
    os.makedirs(output_dir)

if result_format == 'csv':
    output_file = os.path.join(output_dir, 'last_seen.csv')

    with open(output_file, 'w') as f:
        output_fh = f
        write_csv()

    print('Written {}'.format(output_file), file=sys.stderr)
elif result_format == 'html':
    output_css_file = os.path.join(output_dir, 'main.css')
    output_html_file = os.path.join(output_dir, 'last_seen.html')

    css = pkg_resources.read_text('multivac.resources', 'main.css')
    with open(output_css_file, 'w') as f:
        f.write(css)
    print('Written {}'.format(output_css_file), file=sys.stderr)

    with open(output_html_file, 'w') as f:
        output_fh = f
        write_html()
    print('Written {}'.format(output_html_file), file=sys.stderr)
else:
    raise ValueError('Unknown result format: {}'.format(result_format))
