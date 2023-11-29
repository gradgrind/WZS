# time dict lookup

from timeit import default_timer as timer

import numpy as np

from numba import njit
from numba.core import types
from numba.typed import Dict, List

nsize = 100
niter = 100000

keys = []
keys0 = []
h = {}
klist = List()

i = 7
for k in range(nsize):
    keys0.append(k)
    keys.append(i)
    h[k] = i
    klist.append(i)
    i += 1
    if i >= nsize: i = 0

nmap = List()
for k in keys:
    nmap.append(k)
print("keys0:", keys0)
print("keys:", keys)
klist = List()
for k in keys:
    klist.append(k)
npa = np.array(keys)

# pure python with list

def fl():
    v1 = keys
    x = 0
    for i in range(niter):
        for j in range(nsize):
            x = v1[x]
    return x

start = timer()
x = fl()
end = timer()
print("Time List:", end-start, "s", x)


# pure python with dict

def f():
    dmap = h
    x = 0
    for i in range(niter):
        for j in range(nsize):
            x = dmap[x]
    return x

start = timer()
x = f()
end = timer()
print("Time Dict:", end-start, "s", x)

# numba with list

@njit
def fn():
    kl = npa
    x = 0
    for i in range(niter):
        for j in range(nsize):
            x = kl[x]
    return x

x = fn()    # to pre-compile
start = timer()
x = fn()
end = timer()
print("Time Numba + Numpy array:", end-start, "s", x)
