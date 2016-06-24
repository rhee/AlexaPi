#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import division

import numpy as np

def hpf():

    """
    Ref:
        https://tomroelandts.com/articles/how-to-create-a-simple-high-pass-filter

    Usage:
        h = hpf()
        s = np.convolve(s, h)
    """

    fc = 200.0 / 16000
    b = 150.0 / 16000
    N = int(np.ceil((4 / b)))
    if not N % 2: N += 1 # N, odd
    n = np.arange(N)

    # compute a low-pass filter
    h = np.sinc(2 * fc * (n - (N - 1) / 2.))
    w = np.blackman(N)
    h = h * w
    h = h / np.sum(h)

    # spectral inversion, make high-pass filter
    h = -h
    h[(N - 1) / 2] += 1

    return h
