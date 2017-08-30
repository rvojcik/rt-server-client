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
#FOR MAC
import fcntl
import socket
import struct
#END

# Get script path
script_path = os.path.dirname(sys.argv[0])

# Add local module path
sys.path.append(script_path + '/lib/')

import ipaddr
import MySQLdb
from ToolBox import net, dell, base
import rtapi

config_path = script_path + "/conf/"
motd_file_original = "/etc/motd.ls.orig"
motd_file = "/etc/motd"

# Default config file
main_config = "main.conf"

##
## Parsing arguments
##
parser = argparse.ArgumentParser(
    description= 'Server audit automation system for RackTables',
    epilog='Created by Robert Vojcik <robert@vojcik.net>')

parser.add_argument("-f", dest="force_init", default=False, action="store_true", help="Force initialization, automaticly rewrite hostname")
parser.add_argument("-d", dest="debug_mode", default=False, action="store_true", help="Debug mode")

args = parser.parse_args()
##
## END Parsing arguments
##

# Debug mode
debug = base.Debug(args)


try:
    config_file = open(config_path + main_config)
    debug.print_message("Opening config: "+config_path+main_config)
except IOError ,e:
    print("({})".format(e))
    sys.exit()

# Parsing config options
config = ConfigParser()
config.readfp(config_file)

# Close config
config_file.close()

