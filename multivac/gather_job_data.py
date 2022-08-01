#!/usr/bin/env python

import glob
import json
import os
import re
import sys
from pprint import pprint

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_DIR)

version_matcher = re.compile(r"Current runner version: "
                             r"'(\d*.\d*.\d*)'")

job_was_newer_picked_up = re.compile(r'.*Job is about to start running on the runner.*')
database_error = re.compile(r'.*tarantool.error.DatabaseError.*')
yum_repo_error = re.compile(r'.*- Status code: (404|503) for.*')
pytest_failed = re.compile(r'.*\* fail: \d+.*')
pytest_failed_2 = re.compile(r'.*===== \d+ tests failed:.*')
internal_test_run = re.compile(r'.*\[Internal test-run error].*')
luatest_failed = re.compile(r'.*Test failed!.*')
luatest_failed_2 = re.compile(r'.*Tests with errors:.*')
test_hang = re.compile(r'.*Test hung!.*')
package_repo_error = re.compile(r'.*Err:\d+ https*://.* InRelease.*')
package_repo_error_2 = re.compile(r'.*Cannot retrieve metalink for repository: .*')
package_building_error = re.compile(r'.*make\[3]: \*\*\* .*c.o] Error 1.*')
curl_error = re.compile(r'.*curl: \(22\) The requested URL returned error:.*')
module_error = re.compile(r'.*Captured stderr:.*')
module_error_2 = re.compile(r'.*mFailed tests:.*')
python_not_found = re.compile(r'.*python3.\d+: not found.*')
vshard_error = re.compile(r'.*E> Error.*')
jepsen_error = re.compile(r'.*make\[\d+]: \*\*\* \[run-jepsen] Error.*')
dir_not_empty = re.compile(r'.*rm: cannot remove \'.*\': Directory not empty.*')
git_repo_access_error = re.compile(r'.*fatal: unable to access \'https://github.com.*')
git_unsafe_error = re.compile(r'.*fatal: unsafe repository.*')
git_submodule_error = re.compile(r'.*fatal: Needed a single revision.*')
go_tarantool_error = re.compile(r'.*FAIL\s+github.com/tarantool/go-tarantool.*')
ctest_error = re.compile(r'.*The following tests FAILED:.*')
luajit_error = re.compile(r'.*fatal error, exiting the event loop.*')
luajit_error_2 = re.compile(r'.*PANIC: unprotected error.*')
lto_error = re.compile(r'.*lto-wrapper: fatal error:.*')
checkpatch = re.compile(r'.*total: [1-9][\d+]* errors, \d+ lines checked.*')
telegram_bs_error = re.compile(r'.*SyntaxError: EOL while scanning string literal.*')
autorefconf_error = re.compile(r'.*exec: autoreconf: not found.*')
hashicorp_error = re.compile(r'.*curl: \(60\) SSL certificate problem:.*')
tap_test_failed = re.compile(r'.*failed subtest: \d+.*')
could_not_find_readline = re.compile(r'.*Could NOT find Readline.*')
linker_error = re.compile(r'.*clang-14: error: linker.*')


# As far as the failure occurs at the end of the log, let's
# start to parse the file from the end to speed up the process
def reverse_readline(filename, buf_size=8192):
    """A generator that returns the lines of a file in reverse order"""
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


results = {
    'stuck': 0,
    'database error': 0,
    'pytest failed': 0,
    'luatest failed': 0,
    'test hang': 0,
    'tap test failed': 0,
    'apt error': 0,
    'error was not detected': 0,
    'package building error': 0,
    'curl error': 0,
    'hashicorp repo error': 0,
    'module error': 0,
    'python not found': 0,
    'vshard error': 0,
    'jepsen error': 0,
    'dir not empty': 0,
    'git repo access error': 0,
    'git submodule error': 0,
    'git unsafe error': 0,
    'go-tarantool error': 0,
    'yum repo error': 0,
    'ctest error': 0,
    'internal test run': 0,
    'luajit error': 0,
    'lto error': 0,
    'checkpatch': 0,
    'telegram error': 0,
    'autorefconf error': 0,
    'could not find readline': 0,
    'linker error': 0,
}


