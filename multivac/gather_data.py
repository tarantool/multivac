#!/usr/bin/env python
import argparse
import csv
import glob
import json
import os
import re
import sys

from sensors.test_status import test_status_iter
from sensors.failures import specific_failures, generic_failures, \
    compile_failure_specs
from datetime import datetime
from influxdb import influx_connector

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_DIR)

COLOR_RE = re.compile('\033' + r'\[\d(?:;\d\d)?m')
COMPILER_RE = re.compile(r'C compiler identification is '
                         r'(\S* \d*.\d*.\d*)')

# According to distrowatch.com and repology.org/project/glibc/versions
LIBC_VERSIONS = {
    'centos_7': '2.17',
    'centos_8': '2.28',
    'debian_9': '2.24',
    'debian_10': '2.28',
    'debian_11': '2.31',
    'fedora_34': '2.33',
    'fedora_35': '2.34',
    'fedora_36': '2.35',
    'freebsd_12': 'freebsd_12',
    'freebsd_13': 'freebsd_13',
    'opensuse_15_1': '2.26',
    'opensuse_15_2': '2.26',
    'osx_11': 'osx_11',
    'osx_12': 'osx_12',
    'redos_7_3': '2.28',
    'ubuntu_16_04': '2.24',
    'ubuntu_18_04': '2.27',
    'ubuntu_20_04': '2.31',
    'ubuntu_22_04': '2.35',
    'unknown': 'unknown',
}


def decolor(data):
    return COLOR_RE.sub('', data)


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


def detect_error(logs: str, failure_specs: list) -> (str, str):
    for number, line in enumerate(reverse_readline(logs)):
        # check if the line matches one of regular expressions:
        for failure_type in failure_specs:
            for regexp in failure_type['re_compiled']:
                if regexp.match(line):
                    return failure_type['type'], line
    return 'unknown_failure', None


def github_time_to_unix(time: str) -> float:
    # Convert string to a datetime object, then convert it to unix
    # time (seconds), then to timestamp in nanoseconds.
    time_to_datetime = datetime.fromisoformat(
        f"{time.rstrip('Z')}+00:00")
    time_to_unix = datetime.timestamp(time_to_datetime)
    return time_to_unix


# https://github.com/tarantool/tarantool/tree/master/.github/workflows
OS_MATCHER = re.compile(r"[a-z]+_[0-9]+(_[0-9]+)?")
FREEBSD_MATCHER = re.compile(r"freebsd-[0-9]{2}")
# Jobs running right on the runner, not in a container
DEFAULT_RUNNERS_MATCHER = re.compile(
    r"(release|debug|static|conver|cover|"
    r"default_gcc|memtx|integration|out_of_source).*")
DEFAULT_RUNNER_OS = 'ubuntu_20_04'
NUM_MATCHER = re.compile(r".*/(\d*)\.json")


