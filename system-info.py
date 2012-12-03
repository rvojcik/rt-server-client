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

# Get script path
script_path = os.path.dirname(sys.argv[0])

# Add local module path
sys.path.append(script_path + '/lib/')

import ipaddr
import MySQLdb
from ToolBox import net, dell

config_path = script_path + "/conf/"
motd_file_original = "/etc/motd.ls.orig"
motd_file = "/etc/motd"

# Sleep for some seconds. When running on 200 hosts in same second, local dns should have a problem with it
time.sleep(random.randint(1,12))


try:
    config_file = open(config_path + "main.conf")	
except IOError ,e:
    print("({})".format(e))
    sys.exit()

# Parsing config options
config = ConfigParser()
config.readfp(config_file)

def GenerateServiceTag(size):
    """Service tag generator"""

    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    digits = "0123456789"
    chars = letters + digits

    service_tag = "".join(random.choice(chars) for x in range(size))

    return service_tag

def GetVirtualServers():
    """Create list of virtual servers"""

    output = commands.getoutput('xm list')
    virtuals = [] 

    for line in output.splitlines()[2:]:
	virtual = line.split()[0]
	virtuals.append(virtual)	

    return virtuals
	


# Get interface list into interfaces list
device_list = net.get_interfaces()

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
else:
    if not os.path.isfile('/proc/xen/xenbus'):
	#Je to virtual
	server_type_id = 1504
	hypervisor = "no"
    else:
	#Je to hypervisor
	server_type_id = 4
	hypervisor = "yes"
	virtual_servers = GetVirtualServers()

product_name = ''
service_tag = ''
vendor = ''
if server_type_id == 4:
    # Get service tag
    # Server type, model
    for line in commands.getoutput('getSystemId 2>/dev/null').split('\n'):
	if line.find('Product Name:') > -1:
	    product_name = " ".join(str(x) for x in line.split()[2:])
	elif line.find('Service Tag:') > -1:
	    service_tag = line.split()[2]
	elif line.find('Vendor:') > -1:
	    vendor = line.split()[1]

	if vendor == "Supermicro":
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

for interface in device_list:
    # Default values
    switch_name = ''
    switch_port = ''
    # Get ip addresses
    interfaces_ips.append(net.get_ip4_addr(interface))
    interfaces_ips6.append(net.get_ip6_addr(interface))
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


# OS, type, release
os_distribution, os_version, os_codename = platform.dist()
# Stupid debian, empty os_codename
if os_codename == '':
    for line in commands.getoutput('lsb_release -a').split('\n'):
	if line.find('Codename:') > -1:
	    os_codename = line.split()[1]

# Get Drac IP
output = commands.getstatusoutput('omreport chassis remoteaccess config=nic')

if output[0] == 0:
    drac_ip = re.findall('[0-9]{0,3}\.[0-9]{0,3}\.[0-9]{0,3}\.[0-9]{0,3}',output[1])[0]
else:
    drac_ip = ''


# Get support and waranty for service tag
if service_tag == '':
    support_type = ''
    support_ends = ''
else:
    dell_list = dell.get_waranty_info(service_tag)
    if dell_list != None:
	support_type, support_ends = dell_list
    else:
	support_type = ''
	support_ends = ''

# Get hostname
hostname = platform.node()
# Get Kernel version
kernel_version = platform.release()

# Close config
config_file.close()

# Workaround for VPS and servicetag
if server_type_id == 1504:
    service_tag = "VPS-"+hostname

########################
## Debug : Print outputs
#print "Hostname: " + hostname
#print "OS info: " +os_distribution+","+os_version+","+os_codename
#print "Kernel: " +kernel_version
#print "Service-Tag: " +service_tag
#print "Server: "+vendor+" "+product_name
#print "Support: "+support_type+", to "+support_ends
#print "Interfaces: "+" ".join(str(x) for x in device_list[0:])
#print "IPs: "
#count = 0
#for interface in device_list:
#    print interface
#    print "IPv4: "
#    print interfaces_ips[count]
#    print "IPv6: "
#    print interfaces_ips6[count]
#    count += 1
#
#print "Interfaces Connections:"
#count = 0
#for interface in interface_connections:
#    print device_list[count]
#    print interface
#    count += 1

###################
# Database part

