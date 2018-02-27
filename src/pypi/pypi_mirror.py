# -*- coding:utf-8 -*-
import random
import time
import hashlib
import json
import os
import xmlrpclib
import urllib2
import shutil
from multiprocessing.dummy import Pool as ThreadPool


cur_dir = os.path.dirname(os.path.realpath(__file__)) + os.path.sep
base = "D:\\mirrors\\repository\\pypi\\"
conf = {
    "metadata_path": base + "metadata" + os.path.sep,
    "simple_path": base + "simple" + os.path.sep,
    "package_path": base + "packages" + os.path.sep,
    "origin_domain": "pypi.python.org",
    "download_domain": "mirrors.huaweicloud.com/repository/pypi",
    "hosted_domain": "mirrors.huaweicloud.com/repository/pypi"
}


def get_url(url, timeout=120, retry_times=5, ignore_codes=(404,)):
    times = 0
    print("get url: %s" % url)
    while times < retry_times:
        times += 1
        try:
            data = urllib2.urlopen(url, timeout=timeout).read()
            return data
        except urllib2.HTTPError as ex:
            if times >= retry_times:
                if hasattr(ex, 'code') and ex.code in ignore_codes:
                    print("====> error, url(%s) is %d: %s" % (url, ex.code, ex.reason))
                    with open(cur_dir + str(ex.code) + ".error", 'a') as f:
                        f.write(url + "\n")
                    return None
                print("====> error, url(%s): %s" % (url, ex.reason))
                raise ex
        print("retry, get url: %s" % url)


def md5(data):
    h = hashlib.new("md5")
    h.update(data)
    return h.hexdigest()


def is_file_exist(filename):
    if not os.path.exists(filename):
        return False

    lock_filename = filename + ".__lock"
    if os.path.exists(lock_filename):
        return False
    return True


def save_data_as_file(filename, data):
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(os.path.dirname(filename))

    lock_filename = filename + ".__lock"
    with open(lock_filename, 'wb') as f:
        f.write("")
    with open(filename, 'wb') as f:
        f.write(data)
    os.remove(lock_filename)


def create_dir(name):
    if not os.path.exists(name):
        os.makedirs(os.path.dirname(name))


def has_new_packages(part, total):
    for item in part:
        if item not in total:
            return True
    return False


