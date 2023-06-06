import teslapy
import json
# import traceback
from replit import db

LAT_LONG_THRESHOLD = .01
DB_AUTH_KEY = 'tesla_auth'

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


def vehicle_is_at_location(query_lat, query_long, vd=None):
  vd = vd or vd_default()
  return (((vehicle_latitude(vd) - query_lat) <= LAT_LONG_THRESHOLD)
          and ((vehicle_longitude(vd) - query_long) <= LAT_LONG_THRESHOLD))


def get_vehicles():
  global vehicles
  vehicles = instance.vehicle_list()
  return vehicles


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
