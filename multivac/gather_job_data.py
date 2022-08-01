#!/usr/bin/env python
import argparse
import csv
import glob
import json
import os
import re
import sys

from sensors.failures import failure_specs

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_DIR)

version_matcher = re.compile(r"Current runner version: "
                             r"'(\d*.\d*.\d*)'")


# As far as the failure occurs at the end of the log, let's
# start to parse the file from the end to speed up the process
def reverse_readline(filename, buf_size=8192):
    """An iterator that returns the lines of a file in reverse order"""
    with open(filename, encoding='utf8') as fh:
        segment = None
        offset = 0
        fh.seek(0, os.SEEK_END)
        file_size = remaining_size = fh.tell()
        while remaining_size > 0:
            offset = min(file_size, offset + buf_size)
            fh.seek(file_size - offset)
            try:
                buffer = fh.read(min(remaining_size, buf_size))
            except UnicodeDecodeError:
                yield ''
            remaining_size -= buf_size
            lines = buffer.split('\n')
            # The first line of the buffer is probably not a complete line so
            # we'll save it and append it to the last line of the next buffer
            # we read
            if segment is not None:
                # If the previous chunk starts right from the beginning of line
                # do not concat the segment to the last line of new chunk.
                # Instead, yield the segment first
                if buffer[-1] != '\n':
                    lines[-1] += segment
                else:
                    yield segment
            segment = lines[0]
            for index in range(len(lines) - 1, 0, -1):
                if lines[index]:
                    yield lines[index]
        # Don't yield None if the file was empty
        if segment is not None:
            yield segment


def detect_error(logs: str) -> (str, str):
    for number, line in enumerate(reverse_readline(logs)):
        # check if the line matches one of regular expressions:
        for failure_type in failure_specs:
            for regexp in failure_type['re_compiled']:
                if regexp.match(line):
                    return failure_type['type'], line
    return 'unknown', None


class GatherData:
    def __init__(self, cli_args):
        self.workflow_run_jobs_dir = 'workflow_run_jobs'
        self.output_dir = 'output'
        self.gathered_data = dict()
        self.latest_n: int = cli_args.latest
        self.watch_failure = args.watch_failure

    def gather_data(self):
        job_json_files = sorted(glob.glob(
            os.path.join(self.workflow_run_jobs_dir, '*[0-9].json')),
            reverse=True)
        if self.latest_n:
            job_json_files = job_json_files[:self.latest_n]
        for job_json in job_json_files:

            # Load info about jobs from .json
            with open(job_json, 'r') as f:
                job = json.load(f)

            if job['conclusion'] in ['skipped', 'cancelled']:
                continue

            if 'aarch64' in job['name']:
                platform = 'aarch64'
            else:
                platform = 'amd64'

            # Load info about jobs from .log, if there are logs
            job_id = job['id']
            logs = f'{self.workflow_run_jobs_dir}/{job_id}.log'
            job_failure_type = None
            runner_version = None
            try:
                with open(logs, 'r') as f:
                    time_queued = f.readline()[0:19] + 'Z'
                    for _ in range(10):
                        line = f.readline()
                        match = version_matcher.search(line)
                        if match:
                            runner_version = match.group(1)
                            break
            except FileNotFoundError:
                print(f'no logs for job {job_id}')

            if job['conclusion'] == 'failure':
                job_failure_type, failure_line = detect_error(logs)
                if job_failure_type == self.watch_failure:
                    print(
                        f'{job_id}  {job["name"]}\t'
                        f' https://github.com/tarantool/tarantool/runs/'
                        f'{job_id}?check_suite_focus=true\n'
                        f'\t\t\t{failure_line}')
                results[job_failure_type] += 1
                results['total'] += 1

            # Save data to dict
            gathered_job_data = {
                'job_id': job_id,
                'job_name': job['name'],
                'status': job['conclusion'],
                'queued_at': time_queued,
                'started_at': job['started_at'],
                'completed_at': job['completed_at'],
                'runner_label': job['labels'],
                'platform': platform
            }

            if job['runner_name']:
                gathered_job_data.update(
                    {'runner_name': job['runner_name']}
                )
            if runner_version:
                gathered_job_data.update(
                    {'runner_version': runner_version}
                )
            if job_failure_type:
                gathered_job_data.update(
                    {'failure_type': job_failure_type}
                )
            self.gathered_data[job_id] = gathered_job_data

    def write_json(self):
        if not os.path.isdir(self.output_dir):
            os.makedirs(self.output_dir)
        output_file = os.path.join(self.output_dir + '/workflows.json')
        with open(output_file, 'w') as jsonfile:
            json.dump(self.gathered_data, jsonfile, indent=2)

    def write_csv(self):
        if not os.path.isdir(self.output_dir):
            os.makedirs(self.output_dir)
        output_file = os.path.join(self.output_dir + '/workflows.csv')
        fieldnames = [
            'job_id',
            'job_name',
            'status',
            'failure_type',
            'queued_at',
            'started_at',
            'completed_at',
            'platform',
            'runner_label',
            'runner_name',
            'runner_version',
        ]
        with open(output_file, 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for job_data in self.gathered_data.values():
                writer.writerow(job_data)

    def print_failure_stats(self):
        if args.failure_stats:
            sorted_results = list(sorted(results.items(), key=lambda x: x[1], reverse=True))
            for (type, count) in sorted_results:
                if count > 0:
                    print(type, count)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Gather data about GitHub workflows')
    parser.add_argument(
        '--format', choices=['json', 'csv'],
        help='write gathered data in the specified format'
    )
    parser.add_argument(
        '--latest', type=int,
        help='Only take logs from the latest N workflow runs'
    )
    parser.add_argument(
        '--failure-stats', action='store_true',
        help='show overall failure statistics')
    parser.add_argument(
        '--watch-failure', type=str,
        help='show detailed statistics about certain type of workflow failure')

    args = parser.parse_args()

    # compile regular expressions
    for failure_type in failure_specs:
        failure_type.update(
            {'re_compiled': [re.compile(expression) for expression in failure_type['re']]}
        )

    results = {failure_type['type']: 0 for failure_type in failure_specs}
    results.update({'unknown': 0})
    results.update({'total': 0})

    result = GatherData(args)
    result.gather_data()
    if args.format == 'json':
        result.write_json()
    if args.format == 'csv':
        result.write_csv()
    if args.failure_stats:
        result.print_failure_stats()