## Some functions our racktables database
def InsertLog(object_id,content):
    """Function for attaching log information to specific object"""
    sql = "INSERT INTO ObjectLog (object_id,user,date,content) VALUES (%d,'script',now(),'%s')" % (object_id, content)
    dbresult.execute(sql)
    db.commit()

def InsertAttribute(object_id,object_tid,attr_id,string_value,uint_value,name):
    """Add or Update object attribute, history logging supported"""
    
    # Check if attribute exist
    sql = "SELECT string_value,uint_value FROM AttributeValue WHERE object_id = %d AND object_tid = %d AND attr_id = %d" % (object_id, object_tid, attr_id)
    dbresult.execute(sql)
    result = dbresult.fetchone()
    if result != None:
	# Check if attribute value is same and determine attribute type
	old_string_value = result[0]
	old_uint_value = result[1]
	same_flag = "no"
	attribute_type = "None"

	if old_string_value != None:
	    attribute_type = "string"
	    old_value = old_string_value
	    if old_string_value == string_value:
		same_flag = "yes"
	elif old_uint_value != None:
	    attribute_type = "uint"
	    old_value = old_uint_value
	    if old_uint_value == uint_value:
		same_flag = "yes"

	# If exist, update value
	new_value = ''
	if same_flag == "no":
	    if attribute_type == "string":
		sql = "UPDATE AttributeValue SET string_value = '%s' WHERE object_id = %d AND attr_id = %d AND object_tid = %d" % (string_value, object_id, attr_id, object_tid)
		new_value = string_value
	    if attribute_type == "uint":
		sql = "UPDATE AttributeValue SET uint_value = %d WHERE object_id = %d AND attr_id = %d AND object_tid = %d" % (uint_value, object_id, attr_id, object_tid)
		new_value = uint_value

	    dbresult.execute(sql)
	    db.commit()
	# insert history
#	string = "attr id "+str(attr_id)+" "+str(old_value)+"->"+str(new_value)
#	sql = "INSERT INTO ObjectHistory (id, name, objtype_id, comment, user_name) VALUES (%d,'%s',%d, '%s', '%s')" % (object_id, name, object_tid, string,"script")
#	dbresult.execute(sql)
#	db.commit()

    else:
	# Attribute not exist, insert new
	if string_value == "NULL":
	    sql = "INSERT INTO AttributeValue (object_id,object_tid,attr_id,uint_value) VALUES (%d,%d,%d,%d)" % (object_id,object_tid,attr_id,uint_value)
	else:
	    sql = "INSERT INTO AttributeValue (object_id,object_tid,attr_id,string_value) VALUES (%d,%d,%d,'%s')" % (object_id,object_tid,attr_id,string_value)
	dbresult.execute(sql)
	db.commit()

def GetAttributeId(searchstring):
    """Search database using searchstring and return atribute id"""
    sql = "SELECT id FROM Attribute WHERE name LIKE '%"+searchstring+"%'"
    dbresult.execute(sql)
  
    result = dbresult.fetchone()
    if result != None:
	getted_id = result[0]
    else:
	getted_id = None

    return getted_id

def GetInterfaceName(object_id,interface_id):
    """Find name of specified interface"""
    #Get interface id
    sql = "SELECT name FROM Port WHERE object_id = %d AND name = %d" % (object_id, interface_id)
    dbresult.execute(sql)
    result = dbresult.fetchone()
    if result != None:
	port_name = result[0]
    else:
	port_name = None

    return port_name

def GetInterfaceId(object_id,interface):
    """Find id of specified interface"""
    #Get interface id
    sql = "SELECT id,name FROM Port WHERE object_id = %d AND name = '%s'" % (object_id, interface)
    dbresult.execute(sql)
    result = dbresult.fetchone()
    if result != None:
	port_id = result[0]
    else:
	port_id = None

    return port_id

def GetObjectName(object_id):
    """Find object name in database"""
    #Get interface id
    sql = "SELECT name FROM Object WHERE id = %d" % (object_id)
    dbresult.execute(sql)
    result = dbresult.fetchone()
    if result != None:
	object_name = result[0]
    else:
	object_name = None

    return object_id

def GetObjectId(name):
    """Find object id in database"""
    #Get interface id
    sql = "SELECT id FROM Object WHERE name = '%s'" % (name)
    dbresult.execute(sql)
    result = dbresult.fetchone()
    if result != None:
	object_id = result[0]
    else:
	object_id = None

    return object_id

