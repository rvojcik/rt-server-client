#!/usr/bin/python
#
# This is server-audit script for Racktables project
# It discover system, import or update infromation into racktables database
# 
# Script support following infromation
#   * hostname
#    * service tag
#    * supermicro exeption for service tag (same service tag and express servicetag for all machines)
#    * for Dell servers it retrieve support type and support expiration date
#    * Physical and logical interfaces (eth,bond,bridges)
#    * IPv4 and IPv6 IP addresses, import and update in database
#    * Dell Drack IP address (require Dell-OMSA Installed)
#    * OS Dristribution and Release information
#    * HW vendor and product type
#    * Hypervisor recognition (Xen 4.x)
#    * Virtual server recognition (Xen 4.x)
#    * Link Virtual server with hypervisor as container in Racktables
#    * Racktables logging - when change ip addresses or virtual link with hypervisor
#
#    This utility is released under GPL v2
#    
#    Server Audit utility for Racktables Datacenter management project.
#    Copyright (C) 2012  Robert Vojcik (robert@vojcik.net)
#    
#    This program is free software; you can redistribute it and/or
#    modify it under the terms of the GNU General Public License
#    as published by the Free Software Foundation; either version 2
#    of the License, or (at your option) any later version.
#    
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#    
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import sys
import os
import commands
import platform
from ConfigParser import ConfigParser
import time
import datetime
import re
import random
import shutil
import argparse

# Get script path
script_path = os.path.dirname(sys.argv[0])

# Add local module path
sys.path.append(script_path + '/lib/')

import ipaddr
import MySQLdb
from ToolBox import net, dell
import rtapi

config_path = script_path + "/conf/"
motd_file_original = "/etc/motd.ls.orig"
motd_file = "/etc/motd"

# Sleep for some seconds. When running on 200 hosts in same second, local dns should have a problem with it
#time.sleep(random.randint(1,12))


try:
    config_file = open(config_path + "main.conf")
except IOError ,e:
    print("({})".format(e))
    sys.exit()

# Parsing config options
config = ConfigParser()
config.readfp(config_file)

# Close config
config_file.close()

# Parsing arguments {{{
parser = argparse.ArgumentParser(
    description= 'Racktables server client',
    epilog='Created by Robert Vojcik <robert@vojcik.net>')
parser.add_argument("-d", action="store_true", dest="debug_mode", default=False, help="Debug mode")
parser.add_argument("--init-racktables", action="store_true", dest="init_mode", default=False, help="Init or check racktables DB for specials")

args = parser.parse_args()
# END PARSING ARGUMENTS }}}

#### Init Mode
if args.init_mode:
    print "Init mode "
    sys.exit(0)

#### END Init Mode

def print_debug(text):
    """Prind debug information"""
    if args.debug_mode:
        print "DEBUG ",text


def GenerateServiceTag(size):
    """Service tag generator"""

    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    digits = "0123456789"
    chars = letters + digits

    service_tag = "".join(random.choice(chars) for x in range(size))

    print_debug("Generated service tag: " + service_tag)

    return service_tag

def GetVirtualServers(virtualization):
    """Create list of virtual servers"""

    if virtualization == 'xen':
        print_debug("Virtualization is XEN")
        output = commands.getoutput('xm list')
        virtuals = [] 

        for line in output.splitlines()[2:]:
            virtual = line.split()[0]
            virtuals.append(virtual)

    if virtualization == 'vz':
        output = commands.getoutput('vzlist')
        virtuals = [] 

        for line in output.splitlines()[1:]:
            virtual = line.split()[4]
            virtuals.append(virtual)

    print_debug("I found virtuals: " + str(virtuals))
   

    return virtuals

# System examination {{{
# Get interface list into interfaces list
device_list = net.get_interfaces()
print_debug("Founded interfaces: " + str(device_list))

# Get ip address for each interface
# Get connections from lldp
# Empty list for connections
interface_connections = []
interfaces_ips = []
interfaces_ips6 = []
interfaces_mac = []

