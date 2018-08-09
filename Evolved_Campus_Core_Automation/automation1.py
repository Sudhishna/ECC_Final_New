from helpers import Helpers
from jnpr.junos.utils.config import Config
import re
import random
import math
import os
import jinja2
import time
from ipcalculator import IPCalculator
from jnpr.junos.exception import CommitError
from ansible.parsing.dataloader import DataLoader
from ansible.inventory.manager import InventoryManager

"""
Keeping this script simple by calling the functions written in the helper module
"""

helpers = Helpers()

vqfxDict = {}
hosts_dict = {}
link_layer_list = list()
link_layer_map = {} 
bgp_detail = {}

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

for name,value in vqfxDict.iteritems():
    '''
    BGP INFORMATION FETCHED
    IP IS NONE. WILL BE ASSIGNED LATER
    '''
    bgpasn = helpers.fetch_value("bgpasn",1)
    bgp_detail.update({name: {'bgpasn': bgpasn}})

for name,value in vqfxDict.iteritems():
    print "\n#####  Configuring: " + name + " #####\n"
    print "Configuring Below Device " + name + "\nHost IP: " + value['host'] + "\n" + "Host Port: " + value['port'] + "\n"

    # Access the device using pyez netconf and fetch Serial Number
    print "Connecting to the device....\n"
    dev = helpers.device_connect(value['host'],value['port'])
    dev.open()

    # Clear the previous configs if any
    with Config(dev, mode='private') as cu:
        del_interface = "delete protocols bgp"
        cu.load(del_interface, format='set',ignore_warning=True)
        cu.pdiff()
        cu.commit()

    with Config(dev, mode='private') as cu:
        del_interface = "delete protocols lldp"
        cu.load(del_interface, format='set',ignore_warning=True)
        cu.pdiff()
        cu.commit()

    with Config(dev, mode='private') as cu:
        del_interface = "delete routing-options"
        cu.load(del_interface, format='set',ignore_warning=True)
        cu.pdiff()
        cu.commit()

    with Config(dev, mode='private') as cu:
        del_interface = "delete policy-options"
        cu.load(del_interface, format='set',ignore_warning=True)
        cu.pdiff()
        cu.commit()

    on_box_serialnumber = dev.facts["serialnumber"]
    on_box_version = dev.facts["version"]
    on_box_model = dev.facts["model"]
    print " On Box Serialnumber: " + on_box_serialnumber + "\n On Box Version: " + on_box_version + "\n On Box Model: " + on_box_model + "\n"

    # Push the new CONFIG Required
    print("\n\nHOSTNAME and LLDP protocol is configured in the devices")
    cfg = helpers.load_config(on_box_model, name, "basic", dev)

    dev.close()

print "Please wait for the devices to establish the links...."
time.sleep(45)

for name,value in vqfxDict.iteritems():
    # Access the device using pyez netconf and fetch Serial Number
    dev = helpers.device_connect(value['host'],value['port'])
    dev.open()

    # Fetch the link layer information
    interfaces = list() 
    remote_connections = list()
    ints_list = list()
    bgp_list = list()
    interfaces_dict = {}

    print "Fetching LINK LAYER CONNECTIVITY INFORMATION"
    cli_lldp = dev.rpc.get_lldp_neighbors_information()

    for lldp in cli_lldp.findall("lldp-neighbor-information"):
        '''
        LINK LAYER CONNECTIVITY INFORMATION APPENDED
        '''
	local_port = lldp.findtext("lldp-local-interface") 
	if local_port is None:
	    local_port = lldp.findtext("lldp-local-port-id")
	    local_port = local_port
	else:
	    local_port = local_port.split(".")
	    local_port = local_port[0]

	interfaces.append(local_port)

        with Config(dev, mode='private') as cu:  
            del_interface = "delete interfaces " + local_port + " unit 0 family inet"
            cu.load(del_interface, format='set',ignore_warning=True)
            cu.pdiff()
            cu.commit()

	remote_chassis = lldp.findtext("lldp-remote-chassis-id")
	remote_system = lldp.findtext("lldp-remote-system-name")

	remote_connections.append(remote_system)
	remote_port = lldp.findtext("lldp-remote-port-description")
        remote_port = remote_port.split(".")
        remote_port = remote_port[0]
        link_layer_list.append({'local_system': name, 'local_port': local_port, 'local_ip': 'None', 'remote_ip': 'None', 'remote_system': remote_system, 'remote_port': remote_port, 'broadcast': 'None'})

        '''
        INTERFACES INFORMATION FETCHED 
	IP IS NONE. WILL BE ASSIGNED LATER
        '''
        print "Fetching INTERFACES INFORMATION"
	description = "to_" + remote_system
	local_port = local_port.strip()
	description = description.strip()
	ints_list.append({'physical_interface': local_port, 'description': description, 'ip_address': "None" })

    '''
    BGP INFORMATION FETCHED 
    IP IS NONE. WILL BE ASSIGNED LATER
    '''
    print "Fetching BGP INFORMATION"
    local_as = bgp_detail[name]["bgpasn"]
    bgp_router_id = helpers.fetch_value("bgp_router_id",1)

    for remote_connection in remote_connections:
        #print remote_connection
        #print bgp_detail 
        remote_as = bgp_detail[remote_connection]["bgpasn"]
        #print remote_as
	bgp_list.append({ 'remote_as': remote_as, 'remote_peer': 'None', 'remote_description' : remote_connection })

    '''
    INTERFACES,BGP,BGP_ROUTER_ID,BGPASN,ROUTER_FILTER
    INFORMATION APPENDED
    IPs ARE NONE. WILL BE ASSIGNED LATER
    '''
    interfaces_dict.update({name: {'interfaces': ints_list,'bgp_router_id': bgp_router_id,'bgpasn': local_as,'bgp': bgp_list,'route_filter': []}})

    hosts_dict.update(interfaces_dict)
    dev.close()