def GetDictionaryId(searchstring):
    """Search racktables dictionary using searchstring and return id of dictionary element"""
    sql = "SELECT dict_key FROM Dictionary WHERE dict_value LIKE '%"+searchstring+"%'"
    dbresult.execute(sql)

    result = dbresult.fetchone()
    if result != None:
	getted_id = result[0]
    else:
	getted_id = None

    return getted_id

def UpdateNetworkInterface(object_id,interface):
    """Add network interfece to object if not exist"""

    sql = "SELECT id,name FROM Port WHERE object_id = %d AND name = '%s'" % (object_id, interface)
    dbresult.execute(sql)

    result = dbresult.fetchone()
    if result == None:
	
        sql = "INSERT INTO Port (object_id,name,iif_id,type) VALUES (%d,'%s',1,24)" % (object_id,interface)
	dbresult.execute(sql)
	db.commit()
	port_id = dbresult.lastrowid

    else:
	#
	port_id = result[0]


    return port_id

def LinkNetworkInterface(object_id,interface,switch_name,interface_switch):
    """Link two devices togetger"""
    #Get interface id
    port_id = GetInterfaceId(object_id,interface)
    if port_id != None:
	#Get switch object ID
	switch_object_id = GetObjectId(switch_name)
	if switch_object_id != None:
	    switch_port_id = GetInterfaceId(switch_object_id,interface_switch)
	    if switch_port_id != None:
		sql = "SELECT portb FROM Link WHERE porta = %d" % (port_id)
		dbresult.execute(sql)
		result = dbresult.fetchone()
		if result == None:
		    #Insert new connection
		    sql = "INSERT INTO Link (porta,portb) VALUES (%d,%d)" % (port_id, switch_port_id)
		    dbresult.execute(sql)
		    db.commit()
		    resolution = True
		else:
		    #Update old connection
		    old_switch_port_id = result[0]
		    if old_switch_port_id != switch_port_id:
			sql = "UPDATE Link set portb = %d WHERE porta = %d" % (switch_port_id,port_id)
			dbresult.execute(sql)
			db.commit()
			sql = "SELECT Port.name as port_name, Object.name as obj_name FROM Port INNER JOIN Object ON Port.object_id = Object.id WHERE Port.id = %d" % old_switch_port_id
			dbresult.execute(sql)
			result = dbresult.fetchone()
			old_switch_port, old_device_link = result

			text = "Changed link from %s %s -> %s %s" % (old_device_link,old_switch_port)
			InsertLog(object_id,text)
                        resolution = True
                    resolution = None

	    else:
		resolution = None
	else:
	    resolution = None

    else:
	resolution = None

    return resolution

def InterfaceAddIpv4IP(object_id,device,ip):
    """Add/Update IPv4 IP on interface"""

    sql = "SELECT INET_NTOA(ip) from IPv4Allocation WHERE object_id = %d AND name = '%s'" % (object_id,device)
    dbresult.execute(sql)
    result = dbresult.fetchall()

    if result != None:
        old_ips = result
    
    is_there = "no"
	
    for old_ip in old_ips:
	if old_ip[0] == ip:
	    is_there = "yes"

    if is_there == "no":
        sql = "INSERT INTO IPv4Allocation (object_id,ip,name) VALUES (%d,INET_ATON('%s'),'%s')" % (object_id,ip,device)
        dbresult.execute(sql)
        db.commit()
	text = "Added IP %s on %s" % (ip,device)
	InsertLog(object_id,text)

def InterfaceAddIpv6IP(object_id,device,ip):
    """Add/Update IPv6 IP on interface"""
    #Create address object using ipaddr 
    addr6 = ipaddr.IPAddress(ip)
    #Create IPv6 format for Mysql
    ip6 = "".join(str(x) for x in addr6.exploded.split(':'))

    sql = "SELECT HEX(ip) FROM IPv6Allocation WHERE object_id = %d AND name = '%s'" % (object_id, device)
    dbresult.execute(sql)
    result = dbresult.fetchall()
    
    if result != None:
	old_ips = result

    is_there = "no"

    for old_ip in old_ips:
	if old_ip[0] != ip6:
            is_there = "yes"

    if is_there == "no":
        sql = "INSERT INTO IPv6Allocation (object_id,ip,name) VALUES (%d,UNHEX('%s'),'%s')" % (object_id,ip6,device)
        dbresult.execute(sql)
        db.commit()
	text = "Added IPv6 IP %s on %s" % (ip,device)
	InsertLog(object_id,text)