# CPU information
# Read /proc/cpuinfo into variable
cpu_proc = open('/proc/cpuinfo')
file_c = cpu_proc.read()
cpu_proc.close()

# Get number of logical CPUs
cpu_logical_num = file_c.count('processor')
# Get CPU Model Name
cpu_model_name = re.sub(' +',' ',re.findall('model name.*',file_c)[0].split(': ')[1])
# Physical CPU information
lscpu_output = commands.getstatusoutput('lscpu')
if lscpu_output[0] == 0:
    lscpu = lscpu_output[1]
    try:
        cpu_num = int(re.findall('CPU socket.*',lscpu)[0].split(':')[1].strip())
    except:
        cpu_num = int(re.findall('Socket\(s\).*',lscpu)[0].split(':')[1].strip())
    cpu_cores = int(re.findall('Core\(s\) per socket.*',lscpu)[0].split(':')[1].strip())
    cpu_mhz = int(re.findall('CPU MHz.*',lscpu)[0].split(':')[1].strip().split('.')[0])
else:
    cpu_num = ""
    cpu_cores = ""
    cpu_mhz = ""
# Commenting out as if lscpu is missing the following fails on a physical server
print_debug("CPU INFO: cpu_num=%d, cpu_cores=%d, cpu_mhz=%d, cpu_logical_num=%d, cpu_model_name=%s" % (cpu_num, cpu_cores, cpu_mhz, cpu_logical_num, cpu_model_name))

# Check for virtualization 

# Default it's not hypervisor and no virtualization
hypervisor = "no"
server_type_id = 4

# QEMU / KVM
if re.match('.*QEMU.*', cpu_model_name):
    server_type_id = 1504
    print_debug("Hypervisor test: Hypervisor: %s, Server Type: %d" % (hypervisor, server_type_id))

#VMware
output = commands.getoutput('lspci | grep -i VMware | wc -l')
if output >= '20':
    # Default it's not hypervisor and virtualization
    hypervisor = "no"
    server_type_id = 1504
    print_debug("Hypervisor test: Hypervisor: %s, Server Type: %d" % (hypervisor, server_type_id))

# XEN
if os.path.isdir('/proc/xen'):
    if not os.path.isfile('/proc/xen/xenbus'):
        #It is xen virtual server
        hypervisor = "no"
        server_type_id = 1504
        print_debug("Hypervisor test: Hypervisor: %s, Server Type: %d" % (hypervisor, server_type_id))
    else:
        hypervisor = "yes" 
        print_debug("Hypervisor test: Hypervisor: %s, Server Type: %d" % (hypervisor, server_type_id))
        virtual_servers = GetVirtualServers('xen')
    
# OpenVZ
if os.path.isdir('/proc/vz'):
    #It is OpenVZ technology
    if os.path.isfile('/proc/vz/veinfo'):
        #It is OpenVZ Hypervisor
        hypervisor = "yes"
        print_debug("Hypervisor test: Hypervisor: %s, Server Type: %d" % (hypervisor, server_type_id))
        virtual_servers = GetVirtualServers('vz')
    else:
        hypervisor = "no"
        server_type_id = 1504
        print_debug("Hypervisor test: Hypervisor: %s, Server Type: %d" % (hypervisor, server_type_id))

