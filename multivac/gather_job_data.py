#!/usr/bin/env python

import glob
import json
import os
import sys
import re

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_DIR)


class GatherData:
    def __init__(self):
        self.workflow_run_jobs_dir = 'workflow_run_jobs'
        self.output_dir = 'gathered_data'
        self.gathered_data = dict()

    def gather_data(self):
        version_matcher = re.compile(r"Current runner version: "
                                     r"'(\d*.\d*.\d*)'")
        for jobs in glob.glob(os.path.join(self.workflow_run_jobs_dir,
                                           '*.json')):
            runner_version = None
            # Load info about jobs from .json
            with open(jobs, 'r') as f:
                job = json.load(f)

            if job['conclusion'] == 'skipped':
                continue
            if 'aarch64' in job['name']:
                platform = 'aarch64'
            else:
                platform = 'amd64'

            # Load info about jobs from .log, if there are logs
            logs = jobs.rstrip('json') + 'log'
            with open(logs, 'r') as f:
                time_queued = f.readline()[0:19] + 'Z'
                for _ in range(10):
                    line = f.readline()
                    match = version_matcher.search(line)
                    if match:
                        runner_version = match.group(1)
                        break

            # Save data to dict
            self.gathered_data[job['id']] = {
                'job_name': job['name'],
                'status': job['conclusion'],
                'queued_at': time_queued,
                'started_at': job['started_at'],
                'completed_at': job['completed_at'],
                'runner_label': job['labels'],
                'platform': platform
            }

            if job['runner_name']:
                self.gathered_data[job['id']].update(
                    {'runner_name': job['runner_name']}
                )
            if runner_version:
                self.gathered_data[job['id']].update(
                    {'runner_version': runner_version}
                )

    def store_gathered_data(self):
        if not os.path.isdir(self.output_dir):
            os.makedirs(self.output_dir)
        output_file = os.path.join(self.output_dir + '/gathered_data.json')
        with open(output_file, 'w') as f:
            json.dump(self.gathered_data, f, indent=2)


if __name__ == '__main__':
    result = GatherData()
    result.gather_data()
    result.store_gathered_data()
