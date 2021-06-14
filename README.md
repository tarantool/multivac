# Multivac

It collects all troubles of CI.

## Requirements

* Python 3
* requests

## How to use

Add a token on [Personal access token][gh_token] GitHub page, give
`repo:public_repo` access and copy the token to `token.txt`.

Run `./multivac/fetch.py` (it's long, but you can stop just by Ctrl+C).

Run `./multivac/last_seen.py` (can be invoked during fetching).

[gh_token]: https://github.com/settings/tokens
