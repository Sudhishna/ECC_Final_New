import time
import re
import subprocess
import getpass
import os
from ansible.parsing.dataloader import DataLoader
from ansible.inventory.manager import InventoryManager
from campus_config import Campus_Config
from subprocess import call

campus_config = Campus_Config()

VM_USER = getpass.getuser()
HOME_DIR = "/home/%s/" % (VM_USER)

def make_executable(path):
    mode = os.stat(path).st_mode
    mode |= (mode & 0o444) >> 2    # copy R bits to X
    os.chmod(path, mode)

file_name = "/home/ubuntu/Evolved_Campus_Core_Automation/Inventory"

with open(file_name) as f:
    content = f.read()
    campuses = re.findall('\[(.*?)\]',content)

campus_info = {}
leaf = []
spine = []

for campus in campuses:
    if "children" in campus:
        campus_id = campus.rsplit(":",1)[0]
        campus_info.update({campus_id: {'leaf': None,'spine':None}})

for campus in campuses:
    leaf_count = 0
    spine_count = 0
    campus_id = campus.rsplit("-")[1]
    if not "children"in campus:
        if "leaf" in campus:
            data_loader = DataLoader()
            inventory = InventoryManager(loader = data_loader,
                                         sources=[file_name])
            lst = inventory.get_groups_dict()[campus]
            for ls in lst:
                leaf.append(ls + "_" + campus_id)
                leaf_count += 1
            campus_info['campus-' + campus_id]['leaf'] = leaf_count
        elif "spine" in campus:
            data_loader = DataLoader()
            inventory = InventoryManager(loader = data_loader,
                                         sources=[file_name])
            lst = inventory.get_groups_dict()[campus] 
            for ls in lst:
                spine.append(ls + "_" + campus_id)
                spine_count += 1
            campus_info['campus-' + campus_id]['spine'] = spine_count

campuses_info = {}
for campus in campuses:
    if "children" in campus:
        campus_id = campus.rsplit(":",1)[0]
        campuses_info.update({campus_id: {'leaf': [],'spine':[]}})
for campus in campuses:
    leaf_count = 0
    spine_count = 0
    campus_id = campus.rsplit("-")[1]
    if not "children"in campus:
        if "leaf" in campus:
            data_loader = DataLoader()
            inventory = InventoryManager(loader = data_loader,
                                         sources=[file_name])
            lst = inventory.get_groups_dict()[campus]
            for ls in lst:
                campuses_info['campus-' + campus_id]['leaf'].append(ls)
        elif "spine" in campus:
            data_loader = DataLoader()
            inventory = InventoryManager(loader = data_loader,
                                         sources=[file_name])
            lst = inventory.get_groups_dict()[campus]
            for ls in lst:
                campuses_info['campus-' + campus_id]['spine'].append(ls)

spine_leaf_info = {}
for campus in campuses_info:
    for spine_dev in campuses_info[campus]["spine"]:
        spine_leaf_info.update({spine_dev: campuses_info[campus]["leaf"]})

dev_ips = []
for campus in campuses:
    if "children"in campus:
        campus_id = campus.split(":")[0]
        id = campus_id.split("-")[1]
        
        data_loader = DataLoader()
        inventory = InventoryManager(loader = data_loader,
                                     sources=[file_name])
        for dev in inventory.get_groups_dict()[campus_id]:
            dev_ips.append(dev + "_" + id)

servers = []
serverips = []
for campus in campuses:
    if "server"in campus:
        campus_id = campus.split(":")[0]
        id = campus_id.split("-")[1]

        data_loader = DataLoader()
        inventory = InventoryManager(loader = data_loader,
                                     sources=[file_name])
        for dev in inventory.get_groups_dict()[campus_id]:
            servers.append(dev + "_" + id)
            serverips.append(dev)

print servers
print serverips

accept_keys = "#!/bin/sh\n\n# Accept the SSH Keys\n"
for device in serverips:
    accept_keys += "ssh-keygen -R {}\nssh-keyscan -H {} >> ~/.ssh/known_hosts\n\n".format(device,device)
print("{}".format(accept_keys))
with open(HOME_DIR + "/Evolved_Campus_Core_Automation/installations_3.sh", "wt") as fil:
    fil.write(accept_keys)
    fil.close()
time.sleep(3)

make_executable(HOME_DIR + "/Evolved_Campus_Core_Automation/installations_3.sh")

subprocess.call(['./installations_3.sh'])

process = subprocess.Popen(["ansible-playbook", "-i", "Inventory", "server_lldp.yml", "--extra-vars", "ansible_sudo_pass=Clouds123"], stdout=subprocess.PIPE)
server_info, err = process.communicate()
print server_info

server_ip_hostname = re.findall(r"\"ps.stdout,inventory_hostname\": \"\((.*)\)\"",server_info)
print server_ip_hostname
server_hostip_map = {}
for server in server_ip_hostname:
    server = server.split(",")
    server_name = ((server[0].replace("'","")).replace("u","")).strip()
    server_ip = ((server[1].replace("'","")).replace("u","")).strip()

    server_hostip_map.update({server_name.strip(): server_ip.strip()})
    #for server in servers:
    #    if server_ip in server:
    #        server_hostip_map.update({server_name.strip(): server})

print server_hostip_map

dev = campus_config.enable_lldp(dev_ips)

print "Please wait for the devices to establish the links...."
time.sleep(60)

dev = campus_config.campus_underlay(spine,leaf,servers,campus_info,server_hostip_map,spine_leaf_info)

