import jinja2
import json
import os
import threading
from time import sleep
import subprocess
from threading import Timer
import time
from pprint import pprint
from jnpr.junos import Device
import re

leaf = 2
spine = 2

total= leaf+spine
print(total)

inventory_file = "inventory/inventory"
open(inventory_file, 'w').close()

#f = open('sample.json', 'w')
#f.close()

def spinvm(number):
    # Sleeps a random 1 to 10 seconds
    # rand_int_var = randint(1, 10)
    print "++++++++++" + str(number) + "**************"
    subprocess.call(['vagrant','--vqfx-id=%s' % str(number),'up'])
    print "Thread " + str(number) +"completed spinup"

thread_list = []

for i in range(1, total+1):
    # Instantiates the thread
    # (i) does not make a sequence, so (i,)
    t = threading.Timer(3.0,spinvm, args=(i,))              
    # Sticks the thread in a list so that it remains accessible
    thread_list.append(t)

# Starts threads
for thread in thread_list:
    thread.start()
    time.sleep(10)

# This blocks the calling thread until the thread whose join() method is called is terminated.
# From http://docs.python.org/2/library/threading.html#thread-objects
for thread in thread_list:
    thread.join()

# Demonstrates that the main process waited for threads to complete
print "Done creating vms"

vqfxDict = {}

with open('inventory/inventory', 'r') as f:
    for line in f:
        vqfx = line.split(" ",1)[0]
        if "vqfx" in vqfx and "pfe" not in vqfx:
            vqfxDict[vqfx] = {}
            m = re.search('\w*.*ansible_host=(\w*.*?) ',line)
            host = m.group(1)
            vqfxDict[vqfx]['host'] = host
            m = re.search('\w*.*ansible_port=(\w*.*?) ',line)
            port = m.group(1)
            vqfxDict[vqfx]['port'] = port
print vqfxDict

for key,value in vqfxDict.iteritems():
    print "\n#####  Configuring: " + key + " #####\n"
    print "host " + value['host']
    print "port " + value['port']

    dev = Device(host=value['host'], user='root', password='Juniper',port=value['port'])
    dev.open()

    pprint(dev.facts)
    dev.close()
