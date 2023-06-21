import teslapy
import json
import math
# import traceback
from replit import db

LAT_LONG_THRESHOLD = .01
DB_AUTH_KEY = 'tesla_auth'

MIN_CHARGER_VOLTAGE = 220
MIN_CHARGER_CURRENT = 0
MAX_CHARGER_CURRENT = 40
AMP_TARGET_BUDGET = 1

vehicle_data = {}
vehicles = []


def vd_default():
  return list(vehicle_data.values())[0]


def vehicle_id(vd=None):
  vd = vd or vd_default()
  return vd['id']


def vehicle_latitude(vd=None):
  vd = vd or vd_default()
  return vd["drive_state"]["latitude"]


def vehicle_longitude(vd=None):
  vd = vd or vd_default()
  return vd["drive_state"]["longitude"]


def vehicle_is_plugged_in(vd=None):
  vd = vd or vd_default()
  return vd["charge_state"]["charge_port_door_open"]


def vehicle_is_at_location(query_lat, query_long, vd=None):
  vd = vd or vd_default()
  return (((vehicle_latitude(vd) - query_lat) <= LAT_LONG_THRESHOLD)
          and ((vehicle_longitude(vd) - query_long) <= LAT_LONG_THRESHOLD))


def battery_level(vd=None):
  vd = vd or vd_default()
  return vd["charge_state"]["battery_level"]


def charge_limit(vd=None):
  vd = vd or vd_default()
  return vd["charge_state"]["charge_limit_soc"]


def get_vehicles():
  global vehicles
  vehicles = instance.vehicle_list()
  return vehicles


def get_vehicle():
  for vehicle in vehicles:
    return vehicle


def charging_beyond_limit():
  return (battery_level() >= charge_limit())


def is_charging():
  vd = vd_default()
  return vd["charge_state"]["charging_state"] not in ("Stopped", "Complete")


def stop_charging():
  if is_charging():
    print(": Stop charging")
    get_vehicle().command('STOP_CHARGE')
    set_nonsolar_charge_config()


def adjust_charger_by(watts_consuming_now):
  if (charging_beyond_limit()):
    stop_charging()
    print("all charged up")
    return

  print('adjusting charger by', watts_consuming_now, 'kwh')
  print_charger_status()

  vd = vd_default()
  charger_current = vd["charge_state"]["charger_actual_current"]
  charger_voltage = vd["charge_state"]["charger_voltage"]
  target_amps = calculate_target_amps(watts_consuming_now, charger_current,
                                      charger_voltage)

  if (target_amps != charger_current):
    print("Setting charging amps to %i" % (target_amps))
    get_vehicle().command('CHARGING_AMPS', charging_amps=target_amps)

  if vd["charge_state"]["charging_state"] != "Charging":
    print("Start charging")
    get_vehicle().command('START_CHARGE')


def calculate_target_amps(watts_consuming_now, charger_current,
                          charger_voltage):
  charger_watts = charger_current * charger_voltage
  target_watts = charger_watts - watts_consuming_now
  print('target_watts', target_watts)

  target_amps = math.ceil(target_watts / charger_voltage)
  target_amps = target_amps * AMP_TARGET_BUDGET
  target_amps = min(target_amps, MAX_CHARGER_CURRENT)
  target_amps = max(target_amps, MIN_CHARGER_CURRENT)
  return target_amps


def set_nonsolar_charge_config():
  for vehicle in vehicles:
    vehicle.command('CHARGING_AMPS', charging_amps=MAX_CHARGER_CURRENT)


def print_charger_status(vd=None):
  vd = vd or vd_default()
  charger_current = vd["charge_state"]["charger_actual_current"]
  charger_voltage = vd["charge_state"]["charger_voltage"]
  charger_watts = charger_current * charger_voltage
  print("Currently using %i amps, %i volts, %i watts at %i %% battery" %
        (charger_current, charger_voltage, charger_watts, battery_level()))


def get_vehicle_data(vehicle):
  vehicle.sync_wake_up()
  try:
    vd = vehicle.get_vehicle_data()
  except:
    return

  vehicle_data[vehicle_id(vd)] = vd
  return vd


def get_tesla_auth():
  db_init(DB_AUTH_KEY)
  db_record = db.get(DB_AUTH_KEY)[email]
  auth_json = json.loads(db_record)
  return auth_json


def set_tesla_auth(cache):
  # cache = {'email@example.com': {"url": "https://auth.tesla.com/", "sso": {"access_token": "axxess_token", "refresh_token": "refreshhhh_token", "id_token": "iddddd_token", "expires_in": 28800, "token_type": "Bearer", "expires_at": 1673493715.8808246}}}
  email = list(cache.keys())[0]
  db_init(DB_AUTH_KEY)
  db[DB_AUTH_KEY][email] = json.dumps(cache)


def fetch_vehicle_data(email_arg):
  connect(email_arg)
  for vehicle in get_vehicles():
    get_vehicle_data(vehicle)
  return vd_default()


def connect(email_arg):
  global email, instance
  email = email_arg
  instance = teslapy.Tesla(email,
                           cache_loader=get_tesla_auth,
                           cache_dumper=set_tesla_auth)


def db_init(key):
  if not key in db.keys():
    db[key] = {}
