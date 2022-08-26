from os import getenv
from influxdb_client import InfluxDBClient, WriteApi
from influxdb_client.client.write_api import SYNCHRONOUS


def influx_connector() -> WriteApi:
    org = getenv('INFLUX_ORG')
    token = getenv('INFLUX_TOKEN')
    url = getenv('INFLUX_URL')

    client = InfluxDBClient(url=url, token=token, org=org)
    return client.write_api(write_options=SYNCHRONOUS)
