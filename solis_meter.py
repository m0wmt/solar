#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Read modbus data from Ginlong Solis inverter
#
# Based on  https://sequr.be/blog/2021/08/reading-ginlong-solis-inverter-over-serial-and-importing-in-home-assistant-over-mqtt/
#
import logging
import minimalmodbus
import serial
import sys
from datetime import datetime
from datetime import timezone
from influxdb import InfluxDBClient
from influxdb.client import InfluxDBClientError

# Set logging level
logging.basicConfig(stream=sys.stderr, level=logging.ERROR)


def modbus_connect():
  instrument = minimalmodbus.Instrument("/dev/ttyAMA0", 1) # Set to inverter"s address
  instrument.serial.baudrate = 9600
  instrument.serial.bytesize = 8
  instrument.serial.parity   = serial.PARITY_NONE
  instrument.serial.stopbits = 1
  instrument.serial.timeout  = 3
  # instrument.debug = True
  return instrument

def modbus_read(instrument):
  # set all values to 0, inverter seems to shut down during the night!
  Realtime_ACW = 0
  Realtime_DCV = 0
  Realtime_DCI = 0
  Realtime_ACV = 0
  Realtime_ACI = 0
  Realtime_ACF = 0
  Inverter_C = 0
  DC1v = 0
  DC2v = 0
  DC1a = 0
  DC2a = 0
  PV_Power = 0

  #timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
  timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")

  # get data from solis
  # Realtime_ACW = instrument.read_long(3004, functioncode=4, signed=False) # Read AC Watts as Unsigned 32-Bit
  # logging.info("{:<23s}{:10.2f} W".format("AC Watts", Realtime_ACW))
  # Realtime_DCV = instrument.read_register(3021, number_of_decimals=2, functioncode=4, signed=False) # Read DC Volts as Unsigned 16-Bit
  # logging.info("{:<23s}{:10.2f} V".format("DC Volt", Realtime_DCV))
  # Realtime_DCI = instrument.read_register(3022, number_of_decimals=0, functioncode=4, signed=False) # Read DC Current as Unsigned 16-Bit
  # logging.info("{:<23s}{:10.2f} A".format("DC Current", Realtime_DCI))
  Realtime_ACV = instrument.read_register(3035, number_of_decimals=1, functioncode=4, signed=False) # Read AC Volts as Unsigned 16-Bit
  logging.info("{:<23s}{:10.2f} V".format("AC Volt", Realtime_ACV))
  Realtime_ACI = instrument.read_register(3038, number_of_decimals=0, functioncode=4, signed=False) # Read AC Current as Unsigned 16-Bit
  logging.info("{:<23s}{:10.2f} A".format("AC Current", Realtime_ACI))
  Realtime_ACF = instrument.read_register(3042, number_of_decimals=2, functioncode=4, signed=False) # Read AC Frequency as Unsigned 16-Bit
  logging.info("{:<23s}{:10.2f} Hz".format("AC Frequency", Realtime_ACF))
  Inverter_C = instrument.read_register(3041, number_of_decimals=1, functioncode=4, signed=True) # Read Inverter Temperature as Signed 16-Bit
  logging.info("{:<23s}{:10.2f} °C".format("Inverter Temperature", Inverter_C))
  AlltimeEnergy_KW = instrument.read_long(3008, functioncode=4, signed=False) # Read All Time Energy (KWH Total) as Unsigned 32-Bit
  logging.info("{:<23s}{:10.2f} kWh".format("Generated (All time)", AlltimeEnergy_KW))
  Today_KW = instrument.read_register(3014, number_of_decimals=1, functioncode=4, signed=False) # Read Today Energy (KWH Total) as 16-Bit
  logging.info("{:<23s}{:10.2f} kWh".format("Generated (Today)", Today_KW))

  DC1v = instrument.read_register(3021, number_of_decimals=2,functioncode=4, signed=False)
  DC2v = instrument.read_register(3023, number_of_decimals=2,functioncode=4, signed=False)
  DC1a = instrument.read_register(3022, number_of_decimals=1,functioncode=4, signed=False)
  DC2a = instrument.read_register(3024, number_of_decimals=1,functioncode=4, signed=False)
  PV_Power = instrument.read_register(3007, functioncode=4, signed=False)
  LastMonth_KW = instrument.read_register(3013, functioncode=4, signed=False)
  logging.info("{:<23s}{:10.2f} kWh".format("Generated (Last Month)", LastMonth_KW))
  ThisMonth_KW = instrument.read_register(3011, functioncode=4, signed=False)
  logging.info("{:<23s}{:10.2f} kWh".format("Generated (This Month)", LastMonth_KW))

  logging.info("{:<23s}{:10.2f} V".format("DC1v", DC1v))
  logging.info("{:<23s}{:10.2f} V".format("DC2v", DC2v))
  logging.info("{:<23s}{:10.2f} A".format("DC1a", DC1a))
  logging.info("{:<23s}{:10.2f} A".format("DC2a", DC2a))
  logging.info("{:<23s}{:10.2f} W".format("PV Power", PV_Power))

  data = {
    "online": timestamp,
    "acw": Realtime_ACW,
    "dcv": Realtime_DCV,
    "dci": Realtime_DCI,
    "acv": Realtime_ACV,
    "aci": Realtime_ACI,
    "acf": Realtime_ACF,
    "inc": Inverter_C,
    "dc1a": DC1a,
    "dc2a": DC2a,
    "dc1v": DC1v,
    "dc2v": DC2v,
    "pvpower": PV_Power,
    "lastMonth": LastMonth_KW,
    "thisMonth": ThisMonth_KW
  }

  # Fix for 0-values during inverter powerup
  if AlltimeEnergy_KW > 0: data["gat"] = AlltimeEnergy_KW
  if Today_KW > 0: data["gto"] = Today_KW
  
  return data
  
