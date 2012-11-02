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

import socket
import fcntl
import struct
import commands

def get_ip4_addr(ifname):
    addresses = []
    lines = commands.getoutput('ip addr show dev '+ ifname +' | grep "inet "').split('\n')
    for line in lines:
	if line != '':
	    address = line.strip().split(' ')[1].split('/')[0] 
	    addresses.append(address)

    return addresses

def get_ip6_addr(ifname):
    addresses = []
    lines = commands.getoutput('ip addr show dev '+ ifname +' | grep "inet6 "').split('\n')
    for line in lines:
	if line != '':
	    address = line.strip().split(' ')[1].split('/')[0] 
	    if address.find('fe80') != 0:
		addresses.append(address)

    return addresses
def get_hw_addr(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', ifname[:15]))
    return ''.join(['%02x:' % ord(char) for char in info[18:24]])[:-1]

def get_interfaces():

    proc_net_dev = open('/proc/net/dev', 'r')

    count = 0
    interfaces = []

    for line in proc_net_dev:
        if (count > 1):
                words = line.split()
                interface = words[0]
		interface_name = interface.split(':')[0]
		if interface_name.find('eth') > -1:
		    interfaces.append(interface_name)
		elif interface_name.find('bond') > -1:
		    interfaces.append(interface_name)
		elif interface_name.find('san') > -1:
		    interfaces.append(interface_name)
		elif interface_name.find('br') > -1:
		    interfaces.append(interface_name)

        count += 1
   
    proc_net_dev.close()
    
    return interfaces


