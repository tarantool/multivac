Downloading logs from s3
========================

We backup all logs collected with ``fetch.py`` since June, 2021 to s3 bucket
``s3://multivac/tarantool/tarantool``. There are more than 100Gb data, so be
careful with downloading this data.

1.  Install aws according to
    `official instruction <https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html>`__.

2.  Set up aws

    ..  code-block:: console

        $ aws configure --profile your_profile_name

        AWS Access Key ID: ask teamX
        AWS Secret Access Key: ask teamX
        Default region name: ru-msk
        Default output format: json

3.  Check the bucket content

    ..  code-block:: console

        $  aws s3 --endpoint-url https://hb.vkcs.cloud \
            --profile your_profile_name \
            ls s3://multivac/tarantool/tarantool

4.  Download logs from s3

    ..  code-block:: console

        $ aws s3 --endpoint-url https://hb.vkcs.cloud \
            --profile your_profile_name \
            sync s3://multivac/tarantool/tarantool/workflow_run_jobs/ your_path
