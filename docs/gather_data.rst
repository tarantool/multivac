Gathering workflow data
=======================

..  toctree::
    :hidden:

    gather_job_data/failures

Gathering data about workflow jobs.

Writing options
---------------

Gathered data can be written to a CSV or JSON file,
configured with `--format [csv|json]` option.
There is no default option and without `--format`
there will be no output file.

..  code-block:: console

    $ ./multivac/gather_job_data.py --format csv

The resulting output will look like this:

..  literalinclude:: ./gather_job_data/_includes/workflows.csv
    :language: text

Same with JSON:

..  code-block:: console

    $ ./multivac/gather_job_data.py --format json

..  literalinclude:: ./gather_job_data/_includes/workflows.json
    :language: json

Or you can store data in InfluxDB (see :doc:`influxdb`):

..  code-block:: console

    $ multivac/gather_job_data.py --format influxdb

Limiting and filtering workflows
--------------------------------

Workflows which were skipped or cancelled won't be processed.

To gather data from a number of most recent workflows, use `--latest`:

..  code-block:: console

    $ ./multivac/gather_job_data.py --latest 1000

To gather data for the last N days or N hours, use ``--since``:

..  code-block:: console

    $ # see data for the last week (7 days)
    $ ./multivac/gather_job_data.py --since 7d
    $ # see data for the last 12 hours
    $ ./multivac/gather_job_data.py --since 12h

Writing data to a JSON file
---------------------------

To gather workflow data and write it to a JSON file, use ``--format json``
option. To gather data about tests as well, use ``--tests`` or ``-t`` option.

..  code-block:: console

    {
    "8374189766": {
        "job_id": 8374189766,
        "workflow_run_id": 3061077644,
        "job_name": "out_of_source",
        "branch": "master",
        "commit_sha": "416500fed508968d6d890eb3ec3620ef954d1d0a",
        "conclusion": "success",
        "queued_at": "2022-09-15T14:02:44Z",
        "started_at": "2022-09-15T14:02:56Z",
        "completed_at": "2022-09-15T14:08:45Z",
        "platform": "amd64",
        "runner_label": [
            "ubuntu-20.04-self-hosted"
          ],
        "runner_name": "ghacts-shared-8-16-n17",
        "runner_version": "2.296.2"
        "tests": [
            {
            "name": "box/tx_man.test.lua",
            "configuration": null,
            "status": "fail",
            "test_number": 0
            },
            {
            "name": "replication/qsync_advanced.test.lua",
            "configuration": "memtx",
            "status": "fail",
            "test_number": 1
            }
          ]
        }
      }

Writing data to InfluxDB
------------------------

To write data to InfluxDB, you need to set credentials as environmental
variables (see `.env-example` file). Add them to the ``.env`` file and
activate with the command:

..  code-block:: console

    $ source .env && export $(cut -d= -f1 .env)

Script uses different buckets for job data and test data.
The job bucket receives the following structure:

..  code-block:: console

    {
    "measurement":"failure_type or "success",
    "tags":{
        "job_id":"job ID",
        "job_name":"job name",
        "workflow_run_id":"workflow run ID",
        "branch":"head branch",
        "commit_sha":"head commit sha",
        "gc64": "'True' or 'False', as a string,
        "platform": "aarch64 or amd64 runner platform",
        "runner_label":"runner label",
        "runner_version":"runner version",
        "runner_name":"runner name",
        "conclusion":"job conclusion, success or failure"
      },
    "fields":{
        "value":1
      },
    "time":"timestamp time the job started at, in nanoseconds"
    }

The test bucket receives the following structure:

..  code-block:: console

    {
    "measurement": "test_name",
    "tags": {
        "job_id": job ID,
        "configuration": test configuration,
        "job_name": job name,
        "commit_sha": head commit sha,
        "test_attempt": number of test attempt
      },
    "fields": {
        "value": 1
      },
    "time": "time the job started at, in nanoseconds"
    }

Detecting workflow failure reasons
----------------------------------

Multivac can detect types of workflow failures and calculate detailed statistics.
Detailed description of known failure reasons can be found in
:doc:`gather_job_data/failures`.

..  code-block:: console

    $ ./multivac/gather_job_data.py --latest 1000 --failure-stats

    total 20
    package_building_error 5
    unknown 4
    testrun_test_failed 3
    telegram_bot_error 2
    integration_vshard_test_failed 1
    luajit_error 1
    testrun_test_hung 1
    git_repo_access_error 1
    dependency_autoreconf 1
    tap_test_failed 1


Command `--watch-failure name` will return a list of jobs where the named failure has been detected,
along with the links to workflow runs on GitHub and matching log lines:

..  code-block:: console

    $ ./multivac/gather_job_data.py --latest 1000 --watch-failure testrun_test_failed
    7008229080  memtx_allocator_based_on_malloc      https://github.com/tarantool/tarantool/runs/7008229080?check_suite_focus=true
                            2022-06-22T16:27:25.7389940Z * fail: 1
    6936376158  osx_12       https://github.com/tarantool/tarantool/runs/6936376158?check_suite_focus=true
                            2022-06-17T13:11:18.6461930Z * fail: 1
    6933185565  fedora_34 (gc64)     https://github.com/tarantool/tarantool/runs/6933185565?check_suite_focus=true
                            2022-06-17T09:24:50.6543965Z * fail: 1

This is useful when working with yet undetected failure reasons:

..  code-block:: console

    $ ./multivac/gather_job_data.py --latest 1000 --watch-failure unknown

    6966228368  freebsd-13   https://github.com/tarantool/tarantool/runs/6966228368?check_suite_focus=true
                            None
    6947333557  freebsd-12   https://github.com/tarantool/tarantool/runs/6947333557?check_suite_focus=true
                            None
