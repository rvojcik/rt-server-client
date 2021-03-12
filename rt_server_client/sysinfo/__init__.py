# SysInfo part of the rt-server-client
# Here we gather all the information about the system
import fcntl
import socket
import struct
import sys
import os
import subprocess as sp
import platform
import time
import datetime
import re
import random
import shutil
import argparse
import ipaddr
from ..ToolBox import base, net

class SysInfo():
    """
    SysInfo Class will gather and contain all the system information
    """

    def __init__(self, args=False, config=False):
        self.information = {
            'network': {
                'lldp': {},
            },
        }
        self.debug = base.Debug(args)
        self.backup_init = args.backup_init
        self.config = config

    def getHwAddr(self, ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', ifname[:15]))
        return ''.join(['%02x' % ord(char) for char in info[18:24]])

    def GetVirtualServers(self, virt='xen'):
        """Create list of virtual servers"""

        if virt == 'xen':
            command = 'xm list'
            index = 0
        elif virt == 'qemu':
            command = 'virsh list --all'
            index = 1
        else:
            print('Unsupported virtualization')
            sys.exit(1)

        output = sp.run(command, shell=True, universal_newlines=True, stdout=sp.PIPE).stdout
        virtuals = []

        for line in output.splitlines()[2:]:
            if line != '':
                virtual = line.split()[index]
                virtuals.append(virtual)

        self.debug.print_message("Virtual servers: "+str(virtuals))

        return virtuals
    
    def DiscoverAll(self):
        self.DiscoverNetworking()
        self.DiscoverBmc()
        self.DiscoverSystem()

    def DiscoverNetworking(self):
        # Get interface list into interfaces list and filter docker interfaces
        device_list = net.get_interfaces()
        self.information['network']['device_list'] = device_list
        self.debug.print_message("Device list: "+str(device_list))

        # Get ip address for each interface
        # Get connections from lldp
        # Empty list for connections
        self.information['network']['interface_connections'] = []
        self.information['network']['interfaces_ips'] = []
        self.information['network']['interfaces_ips6'] = []

        # Network Interfaces LLDP Connections
        for interface in device_list:
            self.debug.print_message("Processing interface " + interface)
            # Default values
            self.information['network']['lldp']['switch_name'] = ''
            self.information['network']['lldp']['switch_port'] = ''
            # Get ip addresses
            self.information['network']['interfaces_ips'].append(net.get_ip4_addr(interface))
            self.debug.print_message("IPv4: "+str(self.information['network']['interfaces_ips']))

            self.information['network']['interfaces_ips6'].append(net.get_ip6_addr(interface))
            self.debug.print_message("IPv6: "+str(self.information['network']['interfaces_ips6']))

            # Get lldp
            lldp_output = sp.run('lldpctl -f keyvalue ' + interface, shell=True, universal_newlines=True, stdout=sp.PIPE).stdout

            #Test if it's juniper or Force10, otherwise skip this discovery becouse unsupported device
            # For JUniper
            switch_name = ''
            switch_port = ''
            if lldp_output.find('Juniper') > -1:
                for line in lldp_output.split('\n'):
                    if line.find('lldp.'+interface+'.chassis.name') > -1:
                        switch_name = line.split('=')[1]
                    elif line.find('lldp.'+interface+'.port.descr') > -1:
                        switch_port = line.split('=')[1]
            # Others cisco like
            else:
                for line in lldp_output.split('\n'):
                    if line.find('lldp.'+interface+'.chassis.name') > -1:
                        switch_name = line.split('=')[1]
                    elif line.find('lldp.'+interface+'.port.ifname') > -1:
                        switch_port = line.split('=')[1]

            #add connection to list
            connection = [switch_name, switch_port]
            self.debug.print_message("Connection: "+str(connection))
            self.information['network']['interface_connections'].append(connection)

    def DiscoverBmc(self):
        # Get Drac IP
        management_ip_commands = ['omreport chassis remoteaccess config=nic' , 'ipmitool lan print']
        self.information['network']['drac_ip'] = ''
        for mgmcommand in management_ip_commands:
            output = sp.run(mgmcommand, shell=True, universal_newlines=True, stdout=sp.PIPE)
            try:
                self.information['network']['drac_ip'] = re.findall('[0-9]{0,3}\.[0-9]{0,3}\.[0-9]{0,3}\.[0-9]{0,3}',output.stdout)[0]
                break
            except:
                pass
        self.debug.print_message("Drac IP: "+ self.information['network']['drac_ip'])

    def DiscoverSystem(self):
        """ Get all system information """
        # Get service tag
        # Server type, model
        self.information['product_name'] = sp.run('get-bios-ident -s -m', shell=True, universal_newlines=True, stdout=sp.PIPE).stdout.rstrip()
        self.debug.print_message("Product name: "+self.information['product_name'])

        self.information['service_tag'] = sp.run('get-bios-ident -s -t', shell=True, universal_newlines=True, stdout=sp.PIPE).stdout.rstrip()
        self.debug.print_message("Service Tag: "+self.information['service_tag'])

        self.information['vendor'] = sp.run('get-bios-ident -s -v', shell=True, universal_newlines=True, stdout=sp.PIPE).stdout.rstrip()
        self.debug.print_message("Vendor: "+ self.information['vendor'])

        # Check for virtualization
        if not os.path.isdir('/proc/xen'):
            # Not xen, check libvirtd
            if os.path.isfile('/usr/sbin/libvirtd'):
                # It's KVM/QEMU Hypervisor
                self.information['server_type_id'] = 4
                self.information['hypervisor'] = "yes"
                self.information['virtual_servers'] = self.GetVirtualServers(virt='qemu')
                self.debug.print_message("Server is hypervisor")
                self.debug.print_message("Virtuals: "+str(self.information['virtual_servers']))
            elif self.information['vendor'] == 'QEMU':
                # Looks like server but, QEMU vendor
                self.information['server_type_id'] = 1504
                self.information['hypervisor'] = "no"
                self.debug.print_message("Server is virtual (QEMU)")
            else:
                # It's server
                self.information['server_type_id'] = 4
                self.information['hypervisor'] = "no"
                self.debug.print_message("Server is physical normal server")
        else:
            if not os.path.isfile('/proc/xen/xenbus'):
                self.information['server_type_id'] = 1504
                self.information['hypervisor'] = "no"
                self.debug.print_message("Server is virtual (XEN)")
            else:
                self.debug.print_message("Server is hypervisor")
                self.information['server_type_id'] = 4
                self.information['hypervisor'] = "yes"
                self.information['virtual_servers'] = self.GetVirtualServers()
                self.debug.print_message("Virtuals: "+str(self.information['virtual_servers']))


        self.information['hostname'] = platform.node()

        # Workaround for VPS and servicetag
        if self.information['server_type_id'] == 1504:
            self.information['service_tag'] = "VPS-"+ self.information['hostname']
            self.debug.print_message("VPS Service Tag override: "+ self.information['service_tag'])
        else:
            self.information['service_tag'] = sp.run('get-bios-ident -s -t', shell=True, universal_newlines=True, stdout=sp.PIPE).stdout.rstrip()

        # If backup init (register to racktables as backup server)
        if self.backup_init:
            self.information['hostname'] = "%s-%s" % (self.config.get('global', 'init_prefix'), self.information['service_tag'])
        self.debug.print_message("Hostname: "+ self.information['hostname'])

        # CPU information
        # Read /proc/cpuinfo into variable
        cpu_proc = open('/proc/cpuinfo')
        file_c = cpu_proc.read()
        cpu_proc.close()

        # Get number of logical CPUs
        self.information['cpu_logical_num'] = file_c.count('processor')
        self.debug.print_message("Logical CPU num: "+str(self.information['cpu_logical_num']))

        # Get CPU Model Name
        self.information['cpu_model_name'] = re.sub(' +',' ',re.findall('model name.*',file_c)[0].split(': ')[1])
        self.debug.print_message("CPU model name: "+ self.information['cpu_model_name'])

        # Physical CPU information
        lscpu_output = sp.run('lscpu', shell=True, universal_newlines=True, stdout=sp.PIPE)
        if lscpu_output.returncode == 0:
            lscpu = lscpu_output.stdout
            try:
                self.information['cpu_num'] = int(re.findall('CPU socket.*',lscpu)[0].split(':')[1].strip())
            except:
                self.information['cpu_num'] = int(re.findall('Socket\(s\).*',lscpu)[0].split(':')[1].strip())
            self.information['cpu_cores'] = int(re.findall('Core\(s\) per socket.*',lscpu)[0].split(':')[1].strip())
            self.information['cpu_mhz'] = int(re.findall('CPU MHz.*',lscpu)[0].split(':')[1].strip().split('.')[0])
        else:
            self.information['cpu_num'] = ""
            self.information['cpu_cores'] = ""
            self.information['cpu_mhz'] = ""

        self.debug.print_message("CPU NUM, CPU Cores, CPU Mhz: %s, %s, %s" % (self.information['cpu_num'], self.information['cpu_cores'], self.information['cpu_mhz']))

        # Get Memory info
        meminfo = open('/proc/meminfo')
        file_c = meminfo.read()
        meminfo.close()
        self.information['memory_mb'] = int(file_c.split()[1]) / 1024
        self.debug.print_message("Memory MB: %s" % (str(self.information['memory_mb'])))

        # OS, type, release
        self.information['os_distribution'], self.information['os_version'], self.information['os_codename'] = platform.dist()

        # Stupid debian, empty os_codename
        if self.information['os_codename'] == '':
            for line in sp.run('lsb_release -a', shell=True, universal_newlines=True, stdout=sp.PIPE).stdout.split('\n'):
                if line.find('Codename:') > -1:
                    self.information['os_codename'] = line.split()[1]
        self.debug.print_message("os_dist, os_version, os_codename: " + str([self.information['os_distribution'], self.information['os_version'], self.information['os_codename']]))

        # Get label from Drac (display)
        output = sp.run('omreport chassis frontpanel', shell=True, universal_newlines=True, stdout=sp.PIPE)

        if output.returncode == 0:
            try:
                line = re.findall('LCD Line 1.*',output.stdout)[0]
                label = line.split(' ')[4]
                update_label = "yes"
            except:
                update_label = "no"
                label = ""
        else:
            update_label = "no"
            label = ""
        self.debug.print_message("label, update_label: %s %s" % (label, update_label))

        # If hostname and label not match, try to configure LCD
        if self.information['hostname'] != label:
            if sp.run('omconfig chassis frontpanel config=custom lcdindex=1 text="' + self.information['hostname'] + '"', shell=True, universal_newlines=True, stdout=sp.PIPE).returncode == 0:
                label = self.information['hostname']
                update_label = "yes"
        self.debug.print_message("label, update_label: %s %s" % (label, update_label))
        self.information['label'] = label
        self.information['update_label'] = update_label

        # Get Kernel version
        self.information['kernel_version'] = platform.release()
        self.debug.print_message("Kernel: "+ self.information['kernel_version'])

