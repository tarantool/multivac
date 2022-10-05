#!/usr/bin/env python
import argparse
import glob
import json
import os
from datetime import datetime

from gather_job_data import github_time_to_unix
from influxdb import influx_connector
from sensors.test_status import test_status_iter


class GatherTestData:
    def __init__(self, cli_args):
        self.workflow_run_jobs_dir = 'workflow_run_jobs'
        self.job_log_files = sorted(glob.glob(
            os.path.join(self.workflow_run_jobs_dir, '*[0-9].log')),
            reverse=True)
        self.output_dir = 'output'
        self.gathered_test_data = {}
        self.test_metadata = {}
        self.since_seconds = None

        since: str = cli_args.since
        if since and len(since) > 1:
            wrong_usage_message = 'Wrong \'--since\' option: got wrong {}. ' \
                                  'Usage: NN[d|h], example: 42d.'
            if since.endswith('d'):
                try:
                    self.since_seconds = int(since.rstrip('d')) * 86400
                except ValueError:
                    print(wrong_usage_message.format('number'))
            elif since.endswith('h'):
                try:
                    self.since_seconds = int(since.rstrip('h')) * 3600
                except ValueError:
                    print(wrong_usage_message.format('number'))
            else:
                print(wrong_usage_message.format('unit'))

    def collect_data(self):
        curr_time = datetime.timestamp(datetime.now())
        print('Starting to collect data...')
        for log in self.job_log_files:
            log_id = log.lstrip(self.workflow_run_jobs_dir + '/').rstrip('.log')
            self.gathered_test_data[log_id] = list()
            with open(log, 'r') as log_file:
                log_file_list = list(log_file)
            test_number = 0

            if self.since_seconds:
                time = github_time_to_unix(log_file_list[0].split(
                    ' ', 1)[0].split('.', 1)[0])
                if curr_time - time > self.since_seconds:
                    self.gathered_test_data.pop(log_id)
                    break
                    # List of log files is sorted by time: latest to earliest.
                    # So when we find the first log which is out of the selected
                    # time limit, all further logs are also out of limit.

            for test, conf, status in filter(lambda x: x[2] == "fail",
                                             test_status_iter(log_file_list)):
                test_record = {'name': test,
                               'configuration': conf or 'none',
                               'test_number': test_number}
                test_number += 1
                self.gathered_test_data[log_id].append(test_record)

            if len(self.gathered_test_data[log_id]):
                with open(f'{self.workflow_run_jobs_dir}/{log_id}.json',
                          'r') as f:
                    job_json = json.load(f)
                workflow_data = {
                    'job_name': job_json['name'],
                    'time': job_json['started_at'],
                    'commit_sha': job_json['head_sha']
                }
                self.test_metadata[log_id] = workflow_data
            else:
                self.gathered_test_data.pop(log_id)
        print('All test data collected successfully')

    def write_to_json(self):
        print('Writing data to a JSON file...')
        if not os.path.isdir(self.output_dir):
            os.makedirs(self.output_dir)
        output_test_file = os.path.join(self.output_dir + '/tests.json')
        with open(output_test_file, 'w') as jsonfile:
            json.dump(self.gathered_test_data, jsonfile, indent=2)
        print(f'Test data written to {output_test_file}.')

    def write_to_db(self):
        influx_test_bucket = os.environ['INFLUX_TEST_BUCKET']
        influx_org = os.environ['INFLUX_ORG']
        data_list = []
        print('Starting to write data to InfluxDB...')
        for job_id in list(self.gathered_test_data.keys()):
            if not self.gathered_test_data[job_id]:
                continue
            metadata = self.test_metadata[job_id]
            for test in self.gathered_test_data[job_id]:
                tags = {
                    'job_id': job_id,
                    'configuration': test['configuration'],
                    'job_name': metadata['job_name'],
                    'commit_sha': metadata['commit_sha'],
                    'test_number': test['test_number']
                }
                time = github_time_to_unix(metadata['time'])
                data = {
                    'measurement': test['name'],
                    'tags': tags,
                    'fields': {
                        'value': 1
                    },
                    'time': int(time * 1e9)

                }
                data_list.append(data)
                if len(data_list) == 1000:
                    write_api = influx_connector()
                    write_api.write(influx_test_bucket, influx_org, data_list)
                    print('Chunk of 1000 records put to InfluxDB')
                    data_list = []

        write_api = influx_connector()
        write_api.write(influx_test_bucket, influx_org, data_list)
        print(f'Chunk of {len(data_list)} records put to InfluxDB')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Gather data about GitHub workflows')
    parser.add_argument(
        '--format', choices=['json', 'influxdb'],
        help='write gathered data as a json file or to an InfluxDB database'
    )
    parser.add_argument(
        '--since', type=str,
        help='Only take logs since... Usage: --since NN[d|h], '
             'where NN - integer, d for days, h for hours.'
             'Example: \'--since 2d\' option to process only jobs which ran in '
             'the last two days, skip the rest. \'--since 5h \' is option to '
             'process only the last 5 hours.'
    )
    cli_args = parser.parse_args()

    result = GatherTestData(cli_args)
    result.collect_data()
    if cli_args.format == 'json':
        result.write_to_json()
    if cli_args.format == 'influxdb':
        result.write_to_db()
