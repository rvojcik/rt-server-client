RT-server-client
================

Description
-----------

This is server discovery script for Racktables project.
It discover system, import or update infromation into racktables database
 
 Script support following infromation
    * hostname
    * service tag
    * supermicro exeption for service tag (same service tag and express servicetag for all machines)
    * for Dell servers it retrieve support type and support expiration date
    * Physical and logical interfaces (eth,bond,bridges)
    * IPv4 and IPv6 IP addresses, import and update in database
    * Dell Drack IP address (require Dell-OMSA Installed)
    * OS Dristribution and Release information
    * HW vendor and product type
    * Hypervisor recognition (Xen 4.x)
    * Virtual server recognition (Xen 4.x)
    * Link Virtual server with hypervisor as container in Racktables
    * Racktables logging - when change ip addresses or virtual link with hypervisor

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
