# Multivac

It collects data about workflow runs and workflow run jobs from
[GitHub Api](https://docs.github.com/en/rest/actions/workflow-runs)

## Requirements

* Python 3
* requests

## API

### fetch.py

SYNOPSIS

    ./multivac/fetch.py [OPTION] [owner/repo]


DESCRIPTION

    multivac/fetch.py — download workflow runs GitHub API, workflow run jobs
    GitHub API and logs. Result stored in `workflow_runs` and `workflow_run_jobs`
    directories in the root of the project.


OPTIONS

    --branch __branch__

            Branch (all if omitted). To collect data about several branches, use
            this option several times.

    --nologs

            Don't download logs

    --nostop

            Continue till end or rate limit

    --since __N__

            A workflow run list page to start from it. Default: 1


EXAMPLE

    Collect all data about workflow runs and workflow run jobs till the end
    of rate limit from repository `tarantool/multivac` branches `master` and
    `sample-branch`, but don't collect logs:

```console 
$ ./multivac/fetch.py --branch `master` --branch `sample-branch` --nologs --nostop tarantool/multivac
```

### last_seen.py

SYNOPSIS

    ./multivac/last_seen.py --branch __branch__ [OPTIONS]

DESCRIPTION
   
    multivac/last_seen.py - generate common report from data collected by 
    `multivac/fetch.py` and store it in `output` directory. By default, it
    generates a report in CSV format.

OPTIONS

    --branch branch

            Generate a report for a certain branch.

    --format __[csv|html]__

            Generate a report in CSV format or in HTML format.

    --short

            Coalesce 'runs-on' labels by a first word

EXAMPLE

    Generate a report in the HTML format for branches `master` and
    `sample-branch`:

```console
$ ./multivac/last_seen.py --branch master --branch sample-branch --format html
```

### gather_job_data.py

SYNOPSIS
    
    ./multivac/generate_job_data.py [OPTIONS]

DESCRIPTION
    
    Get data about every completed job and group them by job ID. See the
    parameters it collects on the
    [website](https://www.tarantool.io/en/dev/multivac/gather_job_data/).

OPTIONS
    
    --format __[csv|json|infuxdb]__
    
            Store gathered data as `workflows.csv` or `workflows.json` file in
            `output` directory or store data in InfluxDB.
    
    --failure-stats
    
            Show overall failure statistics.
    
    --watch-failure __failure-type__
    
            Show detailed statistics about certain type of workflow failure. See
            list of known failure types with `--failure-stats` option.
    
    --latest __N__
    
            Only take logs from the latest N workflow runs.
    
    --since __N[d|h]__
    
            Only take logs for jobs started N days or hours ago: Nd for N days
            and Nh for N hours.

EXAMPLE
    
    Collect data about jobs started a week ago and earlier and put them to the
    InfluxDB:

```console
$ ./multivac/gather_job_data.py --since 7d --format influxdb
```

### gather_test_data.py

SYNOPSIS

    ./multivac/gather_test_data.py [OPTIONS]

DESCRIPTION

    Get data about every failed test in the completed jobs and group them by
    job ID: test name, test configuration, test number (to unicalize data in
    InfluxDB for correct statistic calculation).

OPTIONS

    --format __[csv|infuxdb]__
    
            Store gathered data as `tests.json` file in `output` directory or
            store data in InfluxDB. For JSON format - will rewrite file if
            exists.
            JSON example: 

                "8301691934": [
                {
                  "name": "box/tx_man.test.lua",
                  "configuration": null,
                  "test_number": 0
                },
                {
                  "name": "replication/qsync_advanced.test.lua",
                  "configuration": "vinyl",
                  "test_number": 1
                },
                ]

            For InfluxDB, collects job name for tests to make graphics:
                {
                "measurement": test_name,
                "tags": {
                    'job_id': job_id,
                    'configuration': test['configuration'],
                    'job_name': metadata['job_name'],
                    'commit_sha': metadata['commit_sha'],
                    'test_number': test['test_number']
                },
                "fields": {
                    "value": 1
                },
                "time": metadata["started_at"]
                }
    
    --since __N[d|h]__
    
            Only take logs for jobs started N days or hours ago: Nd for N days
            and Nh for N hours.

EXAMPLE

    Collect data about jobs started a week ago and earlier and put them to the
    InfluxDB:

```console
$ ./multivac/gather_test_data.py --since 7d --format influxdb
```

## How to use

Add a token on [Personal access token][gh_token] GitHub page, give
`repo:public_repo` access and copy the token to `token.txt`. All the scripts
should be started from the root of the project.

You can set all necessary environment variables at `.env` file as in
`.env-example` and then run the command:

```bash
source .env && export $(cut -d= -f1 .env)
```

### Collect logs:

```
$ ./multivac/fetch.py --branch master tarantool/tarantool
$ ./multivac/fetch.py --branch 2.8 tarantool/tarantool
$ ./multivac/fetch.py --branch 2.7 tarantool/tarantool
$ ./multivac/fetch.py --branch 1.10 tarantool/tarantool
```

If something went wrong during initial script run, you may re-run it with
`--nostop` option: it disables stop heuristic. The heuristics is the following:
stop on a two weeks old workflow run stored on a previous script call.

### Generate report:

```
$ ./multivac/last_seen.py --branch master --branch 2.8 --branch 2.7 --branch 1.10
```

Add `--format html` to get the 'last seen' report in the HTML format instead of
CSV. Reports are stored in the `output` directory.

**Caution:** Don't mix usual `fetch.py` calls with `--nologs` calls (see
below), otherwise some logs may be missed. The script is designed to either
collect meta + logs or just meta. If the meta is up-to-date, there is no cheap
way to ensure that all relevant jobs are collected with logs.

### Get specific data about jobs:

```bash
./multivac/gather_job_data.py --format json
```

See more information on
[website](https://www.tarantool.io/en/dev/multivac/gather_job_data/)

### Get time spent in jobs:

Collect jobs metainformation:

```
$ ./multivac/fetch.py --nologs --nostop tarantool/tarantool
```

You may need to re-run it several times to collect enough information: GitHub
ratelimits requests to 5000 per hour.

If hit by 403 error, look at the last `X-RateLimit-Reset` value in `debug.log`:
it is time, when you may start the script again. Call `date --date=@<..unix
time..> '+%a %b %_d %H:%M:%S %Z %Y'` to translate this value into a human
readable format.

You may continue from a particular page using the `--since N` option (beware of
holes, always leave some overlap).

Next, generate the report itself:

```
$ ./multivac/minutes.py [--short]
```

It prints minutes splitted in two ways:

* per day / per week / per month
* by 'runs-on' ('ubuntu-20.04' and so on)

Use `--short` to merge 'ubuntu-18.04' and 'ubuntu-20.04' into just 'ubuntu'.

[gh_token]: https://github.com/settings/tokens
