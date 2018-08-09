from jnpr.jsnapy import SnapAdmin
from pprint import pprint
from jnpr.junos import Device
import difflib
import re
import xml.etree.ElementTree
from helpers import Helpers
from ansible.parsing.dataloader import DataLoader
from ansible.inventory.manager import InventoryManager

def invokeTests(vmanme):

    js = SnapAdmin()

    helpers = Helpers()

    config_file = """
    hosts:
    - device: 192.168.122.9
      username: ubuntu
    tests:
    - test_diff.yml
    """

    #js.snap(config_file, "pre")
    js.snap(config_file, "post")
    chk = js.check(config_file, "pre", "post")

    '''
    file_name = "/home/ubuntu/Evolved_Campus_Core_Automation/Inventory"
    with open(file_name) as f:
        content = f.read()
        campuses = re.findall('\[(.*?)\]',content)

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

    '''
    spine_leaf_info = {}
    '''
    for campus in campuses_info:
        for leaf_dev in campuses_info[campus]["leaf"]:
            spine_leaf_info.update({leaf_dev: campuses_info[campus]["spine"]})
    '''

    devip = ""
    failed = 0
    test_name = ""
    for check in chk:
        devip = check.device
        failed = check.no_failed
        if not not check.test_results.keys():
            test_name = check.test_results.keys()[0].replace(' ','_')

    ae_id = ""
    dev = helpers.device_connect(devip)
    dev.open()
    data = dev.rpc.get_config(options={'format':'json'})
    for ints in data['configuration']['interfaces']['interface']:
        if "ae" in ints['name']:
            ae_id = ints['name']
    dev.close()

    pre_file = '/home/ubuntu/jsnapy/snapshots/' + devip + '_pre_' + test_name + '.xml'
    post_file = '/home/ubuntu/jsnapy/snapshots/' + devip + '_post_' + test_name + '.xml'

    dict = {}
    if failed != 0:
        with open(pre_file, 'r') as hosts0:
            with open(post_file, 'r') as hosts1:
                diff = difflib.unified_diff(
                    hosts0.readlines(),
                    hosts1.readlines(),
                    fromfile='hosts0',
                    tofile='hosts1',
                    n=0,
                )
                lines = list(diff)[2:]
        print lines
        added = [line[1:] for line in lines if line[0] == '+']
        additions = ""
        for line in added:
            additions += line
        print 'additions'
        vlan_text = ""
        if additions:
            tree = xml.etree.ElementTree.fromstring(additions)
            print tree
            for vlan in tree.findall('l2ng-l2rtb-vlan-name'):
                text = vlan.text
                vlan_text = text.split("vlan")[1]
                print vlan_text

            dict = {'vqfx3': {'vlanid':vlan_text}}
            template_file = '/home/ubuntu/Evolved_Campus_Core_Automation/Config/QFX_vlan_leaf_addition.conf'
            helpers.load_template_config(devip,"spine",dict,template_file)

            '''
            print spine_leaf_info
            for spine_ip in spine_leaf_info[devip]:
                template_file = '/home/ubuntu/Evolved_Campus_Core_Automation/Config/QFX_vlan_spine_addition.conf'
                #helpers.load_template_config(spine_ip,"spine",dict,template_file)
            '''

    if failed != 0:
        with open(post_file) as f:
            lines = f.readlines()
            lines1 = ""
            for line in lines:
                lines1 += line
            with open(pre_file, "w") as f1:
                f1.writelines(lines1)