#FOR MAC
def getHwAddr(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', ifname[:15]))
    return ''.join(['%02x' % ord(char) for char in info[18:24]])
#END


def GetVirtualServers(virtualization):
    """Create list of virtual servers"""

    if virtualization == 'xen':
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
   

    return virtuals


# Sleep for some seconds. When running on 200 hosts in same second, local dns should have a problem with it
if not args.debug_mode:
    time.sleep(random.randint(1,12))

# Get interface list into interfaces list and filter docker interfaces
device_list = net.get_interfaces()
debug.print_message("Device list: "+str(device_list))

# Get ip address for each interface
# Get connections from lldp
# Empty list for connections
interface_connections = []
interfaces_ips = []
interfaces_ips6 = []

# Check for virtualization 
if not os.path.isdir('/proc/xen'):
    #Je to server
    server_type_id = 4
    hypervisor = "no"
    debug.print_message("Server is physical normal server")
else:
    if not os.path.isfile('/proc/xen/xenbus'):
        #Je to virtual
        server_type_id = 1504
        hypervisor = "no"
        debug.print_message("Server is virtual")
    else:
        #Je to hypervisor
        server_type_id = 4
        hypervisor = "yes"
        virtual_servers = GetVirtualServers()
        debug.print_message("Server is hypervisor")
        debug.print_message("Virtuals: "+str(virtual_servers))


product_name = ''
vendor = ''
# Get hostname
hostname = platform.node()
if server_type_id == 4:
    # Get service tag
    # Server type, model
    product_name = commands.getoutput('/opt/server-audit/get-bios-ident.py -s -m')
    debug.print_message("Product name: "+product_name)

    service_tag = commands.getoutput('/opt/server-audit/get-bios-ident.py -s -t')
    debug.print_message("Service Tag: "+service_tag)

    vendor = commands.getoutput('/opt/server-audit/get-bios-ident.py -s -v')
    debug.print_message("Vendor: "+vendor)


# Workaround for VPS and servicetag
elif server_type_id == 1504:
    service_tag = "VPS-"+hostname
    debug.print_message("VPS Service Tag override: "+service_tag)
else:
    service_tag = commands.getoutput('/opt/server-audit/get-bios-ident.py -s -t')

debug.print_message("Hostname: "+hostname)

# CPU information
# Read /proc/cpuinfo into variable
cpu_proc = open('/proc/cpuinfo')
file_c = cpu_proc.read()
cpu_proc.close()

# Get number of logical CPUs
cpu_logical_num = file_c.count('processor')
debug.print_message("Logical CPU num: "+str(cpu_logical_num))

# Get CPU Model Name
cpu_model_name = re.sub(' +',' ',re.findall('model name.*',file_c)[0].split(': ')[1])
debug.print_message("CPU model name: "+cpu_model_name)

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

debug.print_message("CPU NUM, CPU Cores, CPU Mhz: %s, %s, %s" % (cpu_num, cpu_cores, cpu_mhz))

# Get Memory info
meminfo = open('/proc/meminfo')
file_c = meminfo.read()
meminfo.close()
memory_mb = int(file_c.split()[1]) / 1024
debug.print_message("Memory MB: %s" % (str(memory_mb)))

# Network Interfaces LLDP Connections
for interface in device_list:
    debug.print_message("Processing interface " + interface)
    # Default values
    switch_name = ''
    switch_port = ''
    # Get ip addresses
    interfaces_ips.append(net.get_ip4_addr(interface))
    debug.print_message("IPv4: "+str(interfaces_ips))

    interfaces_ips6.append(net.get_ip6_addr(interface))
    debug.print_message("IPv6: "+str(interfaces_ips6))

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
    debug.print_message("Connection: "+str(connection))
    interface_connections.append(connection)


# OS, type, release
os_distribution, os_version, os_codename = platform.dist()

# Stupid debian, empty os_codename
if os_codename == '':
    for line in commands.getoutput('lsb_release -a').split('\n'):
        if line.find('Codename:') > -1:
            os_codename = line.split()[1]
debug.print_message("os_dist, os_version, os_codename: " + str([os_distribution, os_version, os_codename]))

# Get Drac IP
management_ip_commands = ['omreport chassis remoteaccess config=nic' , 'ipmitool lan print']
drac_ip = ''
for mgmcommand in management_ip_commands:
    output = commands.getstatusoutput(mgmcommand)
    if output[0] == 0:
        drac_ip = re.findall('[0-9]{0,3}\.[0-9]{0,3}\.[0-9]{0,3}\.[0-9]{0,3}',output[1])[0]
        break
debug.print_message("Drac IP: "+drac_ip)


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
debug.print_message("label, update_label: %s %s" % (label, update_label))


# If hostname and label not match, try to configure LCD
if hostname != label:
    if commands.getstatusoutput('omconfig chassis frontpanel config=custom lcdindex=1 text="' + hostname + '"')[0] == 0:
        label = hostname
        update_label = "yes"
debug.print_message("label, update_label: %s %s" % (label, update_label))

# Get support and waranty for service tag
#if service_tag == '':
#    support_type = ''
#    support_ends = ''
#else:
#    dell_list = dell.get_waranty_info(service_tag)
#    if dell_list != None:
#        support_type, support_ends = dell_list
#    else:
#        support_type = ''
#        support_ends = ''

# Get Kernel version
kernel_version = platform.release()
debug.print_message("Kernel: "+kernel_version)

## Main Database part

# Create connection to database
try:
    # Create connection to database
    debug.print_message("Database connection [host, port, passwd, database, user] = [ %s, %s, %s, %s, %s ]" % (config.get('mysqldb','host'),"3306", "xxxxxx",config.get('mysqldb','db'),config.get('mysqldb','user'))) 
    db = MySQLdb.connect(host=config.get('mysqldb','host'),port=3306, passwd=config.get('mysqldb','password'),db=config.get('mysqldb','db'),user=config.get('mysqldb','user'))
except MySQLdb.Error ,e:
    print "Error %d: %s" % (e.args[0],e.args[1])
    sys.exit(1)


# Initialize rtapi object
debug.print_message("Initializing RT Api object")
rtobject = rtapi.RTObject(db)


debug.print_message("STARTING MAIN DATABASE INSERTION/UPDATE")
if not rtobject.ObjectExistST(service_tag):
    #
    # service tag not exist
    #
    debug.print_message("Service tag not exist in database")
    if not rtobject.ObjectExistName(hostname):
        # hostname not exist = insert new server Object
        rtobject.AddObject(hostname,server_type_id,service_tag,label)
        object_id = rtobject.GetObjectId(hostname)
        debug.print_message("Added new object to database %s with ID %s" % (str([hostname,server_type_id,service_tag,label]), str(object_id)))

        # Insert attributes, OS info and waranty
        #get id of OS
        searchstring = os_distribution+"%"+os_codename
        os_id = rtobject.GetDictionaryId(searchstring)
        attr_id = rtobject.GetAttributeId("SW type")
        debug.print_message("SW Type, searching for: %s , Found: %s, Updating: %s" %(searchstring, str(os_id), str(attr_id)))
        if os_id != None:
            rtobject.InsertAttribute(object_id,server_type_id,attr_id,"NULL",os_id,hostname)
            debug.print_message("Inserting OS attribute: obj_id=%d srv_type_id=%d attr_id=%d os_id=%d hostname=%s" % (object_id,server_type_id,attr_id,os_id,hostname))
        else:
            debug.print_message("OS id not found in racktables")

        
        if server_type_id == 4:
            #get id of HW
            words = product_name.split()
            searchstring = vendor+"%"+"%".join(str(x) for x in words)
            hw_id = rtobject.GetDictionaryId(searchstring)
            #insert os and hw info
            attr_id = rtobject.GetAttributeId("HW type")
            debug.print_message("HW Type, searching for: %s , Found: %s, Updating: %s" %(searchstring, str(hw_id), str(attr_id)))
            if hw_id != None:
                rtobject.InsertAttribute(object_id,server_type_id,attr_id,"NULL",hw_id,hostname)
                debug.print_message("Inserting HW attribute: obj_id=%d srv_type_id=%d attr_id=%d hw_id=%d hostname=%s" % (object_id,server_type_id,attr_id,hw_id,hostname))
            else:
                debug.print_message("HW id not found in racktables")


            # Insert CPU and Memory Information
            debug.print_message("Inserting CPU attribute information")
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
                debug.print_message("Hypervisor, searching for: %s , Found: %s" %(searchstring, str(attid_hyp)))
                if len(virtual_servers) != 0:
                    rtobject.CleanVirtuals(object_id,virtual_servers)
                    for virtual_name in virtual_servers:
                        virtual_id = rtobject.GetObjectId(virtual_name)   
                        if virtual_id != None:
                            rtobject.LinkVirtualHypervisor(object_id,virtual_id)
                            debug.print_message("Virtual Linking id:%s with %s(%s)" %(str(object_id), str(virtual_id), str(virtual_name)))


            if len(drac_ip) != 0:
                rtobject.UpdateNetworkInterface(object_id,'drac')
                rtobject.InterfaceAddIpv4IP(object_id,'drac',drac_ip)
                debug.print_message("Inserting Drac IP")


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

        # Set Installation Date 
        rtobject.InsertAttribute(object_id,server_type_id,rtobject.GetAttributeId("Installation Date"),"NULL",int(time.time()),hostname)
        rtobject.InsertLog(object_id, "Server-Audit insert instalation date")
        debug.print_message("Inserting installation date: "+str(time.time()))


    else:
        #
        # hostname exist, what to do?
        #
        print "Hostname %s already exist. I'm using service tag: %s" % (hostname,service_tag)
        debug.print_message("Hostname %s already exist. My Service Tag is %s" % (hostname,service_tag))
else:
    #
    # service tag exist
    #
    #check if hostname is the same
    if (rtobject.ObjectExistName(hostname)) or (args.force_init) :

        if args.force_init:
            debug.print_message("Force initialization enabled")
            debug.print_message("Updating hostname")
            rtobject.UpdateObjectName(rtobject.GetObjectId(rtobject.GetObjectNameByAsset(service_tag)), hostname)
        else:
            # hostname exist and service tag is same, update info
            debug.print_message("Hostname already in DB, service tag is matching. Updating information in DB")

        if rtobject.ObjectExistSTName(hostname, service_tag):
            object_id = rtobject.GetObjectId(hostname)
            object_label = rtobject.GetObjectLabel(object_id)
            debug.print_message("Object id is: %s and label %s" %(str(object_id), object_label))
        else:
            print "Can't do it. Hostname %s and service-tag %s already exist, but does not belong to the same server"% (hostname, service_tag)
            debug.print_message("Can't do it. Hostname %s and service-tag %s already exist, but does not belong to the same server"% (hostname, service_tag))
            sys.exit(1)

        # Update Zaloha attribute
        if args.force_init:
            debug.print_message("Updating Zaloha attribute")
            rtobject.InsertAttribute(object_id,server_type_id,rtobject.GetAttributeId("Zaloha"),'NULL',1500,hostname)


        #Update label if it's not same
        if update_label == "yes":
            if label != object_label:
                rtobject.UpdateObjectLabel(object_id, label)
                logstring = "Label changed %s -> %s" % (object_label,label)
                rtobject.InsertLog(object_id,logstring)
                debug.print_message("Updating old label ( %s ) with new ( %s )" %(object_label, label))
            else:
                debug.print_message("Label is same, skip update")

        # Set Installation date if it's blank
        result = rtobject.GetAttributeValue(object_id, rtobject.GetAttributeId("Installation Date"))
        if result == None:
            rtobject.InsertAttribute(object_id,server_type_id,rtobject.GetAttributeId("Installation Date"),"NULL",int(time.time()),hostname)
            rtobject.InsertLog(object_id, "Server-Audit insert instalation date")
            debug.print_message("Installation date is blank, setting actual time")

        # Insert attributes, OS info and waranty
        #get id of OS
        searchstring = os_distribution+"%"+os_codename
        os_id = rtobject.GetDictionaryId(searchstring)
        attr_id = rtobject.GetAttributeId("SW type")
        debug.print_message("SW Type, searching for: %s , Found: %s, Updating: %s" %(searchstring, str(os_id), str(attr_id)))
        if os_id != None:
            rtobject.InsertAttribute(object_id,server_type_id,attr_id,"NULL",os_id,hostname)
            debug.print_message("Updating SW Type")

        #Insert kernel version atributes
        if kernel_version != "":
            attr_id = rtobject.GetAttributeId("Kernel")
            kernel_id=rtobject.GetDictionaryId(kernel_version)
            if kernel_id == None:
                #Have to insert kernel version into dictionary
                debug.print_message("Inseting new kernel version to dictionary: %s"% str(kernel_version))
                # kernels dictionary ahs ID 10003
                rtobject.InsertDictionaryValue(10003,str(kernel_version))
            kernel_id=rtobject.GetDictionaryId(kernel_version)    
            #log kernel change, and update RT
            if rtobject.GetAttributeValue(object_id, attr_id) != None:
                last_kernel_id = rtobject.GetAttributeValue(object_id, attr_id)[1]
                last_kernel_version = rtobject.GetDictionaryValueById(last_kernel_id)
            else: 
                last_kernel_id = ""
                last_kernel_version = ""
            if last_kernel_id != kernel_id:
                logstring = "Kernel changed %s -> %s" % (last_kernel_version,kernel_version)
                rtobject.InsertLog(object_id,logstring)
                rtobject.InsertAttribute(object_id,server_type_id,attr_id,"NULL",kernel_id,hostname)

        if server_type_id == 4:
            #get id of HW
            words = product_name.split()
            searchstring = vendor+"%"+"%".join(str(x) for x in words)
            hw_id = rtobject.GetDictionaryId(searchstring)
            #insert os and hw info
            attr_id = rtobject.GetAttributeId("HW type")
            debug.print_message("HW Type, searching for: %s , Found: %s, Updating: %s" %(searchstring, str(hw_id), str(attr_id)))
            if hw_id != None:
                rtobject.InsertAttribute(object_id,server_type_id,attr_id,"NULL",hw_id,hostname)
                debug.print_message("Updating HW Type")


            # Insert CPU and Memory Information
            debug.print_message("Updating CPU information attributes")
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
                debug.print_message("Hypervisor, searching for: %s , Found: %s" %(searchstring, str(attid_hyp)))                
                if len(virtual_servers) != 0:
                    rtobject.CleanVirtuals(object_id,virtual_servers)
                    for virtual_name in virtual_servers:
                        virtual_id = rtobject.GetObjectId(virtual_name)   
                        if virtual_id != None:
                            rtobject.LinkVirtualHypervisor(object_id,virtual_id)
                            debug.print_message("Virtual Linking id:%s with %s(%s)" %(str(object_id), str(virtual_id), str(virtual_name)))

            if len(drac_ip) != 0:
                rtobject.UpdateNetworkInterface(object_id,'drac')
                drac_list = [drac_ip]
                rtobject.CleanIPAddresses(object_id,drac_list,'drac')
                rtobject.InterfaceAddIpv4IP(object_id,'drac',drac_ip)
                debug.print_message("Updating Drac IP")


        # Clean unused interfaces
        rtobject.CleanUnusedInterfaces(object_id, device_list)
        debug.print_message("Cleaning unused interfaces")

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

        # Update motd from comment And Tags
        comment = rtobject.GetObjectComment(object_id)
        debug.print_message("Getting object comment: \n"+str(comment))

        #Prepare tag comment
        tags_list = rtobject.GetObjectTags(object_id)
        debug.print_message("Retrieving TAG list: "+str(tags_list))
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
            debug.print_message("Tags\n"+comment_tag)

        if comment == None:
            comment = ""
        # copy template to motd, if no exist make tamplate from motd
        try:
            shutil.copy2(motd_file_original, motd_file)
        except IOError :
            shutil.copy2(motd_file,motd_file_original)
        
        debug.print_message("Updating MOTD file")
        motd_open_file = open(motd_file, "a")
        motd_open_file.write("\n\033[34m--- tags ---\033[33m\n\n" + comment_tag + "\033[0m")
        motd_open_file.write("\n\033[34m--- comment ---\033[33m\n\n" + comment + "\033[0m\n")
        motd_open_file.close()

    else:
        #Hostname is different
        print "Service tag %s already exist, but hostname is different." % service_tag
        debug.print_message("Service tag %s already exist, but hostname is different." % service_tag)

db.close()
