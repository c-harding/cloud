#!/usr/bin/env python3

import re
import csv
import sys
from pytimeparse import parse
from datetime import timedelta
from statistics import mean

regex = r'[\s\S]*?nonce\.py.+?(\d+)\n[\s\S]*?(?:Finished|Found) after (.+)'

out = csv.writer(sys.stdout)
out.writerow(['D', 'time', 'timebarup', 'timebardown'])
times = {}
for m in re.finditer(regex, sys.stdin.read()):
    times.setdefault(int(m[1]), []).append(parse(m[2]))

for D, t in sorted(times.items()):
    avg = mean(t)
    out.writerow([D, avg, max(t)-avg, avg-min(t)])
