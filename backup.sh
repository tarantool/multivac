#!/bin/sh
set -xe o pipefail -o nounset

if [ $# -eq 0 ]; then
    echo "usage: $0 dir" 1>&2
    exit 1
fi

DIR="$1"

/usr/local/bin/aws \
  s3 sync /mnt/storage/multivac/${DIR} \
  s3://multivac/tarantool/tarantool/${DIR} \
  --endpoint-url http://hb.bizmrg.com --acl public-read
