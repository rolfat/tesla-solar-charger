#!/usr/bin/env python3

# By Don Barber don@dgb3.net Copyright 2022

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

# Reads from Enphase Solar Panel controller via Enphase API
# to get current electricity production and then sets the charging
# amperage of the Tesla via the Tesla API to match the production.
# The code rounds up so a little electricity is taken off the grid,
# maximizing the usage of solar and minimizing the amount fed back to the grid.
# As the resolution of enphase seems to be every 15 minutes, with a 5 minute
# delay, its not perfect, but gets pretty close.

import requests
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


def processmatch():
  global sparewatts, lastin, lastints, lastout, lastoutts

  maybe_set_night_charging_config()

  print("Consumed: %i watts collected %i seconds ago." %
        (lastout, time.time() - lastoutts))
  print("Produced: %i watts collected %i seconds ago." %
        (lastin, time.time() - lastints))

  sparewatts = lastin - lastout
  print("Spare Watts:", sparewatts)
  if lastoutts > lastvehiclechange_ts:
    for vehicle in tesla.vehicles:
      setcar(vehicle)
  else:
    print(
      "Ignoring as last consumed data is older than last vehicle charge update."
    )
  return


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


def fetch_solar_data():
  INTERVALS_PER_HOUR = 4
  global sparewatts, lastin, lastints, lastout, lastoutts

  fetch_vue_data()
  url = "https://api.enphaseenergy.com/api/v2/systems/%s/consumption_stats?%s" % (
    system_id, auth)
  r = requests.get(url).json()

  new_solar_data = False
  now_out = r['intervals'][-1]['enwh'] * INTERVALS_PER_HOUR
  now_out_ts = r['intervals'][-1]['end_at']
  if now_out_ts > lastoutts or now_out != lastout:
    lastout = now_out
    lastoutts = now_out_ts
    new_solar_data = True

  url = "https://api.enphaseenergy.com/api/v2/systems/%s/summary?%s" % (
    system_id, auth)
  r = requests.get(url).json()
  try:
    now_in = r['current_power']
    now_in_ts = r['last_interval_end_at']
    if (now_in_ts > lastints or now_in != lastin):
      lastin = now_in
      lastints = now_in_ts
      new_solar_data = True
  except:
    pass

  return new_solar_data


while True:
  QUERY_FREQUENCY_SECONDS = (60 * 20)
  try:
    starttime = time.time()
    print("Begin: %s" % time_to_string(starttime))

    vue.fetch_solar_data()

    # if fetch_solar_data() and tesla.fetch_vehicle_data(tesla_email):
    #   processmatch()
    # else:
    #   print("No new data, sleeping...")

    # update_state()

    # sleeptime = (lastoutts + QUERY_FREQUENCY_SECONDS) - time.time()
    # if sleeptime <= 0:
    #   sleeptime = 60
    # print("Waking in %im%is at %s \n" %
    #       ((sleeptime / 60),
    #        (sleeptime % 60), time_to_string(starttime + sleeptime)))
    # time.sleep(sleeptime)
  except Exception as e:
    print(e)
    time.sleep(120)