def CleanVirtuals(object_id,virtual_servers):
    """Clean dead virtuals from hypervisor"""

    sql = "SELECT child_entity_id FROM EntityLink WHERE parent_entity_id = %d" % object_id
    dbresult.execute(sql)

    result = dbresult.fetchall()

    if result != None:
	old_virtuals_ids = result
	delete_virtual_id = []
	new_virtuals_ids = []
	# Translate names into ids
	for new_virt in virtual_servers:
	    new_id = GetObjectId(new_virt)
	    if new_id != None:
	    	new_virtuals_ids.append(new_id)

	for old_id in old_virtuals_ids:
	    try:
		test = new_virtuals_ids.index(old_id[0])
	    except ValueError:
		delete_virtual_id.append(old_id[0]) 
    if len(delete_virtual_id) != 0:
	for virt_id in delete_virtual_id:

	    sql = "DELETE FROM EntityLink WHERE parent_entity_id = %d AND child_entity_id = %d" % (object_id,virt_id)
	    dbresult.execute(sql)
	    db.commit()
	    virt_name = GetObjectName(virt_id)
	    logstring = "Odstraneny virtual %s" % virt_name
	    InsertLog(object_id,logstring)

def CleanIPAddresses(object_id,ip_addresses,device):
    """Clean unused ip from object"""

    sql = "SELECT INET_NTOA(ip) FROM IPv4Allocation WHERE object_id = %d AND name = '%s'" % (object_id, device)
    dbresult.execute(sql)

    result = dbresult.fetchall()

    if result != None:
	old_ips = result
	delete_ips = []

	for old_ip in old_ips:
	    try:
		test = ip_addresses.index(old_ip[0])
	    except ValueError:
		delete_ips.append(old_ip[0]) 
    if len(delete_ips) != 0:
	for ip in delete_ips:
	    sql = "DELETE FROM IPv4Allocation WHERE ip = INET_ATON('%s') AND object_id = %d AND name = '%s'" % (ip,object_id,device)
	    dbresult.execute(sql)
	    db.commit()
	    logstring = "Removed IP %s from %s" % (ip,device)
	    InsertLog(object_id,logstring)

def CleanIPv6Addresses(object_id,ip_addresses,device):
    """Clean unused ipv6 from object"""

    sql = "SELECT HEX(ip) FROM IPv6Allocation WHERE object_id = %d AND name = '%s'" % (object_id,device)
    dbresult.execute(sql)

    result = dbresult.fetchall()

    if result != None:
	old_ips = result
	delete_ips = []
	new_ip6_ips = []

	#We must prepare ipv6 addresses into same format for compare
	for new_ip in ip_addresses:
	    converted = ipaddr.IPAddress(new_ip).exploded.lower()
	    new_ip6_ips.append(converted)


	for old_ip_hex in old_ips:
	    try:
		#First we must construct IP from HEX
	    	tmp = re.sub("(.{4})","\\1:", old_ip_hex[0], re.DOTALL)
		#Remove last : and lower string
		old_ip = tmp[:len(tmp)-1].lower()

		test = new_ip6_ips.index(old_ip)

	    except ValueError:
		delete_ips.append(old_ip)

    if len(delete_ips) != 0:
	for ip in delete_ips:
	    db_ip6_format = "".join(str(x) for x in ip.split(':')) 
	    sql = "DELETE FROM IPv6Allocation WHERE ip = UNHEX('%s') AND object_id = %d AND name = '%s'" % (db_ip6_format,object_id,device)
	    dbresult.execute(sql)
	    db.commit()
	    logstring = "Removed IP %s from %s" % (ip,device)
	    InsertLog(object_id,logstring)

def LinkVirtualHypervisor(object_id,virtual_id):
    """Assign virtual server to correct hypervisor"""
    sql = "SELECT child_entity_id FROM EntityLink WHERE parent_entity_id = %d AND child_entity_id = %d" % (object_id,virtual_id)
    dbresult.execute(sql)

    result = dbresult.fetchone()

    if result == None:
	sql = "INSERT INTO EntityLink (parent_entity_type, parent_entity_id, child_entity_type, child_entity_id) VALUES ('object',%d,'object',%d)" % (object_id, virtual_id)
	dbresult.execute(sql)
	db.commit()
	text = "Linked virtual %s with hypervisor" % GetObjectName(virtual_id)
	InsertLog(object_id,text)