product_name = ''
service_tag = ''
vendor = ''
if server_type_id == 4:
    # Get service tag
    # Server type, model
    getsystemid = commands.getoutput('getSystemId 2>/dev/null')
    print_debug("GetSystemId: %s" % (str(getsystemid)))

    if re.findall('\nProduct Name:.*',getsystemid):
        try:
            product_name = " ".join(str(x) for x in re.findall('\nProduct Name:.*',getsystemid)[0].split()[2:])
        except:
            product_name = "n/a"
    else:
        product_name = "unknown"
    print_debug("Product name: %s" % (str(product_name)))

    if re.findall('\nService Tag:.*',getsystemid):
        try:
            service_tag = re.findall('\nService Tag:.*',getsystemid)[0].split()[2]
        except:
            service_tag = ""
    else:
        service_tag = ""

    if re.findall('\nVendor:.*',getsystemid):
        try:
            vendor = re.findall('\nVendor:.*',getsystemid)[0].split()[1]
        except:
            vendor = "unknown"
    else:
        vendor = "unknown"

    if ( vendor == "Supermicro" or vendor == "unknown" ):
    # There is no way to get uniq identificator of supermicro servers, we must generate some
        stag_path = '/var/opt/service_tag_generated.txt'

        if os.path.isfile(stag_path):
            try:
                stag_file = open(stag_path)
            except IOError ,e:
                print("({})".format(e))
                sys.exit()
        
            service_tag = stag_file.read()
        else:
            service_tag = GenerateServiceTag(10)

            stag_file = open(stag_path, 'w')
            stag_file.write(service_tag)
            stag_file.close()
    print_debug("Vendor: %s" % (str(vendor)))

    chkhp = commands.getoutput('dmidecode -s "system-manufacturer"')
    if chkhp == 'HP':
        vendor = output
        # Default it's not hypervisor and virtualization
        hypervisor = "no"
        server_type_id = 4
        service_tag =  commands.getoutput('dmidecode -s "system-serial-number"')
        product_name = commands.getoutput('dmidecode -s "system-product-name"')
        print_debug("Hypervisor test: Hypervisor: %s, Server Type: %d" % (hypervisor, server_type_id))

# Get Memory info
meminfo = open('/proc/meminfo')
file_c = meminfo.read()
meminfo.close()
memory_mb = int(file_c.split()[1]) / 1024
print_debug("Memory MB: %d" % (memory_mb))

# Network Interfaces LLDP Connections
for interface in device_list:
    # Default values
    switch_name = ''
    switch_port = ''
    # Get ip addresses
    interfaces_ips.append(net.get_ip4_addr(interface))
    interfaces_ips6.append(net.get_ip6_addr(interface))
    interfaces_mac.append(net.get_hw_addr(interface))
    # Get lldp
    lldp_output = commands.getoutput('lldpctl -f keyvalue ' + interface)

    #Test if it's juniper or Force10, otherwise skip this discovery becouse unsupported device
    # For JUniper
    if lldp_output.find('Juniper') > -1:
        for line in lldp_output.split('\n'):
            if line.find('lldp.'+interface+'.chassis.name') > -1:
                switch_name = line.split('=')[1]
            elif line.find('lldp.'+interface+'.port.descr') > -1:
                switch_port = line.split('=')[1]
    # For Force10
    elif lldp_output.find('Force10') > -1:
        for line in lldp_output.split('\n'):
            if line.find('lldp.'+interface+'.chassis.name') > -1:
                switch_name = line.split('=')[1]
            elif line.find('lldp.'+interface+'.port.ifname') > -1:
                switch_port = line.split('=')[1]
    
    #add connection to list
    connection = [switch_name, switch_port]
    interface_connections.append(connection)

    print_debug("Found ips: %s" % (str(interfaces_ips)))
    print_debug("Found ips6: %s" % (str(interfaces_ips6)))
    print_debug("Found mac: %s" % (str(interfaces_mac)))
    print_debug("Found interface connections: %s" % (str(interface_connections)))

# OS, type, release
os_distribution, os_version, os_codename = platform.dist()
# Stupid debian, empty os_codename
if os_codename == '':
    for line in commands.getoutput('lsb_release -a').split('\n'):
        if line.find('Codename:') > -1:
            os_codename = line.split()[1]

if os_distribution == "Ubuntu":
    os_searchstring = os_distribution+"%"+os_version
else:
    os_searchstring = os_distribution+"%"+os_codename

print_debug("OS Info: %s %s %s" % (os_distribution, os_version, os_codename))
print_debug("OS Search string:%s" % (os_searchstring))


# Get Drac IP
output = commands.getstatusoutput('omreport chassis remoteaccess config=nic')

if output[0] == 0:
    drac_ip = re.findall('[0-9]{0,3}\.[0-9]{0,3}\.[0-9]{0,3}\.[0-9]{0,3}',output[1])[0]
else:
    drac_ip = ''
