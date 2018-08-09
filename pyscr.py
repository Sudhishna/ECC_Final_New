from jnpr.junos import Device
from getpass import getpass
import sys

# NETCONF session over SSH
dev = Device(host='192.168.122.9', user='ubuntu')
dev.open()
print (dev.facts)
