#!/usr/bin/python3
#========================================================
# Python script to measure the difference between local
# time and a web time reference (acquired by screen 
# scraping) and report the error in seconds, where 
# positive means the local clock is fast
#========================================================
# Copyright Jody M Sankey 2014
#========================================================
# AppliesTo: linux
# AppliesTo: client, server
# RemoveExtension: True
# PublicPermissions: True
#========================================================

from urllib import request
from datetime import datetime, timedelta
import re
import sys

URL = r"https://www.google.com"
TIME_FMT = r'%a, %d %b %Y %H:%M:%S GMT'
SECONDS_IN_HOUR = 3600


def getWebTime():
    try:
        date_header = request.urlopen(URL).getheader('date')
        return datetime.strptime(date_header, TIME_FMT)
    except Exception as e:
        print('Exception reading web time from header ', date_header, e)
        return None

def getLocalTime():
    return datetime.utcnow()

def dateDifferenceSeconds(t1, t2):
    """Returns a difference between two python dates in seconds"""
    if t1 is None or t2 is None:
        return None
    else:
        return int((t2 - t1).total_seconds())

def getTimesAndDifference():
    local = getLocalTime()
    web = getWebTime()
    return {
        'web': web.isoformat() if web else None,
        'local': local.isoformat() if local else None,
        'difference': dateDifferenceSeconds(web, local)
    }


if __name__ == '__main__':
    times = getTimesAndDifference()
    if not times['web']:
        print("Error: Could not locate time string in " + URL)
        sys.exit(1)
    else:
        print("Local time is: {} seconds after mid".format(times['local']))
        print("Web time is:   {} seconds after mid".format(times['web']))
        print("Difference is {:+d} seconds (+ means local clock is fast)".format(times['difference']))
