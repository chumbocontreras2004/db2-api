import sys

from ppt import ppt

g, p, bs, q, am, bp = sys.argv[1:7]
ppt(int(g), int(p), int(bs), int(q), float(am), float(bp))
