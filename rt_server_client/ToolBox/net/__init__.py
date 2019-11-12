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
import subprocess as sp
import re

def get_ip4_addr(ifname=None):
    addresses = []

    # If no interface specified, try all
    if ifname == None:
        for interface in get_interfaces():
            lines = sp.run('ip addr show dev '+ interface +' | grep "inet "', shell=True, universal_newlines=True, stdout=sp.PIPE).stdout.split('\n')
            for line in lines:
                if line != '':
                    address = line.strip().split(' ')[1].split('/')[0]
                    addresses.append(address)

    else:
        lines = sp.run('ip addr show dev '+ ifname +' | grep "inet "', shell=True, universal_newlines=True, stdout=sp.PIPE).stdout.split('\n')
        for line in lines:
            if line != '':
                address = line.strip().split(' ')[1].split('/')[0]
                addresses.append(address)

    return addresses

def get_ip6_addr(ifname=None):
    addresses = []

    # If no interface specified, try all
    if ifname == None:
        for interface in get_interfaces():
            lines = sp.run('ip addr show dev '+ interface +' | grep "inet6 "', shell=True, universal_newlines=True, stdout=sp.PIPE).stdout.split('\n')
            for line in lines:
                if line != '':
                    address = line.strip().split(' ')[1].split('/')[0]
                    if address.find('fe80') != 0:
                        addresses.append(address)
    else:
        lines = sp.run('ip addr show dev '+ ifname +' | grep "inet6 "', shell=True, universal_newlines=True, stdout=sp.PIPE).stdout.split('\n')
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

            if re.match("^(eth|eno|enp|bond|san|br)[0-9]+.*", interface_name):
                interfaces.append(interface_name)

        count += 1

    proc_net_dev.close()
 
    return interfaces


