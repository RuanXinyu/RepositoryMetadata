# -*- coding:utf-8 -*-
import datetime
import time
import couchdb
import sys
import json
import os
import xmlrpclib
import urllib2
sys.path.append("./../")
import src.utils.http_utils as http


class PypiMetadataGetter:
    def __init__(self):
        self.client = xmlrpclib.ServerProxy('https://pypi.python.org/pypi')
        self.last_updated = ""

    def save_packages(self, last_serial):
        serial = self.client.changelog_last_serial()
        if last_serial == serial:
            exit(0)

        if last_serial == 0:
            names = self.client.list_packages()
        else:
            data = self.client.changelog_since_serial(last_serial)
            names_list = [item[0] for item in data]
            names = list(set(names_list))
        with open("packages.json", "w") as f:
            json.dump({"serial": serial, "names": names}, f)

    def load_packages(self, last_serial):
        if not os.path.exists("packages.json"):
            self.save_packages(last_serial)
        with open("packages.json", "r") as f:
            return json.load(f)

    def run(self):
        server = couchdb.Server('http://admin:admin@127.0.0.1:5984/')
        db = server['pypi']
        if "info:sync" not in db:
            db["info:sync"] = {"changelog_last_serial": 0, "synced_packages_count": 0, "sync_index": 0}
        sync_info = db["info:sync"]
        data = self.load_packages(sync_info["changelog_last_serial"])
        names = data["names"]

        for index in range(sync_info["sync_index"], len(names)):
            start_time = datetime.datetime.now()
            url = "https://pypi.python.org/pypi/%s/json" % names[index]
            print("parse url: " + url)

            page = ""
            try:
                page = http.get_page(url, 120, 5)
            except urllib2.URLError as ex:
                if hasattr(ex, 'code') and ex.code == 404:
                    continue
                print("url " + url + ", " + ex.message)

            doc = json.loads(page)
            if "info" not in doc or "name" not in doc["info"]:
                print("url " + url + ", msg: info not in data or name not in data[info]")
                return

            pkg_id = u"pkg:" + names[index]
            doc["name"] = names[index]
            if pkg_id not in db:
                sync_info["synced_packages_count"] += 1
            db[pkg_id] = doc

            sync_info["sync_time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            sync_info["sync_index"] += 1
            db["info:sync"] = sync_info

            end_time = datetime.datetime.now()
            print("synced time: %ds, sync info: %s" % ((end_time - start_time).seconds, str(sync_info)))
        sync_info["changelog_last_serial"] = data["serial"]
        sync_info["sync_index"] = 0
        db["info:sync"] = sync_info


if __name__ == "__main__":
    pypi = PypiMetadataGetter()
    pypi.run()
