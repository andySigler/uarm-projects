from serial.tools.list_ports import comports
from uarm.wrapper import SwiftAPI


def print_port_info(port_info):
  print('- Port: {0}'.format(port_info.device))
  for key, val in port_info.__dict__.items():
    if (key != 'device' and val and val != 'n/a'):
      print('\t- {0}: {1}'.format(key, val))


def uarm_attempt_connect(port_info):
  if (port_info.hwid and '2341:0042' in port_info.hwid):
    uarm_filter = {'hwid': port_info.hwid}
    try:
      ua = SwiftAPI(filters=uarm_filter, do_not_open=True)
      ua.connect()
      ua.waiting_ready(timeout=3)
      return ua
    except Exception:
      return None


def uarm_print_device_into(ua):
  for key, val in ua.get_device_info().items():
    print('\t- {0}: {1}'.format(key, val))


def uarm_scan_and_connect():
  print('Searching for uArm serial port')
  for p in comports():
    print_port_info(p)
    ua = uarm_attempt_connect(p)
    if ua:
      print('Connected to uArm on port: {0}'.format(p.device))
      uarm_print_device_into(ua)
      return ua
  raise RuntimeError('Unable to find uArm port')


uarm = uarm_scan_and_connect();

