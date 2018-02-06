# -*- coding:utf-8 -*-
import random
import time
import hashlib
import json
import os
import datetime
import urllib2
import re
from multiprocessing.dummy import Pool as ThreadPool


def get_url(url, timeout=120, retry_times=5):
    times = 0
    print("get url: %s" % url)
    while times < retry_times:
        times += 1
        try:
            data = urllib2.urlopen(url, timeout=timeout).read()
            return data
        except urllib2.URLError as ex:
            if times >= retry_times:
                if hasattr(ex, 'code') and ex.code == 404:
                    print("url is 404: " + ex.message)
                    with open("404.error", 'a') as f:
                        f.write(url + "\n")
                    return None
                raise ex
        print("retry, get url: %s" % url)


def sha1(data):
    h = hashlib.new("sha1")
    h.update(data)
    return h.hexdigest()


def save_data_as_file(filename, data):
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(os.path.dirname(filename))
    with open(filename, 'w') as f:
        f.write(data)


def create_dir(name):
    if not os.path.exists(name):
        os.mkdir(os.path.dirname(name))


def to_timestamp(date_str):
    format = '%Y-%m-%dT%H:%M:%S.%fZ' if date_str.find(".") != -1 else '%Y-%m-%dT%H:%M:%S'
    d = datetime.datetime.strptime(date_str, format)
    t = d.timetuple()
    timestamp = int(time.mktime(t))
    return timestamp * 1000 + d.microsecond / 1000


base = "D:\\Code\\RepositoryMetadata\\npm_mirror\\"
conf = {
    "package_path": base + "packages" + os.path.sep,
    "download_url_replacement": ["registry.npmjs.org", "mirrors.huaweicloud.com/repository/npm"],
    "url_to_filename": ["https?://registry.npmjs.org/", "files/"],
    "download_url_modifier": ["https?://registry.npmjs.org/", "https://mirrors.huaweicloud.com/repository/npm/"],
}


