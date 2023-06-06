from pyemvue.enums import Scale, Unit
from replit import db

DB_AUTH_KEY = 'vue_auth'


def get_vue_auth():
  db_init(DB_AUTH_KEY)
  db_record = db.get(DB_AUTH_KEY)
  auth_json = db_record.value
  return auth_json


def db_init(key):
  if not key in db.keys():
    db[key] = {}


def fetch_solar_data():
  vue = pyemvue.PyEmVue()
  vue_auth = get_vue_auth()
  vue.login(username=vue_auth['username'],
            password=vue_auth['value'],
            token_storage_file='keys.json')

  devices = vue.get_devices()
  device_gids = []
  device_info = {}
  for device in devices:
    if not device.device_gid in device_gids:
      device_gids.append(device.device_gid)
      device_info[device.device_gid] = device
    else:
      device_info[device.device_gid].channels += device.channels

  device_usage_dict = vue.get_device_list_usage(deviceGids=device_gids,
                                                instant=None,
                                                scale=Scale.MINUTE.value,
                                                unit=Unit.KWH.value)
  print('device_gid channel_num name usage unit')
  print_recursive(device_usage_dict, device_info)


def print_recursive(usage_dict, info, depth=0):
  for gid, device in usage_dict.items():
    for channelnum, channel in device.channels.items():
      name = channel.name
      if name == 'Main':
        name = info[gid].device_name
      print('-' * depth, f'{gid} {channelnum} {name} {channel.usage} kwh')
      if channel.nested_devices:
        print_recursive(channel.nested_devices, info, depth + 1)
