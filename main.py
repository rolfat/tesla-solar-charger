#!/usr/bin/env python3

# By Don Barber don@dgb3.net Copyright 2022

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

import tesla
import vue
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

last_is_operating = False
last_is_at_home = False

# CHARGE_LIMIT = 70


def maybe_adjust_charger(solar_usage):

  # maybe_set_night_charging_config()

  # vue.print_solar_usage()
  spare_watts = vue.get_solar_usage('1H')
  # print("Spare Watts:", spare_watts)
  for vehicle in tesla.vehicles:
    if should_adjust_charger():
      tesla.adjust_charger_by(spare_watts)


def should_adjust_charger():
  vd = tesla.vd_default()
  name = vd["display_name"]

  if not has_new_solar_data():
    print("no new data, not updating charger")
    return False

  if not tesla.vehicle_is_plugged_in():
    print("%s: Ignoring as not plugged in" % (name))
    return False

  if not tesla.vehicle_is_at_location(home_lat, home_long):
    print("%s: Ignoring as not at home" % (name))
    return False

  if not (is_within_operating_hours()):
    print("%s: Ignoring as outside operating hours" % (name))
    return False

  # if (tesla.battery_level() >= CHARGE_LIMIT):
  #   print("%s: battery at desired charge level" % (name))
  #   return False

  return True


def has_new_solar_data():
  last_data_at = vue.usage_timestamp()
  now = datetime.fromtimestamp(time.time(), timezone)

  seconds_since_last_data = ((now - last_data_at).seconds)
  has_new_data = seconds_since_last_data < QUERY_FREQUENCY_SECONDS
  return has_new_data


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
    tesla.set_nonsolar_charge_config()


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
  QUERY_FREQUENCY_SECONDS = 60 * 15
  try:
    starttime = time.time()
    print("\nBegin: %s" % time_to_string(starttime))
    solar_usage = vue.fetch_solar_data()
    tesla.fetch_vehicle_data(tesla_email)

    maybe_adjust_charger(solar_usage)
    update_state()

    time.sleep(QUERY_FREQUENCY_SECONDS)
  except Exception as e:
    print(e)
    time.sleep(120)
