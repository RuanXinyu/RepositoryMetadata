# -*- coding:utf-8 -*-
from bs4 import BeautifulSoup
import datetime
import time
import couchdb
import sys

sys.path.append("./../")
import utils.http_utils as http


class NugetMetadataGetter:
    def __init__(self):
        self.last_updated = ""
        self.top_properties_map = {"title": "title", "updated": "updated", "summary": "summary"}
        self.sub_properties_map = {"d:id": "id",
                                   "d:version": "version",
                                   "d:gallerydetailsurl": "gallery_details_url",
                                   "d:isabsolutelatestversion": "is_absolute_latest_version",
                                   "d:created": "created",
                                   "d:lastupdated": "last_updated",
                                   "d:published": "published"}

    def to_timestamp(self, date_str):
        format = '%Y-%m-%dT%H:%M:%S.%f' if date_str.find(".") != -1 else '%Y-%m-%dT%H:%M:%S'
        d = datetime.datetime.strptime(date_str, format)
        t = d.timetuple()
        timestamp = int(time.mktime(t))
        return timestamp * 1000 + d.microsecond / 1000

    def run(self):
        server = couchdb.Server('http://admin:admin@127.0.0.1:5984/')
        db = server['nuget_v2']
        if "info:sync" not in db:
            db["info:sync"] = {"nuget_last_updated_time": "1970-01-01T00:00:00.000", "sync_entry_count": 0,
                               "sync_add_count": 0, "sync_update_count": 0}
        sync_info = db["info:sync"]

        while True:
            start_time = datetime.datetime.now()
            self.last_updated = sync_info["nuget_last_updated_time"]
            url = "https://www.nuget.org/api/v2/Packages?$orderby=LastUpdated&$filter=LastUpdated%%20gt%%20datetime%%27%s%%27" % self.last_updated
            print("parse url: " + url)
            page = http.get_page(url, 120, 5)
            soup = BeautifulSoup(page, "html.parser")
            err = soup.find_all("m:error")
            if err:
                print("url " + url + ", msg: " + err.string)
                return

            nodes = soup.find_all("entry")
            if not nodes:
                print("url " + url + ", msg: no entry is found, process exit ...")
                return

            for node in nodes:
                sync_info["sync_entry_count"] += 1
                entry = {"xml": unicode(node)}
                for child in node.children:
                    if child.name in self.top_properties_map:
                        entry[self.top_properties_map[child.name]] = unicode(child.string)
                    elif child.name == "content":
                        entry["content"] = unicode(child["src"])
                    elif child.name == "m:properties":
                        for p in child.children:
                            if p.name in self.sub_properties_map:
                                entry[self.sub_properties_map[p.name]] = unicode(p.string)
                            elif p.name == "d:packagesize":
                                entry["package_size"] = int(p.string)

                id = u"pkg:" + (entry["id"] if entry["id"] else entry["title"])
                if "last_updated" in entry:
                    entry["last_updated_timestamp"] = self.to_timestamp(entry["last_updated"])

                doc = db[id] if id in db else {"count": 0, "latest_version": "", "versions": {}}
                if "is_absolute_latest_version" in entry and entry["is_absolute_latest_version"] == "true":
                    doc["latest_version"] = entry["version"]

                if entry["version"] not in doc["versions"]:
                    doc["count"] += 1
                    sync_info["sync_add_count"] += 1
                else:
                    sync_info["sync_update_count"] += 1

                doc["versions"][entry["version"]] = entry
                db[id] = doc

                sync_info["sync_time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                sync_info["nuget_last_updated_time"] = entry["last_updated"]
                db["info:sync"] = sync_info

            end_time = datetime.datetime.now()
            print("synced time: %ds, sync info: %s" % ((end_time - start_time).seconds, str(sync_info)))


if __name__ == "__main__":
    nuget = NugetMetadataGetter()
    nuget.run()
