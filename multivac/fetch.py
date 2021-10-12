#!/usr/bin/env python

import os
import re
import sys
import argparse
import requests
import json
import datetime


parser = argparse.ArgumentParser(description='Download GitHub Actions logs')
parser.add_argument('--branch', type=str,
                    help='branch (all if omitted)')
parser.add_argument('--nologs', action='store_true',
                    help="Don't download logs")
parser.add_argument('--nostop', action='store_true',
                    help="Continue till end or rate limit")
parser.add_argument('repo_path', type=str,
                    help='owner/repository')
args = parser.parse_args()
if '/' not in args.repo_path:
    raise ValueError('repo_path must be in the form owner/repository')
args.owner, args.repo = args.repo_path.split('/', 1)

token_file = 'token.txt'
if not os.path.exists(token_file):
    raise RuntimeError('{file} is not exists'.format(file=token_file))
if not os.path.isfile(token_file):
    raise RuntimeError('{file} is not a regular file'.format(file=token_file))
with open(token_file, 'r') as f:
    token = f.read().strip()


pid = os.getpid()
startup_time = datetime.datetime.now(datetime.timezone.utc)
session = requests.Session()
session.headers.update({
    'Accept': 'application/vnd.github.v3+json',
    'Authorization': 'token ' + token,
})
debug_log_fh = open('debug.log', 'a')
workflow_runs_dir = 'workflow_runs'
workflow_run_jobs_dir = 'workflow_run_jobs'


def timestamp():
    """ Format current time according to ISO 8601 standard. """
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def debug(fmt, *args):
    print('[{}] {} {}'.format(pid, timestamp(), fmt.format(*args)),
          file=debug_log_fh)


def info(fmt, *args):
    debug(fmt, *args)
    print(fmt.format(*args), file=sys.stderr)


def http_get(url, params=None):
    """ HTTP GET with logging to debug.log.

        Raise on a bad HTTP status.
    """
    debug('HTTP GET: {}', url)

    r = session.get(url, params=params)

    debug('Response HTTP status: {}', r.status_code)
    debug('Response headers:\n{}', json.dumps(dict(r.headers), indent=2))
    content_type = r.headers['content-type']
    if 'content-type'.startswith('application/json'):
        response_text = json.dumps(r.json(), indent=2)
    elif content_type == 'application/zip' or \
            content_type.startswith('text/plain'):
        fmt = '[Don\'t log {} response.]'
        response_text = fmt.format(content_type)
    else:
        fmt = '[Don\'t log response with unknown Content-Type: {}]'
        response_text = fmt.format(content_type)
    debug('Response:\n{}', response_text)

    r.raise_for_status()

    return r


class WorkflowRun:
    def __init__(self, data=None, filepath=None):
        if data:
            self._data = data
        elif filepath:
            self.load(filepath)
        else:
            raise RuntimeError(
                'Neither data nor filepath argument is provided')

    @property
    def id(self):
        return str(self._data['id'])

    @property
    def status(self):
        """ completed, in_progress, pending, queued, requested, waiting.

            https://docs.github.com/en/graphql/reference/enums#checkstatusstate
        """
        return self._data['status']

    @property
    def conclusion(self):
        """ action_required, cancelled, failure, neutral, skipped,
            stale, startup_failure, success, timed_out or None.

            https://docs.github.com/en/graphql/reference/enums#checkconclusionstate
        """
        return self._data['conclusion']

    @property
    def meta(self):
        return self._data

    @property
    def meta_path(self):
        return os.path.join(workflow_runs_dir, self.id + '.json')

    @property
    def created_at(self):
        created_at_str = self._data['created_at'].rstrip('Z') + '+00:00'
        return datetime.datetime.fromisoformat(created_at_str)

    @property
    def updated_at(self):
        updated_at_str = self._data['updated_at'].rstrip('Z') + '+00:00'
        return datetime.datetime.fromisoformat(updated_at_str)

    @property
    def is_stored(self):
        """ Whether the workflow run metainfo is stored.

            It does not check whether all jobs and logs are stored
            as well.
        """
        return os.path.isfile(self.meta_path)

    def store(self):
        info('Write {}', self.meta_path)
        with open(self.meta_path, 'w') as f:
            json.dump(self._data, f, indent=2)

    def load(self, filepath):
        info('Read {}', filepath)
        with open(filepath, 'r') as f:
            self._data = json.load(f)


