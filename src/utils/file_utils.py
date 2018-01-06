# -*- coding: utf-8 -*-

import os
import hashlib


def move_file(src, dst):
    os.makedirs(os.path.dirname(dst), 0640)
    if os.path.exists(dst):
        os.remove(dst)
    os.rename(src, dst)


def hash_file(filename, alg):
    if os.path.isfile(filename):
        h = hashlib.new(alg)
        with open(filename, 'rb') as f:
            data = f.read()
            h.update(data)
        return h.hexdigest()

