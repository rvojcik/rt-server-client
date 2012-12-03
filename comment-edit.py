#!/usr/bin/python
#
# This is comment-edit script for Racktables project
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
from ConfigParser import ConfigParser
import MySQLdb
import platform
import commands

# Basic config
config_path = "/opt/server-audit/conf/"
default_editor = "vim"
tmp_file = '/tmp/comment-edit'

try:
    config_file = open(config_path + "main.conf")	
except IOError ,e:
    print("({})".format(e))
    sys.exit()

# Parsing config options
config = ConfigParser()
config.readfp(config_file)


# Create connection to database
try:
    # Create connection to database
    db = MySQLdb.connect(host=config.get('mysqldb','host'),port=3306, passwd=config.get('mysqldb','password'),db=config.get('mysqldb','db'),user=config.get('mysqldb','user'))
except MySQLdb.Error ,e:
    print "Error %d: %s" % (e.args[0],e.args[1])
    sys.exit(1)
#set cursor for db
dbresult = db.cursor()
	
#Open new comment_file
comment_file = open(tmp_file,'w')

# Get comment from database
sql = "SELECT comment FROM Object WHERE name = '%s'" % (platform.node())
dbresult.execute(sql)
result = dbresult.fetchone()

if result[0] != None:
    comment = result[0]
else:
    comment = ""
   
comment_file.write(comment)
comment_file.close()

#Get editor from environment variables
try:
    comment_editor = os.environ['EDITOR']
except KeyError:
    comment_editor = default_editor

os.system(comment_editor + " " + tmp_file)

answer = raw_input("Would you like to send comment to database ? [y/n] [n]: ")

if answer == "y":
    #Read comment from file
    comment_file = open(tmp_file, 'r')
    comment = comment_file.read()
    sql = "UPDATE Object SET comment = '%s' WHERE name = '%s'" % (comment, platform.node())
    
    dbresult.execute(sql)
    db.commit()

    #Close file
    comment_file.close()

db.close()



   