'''
LINK LAYER MAP:
LINK INFO: LOCAL(PORT,IP,HOST) & REMOTE(PORT,IP,HOST)
REMOVE DUPLICATES: DUPLICATES EXIST BCOS SAME LINK INFO FOUND IN BOTH LOCAL AND REMOTE HOST
'''
print "Creating LINK LAYER MAP: LOCAL(PORT,IP,HOST) & REMOTE(PORT,IP,HOST)"
link_layer_map.update({'link_layer': link_layer_list})
links = link_layer_map["link_layer"]
for link in links:
    for rlink in links:
        if link["local_system"]+link["local_port"] == rlink["remote_system"]+rlink["remote_port"]:
            if link["remote_system"]+link["remote_port"] == rlink["local_system"]+rlink["local_port"]:
		links.remove(rlink)

'''
GENERATE IPS FOR CONNECTED INTERFACES 
BASED ON:
IP START & IP END, NETMASK, ALREADY USED IP
'''
print "GENERATE IPS FOR CONNECTED INTERFACES BASED ON: IP START & IP END, NETMASK, ALREADY USED IP"
for link in links:
    interface_ip = helpers.fetch_value("interface_ip",1)

    ip = IPCalculator(interface_ip)
    ip_detail = ip.__repr__()
    hostrange = ip_detail["hostrange"]
    hostrange = hostrange.split("-")
    broadcast = ip_detail["broadcast"]
    cidr = ip_detail["cidr"]

    link['local_ip'] = hostrange[0]+"/"+str(cidr)
    link['remote_ip'] = hostrange[1]+"/"+str(cidr)
    link['broadcast'] = broadcast+"/"+str(cidr)

'''
ASSIGN THE GENERATED IPs TO THE INTERFACES CONFIG
'''
print "ASSIGN THE GENERATED IPs TO THE INTERFACES CONFIG"
for key, vals in hosts_dict.iteritems():
    hostname = key
    for key,vals in vals.iteritems():
	if key == "interfaces":
	    for val in vals:
	        interface = val["physical_interface"]
		for link in links:
		    if hostname == link["local_system"] and interface == link["local_port"]:
			val["ip_address"] = link["local_ip"]
		    elif hostname == link["remote_system"] and interface == link["remote_port"]:
			val["ip_address"] = link["remote_ip"]


'''
ASSIGN THE GENERATED IPs TO THE "BGP CONFIG,ROUTE FILTERS CONFIG" 
'''
print "ASSIGN THE GENERATED IPs to BGP CONFIG,ROUTE FILTERS CONFIG"
for key,vals in hosts_dict.iteritems():
    hostname = key
    filter_list = list()
    for key,vals in vals.iteritems():
	if key == "bgp":
	    for val in vals:
		bgp_remote_host = val["remote_description"]
		for link in links:
		    if hostname == link["local_system"] and bgp_remote_host == link["remote_system"]:
            		val["remote_peer"] = link["remote_ip"].replace("/30","")
			filter_list.append(val["remote_peer"]+"/32")
		    elif hostname == link["remote_system"] and bgp_remote_host == link["local_system"]:
	    		val["remote_peer"] = link["local_ip"].replace("/30","")
			filter_list.append(val["remote_peer"]+"/32")
	if key == "route_filter":
	    for filter in filter_list:
	        vals.append(filter)

print hosts_dict

'''
CONFIG TEMPLATE
'''
template_filename = "QFX_template.conf"
complete_path = os.path.join(os.getcwd(), 'Config')
template_file = complete_path + "/" + template_filename

templateLoader = jinja2.FileSystemLoader(searchpath="/")
templateEnv = jinja2.Environment(loader=templateLoader)
template = templateEnv.get_template(template_file)

for name,value in vqfxDict.iteritems():
    # Access the device using pyez netconf and fetch Serial Number
    dev = helpers.device_connect(value['host'],value['port'])
    dev.open()

    '''
    RENDER CONFIG BASED ON VARIABLES AND TEMPLATE
    '''
    print "Render the Configuration basd on auto-generated variables and the template"
    device_vars = hosts_dict[name]
    outputText = template.render(device_vars)
    print outputText

    config = Config(dev)

    '''
    LOCK DEVICE CONFIG
    '''
    print "Locking the configuration"
    time.sleep(3);
    try:
        config.lock()
    except LockError as err:
        print ("Unable to lock configuration: {0}".format(err))

    '''
    LOAD DEVICE CONFIG
    '''
    print "Loading configuration changes"
    time.sleep(3);
    try:
        config.load(template_path=template_file, template_vars=device_vars, merge=True)
    except (ConfigLoadError, Exception) as err:
        print ("Unable to load configuration changes: {0}".format(err))

    '''
    COMMIT DEVICE CONFIG
    '''
    print "Committing the configuration"
    time.sleep(3);
    try:
        config.commit(comment='Loaded by example.')
    except CommitError as err:
        print ("Unable to commit configuration: {0}".format(err))


