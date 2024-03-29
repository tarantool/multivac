#!/usr/bin/env bash

set -xe -o pipefail -o nounset

DOC_PROJECT=multivac
DOC_DEST="$S3_UPLOAD_PATH/${DOC_PROJECT}/${BRANCH_NAME}"
# version in doc project and scripts
DOC_VERSION=latest
CHECK_KEY="doc-builds/${DOC_PROJECT}/${BRANCH_NAME}/json/_build_en/json/toctree.fjson"
UPDATE_KEY=$DOCS_UPDATE_KEY
UPDATE_URL=$DOCS_UPDATE_URL

not_exist=false
aws s3api head-object --bucket ${S3_BUCKET} --key ${CHECK_KEY} --endpoint-url="${S3_ENDPOINT_URL}" || not_exist=true
if [ $not_exist ]; then
  echo "toctree.json does not exist"
else
  echo "found toctree.json, remove the branch from s3 location"
  aws s3 rm "${DOC_DEST}"/json --endpoint-url="${S3_ENDPOINT_URL}" --recursive
fi

set -o nounset
aws s3 cp build/json "${DOC_DEST}"/json/_build_en/json \
    --endpoint-url="${S3_ENDPOINT_URL}" --recursive \
    --include "*" --exclude "*.jpg" --exclude "*.png" --exclude "*.svg"

curl --fail --show-error \
    --data '{"update_key":"'"${UPDATE_KEY}"'"}' \
    --header "Content-Type: application/json" \
    --request POST "${UPDATE_URL}""${DOC_VERSION}"/