def detect_error(jobs, logs):
    for number, line in enumerate(reverse_readline(logs)):
        if number == 0:
            if job_was_newer_picked_up.match(line):
                # print(jobs, 'stuck')
                results['stuck'] += 1
                break
        if database_error.match(line):
            # print(jobs, 'database error')
            results['database error'] += 1
            break
        if pytest_failed.match(line) or pytest_failed_2.match(line):
            results['pytest failed'] += 1
            # print(jobs, 'pytest failed')
            break
        if luatest_failed.match(line):
            results['luatest failed'] += 1
            # print(jobs, 'luatest failed')
            break
        if luatest_failed_2.match(line):
            results['luatest failed'] += 1
            # print(jobs, 'luatest failed')
            break
        if test_hang.match(line):
            results['test hang'] += 1
            # print(jobs, 'test hang')
            break
        if package_repo_error.match(line):
            results['apt error'] += 1
            print(jobs, 'apt error')
            break
        if package_building_error.match(line):
            results['package building error'] += 1
            # print(jobs, 'package building error')
            break
        if curl_error.match(line):
            results['curl error'] += 1
            # print(jobs, 'curl error')
            break
        if module_error.match(line):
            results['module error'] += 1
            # print(jobs, 'module error')
            break
        if module_error_2.match(line):
            results['module error'] += 1
            # print(jobs, 'module error 2')
            break
        if python_not_found.match(line):
            results['python not found'] += 1
            # print(jobs, 'python not found')
            break
        if vshard_error.match(line):
            results['vshard error'] += 1
            # print(jobs, 'vshard error')
            break
        if jepsen_error.match(line):
            results['jepsen error'] += 1
            # print(jobs, 'japsen error')
            break
        if dir_not_empty.match(line):
            results['dir not empty'] += 1
            # print(jobs, 'dir not empty')
            break
        if git_repo_access_error.match(line):
            results['git repo access error'] += 1
            # print(jobs, 'git repo access error')
            break
        if git_submodule_error.match(line):
            results['git submodule error'] += 1
            # print(jobs, 'git submodule error')
            break
        if git_unsafe_error.match(line):
            results['git unsafe error'] += 1
            # print(jobs, 'git unsafe error')
            break
        if go_tarantool_error.match(line):
            results['go-tarantool error'] += 1
            # print(jobs, 'go-tarantool error')
            break
        if package_repo_error_2.match(line):
            results['apt error'] += 1
            # print(jobs, 'apt error')
            break
        if yum_repo_error.match(line):
            results['yum repo error'] += 1
            # print(jobs, 'yum repo error')
            break
        if ctest_error.match(line):
            results['ctest error'] += 1
            # print(jobs, 'ctest error')
            break
        if internal_test_run.match(line):
            results['internal test run'] += 1
            # print(jobs, 'internal test run')
            break
        if luajit_error.match(line):
            results['luajit error'] += 1
            # print(jobs, 'luajit error')
            break
        if luajit_error_2.match(line):
            results['luajit error'] += 1
            # print(jobs, 'luajit error')
            break
        if lto_error.match(line):
            results['lto error'] += 1
            # print(jobs, 'lto error')
            break
        if checkpatch.match(line):
            results['checkpatch'] += 1
            # print(jobs, 'checkpatch')
            break
        if telegram_bs_error.match(line):
            results['telegram error'] += 1
            # print(jobs, 'telegram error')
            break
        if autorefconf_error.match(line):
            results['autorefconf error'] += 1
            # print(jobs, 'autorefconf error')
            break
        if hashicorp_error.match(line):
            results['hashicorp repo error'] += 1
            # print(jobs, 'hashicorp repo error')
            break
        if tap_test_failed.match(line):
            results['tap test failed'] += 1
            # print(jobs, 'tap test failed')
            break
        if could_not_find_readline.match(line):
            results['could not find readline'] += 1
            print(jobs, 'could not find readline')
            break
        if could_not_find_readline.match(line):
            results['linker error'] += 1
            print(jobs, 'linker error')
            break
    else:
        results['error was not detected'] += 1
        print(jobs, 'error was not detected')
        # pass


class GatherData:
    def __init__(self):
        self.workflow_run_jobs_dir = 'workflow_run_jobs'
        self.output_dir = 'gathered_data'
        self.gathered_data = dict()

    def gather_data(self):
        for jobs in [f for f in glob.glob(os.path.join(self.workflow_run_jobs_dir,
                                          '*.json')) if '.cache.' not in f]:
            runner_version = None
            # Load info about jobs from .json
            with open(jobs, 'r') as f:
                job = json.load(f)

            # if job['conclusion'] != 'failure':
            #     os.remove(jobs)
            if 'aarch64' in job['name']:
                platform = 'aarch64'
            else:
                platform = 'amd64'

            # Load info about jobs from .log, if there are logs
            logs = jobs.rstrip('json') + 'log'
            try:
                with open(logs, 'r') as f:
                    time_queued = f.readline()[0:19] + 'Z'
                    for _ in range(10):
                        line = f.readline()
                        match = version_matcher.search(line)
                        if match:
                            runner_version = match.group(1)
                            break
                    if job['conclusion'] == 'failure':
                        detect_error(jobs, logs)
            except FileNotFoundError:
                continue
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
    pprint(results)
