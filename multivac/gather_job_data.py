#!/usr/bin/env python
import argparse
import csv
import glob
import json
import os
import re
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_DIR)

version_matcher = re.compile(r"Current runner version: "
                             r"'(\d*.\d*.\d*)'")


class GatherData:
    def __init__(self, cli_args):
        self.workflow_run_jobs_dir = 'workflow_run_jobs'
        self.output_dir = 'output'
        self.gathered_data = dict()
        self.latest_n: int = cli_args.latest

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

            # Save data to dict
            self.gathered_data[job_id] = {
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
                self.gathered_data[job_id].update(
                    {'runner_name': job['runner_name']}
                )
            if runner_version:
                self.gathered_data[job_id].update(
                    {'runner_version': runner_version}
                )

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
    args = parser.parse_args()

    result = GatherData(args)
    result.gather_data()
    if args.format == 'json':
        result.write_json()
    if args.format == 'csv':
        result.write_csv()
