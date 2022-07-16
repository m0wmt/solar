#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Octopus API Interaction
#
import logging
import sys
import requests
from datetime import timedelta, date
from datetime import datetime
from influxdb import InfluxDBClient
from influxdb.client import InfluxDBClientError
from configparser import ConfigParser

#import json

# Set logging level
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

# Read config information
config_object = ConfigParser()
# Full path as this is kicked off 4 times a day via CRON
config_object.read('/home/pi/solar/octopus.cfg')

# Get the octopus config information
octopus = config_object['OCTOPUS']
  
# Set base url for Octopus API
BASE_URL = 'https://api.octopus.energy/v1/'

database_name = 'solar'  # temp for testing otherwise solar

def octopusconsumptionformpan(key, mpan, meter, params=None):
  '''
    Make a GET HTTPS request for information for mpan+meter

    :param key: Octopus API key
    :param mpan: mpan we're querying 
    :param meter: meter serial number
    :params params: any parameters for the API call
  '''

  if params is None:
    params = {}

  url = BASE_URL + 'electricity-meter-points/{}/meters/{}/consumption/'
  url = url.format(mpan, meter)
  r = requests.get(url, auth=(key,''), params=params)
  # print(r.json())
  return r.json()['results']

def writetoinfluxdb(flux_client, yesterday, data, field):
  '''
    Write data to InfluxDb

    :param flux_client: pointer to flux database
    :param yesterday: date of data being ingested, will be yesterdays date
    :param data: data for field we're writing to
    :param field: field in the database we're writing to
  '''

  try:
    # Send consumption info to the database
    if flux_client is not None:
      logging.debug('sending data to influxdb...')
      now = datetime.now().strftime(" %H:%M:%S.0")
      # Create json 
      octopus_json = [{
        'measurement':'solar', 
        'time': str(yesterday) + now,
        'tags':{'Inverter': 'solis'},
        'fields': {
          field:float(data)
          }
            }
        ]

      logging.debug(octopus_json)
      influx_result = flux_client.write_points(octopus_json, database=database_name)
    else:
      logging.error("No influxdb client available!")

  except TypeError as err:
    logging.error("TypeError:\n{}".format(err))

  except ValueError as err:
    logging.error("ValueError:\n{}".format(err))

  except InfluxDBClientError as err:
    logging.error("Influx connection failed:\n{}".format(err))

  except Exception as err:
    logging.error("Exception:\n{}".format(err))

def main():
  flux_client = 0
  flux_client = InfluxDBClient('127.0.0.1', 8086)
  #flux_client.drop_database("solar")
  #flux_client.create_database(database_name)

  api_key = octopus['apikey']
  import_mpan = octopus['importmpan'] 
  meter_serial_number = octopus['serialnumber']
  export_mpan = octopus['exportmpan']

  # Set up parameters
  params = {}
  params['group_by'] = 'day'

  # Get yesterdays date. Octopus are a day behind with consumption information so no point
  # getting todays!
  yesterday = date.today() - timedelta(days=1)
  params['period_from'] = str(yesterday) + 'T00:00:00'
  params['period_to'] = str(yesterday) + 'T23:59:59'

  try:
    # Read Octopus consumption information
    consumption_array = octopusconsumptionformpan(api_key, import_mpan, meter_serial_number, params)
    if len(consumption_array):
      logging.debug(consumption_array[0]['consumption'])
      logging.debug(consumption_array[0]['interval_start'])

      writetoinfluxdb(flux_client, yesterday, consumption_array[0]['consumption'], 'consumption')
    else:
      logging.error('No consumption data retrieved from Octopus!')

    # Read Octopus export information
    export_array = octopusconsumptionformpan(api_key, export_mpan, meter_serial_number, params)
    if len(export_array):
      logging.debug(export_array[0]['consumption'])
      logging.debug(export_array[0]['interval_start'])

      writetoinfluxdb(flux_client, yesterday, export_array[0]['consumption'], 'export')

      # Write data for the current month field (export_yyyymm)
      this_month = str(yesterday)[0:4] + str(yesterday)[5:7]
      writetoinfluxdb(flux_client, yesterday, export_array[0]['consumption'], 'export' + this_month)
    else:
      logging.error('No export data retrieved from Octopus!')

  except Exception as err:
    logging.error("Exception retriving data from Octopus:\n{}".format(err))

if __name__ == "__main__":
  main()
