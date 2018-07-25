#!/usr/bin/env python2
# -*- coding:utf-8 -*-

from pymongo import MongoClient
import tarfile
import random
import time
import hashlib
import json
import os
import sys
import datetime
import urllib2
import httplib
import shutil
import re
import traceback
from multiprocessing.dummy import Pool as ThreadPool
from socket import error as SocketError
import errno

reload(sys)
sys.setdefaultencoding("utf-8")
cur_dir = os.path.dirname(os.path.realpath(__file__)) + os.path.sep


class Utils:
    def __init__(self):
        pass

    @staticmethod
    def read_file(filename, mode="rb"):
        with open(filename, mode) as f:
            return f.read()

    @staticmethod
    def write_file(filename, data, mode="wb"):
        with open(filename, mode) as f:
            return f.write(data)

    @staticmethod
    def read_json_file(filename):
        with open(filename, "rb") as f:
            return json.load(f)

    @staticmethod
    def write_json_file(filename, data):
        with open(filename, "wb") as f:
            json.dump(data, f)

    @staticmethod
    def hash(hash_type, data=None, filename=None):
        if not data and not filename:
            print("please specified data or filename")
        elif not data and filename:
            data = Utils.read_file(filename)

        h = hashlib.new(hash_type)
        h.update(data)
        return h.hexdigest()

    @staticmethod
    def is_file_exist(filename):
        if not os.path.exists(filename):
            return False

        lock_filename = filename + ".__lock"
        if os.path.exists(lock_filename):
            return False
        return True

    @staticmethod
    def create_dir(filename):
        dir_name = os.path.dirname(filename)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

    @staticmethod
    def save_data_as_file(filename, data):
        Utils.create_dir(filename)
        lock_filename = filename + ".__lock"
        Utils.write_file(lock_filename, "")
        Utils.write_file(filename, data)
        os.remove(lock_filename)

    @staticmethod
    def to_timestamp(date_str):
        date_format = '%Y-%m-%dT%H:%M:%S.%fZ' if date_str.find(".") != -1 else '%Y-%m-%dT%H:%M:%S'
        d = datetime.datetime.strptime(date_str, date_format)
        t = d.timetuple()
        timestamp = int(time.mktime(t))
        return timestamp * 1000 + d.microsecond / 1000 * 1000

    @staticmethod
    def get_url(url, timeout=120, retry_times=2, ignore_codes=(401, 403, 404)):
        times = 0
        print("get url: %s" % url)
        while times < retry_times:
            times += 1
            try:
                data = urllib2.urlopen(url, timeout=timeout).read()
                return data
            except (urllib2.URLError, httplib.HTTPException, httplib.IncompleteRead) as ex:
                if times >= retry_times:
                    if hasattr(ex, 'code') and ex.code in ignore_codes:
                        print("[warning]====> url(%s), code(%d): %s" % (url, ex.code, ex.reason))
                        Utils.write_file(cur_dir + str(ex.code) + ".error", url + "\n", mode="a")
                        return None
                    print("[error]====> url(%s): %s" % (url, ex.message))
                    raise ex
            except httplib.BadStatusLine as ex:
                if times >= retry_times:
                    print("[warning]====> url(%s): %s" % (url, ex.message))
                    Utils.write_file(cur_dir + "bad_status_line.error", url + "\n", mode="a")
                    return None
            except SocketError as ex:
                if times >= retry_times:
                    if ex.errno == errno.ECONNRESET:
                        print("[warning]====> url(%s): %s" % (url, ex.message))
                        Utils.write_file(cur_dir + "connect_reset.error", url + "\n", mode="a")
                        return None
                    else:
                        raise ex
            except BaseException as ex:
                if times >= retry_times:
                    print("[error]====> url(%s): %s" % (url, ex.message))
                    raise ex
            print("[retry]====> get url: %s" % url)


class NpmMetadataParser:
    def __init__(self):
        self.db = MongoClient('localhost', 27017).npm

    def save_package(self, data):
        old_package = self.db.npm_packages.find_one({"_id":  data["_id"]})
        self.save_versions(old_package, data)
        package = {
            "_id": data["_id"],
            "_rev": data["_rev"],
            "name": data["name"],
            "description": data["description"],
            "dist-tags": data["dist-tags"],
            "versions": [{"version": key, "time": value} for key, value in data["time"].items()],
            "maintainers": data["maintainers"],
            "repository": data["repository"],
            "homepage": data["homepage"],
            "keywords": data["keywords"],
            "bugs": data["bugs"],
            "readme": data["readme"],
            "readmeFilename": data["readmeFilename"],
            "license": data["license"] if "license" in data else "",
            "dependents": old_package["dependents"] if old_package else []
        }
        self.db.npm_packages.save(package)

    def save_versions(self, old_package, new_package):
        old_versions = [item["version"] for item in old_package["versions"]] if old_package else None
        all_versions = new_package["versions"].keys()
        new_versions = list(set(all_versions).difference(set(old_versions))) if old_package else all_versions

        new_dependencies = []
        old_dependencies = []
        for item in new_package["versions"].values():
            if item["version"] in new_versions:
                new_dependencies += item["dependencies"].keys()
            else:
                old_dependencies += item["dependencies"].keys()
            item["_id"] = item["name"] + ":" + item["version"]
            item["dependencies"] = [{"name": key, "version": value} for key, value in item["dependencies"].items()] if "dependencies" in item else []
            item["devDependencies"] = [{"name": key, "version": value} for key, value in item["devDependencies"].items()] if "devDependencies" in item else []
            if "readmeFilename" in new_package and new_package["readmeFilename"] != "":
                item["readme"] = self.get_readme(item, new_package["readmeFilename"])

        new_dependencies = list(set(new_dependencies).difference(set(old_dependencies)))
        self.save_dependents(new_package, new_dependencies)
        self.db.npm_versions.save([item for item in new_package["versions"].values() if item["version"] in new_versions])

    def save_dependents(self, package, dependencies):
        for dependence in dependencies:
            target = self.db.npm_packages.find_one({"_id": dependence})
            if not target:
                target = {
                    "_id": dependence,
                    "dependents": [package["name"], ]
                }
                self.db.npm_packages.insert_one(target)
            else:
                if package["name"] not in target["dependents"]:
                    target["dependents"].append(package["name"])
                    self.db.npm_packages.save(target)

    def get_readme(self, version, readme_filename):
        readme = ""
        if version["dist"]["tarball"].startswith("https://registry.npmjs.org/"):
            filename = version["dist"]["tarball"].replace("https://registry.npmjs.org/", "")
            tar = tarfile.open(filename, "r:gz")
            info = tar.extractfile(readme_filename)
            if info:
                readme = info.readlines()
            tar.close()
        return readme


if __name__ == "__main__":
    parser = NpmMetadataParser()
    str1 = Utils.get_url("http://registry.npmjs.org/@angular%2fcli", timeout=30)
    data = json.loads(str1)
    parser.save_package(data)