class NpmSyncPackages:
    def __init__(self, packages_filename):
        self.packages_file = packages_filename
        self.packages_info_file = packages_filename + ".info"
        self.updating_info = {"filename": packages_filename, "updated_index": 0, "updated_packages_count": 0, "updated_file_count": 0}

    def load_packages(self):
        if not os.path.exists(self.packages_info_file):
            self.save_updating_info()
        with open(self.packages_info_file, "r") as f:
            self.updating_info = json.load(f)
            print("load packages from '%s': %s" % (self.packages_file, self.updating_info))
        with open(self.packages_file, "r") as f:
            return json.load(f)

    def save_updating_info(self):
        with open(self.packages_info_file, "w") as f:
            json.dump(self.updating_info, f)

    def save_package(self, package):
        metadata_str = get_url("https://skimdb.npmjs.com/registry/%s" % package)
        if metadata_str:
            metadata = json.loads(metadata_str)
            if metadata and "versions" in metadata:
                for version in metadata["versions"].values():
                    if "dist" not in version:
                        continue

                    url = version["dist"]["tarball"]
                    filename = conf["package_path"] + re.sub(conf["url_to_filename"][0], conf["url_to_filename"][1], url)
                    if "download_url_replacement" in conf:
                        version["dist"]["tarball"] = re.sub(conf["download_url_modifier"][0], conf["download_url_modifier"][1], url)
                    if "download_url_replacement" in conf:
                        url = re.sub(conf["download_url_replacement"][0], conf["download_url_replacement"][1], url)
                    if not os.path.exists(filename):
                        data = get_url(url)
                        save_data_as_file(filename, data)
                        print("save file: %s" % filename)
                        local_sha1 = sha1(data)
                        if "shasum" in version["dist"] and version["dist"]["shasum"] != local_sha1:
                            print("sha1 error: %s, remote: %s, local: %s" % (filename, version["dist"]["shasum"], local_sha1))
                            os.remove(filename)
                            exit(-1)
                        self.updating_info["updated_file_count"] += 1
                        self.save_updating_info()

            if not os.path.exists(conf["package_path"] + package):
                self.updating_info["updated_packages_count"] += 1
                self.save_updating_info()
            save_data_as_file(conf["package_path"] + package, json.dumps(metadata))

    def run(self):
        time.sleep(random.randint(1, 10))
        updating_packages = self.load_packages()
        for index in range(self.updating_info["updated_index"], len(updating_packages)):
            print("save_package: '%s'(index=%d) from '%s'" % (updating_packages[index], index, self.packages_file))
            self.save_package(updating_packages[index])
            self.updating_info["updated_index"] += 1
            self.updating_info["updated_time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            self.save_updating_info()
            print(self.updating_info)
        return self.updating_info


class NpmMirror:
    def __init__(self, thread_count=15):
        self.cur_dir = os.path.dirname(os.path.realpath(__file__)) + os.path.sep
        self.updating_info_filename = self.cur_dir + "updating_info.json"
        self.thread_count = thread_count
        self.updating_info = {"last_serial": 0, "cur_serial": 0, "updated_packages_count": 0, "updated_file_count": 0}

    @staticmethod
    def get_total_doc_count():
        info = get_url("https://skimdb.npmjs.com/registry")
        return json.loads(info)["doc_count"]

    @staticmethod
    def get_all_packages():
        filename = conf["package_path"] + ".all"
        if os.path.exists(filename):
            with open(filename, "r") as f:
                all_packages = json.load(f)
        else:
            print("get all docs from 'https://skimdb.npmjs.com/registry/_all_docs'")
            all_packages = get_url("https://skimdb.npmjs.com/registry/_all_docs", timeout=600)
            save_data_as_file(filename, all_packages)
            all_packages = json.loads(all_packages)
        return [item["id"] for item in all_packages["rows"]]

    def changelog_since_serial(self, serial):
        total_count = self.get_total_doc_count()
        print("total count = %d" % total_count)
        updating_packages = []
        for count in range(1000, total_count, 1000):
            json_str = get_url("https://skimdb.npmjs.com/registry/_design/app/_view/updated?skip=%d" % (total_count - count))
            rows = json.loads(json_str)["rows"]
            if to_timestamp(rows[0]["key"]) >= serial:
                updating_packages += [row["id"] for row in rows]
            else:
                for index in range(1, len(rows)):
                    if to_timestamp(rows[index]["key"]) >= serial:
                        updating_packages += [row["id"] for row in rows[index:]]
                        return updating_packages
        return updating_packages

    def save_updating_info(self):
        with open(self.updating_info_filename, "w") as f:
            json.dump(self.updating_info, f)

    def load_mirror_info(self):
        if not os.path.exists(self.updating_info_filename):
            self.save_updating_info()
        else:
            with open(self.updating_info_filename, "r") as f:
                self.updating_info = json.load(f)
        print("mirror info '%s': %s" % (self.updating_info_filename, self.updating_info))

        if self.updating_info["cur_serial"] == 0:
            self.updating_info["cur_serial"] = int(time.time() * 1000)
            if self.updating_info["last_serial"] == 0:
                updating_packages = self.get_all_packages()
            else:
                updating_packages = self.changelog_since_serial(self.updating_info["last_serial"])
                if len(updating_packages) == 0:
                    print("no need to update, exit ...")
                    exit(0)

            print("=====> split updating packages into %s directory ...." % self.updating_info["last_serial"])
            self.updating_info["updating_names_file"] = self.split_packages(updating_packages)
            self.updating_info["updating_names_count"] = len(updating_packages)
            self.save_updating_info()
        else:
            print("continue last updating ....")

    def split_packages(self, updating_packages):
        total_count = len(updating_packages)
        self.thread_count = min(self.thread_count, total_count)

        if total_count % self.thread_count != 0:
            step = total_count / self.thread_count + 1
            self.thread_count = (total_count + step - 1) / step
        else:
            step = total_count / self.thread_count

        serial_dir = self.cur_dir + str(self.updating_info["last_serial"])
        if os.path.exists(serial_dir):
            os.remove(serial_dir)
        os.mkdir(serial_dir)
        names = []
        for index in range(0, self.thread_count):
            start_index = index * step
            end_index = min(start_index + step, total_count)
            data = updating_packages[start_index:end_index]
            filename = "%s%supdating_packages_%d" % (serial_dir, os.path.sep, index)
            with open(filename, "w") as f:
                json.dump(data, f)
            names.append(filename)
        return names

    @staticmethod
    def sync_packages(packages_filename):
        sync = NpmSyncPackages(packages_filename)
        return sync.run()

    def run(self):
        self.load_mirror_info()
        pool = ThreadPool(self.thread_count)
        result = pool.map(NpmMirror.sync_packages, self.updating_info["updating_names_file"])
        pool.close()
        pool.join()

        for item in result:
            self.updating_info["updated_packages_count"] += item["updated_packages_count"]
            self.updating_info["updated_file_count"] += item["updated_file_count"]

        self.updating_info["last_serial"] = self.updating_info["cur_serial"]
        self.updating_info["cur_serial"] = 0
        self.updating_info["updating_names_file"] = []
        self.updating_info["updating_names_count"] = 0
        self.save_updating_info()


if __name__ == "__main__":
    create_dir(conf["package_path"])
    npm = NpmMirror()
    npm.run()