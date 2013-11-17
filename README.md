RT-server-client
================

Description
-----------

This is server discovery script for Racktables project.
It discover system, import or update infromation into racktables database
 
Script support following infromation

    * hostname
    * transfer comment field to server motd (message of the day)
    * commend-edit utility for editing comments on racktables directly from server
    * service tag
    * supermicro exeption for service tag (my supermicro servers has all same ST and Expres ST. I don't know why)
    * for Dell servers: get warranty and support information from Dell website based on server ST.
    * Physical and logical interfaces (eth,bond,bridges,venet and veth)
    * IPv4 and IPv6 IP addresses, import and update in database
    * Dell iDrac IP address (require Dell-OMSA Installed)
    * OS Dristribution and Release information
    * HW vendor and product type
    * Hypervisor recognition (Xen 4.x)
    * Hypervisor recognition (OpenVZ)
    * Virtual server recognition (Xen 4.x)
    * Virtual server recognition (OpenVZ)
    * Link Virtual server with hypervisor as container in Racktables
    * Racktables logging - when change ip addresses or virtual link with hypervisor
    * Interface Connection (LLDPD needed for this feature. System automaticly link server interfaces with switch ports in RackTables)

For some description, screenshots and examples visit https://www.cypherpunk.cz/automatic-server-audit-for-racktables-project/

TODO
----
    * support for other virtualization technology (KVM, VirtualBox)
    * support for windows servers
    * support for FreeBSD

Requirements
------------

Required

    - Python > 2.5.x (tested with 2.5.2, 2.7.3)
    - Python module Beautiful Soup (tested with bs3)
    - lsb-release (detection of Linux distribution and release)

Optional

    - smbios-utils (HW Vendor, Server model and Service-Tag)
     - if you don't use smbios-utils, script generate random servicetag in /etc
    - LLDPd (information about interface connection with switches and other devices)
    - Dell OMSA (for information about iDRAC configuration)

Installation
------------

You should install this application whare you want. I reccommend put it to /opt.

    cd /opt/
    git clone https://github.com/rvojcik/rt-server-client.git
    vim rt-server-client/conf/main.conf
    cd rt-server-client
    ./system-info.py

If it ends without any message, it was successful. Look into RackTables web interface for new object.

Add to root crontab following line for run script every 30 minutes

    */30 * * * * cd /opt/rt-server-client ; ./system-info.py

Normaly script ends without any output. If something go wrong it returns some output of the error. 

'''Dell Servers ans HW Support Type''':

When using with dell servers, script try to find Attribute '''HW support type'''. This is not default racktables attribute.
You must go in racktables to '''Configuration->Attributes->Add attribute'''. 

Add 'HW support type' as string and then go to 'Attribute Map' and assign this new attribute to Server objects.

Without this modification you probably get some error on Dell servers.

Issues
------

Known problem is with Python Beautiful Soup module. 
You should install it from source or from packages. 
Name of module depends on version, inux distribution etc.

If you see someting like this:

    Traceback (most recent call last):
      File "./system-info.py", line 60, in <module>
        from ToolBox import net, dell
      File "./lib/ToolBox/dell/__init__.py", line 22, in <module>
        import bs3
    ImportError: No module named bs3

Edit please '''lib/ToolBox/dell/__init__.py''' and change "import bs3" to correct name of BeautifulSoup
module (eg. bs4, BeautifulSoup ... )
Beware, next parts of code use BeautifulSoup as bs3 so import correct modul with "as bs3"
    import <your name of BeautifulSoup> as bs3 

Example (for Debian Wheezy):
    import BeautifulSoup as bs3


License
-------

This utility is released under GPL v2

RT-server-client utility for Racktables Datacenter management project.
Copyright (C) 2012  Robert Vojcik (robert@vojcik.net)

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Server discovery client for RackTables project. 
Do automatic server discovery and send information to racktables database.

Used for automatic servers documentation.