class GatherData:
    def __init__(self, cli_args):
        self.repo_path = cli_args.repo_path
        self.workflow_run_jobs_dir = f'{self.repo_path}/workflow_run_jobs'
        self.workflow_runs_dir = f'{self.repo_path}/workflow_runs'
        self.output_dir = 'output'
        self.gathered_data = dict()
        self.latest_n: int = cli_args.latest
        self.watch_failure = args.watch_failure
        self.tests_flag = cli_args.tests
        self.since_seconds = None

        if args.format == 'influxdb':
            self.influx_org = os.environ['INFLUX_ORG']

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

    @staticmethod
    def get_test_data(log_file) -> list:
        """To use this function, you should open log file first and put lines
        to a variable as a list. This function will call the `test_status`
        sensor to collect data about failed tests: test name and configuration.
        All attempts numbered for unicalization in InfluxDB.
        Returns a list of dictionaries. Works only if option `-t` set."""

        if not args.tests:
            return []

        test_attempt = 1
        tests_data = []

        for test_name, conf, status in filter(lambda x: x[2] == "fail",
                                              test_status_iter(log_file)):
            #  Check if the test retried to set correct attempt number
            for test in tests_data[::-1]:
                if test['name'] == test_name and test['conf'] == conf:
                    test_attempt = test['test_attempt'] + 1
                    break

            # Detect type of the test
            test_type_name = test_name.split('/')[0]
            test_subtype = 'None'
            if test_type_name.endswith('tap'):
                test_type = 'tap'
            elif test_type_name.endswith('luatest'):
                test_type = 'luatest'
            else:
                test_type = 'diff'
                if test_type_name.endswith('py'):
                    test_subtype = 'python'
                if 'sql' in test_type_name:
                    test_subtype = 'sql'
            test_record = {'name': test_name,
                           'conf': conf or 'none',
                           'test_type': test_type,
                           'test_subtype': test_subtype,
                           'test_attempt': test_attempt}
            test_attempt = 1
            tests_data.append(test_record)

        return tests_data

    @staticmethod
    def get_release_or_debug(log_file):
        for line in log_file:
            if '| Target:' in line and \
                    line.endswith('Debug\n'):
                return 'True'
        return 'False'

    @staticmethod
    def detect_os_version(job_name):

        os_match = OS_MATCHER.search(job_name)
        if os_match:
            return os_match.group()
        freebsd_match = FREEBSD_MATCHER.search(job_name)
        if freebsd_match:
            freebsd_version = freebsd_match.group().split('-')[1]
            return f'freebsd_{freebsd_version}'
        if DEFAULT_RUNNERS_MATCHER.match(job_name):
            return DEFAULT_RUNNER_OS
        return 'unknown'

    @staticmethod
    def get_runner_version(log_file):
        version_matcher = re.compile(r"Current runner version: "
                                     r"'(\d*.\d*.\d*)'")
        freebsd_version_matcher = re.compile(r"Runner Version: "
                                             r"(\d*.\d*.\S*)")
        for line in log_file:
            match = version_matcher.search(line)
            if match:
                runner_version = match.group(1)
                return runner_version
            else:
                freebsd_match = freebsd_version_matcher.search(line)
                if freebsd_match:
                    runner_version = freebsd_match.group(1)
                    return runner_version
        return "unknown_runner_version"

    @staticmethod
    def get_compiler_version(log_file):
        compiler = 'undefined_compiler'
        for line in log_file:
            compiler_match = COMPILER_RE.search(line)
            if compiler_match:
                compiler = compiler_match.group(1)
        return compiler

    def gather_data(self):
        # workflow_run_jobs/*[0-9].json
        workflow_files = glob.glob(
            os.path.join(self.workflow_run_jobs_dir, '*[0-9].json'))

        def sorter(filename):
            return int(NUM_MATCHER.search(filename).group(1))

        job_json_files = sorted(workflow_files, reverse=True, key=sorter)
        if self.latest_n:
            job_json_files = job_json_files[:self.latest_n]

        curr_time = datetime.timestamp(datetime.now())
        for job_json in job_json_files:

            # Load info about jobs from job API JSON file
            with open(job_json, 'r') as f:
                job = json.load(f)

            # Don't process skipped and canceled job logs
            if job['conclusion'] in ['skipped', 'cancelled']:
                continue

            # We have files sorted descending, so when we meet the first job
            # later than `since` argument, we know that all the following are
            # later too
            if self.since_seconds:
                job_started = github_time_to_unix(job['started_at'])
                if curr_time - job_started > self.since_seconds:
                    break

            if 'aarch64' in job['name']:
                platform = 'aarch64'
            else:
                platform = 'amd64'

            job_id = job['id']

            if 'gc64' in job['name'] or platform == 'aarch64':
                gc64 = 'True'
            else:
                gc64 = 'False'

            # Take data from GitHub Workflow runs API
            run_file_path = f"{self.workflow_runs_dir}/{job['run_id']}.json"
            try:
                with open(run_file_path) as run_file:
                    run = json.load(run_file)
                    branch = run['head_branch']
            except FileNotFoundError:
                print(f"Job {job_id}: no runs found, can't open "
                      f"{run_file_path}")
            except ValueError:
                print(f"Job {job_id}: can't decode JSON in {run_file_path}")

            # Load info about jobs and tests from .log, if there are logs
            logs = f'{self.workflow_run_jobs_dir}/{job_id}.log'
            job_failure_type = None
            try:
                with open(logs, 'r') as log_file:
                    log_file_as_list = list(map(decolor, log_file))

                    time_queued = log_file_as_list[0][0:19] + 'Z'
                    test_data = self.get_test_data(log_file_as_list)
                    debug = self.get_release_or_debug(log_file_as_list)
                    runner_version = self.get_runner_version(log_file_as_list)
                    compiler = self.get_compiler_version(log_file_as_list)
            except FileNotFoundError:
                print(f'no logs for job {job_id}')

            if job['conclusion'] == 'failure':
                # Detect failure type, collect total failures of certain type
                job_failure_type, failure_line = detect_error(logs,
                                                              specific_failures)
                if job_failure_type == 'unknown_failure':
                    job_failure_type, failure_line = detect_error(logs,
                                                                  generic_failures)
                if job_failure_type == self.watch_failure:
                    print(
                        f'{job_id}  {job["name"]}\t'
                        f' https://github.com/tarantool/tarantool/runs/'
                        f'{job_id}?check_suite_focus=true\n'
                        f'\t\t\t{failure_line}')
                results[job_failure_type] += 1
                results['total'] += 1

            # Get OS name and version
            os_version = self.detect_os_version(job['name'])

            # Save data to dict
            gathered_job_data = {
                'job_id': job_id,
                'workflow_run_id': job['run_id'],
                'job_name': job['name'],
                'os_version': os_version,
                'branch': branch,
                'commit_sha': job['head_sha'],
                'conclusion': job['conclusion'],
                'queued_at': time_queued,
                'started_at': job['started_at'],
                'completed_at': job['completed_at'],
                'platform': platform,
                'runner_label': job['labels'],
                'gc64': gc64,
                'debug': debug,
                'html_url': job['html_url'],
                'runner_name': job['runner_name'] or "unknown",
                'runner_version': runner_version or "unknown",
                'failure_type': job_failure_type or "not_failed",
                'compiler_version': compiler,
                'libc_version': LIBC_VERSIONS[os_version] or 'failed_to_detect',
            }

            if test_data:
                gathered_job_data.update(
                    {'failed_tests': test_data}
                )
            self.gathered_data[job_id] = gathered_job_data

    def put_to_db_job(self):
        influx_job_bucket = os.environ['INFLUX_JOB_BUCKET']
        influx_org = os.environ['INFLUX_ORG']
        data_list = list()

        print('Writing job data to InfluxDB...')
        for job in list(self.gathered_data.keys()):
            curr_job = self.gathered_data[job]

            measurement = curr_job.get('failure_type') or curr_job['conclusion']

            time_job_queued = github_time_to_unix(curr_job['queued_at'])

            tags = {
                'job_id': curr_job['job_id'],
                'job_name': curr_job['job_name'],
                'workflow_run_id': curr_job['workflow_run_id'],
                'branch': curr_job['branch'],
                'commit_sha': curr_job['commit_sha'],
                'platform': curr_job['platform'],
                'runner_label': curr_job['runner_label'],
                'conclusion': curr_job['conclusion'],
                'gc64': curr_job['gc64'],
                'runner_version': curr_job['runner_version'],
                'runner_name': curr_job['runner_name'],
                'repository': self.repo_path,
            }

            fields = {
                'value': 1
            }

            data = {
                'measurement': measurement,
                'tags': tags,
                'fields': fields,
                # We have `time_job_queued` in seconds, but InfluxDB precision
                # is nanoseconds, convert
                'time': int(time_job_queued * 1e9)
            }
            data_list.append(data)
            if len(data_list) == 1000:
                write_api = influx_connector()
                write_api.write(influx_job_bucket, influx_org, data_list)
                print('Chunk of 1000 records put to InfluxDB')
                data_list = []

        write_api = influx_connector()
        write_api.write(influx_job_bucket, influx_org, data_list)
        print(f'Chunk of {len(data_list)} records put to InfluxDB')

    def put_to_db_test(self):
        influx_test_bucket = os.environ['INFLUX_TEST_BUCKET']
        influx_org = os.environ['INFLUX_ORG']
        data_list = []
        print('Writing test data to InfluxDB...')
        for job_id in filter(
                lambda x: 'failed_tests' in list(self.gathered_data[x].keys()),
                list(self.gathered_data.keys())):
            job_info = self.gathered_data[job_id]
            for test in job_info.get('failed_tests'):
                tags = {
                    'configuration': test['conf'],
                    'test_type': test['test_type'],
                    'test_subtype': test['test_subtype'],
                    'debug': job_info['debug'],
                    'job_id': job_id,
                    'job_name': job_info['job_name'],
                    'commit_sha': job_info['commit_sha'],
                    'test_attempt': test['test_attempt'],
                    'branch': job_info['branch'],
                    'architecture': job_info['platform'],
                    'gc64': job_info['gc64'],
                    'os_version': job_info['os_version'],
                    'compiler_version': job_info['compiler_version'],
                    'libc_version': job_info['libc_version'],
                    'repository': self.repo_path,
                }
                time = github_time_to_unix(
                    self.gathered_data[job_id]['started_at'])
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

    def put_data_for_table_to_db(self):
        influx_test_bucket = os.environ['INFLUX_TABLE_BUCKET']
        influx_org = os.environ['INFLUX_ORG']
        data_list = []
        base_url = f'github.com/{self.repo_path}'
        s3_url = f'multivac.hb.bizmrg.com/{self.repo_path}'
        print('Writing data for tests table to InfluxDB...')
        for job_id in filter(
                lambda x: 'failed_tests' in list(self.gathered_data[x].keys()),
                list(self.gathered_data.keys())):
            job_info = self.gathered_data[job_id]
            for test in job_info.get('failed_tests'):
                tags = {
                    'configuration': test['conf'],
                    'test_type': test['test_type'],
                    'test_subtype': test['test_subtype'],
                    'debug': job_info['debug'],
                    'job_id': job_id,
                    'job_name': job_info['job_name'],
                    'commit_sha': job_info['commit_sha'],
                    'test_attempt': test['test_attempt'],
                    'branch': job_info['branch'],
                    'architecture': job_info['platform'],
                    'gc64': job_info['gc64'],
                    'os_version': job_info['os_version'],
                    'repository': self.repo_path,
                    'job_link': job_info['html_url'].lstrip('https://'),
                    'commit_link': f"{base_url}/commit/{job_info['commit_sha']}",
                    'job_json': f"{s3_url}/workflow_run_jobs/{job_id}.json",
                    'job_log': f"{s3_url}/workflow_run_jobs/{job_id}.log",
                    'workflow_run_json': f"{s3_url}/workflow_runs/"
                                         f"{job_info['workflow_run_id']}.json"
                }
                time = github_time_to_unix(
                    self.gathered_data[job_id]['started_at'])
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
            'workflow_run_id',
            'job_name',
            'branch',
            'commit_sha',
            'conclusion',
            'queued_at',
            'started_at',
            'completed_at',
            'platform',
            'runner_label',
            'runner_name',
            'runner_version',
            'failure_type',
        ]
        with open(output_file, 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for job_data in self.gathered_data.values():
                writer.writerow(job_data)

    def print_failure_stats(self):
        if args.failure_stats:
            sorted_results = list(
                sorted(results.items(), key=lambda x: x[1], reverse=True))
            for (type, count) in sorted_results:
                if count > 0:
                    print(type, count)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Gather data about GitHub workflows')
    parser.add_argument(
        '--format', choices=['json', 'csv', 'influxdb'],
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
    parser.add_argument(
        '--since', type=str,
        help='Only take logs since... Usage: --since NN[d|h], '
             'where NN - integer, d for days, h for hours.'
             'Example: \'--since 2d\' option to process only jobs which ran in '
             'the last two days, skip the rest. \'--since 5h \' is option to '
             'process only the last 5 hours.'
    )
    parser.add_argument('--repo-path', type=str, default='tarantool/tarantool',
                        help='repository (without owner)')
    parser.add_argument('--tests', '-t', action='store_true')

    args = parser.parse_args()

    # compile regular expressions
    compile_failure_specs(specific_failures)
    compile_failure_specs(generic_failures)

    results = {failure_type['type']: 0 for failure_type in generic_failures}
    results.update(
        {failure_type['type']: 0 for failure_type in specific_failures})
    results.update({'unknown_failure': 0})
    results.update({'total': 0})

    result = GatherData(args)
    result.gather_data()
    if args.format == 'json':
        result.write_json()
    if args.format == 'csv':
        result.write_csv()
    if args.format == 'influxdb':
        result.put_to_db_job()
        if args.tests:
            result.put_to_db_test()
            result.put_data_for_table_to_db()
    if args.failure_stats:
        result.print_failure_stats()