def returnZeroValues():
  #timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
  timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")

  data = {
    "online": timestamp,
#    "acw": 0,
#    "dcv": 0,
#    "dci": 0,
    "acv": 0,
    "aci": 0,
    "acf": 0,
    "inc": 0,
    "dc1a": 0,
    "dc2a": 0,
    "dc1v": 0,
    "dc2v": 0,
    "pvpower" : 0
  }

  return data

def sendDataToInflux(flux_client, data):
  if flux_client is not None:
    logging.debug("sending data to influxdb...")
    # Create json 
    solar_json = [{
      "measurement":"solar", 
      "time": data["online"],
      "tags":{"Inverter": "solis"},
      "fields": {
#        "acw":float(data["acw"]),
#        "dcv":float(data["dcv"]),
#        "dci":float(data["dci"]),
        "acv":float(data["acv"]),
        "aci":float(data["aci"]),
        "acf":float(data["acf"]),
        "inc":float(data["inc"]),
        "gat":float(data["gat"]),
        "gto":float(data["gto"]),
        "dc1a":float(data["dc1a"]),
        "dc2a":float(data["dc2a"]),
        "dc1v":float(data["dc1v"]),
        "dc2v":float(data["dc2v"]),
        "pvpower":float(data["pvpower"]),
  			"lastMonth":float(data["lastMonth"]),
  			"thisMonth":float(data["thisMonth"])
          }
          }
      ]

    logging.debug(solar_json)
    flux_client.write_points(solar_json, database="solar")

def main():
  flux_client = 0

  flux_client = InfluxDBClient("127.0.0.1", 8086)
  #flux_client.drop_database("solar")
  #flux_client.create_database("solar")

  try:
    modc = modbus_connect()
    logging.debug(modc)

    data = modbus_read(modc)
    logging.debug(data)

    if flux_client is not None:
      sendDataToInflux(flux_client, data)
    else:
      logging.error("No influxdb client available!")

  except TypeError as err:
    logging.error("TypeError:\n{}".format(err))

  except ValueError as err:
    logging.error("ValueError:\n{}".format(err))

  except InfluxDBClientError as err:
    logging.error("Influx connection failed:\n{}".format(err))

  except minimalmodbus.NoResponseError as err:
    logging.error("Modbus no response:\n{}".format(err))
    if flux_client is not None:
      zero_data = returnZeroValues()
      sendDataToInflux(flux_client, zero_data)

  except Exception as err:
    logging.error("Exception:\n{}".format(err))

if __name__ == "__main__":
  main()
