#!/usr/bin/python
#
# Script retrieve waranty information from Dell website based on server Service-Tag 
#
# Use service-tag as script argument
# http://www.dell.com/support/troubleshooting/us/en/04/Servicetag/<servicetag>

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

# Add local module path
sys.path.append('lib/')

from ToolBox import dell

if len(sys.argv[1:]) == 0:
	print "Missing service-tag parameter"
	print "Usage: " + sys.argv[0] + " <service-tag>"
	sys.exit(1)
else:

	support_type, support_time = dell.get_waranty_info(sys.argv[1])
	print support_type + " -> " + support_time
 
