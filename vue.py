import pyemvue
from pyemvue.enums import Scale, Unit
from replit import db
import json

DB_AUTH_KEY = 'vue_auth'


def get_vue_auth():
  db_init(DB_AUTH_KEY)
  db_record = db.get(DB_AUTH_KEY)
  return db_record.value


def db_init(key):
  if not key in db.keys():
    db[key] = {}


def init():
  global vue
  vue = pyemvue.PyEmVue()
  vue_auth = get_vue_auth()
  #print('logging in with', vue_auth['username'])
  vue.login(username=vue_auth['username'], password=vue_auth['password'])
  #print('login complete')


def fetch_solar_data():
  devices = vue.get_devices()
  device_gids = []
  for device in devices:
    if not device.device_gid in device_gids:
      device_gids.append(device.device_gid)

  device_usage_dict = vue.get_device_list_usage(deviceGids=device_gids,
                                                instant=None,
                                                scale=Scale.MINUTES_15.value,
                                                unit=Unit.KWH.value)
  for gid, device in device_usage_dict.items():
    for channelnum, channel in device.channels.items():
      print('usage', channel.usage, 'kWh')
