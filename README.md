# Multivac

It collects all troubles of CI.

## Requirements

* Python 3
* requests

## How to use

Add a token on [Personal access token][gh_token] GitHub page, give
`repo:public_repo` access and copy the token to `token.txt`.

Collect logs:

```
$ ./multivac/fetch.py --branch master tarantool/tarantool
$ ./multivac/fetch.py --branch 2.8 tarantool/tarantool
$ ./multivac/fetch.py --branch 2.7 tarantool/tarantool
$ ./multivac/fetch.py --branch 1.10 tarantool/tarantool
```

If something went wrong during initial script run, you may re-run it with
`--nostop` option: it disables stop heuristic. The heuristics is the following:
stop on a two weeks old workflow run stored on a previous script call.

Generate report:

```
$ ./multivac/last_seen.py --branch master --branch 2.8 --branch 2.7 --branch 1.10
```

Add `--format html` to get the 'last seen' report in the HTML format instead of
CSV. Reports are stored in the `output` directory.

**Caution:** Don't mix usual `fetch.py` calls with `--nologs` calls (see
below), otherwise some logs may be missed. The script is designed to either
collect meta + logs or just meta. If the meta is up-to-date, there is no cheap
way to ensure that all relevant jobs are collected with logs.

[gh_token]: https://github.com/settings/tokens
