How to connect to InfluxDB
==========================

1. Install InfluxDB 2 according to
[official instruction](https://docs.influxdata.com/influxdb/v2.4/install/)
2. Launch InfluxDB:
```bash
influxd
```
After that you will be able to work with your InfluxDB with web-interface at
http://localhost:8086 . You can change it with
[instruction](https://docs.influxdata.com/influxdb/v2.4/reference/urls/). Go to
your site and create the account. Save your login organisation as environmental
variable or in `.env` as `INFLUX_ORG`
3. Go to `<localhost:8086> -> Load data -> Buckets` to create bucket. Save
bucket name to environmental variable or in `.env` file as
`INFLUX_BUCKET=<bucket>`
4. Go to `<localhost:8086> -> Load data -> API Tokens` to get your token. Save
token to environmental variable or in `.env` file as `INFLUX_TOKEN=<token>`
5. Save your InfluxDB site to environmental variable or in `.env` file as
`INFLUX_URL`
6. If you've written variables to `.env`, run the following command:
```bash
source .env && export $(cut -d= -f1 .env)
```

Now you are ready to start any python script using InfluxDB connector
