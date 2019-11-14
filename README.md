RT-server-client
================

![pipeline](https://gitlab.com/rvojcik/rt-server-client/badges/master/pipeline.svg)

UPDATE:
-------
According to new version 0.3.0 there are few breaking changes.
Be aware when upgrading.

**CHANGELOG 0.3.0:**
* Removed Python 2.7 support, **Python 3.x only is supported**
* Big redesign in SW installation. Use setup.py or pip to install
* `--init` option for initializing custom Attributes in racktables
* split code into few different classes  

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

Requirements
------------

Required

* racktables-api (install with pip >=0.2.7)
* Python >= 3.5.x 
* lsb-release package(detection of Linux distribution and release)

Optional

* smbios-utils (HW Vendor, Server model and Service-Tag)
* if you don't use smbios-utils, script generate random servicetag in /etc
* LLDPd (information about interface connection with switches and other devices)
* Dell OMSA (for information about iDRAC configuration)

Installation
------------

Install it as normal python sw using pip or setup.py.

**PIP Install**

    pip install rt-server-client

**Manual Install**

    git clone https://github.com/rvojcik/rt-server-client
    cd ./rt-server-client
    sudo python ./setup.py install

**Configuration**

Configuration file have to be located in `/etc/rt-server-client/main.conf` with content something like this:
```
[mysqldb]
user=racktables
password=mysecretpass
db=racktables_db
host=192.168.1.1
port=3306
```

When you have your configuration file you have to run **initialization** of the project.
It requires number of custom attributes in racktables database. Initialization process
check if these attributes are available and map them to correct object types.

Just run
```
    system-info -d --init
```

Normaly script ends without any output. If something go wrong it returns some output of the error. 

Then you can run the `system-info` manualy, from crontab or timer.

