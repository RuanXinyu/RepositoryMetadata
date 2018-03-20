# -*- coding:utf-8 -*-
import random
import time
import hashlib
import json
import os
import xmlrpclib
import sys
import datetime
import urllib2
import httplib
import shutil
import socket
import socks
import traceback
from multiprocessing.dummy import Pool as ThreadPool


reload(sys)
sys.setdefaultencoding("utf-8")
cur_dir = os.path.dirname(os.path.realpath(__file__)) + os.path.sep
conf = {
    "metadata_path": "D:\\mirrors\\repository\\pypi\\metadata\\",
    "simple_path": "D:\\mirrors\\repository\\pypi\\simple\\"
}


def rename():
    os.renames(conf["metadata_path"] + ".all", conf["simple_path"] + ".all")
    with open(conf["simple_path"] + ".all", "rb") as f:
        packages = json.load(f)
    for package in packages:
        package_name = package.lower().replace("_", "-").replace(".", "-")
        old_metadata_filename = conf["metadata_path"] + package.lower() + ".json"
        new_metadata_filename = conf["simple_path"] + package.lower() + os.path.sep + "json"
        if os.path.exists(old_metadata_filename):
            os.renames(old_metadata_filename, new_metadata_filename)
            os.renames(conf["simple_path"] + package.lower(), conf["simple_path"] + package_name)
            print(conf["simple_path"] + package_name)


if __name__ == "__main__":
    rename()