print_debug("Drac IP: %s" % (drac_ip))
# Get label from Drac (display)

output = commands.getstatusoutput('omreport chassis frontpanel')

if output[0] == 0:
    try:
        line = re.findall('LCD Line 1.*',output[1])[0]
        label = line.split(' ')[4]
        update_label = "yes"
    except:
        update_label = "no"
        label = ""
else:
    update_label = "no"
    label = ""
print_debug("Drac Label: update=%s, text=%s" % (update_label, label))

# Get hostname
hostname = platform.node()
print_debug("Hostname: " + hostname)
# Get Kernel version
kernel_version = platform.release()
print_debug("Kernel: " + kernel_version)

# Workaround for VPS and servicetag
if server_type_id == 1504:
    service_tag = "VPS-"+hostname
    print_debug("VPS Service tag: " + service_tag)

print_debug("Service TAG: %s" % (str(service_tag)))
# System examination }}}

## Main Database part

# Create connection to database
try:
    # Create connection to database
    db = MySQLdb.connect(host=config.get('mysqldb','host'),port=3306, passwd=config.get('mysqldb','password'),db=config.get('mysqldb','db'),user=config.get('mysqldb','user'))
except MySQLdb.Error ,e:
    print "Error %d: %s" % (e.args[0],e.args[1])
    sys.exit(1)


# Initialize rtapi object
rtobject = rtapi.RTObject(db)


if not rtobject.ObjectExistST(service_tag):
    print_debug("Object with service tag %s is not in DB" % (service_tag))
    #
    # service tag not exist
    #
    if not rtobject.ObjectExistName(hostname):
        print_debug("Object with hostname %s is not in DB" % (hostname))
        # hostname not exist = insert new server Object
        rtobject.AddObject(hostname,server_type_id,service_tag,label)
        object_id = rtobject.GetObjectId(hostname)

        # Insert attributes, OS info and waranty
        #get id of OS
        os_id = rtobject.GetDictionaryId(os_searchstring)
        attr_id = rtobject.GetAttributeId("SW type")
        if os_id != None:
            rtobject.InsertAttribute(object_id,server_type_id,attr_id,"NULL",os_id,hostname)

        
        if server_type_id == 4:
            #get id of HW
            words = product_name.split()
            searchstring = vendor+"%"+"%".join(str(x) for x in words)
            hw_id = rtobject.GetDictionaryId(searchstring)
            #insert os and hw info
            attr_id = rtobject.GetAttributeId("HW type")
            if hw_id != None:
                rtobject.InsertAttribute(object_id,server_type_id,attr_id,"NULL",hw_id,hostname)


            # Insert CPU and Memory Information
            if cpu_model_name != "":
                rtobject.InsertAttribute(object_id,server_type_id,rtobject.GetAttributeId("CPU Model"),cpu_model_name,"NULL",hostname)
            if cpu_logical_num != "":
                rtobject.InsertAttribute(object_id,server_type_id,rtobject.GetAttributeId("CPUs Logical"),"NULL",cpu_logical_num,hostname)
            if cpu_num != "":
                rtobject.InsertAttribute(object_id,server_type_id,rtobject.GetAttributeId("CPUs"),"NULL",cpu_num,hostname)
            if cpu_cores != "":
                rtobject.InsertAttribute(object_id,server_type_id,rtobject.GetAttributeId("Cores per CPU"),"NULL",cpu_cores,hostname)
            if cpu_mhz != "":
                rtobject.InsertAttribute(object_id,server_type_id,rtobject.GetAttributeId("CPU, MHz"),"NULL",cpu_mhz,hostname)
            if memory_mb != "":
                rtobject.InsertAttribute(object_id,server_type_id,rtobject.GetAttributeId("RAM Mem, MB"),"NULL",memory_mb,hostname)


            if hypervisor == "yes":
                searchstring = "Hypervisor"
                attid_hyp = rtobject.GetAttributeId(searchstring)
                rtobject.InsertAttribute(object_id,server_type_id,attid_hyp,'NULL',1501,hostname)
                if len(virtual_servers) != 0:
                    rtobject.CleanVirtuals(object_id,virtual_servers)
                    for virtual_name in virtual_servers:
                        virtual_id = rtobject.GetObjectId(virtual_name)   
                        if virtual_id != None:
                            rtobject.LinkVirtualHypervisor(object_id,virtual_id)


            if len(drac_ip) != 0:
                rtobject.UpdateNetworkInterface(object_id,'drac')
                rtobject.InterfaceAddIpv4IP(object_id,'drac',drac_ip)


        for device in device_list:
            #Add/update network interface
            port_id = rtobject.UpdateNetworkInterface(object_id,device)
            #Add network connections
            if interface_connections[device_list.index(device)] != '':
                rtobject.LinkNetworkInterface(object_id,device,interface_connections[device_list.index(device)][0],interface_connections[device_list.index(device)][1])
            #Add IPv4 ips
            if interfaces_ips[device_list.index(device)] != '':
                for ip in interfaces_ips[device_list.index(device)]:
                    rtobject.InterfaceAddIpv4IP(object_id,device,ip)
            #Add IPv6 ips
            if interfaces_ips6[device_list.index(device)] != '':
                for ip in interfaces_ips6[device_list.index(device)]:
                    rtobject.InterfaceAddIpv6IP(object_id,device,ip)
            #Add MAC address
            if interfaces_mac[device_list.index(device)] != '':
                mac = interfaces_mac[device_list.index(device)]
                print_debug("Calling InterfaceAddMAC(%d,%s,%s)"%(object_id, device, mac))
                rtobject.InterfaceAddMAC(object_id,device,mac)


    else:
        #
        # hostname exist, what to do?
        #
        print "Hostname %s already exist. I'm using service tag: %s" % (hostname,service_tag)
