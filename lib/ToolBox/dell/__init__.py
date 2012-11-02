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
import urllib2
#from bs4 import BeautifulSoup
import bs3

def get_waranty_info(service_tag):
    dell_support_url = "http://www.dell.com/support/troubleshooting/us/en/04/Servicetag/"
    try:
	soup = bs3.BeautifulSoup(urllib2.urlopen(dell_support_url+service_tag).read())
    except URLError:
	soup = None

    if soup != None:
	
	tmp = soup.find('li', {"class" : "TopTwoWarrantyListItem"})
	if tmp != None:
	   support_type = tmp.findAll('b')[0].string
	else:
	    support_type = ''
	tmp = soup.find('li', {"class" : "TopTwoWarrantyListItem"})
	if tmp != None:
	   support_time = tmp.findAll('b')[1].string
	else:
	    support_time = ''

	output_list = [support_type, support_time]
    else:
	output_list = None

    return output_list
