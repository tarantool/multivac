# Multivac

It collects data about workflow runs and workflow run jobs from
[GitHub Api](https://docs.github.com/en/rest/actions/workflow-runs)

## Requirements

* Python 3
* requests

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