else:
    #
    # service tag exist
    #
    #check if hostname is the same
    print_debug("Object with service tag %s is already in DB" % (service_tag))
    if rtobject.ObjectExistName(hostname):
        print_debug("Object with hostname %s is already in DB" % (hostname))
        # hostname exist and service tag is same, update info

        if rtobject.ObjectExistSTName(hostname, service_tag):
            object_id = rtobject.GetObjectId(hostname)
            object_label = rtobject.GetObjectLabel(object_id)
        else:
            print "Can't do it. Hostname %s and service-tag %s already exist, but does not belong to the same server"% (hostname, service_tag)
            sys.exit(1)

        #Update label if it's not same
        if update_label == "yes":
            if label != object_label:
                rtobject.UpdateObjectLabel(object_id, label)
                logstring = "Label changed %s -> %s" % (object_label,label)
                rtobject.InsertLog(object_id,logstring)

        #get id of OS
        os_id = rtobject.GetDictionaryId(os_searchstring)
        attr_id = rtobject.GetAttributeId("SW type")
        if os_id != None:
            rtobject.InsertAttribute(object_id,server_type_id,attr_id,"NULL",os_id,hostname)

        if server_type_id == 4:
            #get id of HW
            words = product_name.split()
            searchstring = vendor+"%"+"%".join(str(x) for x in words)
            hw_id = rtobject.GetDictionaryId(searchstring)
            
            #insert os and hw info
            attr_id = rtobject.GetAttributeId("HW type")
            if hw_id != None:
                rtobject.InsertAttribute(object_id,server_type_id,attr_id,"NULL",hw_id,hostname)


            # Insert CPU and Memory Information
            if cpu_model_name != "":
                rtobject.InsertAttribute(object_id,server_type_id,rtobject.GetAttributeId("CPU Model"),cpu_model_name,"NULL",hostname)
            if cpu_logical_num != "":
                rtobject.InsertAttribute(object_id,server_type_id,rtobject.GetAttributeId("CPUs Logical"),"NULL",cpu_logical_num,hostname)
            if cpu_num != "":
                rtobject.InsertAttribute(object_id,server_type_id,rtobject.GetAttributeId("CPUs"),"NULL",cpu_num,hostname)
            if cpu_cores != "":
                rtobject.InsertAttribute(object_id,server_type_id,rtobject.GetAttributeId("Cores per CPU"),"NULL",cpu_cores,hostname)
            if cpu_mhz != "":
                rtobject.InsertAttribute(object_id,server_type_id,rtobject.GetAttributeId("CPU, MHz"),"NULL",cpu_mhz,hostname)
            if memory_mb != "":
                rtobject.InsertAttribute(object_id,server_type_id,rtobject.GetAttributeId("RAM Mem, MB"),"NULL",memory_mb,hostname)

            if hypervisor == "yes":
                searchstring = "Hypervisor"
                attid_hyp = rtobject.GetAttributeId(searchstring)
                rtobject.InsertAttribute(object_id,server_type_id,attid_hyp,'NULL',1501,hostname)
                if len(virtual_servers) != 0:
                    rtobject.CleanVirtuals(object_id,virtual_servers)
                    for virtual_name in virtual_servers:
                        virtual_id = rtobject.GetObjectId(virtual_name)   
                        if virtual_id != None:
                            rtobject.LinkVirtualHypervisor(object_id,virtual_id)

            if len(drac_ip) != 0:
                rtobject.UpdateNetworkInterface(object_id,'drac')
                drac_list = [drac_ip]
                rtobject.CleanIPAddresses(object_id,drac_list,'drac')
                rtobject.InterfaceAddIpv4IP(object_id,'drac',drac_ip)


        # Clean unused interfaces
        rtobject.CleanUnusedInterfaces(object_id, device_list)

        for device in device_list:
            #Add/update network interface
            port_id = rtobject.UpdateNetworkInterface(object_id,device)
            #Add network connections
            if interface_connections[device_list.index(device)] != '':
                rtobject.LinkNetworkInterface(object_id,device,interface_connections[device_list.index(device)][0],interface_connections[device_list.index(device)][1])
            #Add IPv4 ips
            if interfaces_ips[device_list.index(device)] != '':
                rtobject.CleanIPAddresses(object_id,interfaces_ips[device_list.index(device)],device)
                for ip in interfaces_ips[device_list.index(device)]:
                    rtobject.InterfaceAddIpv4IP(object_id,device,ip)
            #Add IPv6 ips
            if interfaces_ips6[device_list.index(device)] != '':
                rtobject.CleanIPv6Addresses(object_id,interfaces_ips6[device_list.index(device)],device)
                for ip in interfaces_ips6[device_list.index(device)]:
                    rtobject.InterfaceAddIpv6IP(object_id,device,ip)
            #Add MAC address
            if interfaces_mac[device_list.index(device)] != '':
                mac = interfaces_mac[device_list.index(device)]
                print_debug("Calling InterfaceAddMAC(%d,%s,%s)"%(object_id, device, mac))
                rtobject.InterfaceAddMAC(object_id,device,mac)

        # Update motd from comment And Tags
        comment = rtobject.GetObjectComment(object_id)

        #Prepare tag comment
        tags_list = rtobject.GetObjectTags(object_id)
        tag_array={}
        comment_tag=''
        for tag_row in tags_list:
                #tag_array[tag_row[0]]
            if not tag_array.get(tag_row[0]):
                tag_array[tag_row[0]] = []
            tag_array[tag_row[0]].append(tag_row[1])
        for key in tag_array.keys():
            if key:
                comment_tag = comment_tag + key + ": " 
            for tag in tag_array[key]:
                comment_tag = comment_tag + tag + " "
            comment_tag = comment_tag + "\n"

        if comment != None:
            # copy template to motd, if no exist make tamplate from motd
            try:
                shutil.copy2(motd_file_original, motd_file)
            except IOError :
                shutil.copy2(motd_file,motd_file_original)
            
            motd_open_file = open(motd_file, "a")
            motd_open_file.write("\n\033[34m--- tags ---\033[33m\n\n" + comment_tag + "\033[0m")
            motd_open_file.write("\n\033[34m--- comment ---\033[33m\n\n" + comment + "\033[0m\n")
            motd_open_file.close()

    else:
        #Hostname is different
        print "Service tag %s already exist, but hostname is different." % service_tag

db.close()
