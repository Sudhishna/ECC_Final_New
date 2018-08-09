from helpers import Helpers
from jnpr.junos.utils.config import Config
import re
import random
import math
import os
import jinja2
import time
import subprocess
from ipcalculator import IPCalculator
from jnpr.junos.exception import ConnectError
from jnpr.junos.exception import LockError
from jnpr.junos.exception import UnlockError
from jnpr.junos.exception import ConfigLoadError
from jnpr.junos.exception import CommitError
from subprocess import call


"""
Keeping this script simple by calling the functions written in the helper module
"""
class Campus_Config:

    def enable_lldp(self, spine_ips):

        #server_list = []
        #for server_dev in server_ips:
        #    server_ip = server_dev.split("_")[0]
        #    server_list.append(server_ip)
        #server_inv = ','.join(map(str, server_list))
        #process = subprocess.Popen(["ansible-playbook", "-i", "Inventory", "server_lldp.yml", "--extra-vars", "ansible_sudo_pass=Clouds123"], stdout=subprocess.PIPE)
        #server_info, err = process.communicate()
        #server_ip_hostname = re.findall(r"\"ps.stdout,inventory_hostname\": \"\((.*)\)\"",server_info)
        #server_hostip_map = {}
        #for servers in server_ip_hostname:
        #    servers = servers.split(",")
        #    server_name = ''
        #    server_ip = ''
        #    for server in servers:
        #        if "server" in server: 
        #            server_name = server.replace("'","")
        #            server_name = server_name.replace("u","")
        #        else:
        #            server_ip = server.replace("'","")
        #            server_ip = server_ip.replace("u","")

        #    server_hostip_map.update({server_name.strip(): server_ip.strip()})
        #print server_hostip_map

        #ansible_output = call(["ansible-playbook", "-i", "Inventory", "server_lldp.yml", "--extra-vars", "ansible_sudo_pass=Clouds123"])
        #print ansible_output

        helpers = Helpers()
        for spine_dev in spine_ips:
            spine_ip = spine_dev.split("_")[0]
            campus_id = spine_dev.split("_")[1]
            # Access the device using pyez netconf and fetch Serial Number
            print "Connecting to the device....\n"
            dev = helpers.device_connect(spine_ip)
            dev.open()
            on_box_hostname = dev.facts["hostname"]

            print "\n#####  Configuring: " + on_box_hostname + " #####\n"
            print "Configuring Below Device " + on_box_hostname + "\nHost IP: " + spine_ip + "\n"

            # Clear the previous configs if any
            with Config(dev, mode='private') as cu:
                 del_config = """
                             delete protocols bgp
                             delete protocols evpn
                             delete routing-options
                             delete vlans
                             delete switch-options
                             delete policy-options
                             delete interfaces xe-0/0/0
                             delete interfaces xe-0/0/1
                             delete interfaces xe-0/0/2
                             delete interfaces xe-0/0/3
                             delete interfaces xe-0/0/4
                             delete interfaces lo0
                             delete interfaces ae1
                             delete interfaces ae2
                             delete interfaces irb
                             delete routing-instances  
                             delete chassis
                             """
                 cu.load(del_config, format='set',ignore_warning=True)
                 cu.pdiff()
                 cu.commit()

            on_box_serialnumber = dev.facts["serialnumber"]
            on_box_version = dev.facts["version"]
            on_box_model = dev.facts["model"]
            print " On Box Serialnumber: " + on_box_serialnumber + "\n On Box Version: " + on_box_version + "\n On Box Model: " + on_box_model + "\n"

            # Push the new CONFIG Required
            print("\n\nLLDP protocol is configured in the devices")
            cfg = helpers.load_config(on_box_model, "basic", dev)

            dev.close()

    def campus_underlay(self, spine_ips, leaf_ips, server_ips, campus_info, server_hostip_map, spine_leaf_info):
	helpers = Helpers()

	vqfxDict = {}
	hosts_dict = {}
	link_layer_list = list()
        #leaf_link_layer_list = list()
	link_layer_map = {} 
	bgp_detail = {}
        vlans_list = list()

        host_ip_map = {}
        spine_leaf_map = {}
        for spine_dev in spine_ips:
            spine_ip = spine_dev.split("_")[0]
            campus_id = spine_dev.split("_")[1]
            '''
            BGP INFORMATION FETCHED
            IP IS NONE. WILL BE ASSIGNED LATER
            '''
	    dev = helpers.device_connect(spine_ip)
            dev.open()
	
	    on_box_hostname = dev.facts["hostname"]
            host_ip_map.update({on_box_hostname: spine_dev})
            spine_leaf_map.update({on_box_hostname: spine_ip})
            bgpasn = helpers.fetch_value("bgpasn",1)
            bgp_detail.update({on_box_hostname: {'bgpasn': bgpasn}})

	    dev.close()

        for leaf_dev in leaf_ips:
            leaf_ip = leaf_dev.split("_")[0]
            #campus_id = leaf_dev.split("_")[1]
            dev = helpers.device_connect(leaf_ip)
            dev.open()

            on_box_hostname = dev.facts["hostname"]
            host_ip_map.update({on_box_hostname: leaf_dev})
            spine_leaf_map.update({on_box_hostname: leaf_ip})

            dev.close()
        device_host_ip_map = host_ip_map.copy()
        device_host_ip_map.update(server_hostip_map) 
        print spine_leaf_map

        spine_leaf_hostname = {}
        for key,value in spine_leaf_info.iteritems():
            print spine_leaf_map.keys()[spine_leaf_map.values().index(key)]
            spine_hostname = spine_leaf_map.keys()[spine_leaf_map.values().index(key)]
            leaves_hostname = []
            for val in value:
                print spine_leaf_map.keys()[spine_leaf_map.values().index(val)]
                leaves_hostname.append(spine_leaf_map.keys()[spine_leaf_map.values().index(val)])
            spine_leaf_hostname.update({spine_hostname: leaves_hostname})

        print spine_leaf_hostname

        leaf_link_layer_list = {}
        leaf_count = 0
        for leaf_dev in leaf_ips:
            leaf_ip = leaf_dev.split("_")[0]
            campus_id = leaf_dev.split("_")[1]
            dev = helpers.device_connect(leaf_ip)
            dev.open()
            on_box_hostname = dev.facts["hostname"]

            interfaces_list = list()
            server_interfaces_list = list()
            server_list = list()

            cli_lldp = dev.rpc.get_lldp_neighbors_information()

            leaf_links_list = list()
            for lldp in cli_lldp.findall("lldp-neighbor-information"):
                local_port = lldp.findtext("lldp-local-interface")
                if local_port is None:
                    local_port = lldp.findtext("lldp-local-port-id")
                    local_port = local_port
                else:
                    local_port = local_port.split(".")
                    local_port = local_port[0]

                print local_port

                remote_system = lldp.findtext("lldp-remote-system-name")
                print "**" + remote_system + "**"
                print "**" + device_host_ip_map[remote_system] + "**"
                print spine_ips
                print device_host_ip_map[remote_system] in spine_ips
                print server_ips
                print device_host_ip_map[remote_system] + "_" + campus_id in server_ips

                if device_host_ip_map[remote_system] in spine_ips:
                    local_port = local_port.strip()
                    interfaces_list.append(local_port)
                elif device_host_ip_map[remote_system] + "_" + campus_id in server_ips:
                    server_interfaces_list.append(local_port) 
                    server_list.append(device_host_ip_map[remote_system])

            leaf_router_ip = helpers.fetch_value("bgp_router_id",1)
            leaf_count += 1
            if len(str(leaf_count)) == 1:
                leaf_vlan = str(leaf_count) + '0'
            elif len(str(leaf_count)) == 2:
                leaf_vlan = str(leaf_count)
            vlans_list.append(leaf_vlan)
            leaf_link_layer_list.update({on_box_hostname:{'ae_id':None,'interfaces':interfaces_list,'leaf_router_ip':leaf_router_ip,'server_interfaces':server_interfaces_list,'leaf_vlan':leaf_vlan}})

            print server_list
            server_count = 20 
            for server in server_list:
                print server
 
                mngmt_ip = IPCalculator(server + "/24")
                mngmt_ip_detail = mngmt_ip.__repr__()

                mngmt_hostrange = mngmt_ip_detail["hostrange"]
                mngmt_hostrange = mngmt_hostrange.split("-")
                print mngmt_hostrange

                #mngmt_gateway = mngmt_hostrange[1].rsplit('.',1)[0] + "." + "100"
                #print mngmt_gateway

                mngmt_broadcast = mngmt_ip_detail["broadcast"]
                print mngmt_broadcast

                mngmt_network = mngmt_hostrange[1].rsplit('.',1)[0] + "." + "0"
                print mngmt_network

                server_network = leaf_vlan + "." + leaf_vlan  + "." + leaf_vlan  + "." + "0"
                print server_network

                ip = IPCalculator(server_network + "/24")
                ip_detail = ip.__repr__()

                hostrange = ip_detail["hostrange"]
                hostrange = hostrange.split("-")
                print hostrange

                server_gateway = hostrange[1].rsplit('.',1)[0] + "." + "100"
                print server_gateway

                server_broadcast = ip_detail["broadcast"]
                print server_broadcast

                server_host_ips = helpers.ips(hostrange[0],hostrange[1].rsplit('.',1)[0] + "." + "100")
                server_host = server_host_ips[server_count]

                server_interface_config = "auto lo\\niface lo inet loopback\\n\\nauto ens3\\niface ens3 inet static\\naddress " + server + "\\nnetmask 255.255.255.0\\nnetwork " + mngmt_network + "\\nbroadcast " + mngmt_broadcast + "\\nup route add -net 192.168.0.0/12 gateway 192.168.122.1 dev ens3" + "\\n\\nauto ens4\\niface ens4 inet static\\naddress " + server_host + "\\nnetmask 255.255.255.0\\nnetwork " + server_network + "\\nbroadcast " + server_broadcast + "\\ngateway " + server_gateway
                print server_interface_config
                process = subprocess.Popen(["ansible-playbook", "-i", server + ",", "server_interface.yml", "--extra-vars", "ansible_sudo_pass=Clouds123 " + "interface_config='" + server_interface_config + "'"], stdout=subprocess.PIPE)
                servr_info, err = process.communicate()
                print servr_info

                server_count += 1
                
        ae_list = {}
        #leaf_interfaces_list = list()
        for spine_dev in spine_ips:
            spine_ip = spine_dev.split("_")[0]
            campus_id = spine_dev.split("_")[1]
            # Access the device using pyez netconf and fetch Serial Number
            dev = helpers.device_connect(spine_ip)
            dev.open()
	    on_box_hostname = dev.facts["hostname"]
		
            # Fetch the link layer information
            interfaces = list() 
            remote_connections = list()
            ints_list = list()
            bgp_list = list()
            interfaces_dict = {}

            print "Fetching LINK LAYER CONNECTIVITY INFORMATION"
            cli_lldp = dev.rpc.get_lldp_neighbors_information()

            leaf_links_list = list()
            ae_id = 0
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

                with Config(dev, mode='private') as cu:  
                    del_interface = "delete interfaces " + local_port + " unit 0 family inet"
                    cu.load(del_interface, format='set',ignore_warning=True)
                    cu.pdiff()
                    cu.commit()

	        remote_chassis = lldp.findtext("lldp-remote-chassis-id")
	        remote_system = lldp.findtext("lldp-remote-system-name")

                #if remote_system in list(set(bgp_detail.keys())) :
                #print host_ip_map[remote_system]
                #print spine_ips
                if host_ip_map[remote_system] in spine_ips:
                    interfaces.append(local_port)

	            remote_connections.append(remote_system)
	            remote_port = lldp.findtext("lldp-remote-port-description")
                    remote_port = remote_port.split(".")
                    remote_port = remote_port[0]
                    link_layer_list.append({'local_system': on_box_hostname, 'local_port': local_port, 'local_ip': 'None', 'remote_ip': 'None', 'remote_system': remote_system, 'remote_port': remote_port, 'broadcast': 'None'})

                    '''
                    INTERFACES INFORMATION FETCHED 
	            IP IS NONE. WILL BE ASSIGNED LATER
                    '''
                    #print "Fetching INTERFACES INFORMATION"
    	            description = "to_" + remote_system
	            local_port = local_port.strip()
                    description = description.strip()
	            ints_list.append({'physical_interface': local_port, 'description': description, 'ip_address': "None" })
                elif host_ip_map[remote_system] in leaf_ips:
                    ae_list_id = ''
                    local_port = local_port.strip()

                    remote_port = lldp.findtext("lldp-remote-port-description")
                    remote_port = remote_port.split(".")
                    remote_port = remote_port[0]
                    #leaf_link_layer_list.append({'local_system': on_box_hostname, 'local_port': local_port, 'remote_system': remote_system, 'remote_port': remote_port})
                    if remote_system in list(ae_list.keys()):
                        ae_list_id = ae_list[remote_system]
                    else:
                        ae_id += 1
                        ae_list_id = "ae" + str(ae_id)
                        
                        
                    #print remote_system,remote_port 
                    #leaf_interfaces_list.append({'remote_system':remote_system,'ae_id':ae_list_id,'remote_port':remote_port})
                    leaf_links_list.append({'ae_id':ae_list_id,'agg_id':{'vlans':[]},'local_system': on_box_hostname, 'local_port': local_port, 'remote_system': remote_system, 'remote_port': remote_port})
                    #leaf_interfaces_list.append({'remote_system':remote_system,'remote_port':remote_port})
                    ae_list.update({remote_system:ae_list_id})
                    #leaf_link_layer_list.update({on_box_hostname:{'ae_id':None
                    leaf_link_layer_list[remote_system]['ae_id'] = ae_list_id
                    #for key, vals in ae_list.iteritems():
                    #    print key,ae_list[key]
                    #ae_list[remote_system]['interfaces_list'].append(remote_port)

            '''
            BGP INFORMATION FETCHED 
            IP IS NONE. WILL BE ASSIGNED LATER
            '''
            #print "Fetching BGP INFORMATION"
            local_as = bgp_detail[on_box_hostname]["bgpasn"]
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
            #aggregated_link_count = campus_info['campus-' + campus_id]['leaf']
            leaf_count = campus_info['campus-' + campus_id]['leaf']
            spine_count = campus_info['campus-' + campus_id]['spine']
            agg_esi_id = ''
            if len(str(campus_id)) == 1:
                agg_esi_id = "0" + campus_id
            elif len(str(campus_id)) == 2:
                agg_esi_id = campus_id
            aggregated_links = {}
            #for x in range(1,aggregated_link_count+1):
            aggregated_links.update({'chassis_device_count':leaf_count,'links_info':leaf_links_list,'agg_esi_id':agg_esi_id})
            hostnumber_pattern = re.search('(\d+)', on_box_hostname)
            hostnumber = hostnumber_pattern.group(1)

            interfaces_dict.update({on_box_hostname: {'hostnumber':hostnumber,'interfaces': ints_list,'bgp_router_id': bgp_router_id,'bgpasn': local_as,'bgp': bgp_list,'route_filter': [],'overlay_peers': [],'vlans': vlans_list,'campus_id':campus_id,'aggregated_links':aggregated_links}})

            hosts_dict.update(interfaces_dict)
            dev.close()

        print "********************************************"
        print leaf_link_layer_list
        print "********************************************"

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
            print "local_ip"
            print link['local_ip']
            link['remote_ip'] = hostrange[1]+"/"+str(cidr)
            print "remote_ip"
            print link['remote_ip']
            link['broadcast'] = broadcast+"/"+str(cidr)
            print "broadcast"
            print link['broadcast']

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
        for key,values in hosts_dict.iteritems():
            hostname = key
            filter_list = list()
            for key,vals in values.iteritems():
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
            for filter in filter_list:
                values['route_filter'].append(filter)

        '''
        ASSIGN THE GENERATED IPs TO THE "BGP CONFIG,ROUTE FILTERS CONFIG"
        '''
        print "ASSIGN THE GENERATED IPs to BGP CONFIG,ROUTE FILTERS CONFIG"
        for key,values in hosts_dict.iteritems():
            hostname = key
            filter_list = list()
            for key,vals in values.iteritems():
                if key == "bgp":
                    for val in vals:
                        bgp_remote_host = val["remote_description"]
                        print bgp_remote_host
                        print hosts_dict[bgp_remote_host]["bgp_router_id"]
                        filter_list.append(hosts_dict[bgp_remote_host]["bgp_router_id"])
            for filter in filter_list:
                values['overlay_peers'].append(filter)

        spine_leaves_list = {}
        for key in spine_leaf_hostname:
            spine_hostname = key
            spine_leaves = {}
            for val in spine_leaf_hostname[key]:
                spine_leaves.update({leaf_link_layer_list[val]['ae_id']: {'leaf_vlan':leaf_link_layer_list[val]['leaf_vlan']}})
            spine_leaves_list.update({spine_hostname:spine_leaves})


        for key in spine_leaves_list:
            for val in hosts_dict[key]['aggregated_links']['links_info']:
                ae_id =  val['ae_id']
                val['agg_id']['vlans'].append(spine_leaves_list[key][ae_id]['leaf_vlan'])
        print hosts_dict

        template_filename = "QFX_leaf.conf"
        complete_path = os.path.join(os.getcwd(), 'Config')
        template_file = complete_path + "/" + template_filename

        for leaf_dev in leaf_ips:
            leaf_ip = leaf_dev.split("_")[0]
            campus_id = leaf_dev.split("_")[1]
            helpers.load_template_config(leaf_ip,"leaf",leaf_link_layer_list,template_file)

        '''
        CONFIG TEMPLATE
        '''
        print "EBGP"
        template_filename = "QFX_eBGP.conf"
        complete_path = os.path.join(os.getcwd(), 'Config')
        template_file = complete_path + "/" + template_filename

        for spine_dev in spine_ips:
            spine_ip = spine_dev.split("_")[0]
            campus_id = spine_dev.split("_")[1]
            helpers.load_template_config(spine_ip,"spine",hosts_dict,template_file)

        '''
        CONFIG TEMPLATE
        '''
        print "IBGP"
        template_filename = "QFX_iBGP.conf"
        complete_path = os.path.join(os.getcwd(), 'Config')
        template_file = complete_path + "/" + template_filename

        for spine_dev in spine_ips:
            spine_ip = spine_dev.split("_")[0]
            campus_id = spine_dev.split("_")[1]
            helpers.load_template_config(spine_ip,"spine",hosts_dict,template_file)

        '''
        CONFIG TEMPLATE
        '''
        print "VLANS"
        template_filename = "QFX_vlans.conf"
        complete_path = os.path.join(os.getcwd(), 'Config')
        template_file = complete_path + "/" + template_filename

        for spine_dev in spine_ips:
            spine_ip = spine_dev.split("_")[0]
            campus_id = spine_dev.split("_")[1]
            helpers.load_template_config(spine_ip,"spine",hosts_dict,template_file)

        '''
        CONFIG TEMPLATE
        '''
        print "Routing Instance"
        template_filename = "QFX_routing_instance.conf"
        complete_path = os.path.join(os.getcwd(), 'Config')
        template_file = complete_path + "/" + template_filename

        for spine_dev in spine_ips:
            spine_ip = spine_dev.split("_")[0]
            campus_id = spine_dev.split("_")[1]
            helpers.load_template_config(spine_ip,"spine",hosts_dict,template_file)

        '''
        CONFIG TEMPLATE
        '''
        print "Agg Link"
        template_filename = "QFX_ae.conf"
        complete_path = os.path.join(os.getcwd(), 'Config')
        template_file = complete_path + "/" + template_filename

        for spine_dev in spine_ips:
            spine_ip = spine_dev.split("_")[0]
            campus_id = spine_dev.split("_")[1]
            helpers.load_template_config(spine_ip,"spine",hosts_dict,template_file)


