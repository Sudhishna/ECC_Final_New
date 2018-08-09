#
# DO NOT ALTER OR REMOVE COPYRIGHT NOTICES OR THIS FILE HEADER
#
# Copyright (c) 2015 Juniper Networks, Inc.
# All rights reserved.
#
# Use is subject to license terms.
#
# Licensed under the Apache License, Version 2.0 (the ?License?); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at http://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author:      Subrata Mazumdar (subratam@junpier.net)
# Description: A Python object to provide information about Host-Only Network Interfaces. 
# 

import sys
from pprint import pformat

import virtualbox
import netaddr



# VirtualBox API: http://pythonhosted.org/pyvbox/virtualbox/library.html

class VBHONetUtil:
    """ Utility Methods for Host-only network in VritualBox """
    
    manager = None
    vbox    = None
    host    = None

    ctx     = None

    def __init__(self): 

        # vboxapi.VirtualBoxManager
        self.manager = virtualbox.Manager().manager

        #IVrtualBox
        self.vbox = self.manager.vbox

        # IHost
        self.host = self.manager.vbox.host

        self.ctx = {
            'manager':       self.manager,
            'vbox':          self.manager.vbox,
            'host':          self.manager.vbox.host,
        }

    def getNetworkInterfaces(self):
        # IHostNetworkInterface[]
        niList = self.host.getNetworkInterfaces()
        # niList = manager.getArray(host, 'networkInterfaces')
    
        return niList
    
    def getNetworkInterfaceByName(self, netName):
        if (netName == None) :
            return None
        # IHostNetworkInterface[]
        niList = self.host.getNetworkInterfaces()
        for ni in niList:
            if ni.name == netName: 
                return ni;
        return None
    
    def getHostOnlyNetworkInterfaces(self):
        # IHostNetworkInterface[]
        niList = self.host.findHostNetworkInterfacesOfType(virtualbox.library.HostNetworkInterfaceType.host_only)
        return niList
    
    def getHostOnlyNetworkNames(self):
        # IHostNetworkInterface[]
        niNameList = []
    
        # IHostNetworkInterface[]
        niList = self.getHostOnlyNetworkInterfaces()
        for ni in niList:
            niNameList.append(str(ni.name))
        return niNameList
    
    def getHostOnlyNetworkInterfaceByGuestIP(self, guestIP):
    
        # IHostNetworkInterface[]
        niList = self.getHostOnlyNetworkInterfaces()
    
        for ni in niList:
            # VirtulBox host-only networks are defined based on GW interface address for the network and net-mask
            vboxHoNetGWIPAddr = ni.IPAddress + "/" + ni.networkMask;
            vboxHoNetGWSubnet = netaddr.IPNetwork(vboxHoNetGWIPAddr)

            # guestIPNetAddr = guestIP + "/" + ni.networkMask;
            # Create a /32 network address first and then get subnet based on net-mask of GW
            guestIPSubnet = netaddr.IPNetwork(guestIP) 
            guestIPSubnet.prefixlen = vboxHoNetGWSubnet.prefixlen

            # print " host-subnet: %s gw-subnet: %s)" % (str(guestIPSubnet), str(vboxHoNetGWSubnet))
            # print " host-subnet: %s gw-subnet: %s)" % (str(guestIPSubnet.network), str(vboxHoNetGWSubnet.network))
            # Check to see the subnet for guest-ip is same as subnet for host-only net GW interface.
            if (guestIPSubnet == vboxHoNetGWSubnet ) :
                return ni
        return None

    def getHostOnlyNetworkNameByGuestIP(self, guestIP):
        ni = self.getHostOnlyNetworkInterfaceByGuestIP(guestIP)
        if (ni != None):
            return str(ni.name)
        return None
    
    def getInternalNetworkInterfaces(self):
        # IHostNetworkInterface[]
        niList = self.vbox.getInternalNetworks();
        return niList
    
    
    def testHONetIfaces(self):
    
        # Command line args are in sys.argv[1], sys.argv[2] ...
        # sys.argv[0] is the script name itself and can be ignored
    
        niList = self.getNetworkInterfaces()
        for ni in niList:
            print "  %s (%s/%s)" % (ni.name, ni.IPAddress, ni.networkMask)
    
        print ""
        niNameList = self.getHostOnlyNetworkNames()
        print "  Vboxnets: ["
        for niName in niNameList:
            if (niName != None) :
                vboxnet = self.getNetworkInterfaceByName(niName)
                print "    " + str(niName) + " : " + str(vboxnet)
        print "  ]"
    
        print ""
        print "  Vboxnets: ["
        niList = self.getHostOnlyNetworkInterfaces()
        for ni in niList:
            print "  %s (%s/%s)" % (ni.name, ni.IPAddress, ni.networkMask)
        print "  ]"
    
        print ""
        guestIPList = ['10.10.0.11', '10.10.0.0', '10.10.1.12', '10.10.2.255', '10.10.3.0', '10.10.4.1',] 
        for guestIP in guestIPList:
            vboxnetName = self.getHostOnlyNetworkNameByGuestIP(guestIP)
            print "  %s ==> %s" % (guestIP, vboxnetName)
            if (vboxnetName != None) :
                vboxnet = self.getNetworkInterfaceByName(vboxnetName)
                print "    " + str(vboxnetName) + " : " + str(vboxnet)
    
        print ""
    
    def getVMList(self):
        vmlist = []
        if self.vbox is not None:
            vmlist = self.vbox.getMachines()
        else:
            vmlist = []
        return vmlist

    def getVMNetworkAdapaters(self, vm):
        # print "vm: " + vm.name 
        naList = []

        sysProps = self.vbox.systemProperties
        maxAdapters = sysProps.getMaxNetworkAdapters(vm.chipsetType)
        for slot in range(maxAdapters) :
            na = vm.getNetworkAdapter(slot)
            if (na != None and na.enabled):
                naList.append(na)
        # for na in naList:
        #     print "vm: %s naType: %s na.atType: %s enabled: %s" %(vm.name, na.adapterType, na.attachmentType, na.enabled)
        return naList

    def getVMTypedNetworkAdapaters(self, vm, natype):
        naList = self.getVMNetworkAdapaters(vm)
        typedNAList = []
        for na in naList:
            if (na.attachmentType == natype):
                typedNAList.append(na)
        return typedNAList

    def getVMTypedNetworkAdapterNames(self, vm, natype):
        typedNAList = self.getVMTypedNetworkAdapaters(vm, natype)

        typedNINameList = []
        for na in typedNAList:
            naName = None
            if (natype == virtualbox.library.NetworkAttachmentType.nat):        # 1
                naName = na.NATNetwork
            elif (natype == virtualbox.library.NetworkAttachmentType.bridged):  # 2
                naName = na.bridgedInterface
            elif (natype == virtualbox.library.NetworkAttachmentType.internal): # 3
                naName = na.internalNetwork
            elif (natype == virtualbox.library.NetworkAttachmentType.host_only): # 4
                naName = na.hostOnlyInterface
            elif (natype == virtualbox.library.NetworkAttachmentType.generic):   # 5
                naName = na.genericDriver
            elif (natype == virtualbox.library.NetworkAttachmentType.nat_network): # 6
                naName = na.NATNetwork
            else:
                naName = "Unattached"
            typedNINameList.append(naName)
        return typedNINameList

    def getVMInternalNetworkAdapaters(self, vm):
        naList = self.getVMTypedNetworkAdapaters(vm, virtualbox.library.NetworkAttachmentType.internal)
        return naList;

    def getVMInternalNetworkAdapterNames(self, vm):
        naNameList = self.getVMTypedNetworkAdapterNames(vm, virtualbox.library.NetworkAttachmentType.internal)
        return naNameList;

    def getVMHONetworkAdapaters(self, vm):
        naNameList = self.getVMTypedNetworkAdapaters(vm, virtualbox.library.NetworkAttachmentType.host_only)
        return naNameList;

    def getVMHONetworkAdapterNames(self, vm):
        naList = self.getVMTypedNetworkAdapterNames(vm, virtualbox.library.NetworkAttachmentType.host_only)
        return naList;

    def getNetworkAdapterName(self, na):
        naName = None
        natype = na.attachmentType;
        if (natype == virtualbox.library.NetworkAttachmentType.nat):        # 1
            naName = na.NATNetwork
        elif (natype == virtualbox.library.NetworkAttachmentType.bridged):  # 2
            naName = na.bridgedInterface
        elif (natype == virtualbox.library.NetworkAttachmentType.internal): # 3
            naName = na.internalNetwork
        elif (natype == virtualbox.library.NetworkAttachmentType.host_only): # 4
            naName = na.hostOnlyInterface
        elif (natype == virtualbox.library.NetworkAttachmentType.generic):   # 5
            naName = na.genericDriver
        elif (natype == virtualbox.library.NetworkAttachmentType.nat_network): # 6
            naName = na.NATNetwork
        else:
            naName = "Unattached"
        return naName

    def getAllTopoNetworkAdapaters(self, vmList):
        naList = []
        for vm in vmList:
            vmNAList = self.getVMNetworkAdapaters(vm);
            if (len(vmNAList) > 0) :
                naList.extend(vmNAList);
        return naList

    def getTopoNetworkAdapterNames(self, vmList):
        naList = self.getAllTopoNetworkAdapaters(vmList)
        naNameList = []
        for na in naList:
            naName = self.getNetworkAdapterName(na)
            naNameList.append(naName)
        return sorted(set(naNameList))

    def getTopoNetworkAdapaters(self, vmList):
        naNameList = self.getTopoNetworkAdapterNames(vmList)
        naList = []
        for naName in naNameList:
            na = None
            # na = self.getNetworkAdapterByName(naName)
            if (n != None):
                naNameList.append(na)
        return naList

    def getTopoTypedNetworkAdapaters(self, vmList, natype):
        naList = self.getAllTopoNetworkAdapaters(vmList)
        typedNAList = []
        for na in naList:
            if (na.attachmentType == natype):
                typedNAList.append(na)
        return typedNAList


    def getTopoTypedNetworkAdapterNames(self, vmList, natype):
        naList = self.getTopoTypedNetworkAdapaters(vmList, natype)

        naNameList = []
        for na in naList:
            naName = self.getNetworkAdapterName(na)
            naNameList.append(naName)
        return sorted(set(naNameList))

    def getTopoInternalNetworkAdapaters(self, vmList):
        naList = self.getTopoTypedNetworkAdapaters(vmList, virtualbox.library.NetworkAttachmentType.internal)
        return naList;

    def getTopoInternalNetworkAdapterNames(self, vmList):
        naNameList = self.getTopoTypedNetworkAdapterNames(vmList, virtualbox.library.NetworkAttachmentType.internal)
        return naNameList;

    def getTopoHONetworkAdapaters(self, vmList):
        naNameList = self.getTopoTypedNetworkAdapaters(vmList, virtualbox.library.NetworkAttachmentType.host_only)
        return naNameList;

    def getTopoHONetworkAdapterNames(self, vmList):
        naList = self.getTopoTypedNetworkAdapterNames(vmList, virtualbox.library.NetworkAttachmentType.host_only)
        return naList;


    def getMachineById(self, uuid):
        try:
            mach = self.vbox.getMachine(uuid)
        except:
            mach = self.vbox.findMachine(uuid)
        return mach
    
    def dumpVMInfo(self, vm):
        # print "vm: " + str(vm)
        if vm == None:
            return 
    
        print
        print "vm: " + vm.name + "{"
        sharedFolders = vm.getSharedFolders()
        print "    sharedFolders: (%s) {" % (len(sharedFolders)) 
        # for sf in ctx['manager'].getArray(vm, 'sharedFolders'):
        for sf in sharedFolders:
            print "        name=%s host=%s accessible: %s writable: %s" % (sf.name, sf.hostPath, sf.accessible, sf.writable)
        print "    }"

        naList = self.getVMNetworkAdapaters(vm)
        print "    Network Interfaces:" + pformat(naList, indent=4)

        inNAList = self.getVMInternalNetworkAdapaters(vm)
        print "    InternalNetwork Interfaces:" + pformat(inNAList, indent=4)

        for nat in virtualbox.library.NetworkAttachmentType._enums:
            name = nat[0]
            value = nat[1]
            typedNINameList = self.getVMTypedNetworkAdapterNames(vm, virtualbox.library.NetworkAttachmentType(value))
            print "    %s interfaces { %s }" % (name, ",".join(typedNINameList))
            # print ",".join(typedNINameList)
            # pprint(typedNINameList)
            # name = nat["name"]
            # print "}"

        inNINameList = self.getVMInternalNetworkAdapterNames(vm)
        print "    %s interfaces { %s }" % ("InternalNetwork", ",".join(inNINameList))

        hoNINameList = self.getVMHONetworkAdapterNames(vm)
        print "    %s interfaces : { %s }" % ("HostOnlyNetwork", ",".join(hoNINameList))
        print "}"


    def testVM(self, args):
        naList = []
        if len(args) >= 2:
            # print "usage: %s [vmname|uuid]" % (args[0])
            # return None
            uuid = args[1]

            # IMachine
            vm = self.vbox.findMachine(uuid)
            self.dumpVMInfo(vm)
        else: 
            vmlist = self.getVMList()
            for vm in vmlist:
                self.dumpVMInfo(vm)
            # end-of for
        # end-of if
    
    def dumpTopoInfo(self, vmList):

        naNameList = self.getTopoNetworkAdapterNames(vmList)
        print "    Network Interfaces { %s }" % (",".join(naNameList))

        # inNAList = self.getVMInternalNetworkAdapaters(vmList)
        # print "    InternalNetwork Interfaces:" + pformat(inNAList, indent=4)

        for nat in virtualbox.library.NetworkAttachmentType._enums:
            name = nat[0]
            value = nat[1]
            typedNINameList = self.getTopoTypedNetworkAdapterNames(vmList, virtualbox.library.NetworkAttachmentType(value))
            print "    %s interfaces { %s }" % (name, ",".join(typedNINameList))
            # print ",".join(typedNINameList)
            # pprint(typedNINameList)
            # name = nat["name"]
            # print "}"

        inNINameList = self.getTopoInternalNetworkAdapterNames(vmList)
        print "    %s interfaces { %s }" % ("InternalNetwork", ",".join(inNINameList))

        hoNINameList = self.getTopoHONetworkAdapterNames(vmList)
        print "    %s interfaces : { %s }" % ("HostOnlyNetwork", ",".join(hoNINameList))
        print "}"

    def testVMTopo(self, args):

        vmNameList = []
        if len(args) >= 2:
            # print "usage: %s [vmname|uuid]" % (args[0])
            # return None
            uuid = args[1]
            for i in (len(args) - 1) :
                vmNameList.append(args[i+1])
        else: 
            vmNameList = ['t6_VBN1-2VMX-31', 't6_VBN1-2VMX-32']
        # end-of if
        print "    vmList: { %s }" % (",".join(vmNameList))

        vmList = []
        for vmName in vmNameList:
            vm = self.vbox.findMachine(vmName)
            if (vm != None):
                vmList.append(vm)
            # end-of if
        # end-of for

        # for vm in vmList:
        #     self.dumpVMInfo(vm)

        naNameList = self.getTopoNetworkAdapterNames(vmList)
        print "    naNameList: { %s }" % (",".join(naNameList))
        self.dumpTopoInfo(vmList)

        # end-of for
    

# Gather our code in a main() function
def main():
    # Command line args are in sys.argv[1], sys.argv[2] ...
    # sys.argv[0] is the script name itself and can be ignored

    vbhoNetUtil = VBHONetUtil()

    # vbhoNetUtil.testHONetIfaces()
    # vbhoNetUtil.testVM(sys.argv)

    vbhoNetUtil.testVMTopo(sys.argv)

# Standard boilerplate to call the main() function to begin
# the program.
if __name__ == '__main__':
    main()
