#!/usr/bin/env python

import os
import re
import sys
import argparse
import requests
import json
import zipfile
import datetime


parser = argparse.ArgumentParser(description='Fetch GitHub Actions logs')
parser.add_argument('--branch', type=str, help='branch (all if omitted)')
parser.add_argument('repo_path', type=str, help='owner/repository')
args = parser.parse_args()
if '/' not in args.repo_path:
    raise ValueError('repo_path must be in the form owner/repository')
owner, repo = args.repo_path.split('/', 1)
branch = args.branch

token_file = 'token.txt'
if not os.path.exists(token_file):
    raise RuntimeError('{file} is not exists'.format(file=token_file))
if not os.path.isfile(token_file):
    raise RuntimeError('{file} is not a regular file'.format(file=token_file))
with open(token_file, 'r') as f:
    token = f.read().strip()


session = requests.Session()
session.headers.update({
    'Accept': 'application/vnd.github.v3+json',
    'Authorization': 'token ' + token,
})
debug_log_fh = open('debug.log', 'a')


def timestamp():
    return datetime.datetime.now().isoformat()


def http_get(url, params=None):
    """HTTP GET with logging to debug.log and raise on a bad HTTP status."""
    print('{} HTTP GET: {}'.format(timestamp(), url), file=debug_log_fh)

    r = session.get(url, params=params)

    print('{} Response headers:\n{}'.format(timestamp(),
          json.dumps(dict(r.headers), indent=2)), file=debug_log_fh)
    if r.headers['content-type'] == 'application/zip':
        response_text = '[Don\'t log application/zip response.]'
    elif r.headers['content-type'].startswith('application/json'):
        response_text = json.dumps(r.json(), indent=2)
    else:
        response_text = r.text
    print('{} Response:\n{}'.format(timestamp(), response_text),
          file=debug_log_fh)

    r.raise_for_status()

    return r


class Run:
    def __init__(self, data):
        self._data = data

    @property
    def id(self):
        return str(self._data['id'])

    @property
    def status(self):
        return self._data['status']

    @property
    def conclusion(self):
        return self._data['conclusion']

    @property
    def logs_url(self):
        return self._data['logs_url']

    @property
    def meta_path(self):
        return os.path.join('runs', self.id + '.json')

    @property
    def logs_archive_path(self):
        return os.path.join('runs', self.id + '.logs.zip')

    @property
    def log_path(self):
        return os.path.join('runs', self.id + '.log')

    @property
    def is_stored(self):
        return os.path.isfile(self.meta_path) and      \
            os.path.isfile(self.logs_archive_path) and \
            os.path.isfile(self.log_path)

    def _log(self, *args):
        print(*args, file=sys.stderr)

    def store(self):
        self._log('Write {}'.format(self.meta_path))
        with open(self.meta_path, 'w') as f:
            json.dump(self._data, f, indent=2)

        self._log('Download {}'.format(self.logs_url))
        r = http_get(self.logs_url)
        self._log('Write {}'.format(self.logs_archive_path))
        with open(self.logs_archive_path, 'wb') as f:
            f.write(r.content)

        # TODO: How to append logs in a correct order?
        with zipfile.ZipFile(self.logs_archive_path, 'r') as z:
            for entry in zipfile.Path(z).iterdir():
                if not entry.is_file():
                    continue
                self._log('Append {} to {}'.format(entry.name, self.log_path))
                with entry.open('rb') as f:
                    data = f.read()
                with open(self.log_path, 'ab') as f:
                    f.write(data)


def status(pages, pages_all, run_count, run_total, url):
    print('[pages {:2} / {:2}] [runs {:4} / {:4}] Download {}'.format(
          pages, pages_all, run_count, run_total, url), file=sys.stderr)


def runs():
    params = {
        # 100 is the maximum.
        'per_page': 100,
        'branch': branch,
    }
    url = 'https://api.github.com/repos/{}/{}/actions/runs'.format(owner, repo)
    status(0, '??', 0, '??', url)
    r = http_get(url, params=params)

    run_count = 0
    for data in r.json()['workflow_runs']:
        run_count += 1
        yield Run(data)

    pages_all_str = '??'
    last_url = r.links['last']['url']
    pages_all_match = re.search(r'[^_]page=(\d+)', last_url)
    if pages_all_match:
        pages_all_str = pages_all_match.group(1)

    pages = 1
    while 'next' in r.links:
        next_url = r.links['next']['url']
        run_total = r.json()['total_count']
        status(pages, pages_all_str, run_count, run_total, next_url)
        r = http_get(next_url, params=params)
        for data in r.json()['workflow_runs']:
            run_count += 1
            yield Run(data)
        pages += 1


if not os.path.isdir('runs'):
    os.makedirs('runs')

for run in runs():
    if run.conclusion is None:
        print('Skip {}: {}'.format(run.id, run.status))
        continue
    if run.is_stored:
        print('Skip {}: already stored'.format(run.id))
        continue
    run.store()

debug_log_fh.close()