class WorkflowRunJob:
    def __init__(self, data):
        self._data = data
        self.log = None

    @property
    def id(self):
        return str(self._data['id'])

    @property
    def status(self):
        """ completed, in_progress, pending, queued, requested, waiting.

            https://docs.github.com/en/graphql/reference/enums#checkstatusstate
        """
        return self._data['status']

    @property
    def conclusion(self):
        """ action_required, cancelled, failure, neutral, skipped,
            stale, startup_failure, success, timed_out or None.

            https://docs.github.com/en/graphql/reference/enums#checkconclusionstate
        """
        return self._data['conclusion']

    @property
    def meta(self):
        return self._data

    @property
    def meta_path(self):
        return os.path.join(workflow_run_jobs_dir, self.id + '.json')

    @property
    def log_path(self):
        return os.path.join(workflow_run_jobs_dir, self.id + '.log')

    @property
    def log_url(self):
        url_fmt = 'https://api.github.com/repos/{}/{}/actions/jobs/{}/logs'
        return url_fmt.format(args.owner, args.repo, self.id)

    @property
    def is_stored(self):
        if not os.path.isfile(self.meta_path):
            return False
        if not args.nologs and not os.path.isfile(self.log_path):
            return False
        return True

    def download_log(self):
        url = self.log_url
        info('Download {}', url)
        r = http_get(url)
        self.log = r.content

    def store(self):
        info('Write {}', self.meta_path)
        with open(self.meta_path, 'w') as f:
            json.dump(self._data, f, indent=2)

        if self.log:
            info('Write {}', self.log_path)
            with open(self.log_path, 'wb') as f:
                f.write(self.log)