class PypiSyncPackages:
    def __init__(self, packages_filename):
        self.packages_file = packages_filename
        self.packages_info_file = packages_filename + ".info"
        self.updating_info = {"filename": packages_filename, "updated_index": 0, "updated_packages_count": 0, "updated_file_count": 0}

    def load_packages(self):
        if not is_file_exist(self.packages_info_file):
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
        metadata = get_url("https://pypi.python.org/pypi/%s/json" % package)
        if metadata:
            metadata = json.loads(metadata)
            if "releases" not in metadata:
                return
            for version in metadata["releases"].values():
                for item in version:
                    filename = conf["package_path"] + item["path"]
                    if is_file_exist(filename):
                        continue

                    if "download_domain" in conf:
                        item["url"] = item["url"].replace(conf["origin_domain"], conf["download_domain"])
                    data = get_url(item["url"])
                    if data:
                        save_data_as_file(filename, data)
                        print("save file: %s" % filename)
                        local_md5 = md5(data)
                        if item["md5_digest"] != local_md5:
                            print("md5 error: %s, remote: %s, local: %s" % (filename, item["md5_digest"], local_md5))
                            os.remove(filename)
                            exit(-1)
                        self.updating_info["updated_file_count"] += 1
                        self.save_updating_info()

            index_data = get_url("https://pypi.python.org/simple/%s/" % package)
            save_data_as_file(conf["simple_path"] + package + os.path.sep + "index.html", index_data)
            if not is_file_exist(conf["metadata_path"] + package + ".json"):
                self.updating_info["updated_packages_count"] += 1
                self.save_updating_info()
            save_data_as_file(conf["metadata_path"] + package + ".json", json.dumps(metadata))
        else:
            print("'%s' is not found ..." % package)

    def run(self):
        time.sleep(random.randint(1, 10))
        updating_packages = self.load_packages()
        for index in range(self.updating_info["updated_index"], len(updating_packages)):
            print("save package: '%s'(index=%d) from '%s'" % (updating_packages[index], index, self.packages_file))
            self.save_package(updating_packages[index])
            self.updating_info["updated_index"] += 1
            self.updating_info["updated_time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            self.save_updating_info()
            print(self.updating_info)
        return self.updating_info


class PypiMirror:
    def __init__(self, thread_count=1):
        self.client = xmlrpclib.ServerProxy('https://pypi.python.org/pypi')
        self.cur_dir = os.path.dirname(os.path.realpath(__file__)) + os.path.sep
        self.updating_info_filename = self.cur_dir + "updating_info.json"
        self.thread_count = thread_count
        self.updating_info = {"last_serial": 0, "cur_serial": 0, "updated_packages_count": 0, "updated_file_count": 0}

    def get_all_packages(self):
        filename = conf["metadata_path"] + ".all"
        if is_file_exist(filename):
            with open(filename, "r") as f:
                return json.load(f)
        else:
            packages = self.client.list_packages()
            with open(filename, "w") as f:
                json.dump(packages, f)

            index_data = get_url("https://pypi.python.org/simple/")
            save_data_as_file(conf["simple_path"] + "index.html", index_data)
            return packages

    def save_updating_info(self):
        with open(self.updating_info_filename, "w") as f:
            json.dump(self.updating_info, f)

    def loading_updating_packages_from_files(self):
        updating_packages = []
        if "updating_names_file" in self.updating_info:
            for filename in self.updating_info["updating_names_file"]:
                if is_file_exist(filename + ".info"):
                    with open(filename + ".info", "r") as f:
                        info = json.load(f)
                else:
                    info = {"updated_packages_count": 0, "updated_file_count": 0, "updated_index": 0}
                with open(filename, "r") as f:
                    packages = json.load(f)
                self.updating_info["updated_packages_count"] += info["updated_packages_count"]
                self.updating_info["updated_file_count"] += info["updated_file_count"]
                updating_packages += packages[info["updated_index"]:]
        self.save_updating_info()
        return updating_packages

    def load_mirror_info(self):
        if not is_file_exist(self.updating_info_filename):
            self.save_updating_info()
        else:
            with open(self.updating_info_filename, "r") as f:
                self.updating_info = json.load(f)
        print("mirror info '%s': %s" % (self.updating_info_filename, self.updating_info))

        if self.updating_info["cur_serial"] == 0:
            print("get last_serial ...")
            self.updating_info["cur_serial"] = self.client.changelog_last_serial()
            if self.updating_info["last_serial"] == self.updating_info["cur_serial"]:
                updating_packages = []
            elif self.updating_info["last_serial"] == 0:
                print("====> get all packages ....")
                # with open("updating_packages.json", "r") as f:
                #     updating_packages = json.load(f)
                updating_packages = self.get_all_packages()
                with open("updating_packages.json", "w") as f:
                    json.dump(updating_packages, f)
            else:
                print("====> get changelog_since_serial %d ...." % self.updating_info["last_serial"])
                data = self.client.changelog_since_serial(self.updating_info["last_serial"])
                names_list = [item[0] for item in data]
                updating_packages = list(set(names_list))

                # if has new package, re-get all packages
                all_packages = self.get_all_packages()
                if has_new_packages(updating_packages, all_packages):
                    os.remove(conf["metadata_path"] + ".all")
                    self.get_all_packages()
        else:
            print("continue last updating, loading updating info....")
            updating_packages = self.loading_updating_packages_from_files()
            print("reload mirror info: %s" % self.updating_info)

        if len(updating_packages) == 0:
            print("no need to update, exit ...")
            self.updating_info["cur_serial"] = 0
            self.save_updating_info()
            exit(0)

        print("=====> split updating packages into %s directory ...." % self.updating_info["last_serial"])
        self.updating_info["updating_names_file"] = self.split_packages(updating_packages)
        self.updating_info["updating_names_count"] = len(updating_packages)
        self.save_updating_info()

    def split_packages(self, updating_packages):
        total_count = len(updating_packages)
        self.thread_count = min(self.thread_count, total_count)

        if total_count % self.thread_count != 0:
            step = total_count / self.thread_count + 1
            self.thread_count = (total_count + step - 1) / step
        else:
            step = total_count / self.thread_count

        serial_dir = self.cur_dir + str(self.updating_info["last_serial"])
        if os.path.exists(serial_dir + "_back"):
            shutil.rmtree(serial_dir + "_back")
        if os.path.exists(serial_dir):
            os.rename(serial_dir, serial_dir + "_back")
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
        sync = PypiSyncPackages(packages_filename)
        return sync.run()

    def run(self):
        self.load_mirror_info()
        pool = ThreadPool(self.thread_count)
        result = pool.map(PypiMirror.sync_packages, self.updating_info["updating_names_file"])
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
    create_dir(conf["metadata_path"])
    create_dir(conf["simple_path"])
    create_dir(conf["package_path"])
    pypi = PypiMirror()
    pypi.run()
