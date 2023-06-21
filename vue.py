import pyemvue
from pyemvue.enums import Scale, Unit
from replit import db

DB_AUTH_KEY = 'vue_auth'

solar_usage = {}


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


def get_solar_usage(time_scale):
  for channelnum, channel in solar_usage[time_scale].channels.items():
    return channel.usage


def usage_timestamp():
  first_entry = list(solar_usage.values())[0]
  for channelnum, channel in first_entry.channels.items():
    return channel.timestamp


def print_solar_usage():
  print('solar usage: ')
  for scale in solar_usage.keys():
    usage = get_solar_usage(scale)
    print(usage, Unit.KWH.value, scale)


def fetch_solar_data():
  global solar_usage
  devices = vue.get_devices()
  device_gids = []
  for device in devices:
    if not device.device_gid in device_gids:
      device_gids.append(device.device_gid)

  for scale in Scale:
    solar_usage[scale.value] = vue.get_device_list_usage(
      deviceGids=device_gids,
      instant=None,
      scale=scale.value,
      unit=Unit.KWH.value)[device.device_gid]
  return solar_usage
