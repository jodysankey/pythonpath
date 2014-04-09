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
from datetime import datetime
import re
import sys

URL = r"http://time.is/GMT"
REGEX = r'<div id=\"twd\">(\d\d):(\d\d):(\d\d)'
SECONDS_IN_HOUR = 3600


def getWebSecondsPastMidx():
    text = request.urlopen(URL).read().decode("UTF-8")
    match = re.search(REGEX, text)
    if not match: return None
    # Convert to a number of seconds past midnight/midday (because not 24h web clock <sigh>)
    val = 0
    for i in range(0,3):
        val = val*60 + int(match.groups()[i])
    return  val % (12 * SECONDS_IN_HOUR)

def getLocalSecondsPastMidx():
    t = datetime.utcnow()
    val = (t.hour*60 + t.minute)*60 + t.second
    return  val % (12 * SECONDS_IN_HOUR)

def normalizedDifference(t1, t2):
    """Returns a difference between two times, accounting for the fact
    that either may have just rolled past a midday/midnight"""
    if t1 is None or t2 is None:
        delta = None
    else:
        delta = t2 - t1
        if delta > 6*SECONDS_IN_HOUR:
            delta -= 12*SECONDS_IN_HOUR
        elif delta < -6*SECONDS_IN_HOUR:
            delta -= 12*SECONDS_IN_HOUR
    return delta

def getTimesAndDifference():
    local = getLocalSecondsPastMidx()
    web = getWebSecondsPastMidx()
    return {
        'web': web,
        'local': local,
        'difference': normalizedDifference(web, local)
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