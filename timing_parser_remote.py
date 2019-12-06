#!/usr/bin/env python3

import re
import csv
import sys
from pytimeparse import parse
from datetime import timedelta
from statistics import mean
from itertools import chain

regex = r'[\s\S]*?nonce\.py.+?(\d+) \d+\n(?:(?:.*?\n(?!nonce\.py))*?running after (.+))?(?:.*?\n(?!nonce\.py))*?(?:Finished|Found) after (.+)'

out = csv.writer(sys.stdout)
out.writerow(['D', 'time', 'timebarup', 'timebardown',
              'startup', 'startupbarup', 'startupbardown'])
times = {}
startupTimes = {}
for m in re.finditer(regex, sys.stdin.read()):
    times.setdefault(int(m[1]), []).append(parse(m[3]))
    if m[2]:
        startupTimes.setdefault(int(m[1]), []).append(parse(m[2]))

for D in sorted(set(chain(times.keys(), startupTimes.keys()))):
    avgTime = mean(times[D] or [0])
    avgStartupTime = mean(startupTimes.get(D, [0]))
    out.writerow([D,
                  avgTime, max(times[D])-avgTime, avgTime - min(times[D]),
                  avgStartupTime,
                  max(startupTimes.get(D, [0])) - avgStartupTime,
                  avgStartupTime-min(startupTimes.get(D, [0]))])