## Main Database part

# Create connection to database
try:
    # Create connection to database
    db = MySQLdb.connect(host=config.get('mysqldb','host'),port=3306, passwd=config.get('mysqldb','password'),db=config.get('mysqldb','db'),user=config.get('mysqldb','user'))
except MySQLdb.Error ,e:
    print "Error %d: %s" % (e.args[0],e.args[1])
    sys.exit(1)
#set cursor for db
dbresult = db.cursor()



dbresult.execute('SELECT name FROM Object WHERE asset_no = \''+service_tag+'\'')

if dbresult.fetchone() == None:
    #
    # service tag not exist
    #
    dbresult.execute('select name from Object where name = \''+hostname+'\'')
    if dbresult.fetchone() == None:
	# hostname not exist = insert new server Object
	sql = "INSERT INTO Object (name,objtype_id,asset_no,label) VALUES ('%s',%d,'%s','%s')" % (hostname,server_type_id,service_tag,hostname)
	dbresult.execute(sql)
	db.commit()
	object_id = dbresult.lastrowid

	# Insert attributes, OS info and waranty
	#get id of OS
	searchstring = os_distribution+"%"+os_codename
	os_id = GetDictionaryId(searchstring)
	attr_id = GetAttributeId("SW type")
	if os_id != None:
	    InsertAttribute(object_id,server_type_id,attr_id,"NULL",os_id,hostname)

	
	if server_type_id == 4:
	    #get id of HW
	    words = product_name.split()
	    searchstring = vendor+"%"+"%".join(str(x) for x in words)
	    hw_id = GetDictionaryId(searchstring)
	    #insert os and hw info
	    attr_id = GetAttributeId("HW type")
	    if hw_id != None:
		InsertAttribute(object_id,server_type_id,attr_id,"NULL",hw_id,hostname)

	    ## insert waranty info
	    if len(re.findall('[0-9]{0,2}\/[0-9]{0,2}\/[0-9]{4}', support_ends)):
		attid_hw_warranty = GetAttributeId("HW warranty expiration")
		attid_hw_support = GetAttributeId("HW support type")
		uint_value = time.mktime(datetime.datetime.strptime(support_ends, "%m/%d/%Y").timetuple())
		#Insert HW warranty expiration
		InsertAttribute(object_id,server_type_id,attid_hw_warranty,"NULL",uint_value,hostname)
		#Insert HW warranty type
		InsertAttribute(object_id,server_type_id,attid_hw_support,support_type,"NULL",hostname)


	    if hypervisor == "yes":
		searchstring = "Hypervisor"
		attid_hyp = GetAttributeId(searchstring)
		InsertAttribute(object_id,server_type_id,attid_hyp,'NULL',1501,hostname)
		if len(virtual_servers) != 0:
		    CleanVirtuals(object_id,virtual_servers)
		    for virtual_name in virtual_servers:
			virtual_id = GetObjectId(virtual_name)   
			if virtual_id != None:
			    LinkVirtualHypervisor(object_id,virtual_id)

	    if len(drac_ip) != 0:
		UpdateNetworkInterface(object_id,'drac')
		InterfaceAddIpv4IP(object_id,'drac',drac_ip)


	for device in device_list:
	    #Add/update network interface
	    port_id = UpdateNetworkInterface(object_id,device)
	    #Add network connections
	    if interface_connections[device_list.index(device)] != '':
		LinkNetworkInterface(object_id,device,interface_connections[device_list.index(device)][0],interface_connections[device_list.index(device)][1])
	    #Add IPv4 ips
	    if interfaces_ips[device_list.index(device)] != '':
		for ip in interfaces_ips[device_list.index(device)]:
		    InterfaceAddIpv4IP(object_id,device,ip)
	    #Add IPv6 ips
	    if interfaces_ips6[device_list.index(device)] != '':
		for ip in interfaces_ips6[device_list.index(device)]:
		    InterfaceAddIpv6IP(object_id,device,ip)




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
    dbresult.execute('SELECT NAME FROM Object WHERE name = \''+hostname+'\'')
    if dbresult.fetchone() != None:
	# hostname exist and service tag is same, update info
	sql = "SELECT id FROM Object WHERE name = '%s' AND asset_no = '%s'" % (hostname,service_tag)
	dbresult.execute(sql)
	result = dbresult.fetchone()

	if result != None:
	    object_id = result[0]
	else:
	    sys.exit(1)

	# Insert attributes, OS info and waranty
	#get id of OS
	searchstring = os_distribution+"%"+os_codename
	os_id = GetDictionaryId(searchstring)
	attr_id = GetAttributeId("SW type")
	if os_id != None:
	    InsertAttribute(object_id,server_type_id,attr_id,"NULL",os_id,hostname)

	if server_type_id == 4:
	    #get id of HW
	    words = product_name.split()
	    searchstring = vendor+"%"+"%".join(str(x) for x in words)
	    hw_id = GetDictionaryId(searchstring)
	    
	    #insert os and hw info
	    attr_id = GetAttributeId("HW type")
	    if hw_id != None:
		InsertAttribute(object_id,server_type_id,attr_id,"NULL",hw_id,hostname)

	    ## insert waranty info
	    if len(re.findall('[0-9]{0,2}\/[0-9]{0,2}\/[0-9]{4}', support_ends)):
		attid_hw_warranty = GetAttributeId("HW warranty expiration")
		attid_hw_support = GetAttributeId("HW support type")
		uint_value = time.mktime(datetime.datetime.strptime(support_ends, "%m/%d/%Y").timetuple())
		#Insert HW warranty expiration
		InsertAttribute(object_id,server_type_id,attid_hw_warranty,"NULL",uint_value,hostname)
		#Insert HW warranty type
		InsertAttribute(object_id,server_type_id,attid_hw_support,support_type,"NULL",hostname)


	    if hypervisor == "yes":
		searchstring = "Hypervisor"
		attid_hyp = GetAttributeId(searchstring)
		InsertAttribute(object_id,server_type_id,attid_hyp,'NULL',1501,hostname)
		if len(virtual_servers) != 0:
		    CleanVirtuals(object_id,virtual_servers)
		    for virtual_name in virtual_servers:
			virtual_id = GetObjectId(virtual_name)   
                        if virtual_id != None:
			    LinkVirtualHypervisor(object_id,virtual_id)

	    if len(drac_ip) != 0:
		UpdateNetworkInterface(object_id,'drac')
		drac_list = [drac_ip]
		CleanIPAddresses(object_id,drac_list,'drac')
		InterfaceAddIpv4IP(object_id,'drac',drac_ip)


	for device in device_list:
	    #Add/update network interface
	    port_id = UpdateNetworkInterface(object_id,device)
	    #Add network connections
	    if interface_connections[device_list.index(device)] != '':
		LinkNetworkInterface(object_id,device,interface_connections[device_list.index(device)][0],interface_connections[device_list.index(device)][1])
	    #Add IPv4 ips
	    if interfaces_ips[device_list.index(device)] != '':
		CleanIPAddresses(object_id,interfaces_ips[device_list.index(device)],device)
		for ip in interfaces_ips[device_list.index(device)]:
		    InterfaceAddIpv4IP(object_id,device,ip)
	    #Add IPv6 ips
	    if interfaces_ips6[device_list.index(device)] != '':
		CleanIPv6Addresses(object_id,interfaces_ips6[device_list.index(device)],device)
		for ip in interfaces_ips6[device_list.index(device)]:
		    InterfaceAddIpv6IP(object_id,device,ip)

	# Update motd from comment
	sql = "SELECT comment FROM Object WHERE id = %d" % (object_id)
	dbresult.execute(sql)
	result = dbresult.fetchone()
    
    	comment = ""
	if result[0] != None:
	    comment = result[0]
	    # copy template to motd, if no exist make tamplate from motd
	    try:
	    	shutil.copy2(motd_file_original, motd_file)
	    except IOError :
		shutil.copy2(motd_file,motd_file_original)
	    
	    motd_open_file = open(motd_file, "a")
	    motd_open_file.write("\n\033[34m--- comment ---\033[33m\n\n" + comment + "\033[0m\n\n")
	    motd_open_file.close()

    else:
	#Hostname is different
	print "Service tag %s already exist, but hostname is different." % service_tag

db.close()
