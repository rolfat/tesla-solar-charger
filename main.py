#!/usr/bin/env python3

# By Don Barber don@dgb3.net Copyright 2022

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

import tesla
import vue
import math
import time
import pytz
import os
from datetime import datetime

home_lat = float(os.getenv("homelat"))
home_long = float(os.getenv("homelong"))
tesla_email = os.getenv("teslaemail")
api_key = os.getenv("apikey")
user_id = os.getenv("userid")
system_id = os.getenv("systemid")
auth = "key=%s&user_id=%s" % (api_key, user_id)
timezone = pytz.timezone('US/Pacific')

MIN_CHARGER_VOLTAGE = 220
MIN_CHARGER_CURRENT = 0
MAX_CHARGER_CURRENT = 40
AMP_TARGET_BUDGET = 1.1

CHARGE_LIMIT_OPERATING = 70
CHARGE_LIMIT_NONOPERATING = 55


# amps * volts = watts
def maybe_adjust_charger(solar_usage):

  # maybe_set_night_charging_config()
  print('ereh')

  vue.print_solar_usage()

  if not has_new_data(solar_usage):
    print("no new data, not updating charger")
    return

  print("Spare Watts:", sparewatts)
  for vehicle in tesla.vehicles:
    setcar(vehicle)


def has_new_data(solar_usage):
  return False


def setcar(vehicle):

  global sparewatts, lastvehiclechange_ts, lastoutts, lastin
  vd = tesla.vd_default()
  name = vd["display_name"]
  if vd["charge_state"]["charge_port_door_open"] != True:
    print("%s: Ignoring as not plugged in" % (name))
    return

  if not tesla.vehicle_is_at_location(home_lat, home_long):
    print("%s: Ignoring as not at home" % (name))
    return

  if not (is_within_operating_hours()):
    print("%s: Ignoring as outside operating hours" % (name))
    return

  battery_level = vd["charge_state"]["battery_level"]
  print("battery level: %s" % (battery_level))

  charger_current = vd["charge_state"]["charger_actual_current"]
  charger_voltage = max(vd["charge_state"]["charger_voltage"],
                        MIN_CHARGER_VOLTAGE)
  charger_watts = charger_current * charger_voltage

  print("Currently using %i amps, %i volts, %i watts" %
        (charger_current, charger_voltage, charger_watts))
  freewatts = sparewatts + charger_watts
  freewatts = min(freewatts, lastin)
  print("freewatts: %i" % freewatts)

  if battery_level < CHARGE_LIMIT_OPERATING and freewatts > 0:
    amptarget = math.ceil(freewatts / charger_voltage)
    amptarget = amptarget * AMP_TARGET_BUDGET
    amptarget = min(amptarget, MAX_CHARGER_CURRENT)
    amptarget = max(amptarget, MIN_CHARGER_CURRENT)

    print("Setting charging amps to %i" % (amptarget))
    vehicle.command('CHARGING_AMPS', charging_amps=amptarget)
    sparewatts = freewatts - (amptarget * charger_voltage)
    lastvehiclechange_ts = lastoutts
    if vd["charge_state"]["charging_state"] != "Charging":
      print("%s: Start charging" % name)
      vehicle.command('START_CHARGE')
  elif vd["charge_state"]["charging_state"] not in ("Stopped", "Complete"):
    sparewatts = freewatts
    print("%s: Stop charging" % name)
    vehicle.command('STOP_CHARGE')
    set_nonsolar_charge_config(vehicle)
    lastvehiclechange_ts = lastoutts


def set_nonsolar_charge_config(vehicle):
  vehicle.command('CHARGING_AMPS', charging_amps=MAX_CHARGER_CURRENT)


lastints = 0
lastin = 0
lastout = 1000000
lastoutts = 0
lastvehiclechange_ts = 0

last_is_operating = False
last_is_at_home = False


def time_to_string(timestamp):
  DATETIME_FORMAT = "%d %b %Y, %H:%M:%S"

  date_time = datetime.fromtimestamp(timestamp, timezone)
  return date_time.strftime(DATETIME_FORMAT)


def maybe_set_night_charging_config():
  is_at_home = tesla.vehicle_is_at_location(home_lat, home_long)

  just_arrived_home = False
  if (is_at_home and not last_is_at_home):
    just_arrived_home = True

  should_set_config = (just_arrived_home and not is_within_operating_hours()
                       ) or (is_at_home and did_exit_operating_hours())

  if should_set_config:
    print('setting nighttime config')
    for vehicle in tesla.vehicles:
      set_nonsolar_charge_config(vehicle)


def did_exit_operating_hours():
  return last_is_operating and not is_within_operating_hours()


def is_within_operating_hours():
  OPERATING_HOURS_START = 7
  OPERATING_HOURS_END = 17
  operating_hours = range(OPERATING_HOURS_START, OPERATING_HOURS_END)

  current_time = datetime.fromtimestamp(time.time(), timezone)
  return (current_time.hour in operating_hours)


def update_state():
  global last_is_operating, last_is_at_home
  last_is_operating = is_within_operating_hours()
  last_is_at_home = tesla.vehicle_is_at_location(home_lat, home_long)


vue.init()
while True:
  QUERY_FREQUENCY_SECONDS = 60
  try:
    starttime = time.time()
    print("\nBegin: %s" % time_to_string(starttime))
    solar_usage = vue.fetch_solar_data()
    # tesla.fetch_vehicle_data(tesla_email)

    maybe_adjust_charger(solar_usage)

    # update_state()

    time.sleep(QUERY_FREQUENCY_SECONDS)
  except Exception as e:
    print(e)
    time.sleep(120)
