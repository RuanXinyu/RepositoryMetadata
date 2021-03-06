# -*- coding:utf-8 -*-
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
exit_flag = False
conf = {
    "package_path": "D:\\mirrors\\repository\\npm\\",
    "origin_domain": "registry.npmjs.org",
    "hosted_domain": "https://mirrors.huaweicloud.com/repository/npm"
}


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


class NpmSyncPackages:
    def __init__(self, packages_filename):
        self.packages_file = packages_filename
        self.packages_info_file = packages_filename + ".info"
        self.updating_info = {"filename": packages_filename, "updated_index": 0, "updated_packages_count": 0, "updated_file_count": 0, "retry_packages": []}

    def load_packages(self):
        if not Utils.is_file_exist(self.packages_info_file):
            self.save_updating_info()
        self.updating_info = Utils.read_json_file(self.packages_info_file)
        print("load packages from '%s': %s" % (self.packages_file, self.updating_info))
        return Utils.read_json_file(self.packages_file)

    def save_updating_info(self):
        Utils.write_json_file(self.packages_info_file, self.updating_info)

    @staticmethod
    def check_exit_flag():
        lock_file = cur_dir + "exit"
        if os.path.exists(lock_file):
            os.remove(lock_file)
            raise BaseException("exit file is found, raise an exit exception")
        if exit_flag:
            raise BaseException("exit flag is true, raise an exit exception")

    def save_package(self, package):
        metadata_str = Utils.get_url("https://replicate.npmjs.com/registry/%s" % package["id"].replace("/", "%2f"))
        if metadata_str:
            metadata = json.loads(metadata_str)
        else:
            return

        if metadata and "versions" in metadata:
            for version in metadata["versions"].values():
                self.check_exit_flag()
                if "dist" not in version:
                    continue

                url = version["dist"]["tarball"]
                match_domain = "://" + conf["origin_domain"] + "/"
                index = url.find(match_domain)
                if not url.endswith(".tgz") or index == -1:
                    continue

                filename = url[index + len(match_domain):]
                full_filename = conf["package_path"] + filename

                if not Utils.is_file_exist(full_filename):
                    data = Utils.get_url(url, timeout=240)
                    if data:
                        Utils.save_data_as_file(full_filename, data)
                        print("save file: %s" % full_filename)
                        local_sha1 = Utils.hash("sha1", data)
                        if "shasum" in version["dist"] and version["dist"]["shasum"] != local_sha1:
                            print("[error]====> sha1 error: %s, remote: %s, local: %s" % (full_filename, version["dist"]["shasum"], local_sha1))
                            os.remove(full_filename)
                            raise BaseException("[error]====> sha1 error")
                        self.updating_info["updated_file_count"] += 1
                        self.save_updating_info()

                if Utils.is_file_exist(full_filename):
                    version["dist"]["tarball"] = conf["hosted_domain"] + "/" + filename

        if not Utils.is_file_exist(conf["package_path"] + package["id"] + "/index.json"):
            self.updating_info["updated_packages_count"] += 1
        Utils.save_data_as_file(conf["package_path"] + package["id"] + "/index.json", json.dumps(metadata))

        if "_rev" in metadata and package["rev"] != "" and metadata["_rev"] != package["rev"]:
            print("[warning]====> %s json expect rev %s, but got %s" % (package["id"], package["rev"], metadata["_rev"]))
            self.updating_info["retry_packages"].append(package)

    def run(self):
        try:
            time.sleep(random.randint(1, 10))
            updating_packages = self.load_packages()
            for index in range(self.updating_info["updated_index"], len(updating_packages)):
                print("save_package: '%s'(index=%d) from '%s'" % (updating_packages[index], index, self.packages_file))
                self.save_package(updating_packages[index])
                self.updating_info["updated_index"] += 1
                self.updating_info["updated_time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                self.save_updating_info()
                print(self.updating_info)
        except BaseException as ex:
            print("[exit]==============> %s, %s" % (self.packages_file, ex.message))
            if str(ex.message).find("exit exception") == -1:
                traceback.print_exc()
            global exit_flag
            exit_flag = True

        return self.updating_info


class NpmMirror:
    def __init__(self, thread_count=25):
        self.cur_dir = os.path.dirname(os.path.realpath(__file__)) + os.path.sep
        self.updating_info_filename = self.cur_dir + "updating_info.json"
        self.thread_count = thread_count
        self.updating_info = {"serial": 0, "updated_packages_count": 0, "updated_file_count": 0}

    @staticmethod
    def get_last_update_seq():
        db_info = json.loads(Utils.get_url("https://replicate.npmjs.com/registry", timeout=60))
        return db_info["update_seq"]

    def get_all_packages(self):
        self.updating_info["serial"] = self.get_last_update_seq()
        filename = conf["package_path"] + "-/all"
        print("get all docs from 'https://replicate.npmjs.com/registry/_all_docs'")
        all_packages = Utils.get_url("https://replicate.npmjs.com/registry/_all_docs", timeout=600)
        Utils.save_data_as_file(filename, all_packages)
        all_packages = json.loads(all_packages)
        data = {}
        for item in all_packages["rows"]:
            rev_num = int(item["value"]["rev"].split("-")[0])
            if item["id"] not in data or data[item["id"]]["rev_num"] < rev_num:
                data[item["id"]] = {"rev_num": rev_num, "rev": item["value"]["rev"]}
        return data

    def changelog_since_serial(self):
        changes = json.loads(Utils.get_url("https://replicate.npmjs.com/registry/_changes?feed=normal&since=%d" % self.updating_info["serial"]))
        updating_packages = {}
        for item in changes["results"]:
            rev_info = {"rev_num": 0, "rev": ""}
            for change in item["changes"]:
                rev = int(change["rev"].split("-")[0])
                if rev > rev_info["rev_num"]:
                    rev_info = {"rev_num": rev, "rev": change["rev"]}
            if item["id"] not in updating_packages or updating_packages[item["id"]]["rev_num"] < rev_info["rev_num"]:
                updating_packages[item["id"]] = {"rev_num": rev_info["rev_num"], "rev": rev_info["rev"]}
        self.updating_info["serial"] = changes["last_seq"]
        return updating_packages

    def save_updating_info(self):
        Utils.write_json_file(self.updating_info_filename, self.updating_info)

    def loading_updating_packages_from_files(self, updating_packages):
        if "updating_names_file" in self.updating_info:
            for filename in self.updating_info["updating_names_file"]:
                if Utils.is_file_exist(filename + ".info"):
                    info = Utils.read_json_file(filename + ".info")
                else:
                    info = {"updated_packages_count": 0, "updated_file_count": 0, "updated_index": 0, "retry_packages": []}
                packages = Utils.read_json_file(filename)
                data = packages[info["updated_index"]:] + info["retry_packages"]
                for item in data:
                    if item["id"] not in updating_packages or updating_packages[item["id"]]["rev_num"] < item["rev_num"]:
                        updating_packages[item["id"]] = {"rev_num": item["rev_num"], "rev": item["rev"]}
        return updating_packages

    def load_mirror_info(self):
        if not Utils.is_file_exist(self.updating_info_filename):
            self.save_updating_info()
        else:
            self.updating_info = Utils.read_json_file(self.updating_info_filename)
        print("mirror info '%s': %s" % (self.updating_info_filename, self.updating_info))

        updating_packages = {}
        if self.updating_info["serial"] == 0:
            print("====> get all packages ....")
            updating_packages = self.get_all_packages()
        else:
            print("====> get changelog_since_serial %d ...." % self.updating_info["serial"])
            updating_packages = self.changelog_since_serial()
        print("updating packages count from last serial: %d" % len(updating_packages))

        print("loading last updating info....")
        self.loading_updating_packages_from_files(updating_packages)
        print("total updating packages count: %d" % len(updating_packages))

        if len(updating_packages) == 0:
            print("[exit]====> no need to update, exit ...")
            exit(0)

        updating_packages = [{"id": name, "rev_num": rev["rev_num"], "rev": rev["rev"]} for name, rev in updating_packages.items()]
        print("=====> split updating %d packages into directory ...." % len(updating_packages))
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

        serial_dir = self.cur_dir + "thread_data"
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
            Utils.write_json_file(filename, data)
            names.append(filename)
        return names

    @staticmethod
    def sync_packages(packages_filename):
        sync = NpmSyncPackages(packages_filename)
        return sync.run()

    def run(self):
        try:
            self.load_mirror_info()
            pool = ThreadPool(self.thread_count)
            result = pool.map(NpmMirror.sync_packages, self.updating_info["updating_names_file"])
            pool.close()
            pool.join()

            for item in result:
                self.updating_info["updated_packages_count"] += item["updated_packages_count"]
                self.updating_info["updated_file_count"] += item["updated_file_count"]
            self.save_updating_info()
            print("[main exit]====>: %s" % self.updating_info)
        except SystemExit:
            pass
        except BaseException as ex:
            print("[main exit]==============> %s" % ex.message)
            traceback.print_exc()


if __name__ == "__main__":
    print("\n\n\n==============[start]: %s===============\n\n" % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
    Utils.create_dir(conf["package_path"])
    npm = NpmMirror()
    npm.run()
