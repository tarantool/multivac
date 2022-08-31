InfluxDB connector
==================

InfluxDB is the database we use to store data and build dashboards. Our InfluxDB
connector is in `multivac/influxdb.py`.

Run and connect to InfluxDB locally
-----------------------------------

1.  Install InfluxDB 2 according to
    `official instruction <https://docs.influxdata.com/influxdb/v2.4/install/>`__.

2.  Launch InfluxDB:

    ..  code-block:: console

        $ influxd

    After that you will be able to work with your InfluxDB with web-interface at
    http://localhost:8086 . You can change it with
    `instruction <https://docs.influxdata.com/influxdb/v2.4/reference/urls/>`__.
    Go to your site and create the account. Save your login organisation as
    environmental variable or in `.env` as `INFLUX_ORG`

3.   Go to `<localhost:8086> -> Load data -> Buckets` to create bucket. Save
     bucket name to environmental variable or in `.env` file as
     `INFLUX_BUCKET=<bucket>`

4.  Go to `<localhost:8086> -> Load data -> API Tokens` to get your token. Save
    token to environmental variable or in `.env` file as `INFLUX_TOKEN=<token>`

5.  Save your InfluxDB site to environmental variable or in `.env` file as
    `INFLUX_URL`

6.  If you've written variables to `.env`, run the following command:

    ..  code-block:: console

        $ source .env && export $(cut -d= -f1 .env)

Now you are ready to start any python script using InfluxDB connector

Using InfluxDB connector from code
----------------------------------

To use our connector from your code, import the connector:

..  code-block:: python3

    from multivac.influxdb import influx_connector
    ...
    bucket = os.getenv('INFLUX_BUCKET')
    org = os.getenv('INFLUX_ORG')

    write_api = influx_connector()
    data = {
        'measurement': <your_record_ID, required>,
        'tags': {<'indexed key/value structure, not required'>},
        'fields': {<'not indexed key/value structure, required'>},
        'time': <'unix time in nanoseconds, not required'>
    }
    write_api.write(bucket, org, [data])

InfluxDB connector in gather_job_data.py
----------------------------------------

-   **Measurement:** failure type (or "successful jobs");
-   **Tags:** job_name, job_id, run_id, branch, commit_sha, platform, status,
    runner_label;
-   **Fields:** time the job was in queue, time the job was in progress;
-   **Time:** queued at.

Usage:

..  code-block:: console

    $ multivac/gather_job_data.py --format influxdb