def workflow_runs_download_info(pages, pages_all, obj_count, obj_total, url,
                                params):
    per_page = params['per_page']
    branch = params['branch']

    # GitHub does not allow to download workflow runs beyond first
    # 1000, when branch is passed. It seems, it is the limitation
    # for search requests.
    if branch is not None:
        if isinstance(pages_all, int):
            pages_all = min(pages_all, 1000 // per_page)
        if isinstance(obj_total, int):
            obj_total = min(obj_total, 1000)

    info('[pages {:2} / {:2}] [objects {:4} / {:4}] Download {}'.format(
          pages, pages_all, obj_count, obj_total, url))


def workflow_runs_page_info(response):
    """ Show information about workflow run search response:
        the list of workflow run IDs.
    """
    ids = []
    for data in response.json()['workflow_runs']:
        ids.append(data['id'])
    info('Workflow run IDs on this page: {}', ids)


def download_workflow_runs(branch=None):
    """ Download and yield workflow runs metainformation from
        fresh ones toward older ones.
    """
    params = {
        # 100 is the maximum.
        'per_page': 100,
        'branch': branch,
    }
    url = 'https://api.github.com/repos/{}/{}/actions/runs'.format(
        args.owner, args.repo)
    workflow_runs_download_info(0, '??', 0, '??', url, params)
    r = http_get(url, params=params)
    workflow_runs_page_info(r)

    run_count = 0
    for data in r.json()['workflow_runs']:
        run_count += 1
        yield WorkflowRun(data=data)

    pages_all = '??'
    last_url = r.links['last']['url']
    pages_all_match = re.search(r'[^_]page=(\d+)', last_url)
    if pages_all_match:
        pages_all = int(pages_all_match.group(1))

    pages = 1
    while 'next' in r.links:
        next_url = r.links['next']['url']
        run_total = r.json()['total_count']
        workflow_runs_download_info(pages, pages_all, run_count, run_total,
                                    next_url, params)
        r = http_get(next_url, params=params)
        workflow_runs_page_info(r)
        for data in r.json()['workflow_runs']:
            run_count += 1
            yield WorkflowRun(data=data)
        pages += 1


def workflow_run_jobs_page_info(response):
    """ Show information about workflow run jobs search response:
        the list of job IDs.
    """
    ids = []
    for data in response.json()['jobs']:
        ids.append(data['id'])
    info('Workflow run job IDs: {}', ids)


def download_workflow_run_jobs(workflow_run_id):
    """ Download and yield workflow run jobs metainformation for
        given workflow run. An object for each (re)run.
    """
    params = {
        # 100 is the maximum.
        'per_page': 100,
        # Download all jobs, not only the latest one.
        'filter': 'all',
    }
    url = 'https://api.github.com/repos/{}/{}/actions/runs/{}/jobs'.format(
        args.owner, args.repo, workflow_run_id)
    info('Download {}', url)
    r = http_get(url, params=params)
    workflow_run_jobs_page_info(r)

    # Assume that nobody will rerun a workflow run more than 100
    # times. So we can download only the first page.

    for data in r.json()['jobs']:
        yield WorkflowRunJob(data)


if not os.path.isdir(workflow_runs_dir):
    os.makedirs(workflow_runs_dir)
if not os.path.isdir(workflow_run_jobs_dir):
    os.makedirs(workflow_run_jobs_dir)

ignore_in_stop_condition = set()

for run in download_workflow_runs(args.branch):
    # Stop condition.
    #
    # If there are no stored runs, continue till the end (how much
    # GitHub allows to download, it is 1000 runs).
    #
    # However we don't stop on a first known workflow run.
    # A restarted workflow run keeps its position in the list
    # (see [1]). So we re-check known runs and stop only when
    # reach two weeks old runs (unlikely somebody will restart
    # them).
    #
    # Actually this is not the optimal traverse algorithm, but
    # it is simple to implement.
    #
    # [1]: https://github.community/t/135654
    is_ignored = run.id in ignore_in_stop_condition
    run_is_old = startup_time - run.created_at > datetime.timedelta(weeks=2)
    if not args.nostop and run.is_stored and run_is_old and not is_ignored:
        info('Found stored workflow run {} older than 2 weeks, stopping...',
             run.id)
        break

    # Skip incomplete runs. We'll look at them next time.
    if run.status != 'completed':
        reason = 'incomplete'
        info('Skip workflow run {}: {}', run.id, reason)
        continue

    # Skip already processed runs if there were no restarts.
    if run.is_stored:
        run_past_info = WorkflowRun(filepath=run.meta_path)
        if run.updated_at == run_past_info.updated_at:
            info(("Workflow run {} was not changed ({}), don't download " +
                 "jobs again"), run.id, run.updated_at)
            continue
        info('Workflow run {} was updated ({} vs {}), downloading jobs...',
             run.id, run_past_info.updated_at, run.updated_at)

    # Download jobs meta.
    jobs = list(download_workflow_run_jobs(run.id))

    # Skip if there are incomplete jobs.
    incomplete_jobs = [job for job in jobs if job.status != 'completed']
    if incomplete_jobs:
        reason = 'incomplete jobs'
        info('Skip workflow run {}: {}', run.id, reason)
        continue

    # Download logs, store job meta and logs.
    for job in jobs:
        if not job.is_stored:
            if not args.nologs:
                job.download_log()
            job.store()

    # Store workflow run meta (or update it).
    run.store()
    # A new workflow run may be created while the script works.
    # So the same workflow run may appear twice: on page N and
    # on page N+1. If we'll not ignore it in the stop condition,
    # the first script invocation may stop prematurely.
    ignore_in_stop_condition.add(run.id)

debug_log_fh.close()
