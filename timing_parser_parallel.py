#!/usr/bin/env python3

import re
import csv
import sys
from pytimeparse import parse
from datetime import timedelta
from statistics import mean
from itertools import chain

regex = r'[\s\S]*?nonce\.py.+?(\d+) (\d+)\n(?:.*?\n(?!nonce\.py))*?(?:Finished|Found) after (.+)'

out = csv.writer(sys.stdout)
out.writerow(['D', 'n', 'time', 'timebarup', 'timebardown'])
times = {}
for m in re.finditer(regex, sys.stdin.read()):
    times.setdefault((int(m[1]), int(m[2])), []).append(parse(m[3]))

for D, t in sorted(times.items()):
    avgTime = mean(times[D] or [0])
    out.writerow([*D, avgTime,
                  max(times[D]) - avgTime,
                  avgTime - min(times[D])])
