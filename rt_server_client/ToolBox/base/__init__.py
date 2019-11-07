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

from __future__ import print_function
import sys
from .. import colors

class Debug:
    """Debug Class"""
    def __init__(self,args):
        if args:
            if args.debug_mode:
                self.debug_enable = True
            else:
                self.debug_enable = False
        else:
            self.debug_enable = False

    def print_message(self,message):
        """Print debug messages"""

        if self.debug_enable:
            print("[DEBUG] " + str(message))

def pwrn(*objs):
    """Print warning messages"""
    print(colors.term.YELLOW + 'WARNING: ', *objs, end=colors.term.NOC+"\n", file=sys.stderr)

def perr(*objs):
    """Print error messages"""
    print(colors.term.RED + 'ERROR: ', *objs, end=colors.term.NOC+"\n", file=sys.stderr)

def pok(*objs):
    """Print error messages"""
    print(colors.term.GREEN + 'SUCCESS: ', *objs, end=colors.term.NOC+"\n", file=sys.stderr)

def pout(*objs):
    """Print messages"""
    print(colors.term.BLUE, *objs, end=colors.term.NOC+"\n", file=sys.stdout)
