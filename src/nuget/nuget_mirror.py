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
import zlib
import StringIO


reload(sys)
sys.setdefaultencoding("utf-8")
cur_dir = os.path.dirname(os.path.realpath(__file__)) + os.path.sep
exit_flag = False
conf = {
    "package_path": "D:\\mirrors\\repository\\nuget_v3\\",
    "catalog_url": "https://az636225.vo.msecnd.net/v3-catalog0/index.json",
    "registrations_base_urls": [
        "https://api.nuget.org/v3/registration3/",
        "https://api.nuget.org/v3/registration3-gz-semver2/",
    ],
    "package_base_address": "https://api.nuget.org/v3-flatcontainer/",
    "origin_domain": "https://api.nuget.org/",
    "hosted_domain": "http://mirrors.huaweicloud.com:8082/repository/nuget_v3/",
    "options": "update"
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
        print("save file: %s" % filename)
        Utils.create_dir(filename)
        lock_filename = filename + ".__lock"
        Utils.write_file(lock_filename, "")
        Utils.write_file(filename, data)
        os.remove(lock_filename)

    @staticmethod
    def to_timestamp(date_str):
        # print(date_str)
        date_format = '%Y-%m-%dT%H:%M:%S'
        index = date_str.find(".")
        if index != -1:
            if len(date_str) - index > 8:
                date_str = date_str[:index + 7] + "Z"
            date_format = '%Y-%m-%dT%H:%M:%S.%fZ'
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
                request = urllib2.urlopen(url, timeout=timeout)
                request_info = request.info()
                data = request.read()
                if ('Content-Encoding' in request_info and request_info['Content-Encoding'] == 'gzip') or (
                        'content-encoding' in request_info and request_info['content-encoding'] == 'gzip'):
                    data = zlib.decompress(data, 16 + zlib.MAX_WBITS)
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


class NugetSyncPackages:
    def __init__(self, packages_filename):
        self.packages_file = packages_filename
        self.packages_info_file = packages_filename + ".info"
        self.updating_info = {"filename": packages_filename, "updated_index": 0, "updated_packages_count": 0, "updated_file_count": 0}

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

    @staticmethod
    def get_filename_from_url(url):
        url = url.lower()
        if url.startswith(conf["origin_domain"]):
            filename = url[len(conf["origin_domain"]):]
        elif url.startswith(conf["hosted_domain"]):
            filename = url[len(conf["hosted_domain"]):]
        else:
            raise BaseException("get file name error from %s" % url)
        return filename

    @staticmethod
    def change_url_in_str(text):
        text = text.replace(conf["package_base_address"], conf["hosted_domain"] + "v3-flatcontainer/")
        for registrations_base_url in conf["registrations_base_urls"]:
            hosted_registrations_base_url = registrations_base_url.replace(conf["origin_domain"], conf["hosted_domain"])
            text = text.replace(registrations_base_url, hosted_registrations_base_url)
        return text

    def save_url_as_file(self, url, override=False):
        filename = self.get_filename_from_url(url)
        full_filename = conf["package_path"] + filename
        exist = Utils.is_file_exist(full_filename)
        if override or not exist:
            data = Utils.get_url(conf["origin_domain"] + filename)
            if data:
                Utils.save_data_as_file(full_filename, data)
        return exist

    def save_metadata_data_as_file(self, filename, data, replace_semver2_url=False):
        data = self.change_url_in_str(data)
        Utils.save_data_as_file(filename, data)
        if filename.startswith(conf["package_path"] + "v3/registration3/"):
            filename = filename.replace("v3/registration3/", "v3/registration3-gz/")
            data = data.replace("/v3/registration3/", "/v3/registration3-gz/")
            Utils.save_data_as_file(filename, data)
            if replace_semver2_url:
                filename = filename.replace("v3/registration3-gz/", "v3/registration3-gz-semver2/")
                data = data.replace("/v3/registration3-gz/", "/v3/registration3-gz-semver2/")
                Utils.save_data_as_file(filename, data)

    def save_leafs(self, items):
        for leaf in items:
            self.check_exit_flag()
            filename = self.get_filename_from_url(leaf["@id"])
            full_filename = conf["package_path"] + filename
            if not Utils.is_file_exist(full_filename):
                metadata_str = Utils.get_url(conf["origin_domain"] + filename)
                if metadata_str:
                    if not self.save_url_as_file(leaf["packageContent"]):
                        self.updating_info["updated_file_count"] += 1
                        self.save_updating_info()
                    self.save_url_as_file("%s%s/%s/%s.nuspec" % (
                        conf["package_base_address"],
                        leaf["catalogEntry"]["id"].lower(),
                        leaf["catalogEntry"]["version"].lower(),
                        leaf["catalogEntry"]["id"].lower(),
                    ))
                    self.save_metadata_data_as_file(full_filename, metadata_str, replace_semver2_url=True)
                else:
                    raise BaseException("[error]====>get leaf: %s" % conf["origin_domain"] + filename)

    def save_page(self, page_url):
        filename = self.get_filename_from_url(page_url)
        full_filename = conf["package_path"] + filename
        if not Utils.is_file_exist(full_filename):
            metadata_str = Utils.get_url(conf["origin_domain"] + filename)
            if metadata_str:
                metadata = json.loads(metadata_str)
                self.save_leafs(metadata["items"])
                self.save_metadata_data_as_file(full_filename, metadata_str)
            else:
                print("[error]====>get page: %s" % conf["origin_domain"] + filename)
                # raise BaseException("[error]====>get page: %s" % conf["origin_domain"] + filename)

    def save_package(self, package):
        for registrations_base_url in conf["registrations_base_urls"]:
            index_url = registrations_base_url + package.lower() + "/index.json"
            filename = self.get_filename_from_url(index_url)
            full_filename = conf["package_path"] + filename
            metadata_str = Utils.get_url(index_url)
            if metadata_str:
                metadata = json.loads(metadata_str)
                for page in metadata["items"]:
                    if "items" in page:
                        self.save_leafs(page["items"])
                    else:
                        self.save_page(page["@id"])
                self.save_metadata_data_as_file(full_filename, metadata_str)
            else:
                print("[error]====>get index: %s" % conf["origin_domain"] + filename)
                # raise BaseException("[error]====>get index: %s" % conf["origin_domain"] + filename)
        if not self.save_url_as_file(conf["package_base_address"] + package.lower() + "/index.json", override=True):
            self.updating_info["updated_packages_count"] += 1

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


class NugetMirror:
    def __init__(self, thread_count=1):
        self.cur_dir = os.path.dirname(os.path.realpath(__file__)) + os.path.sep
        self.updating_info_filename = self.cur_dir + "updating_info.json"
        self.thread_count = thread_count
        self.updating_info = {"last_serial": 0, "cur_serial": 0, "updated_packages_count": 0, "updated_file_count": 0}

    def changelog_since_serial(self, serial):
        catalog0 = json.loads(Utils.get_url(conf["catalog_url"]))
        if Utils.to_timestamp(catalog0["commitTimeStamp"]) < serial:
            return []

        catalog_leafs = []
        for page in catalog0["items"]:
            if Utils.to_timestamp(page["commitTimeStamp"]) > serial:
                filename = page["@id"].replace("https://az636225.vo.msecnd.net/", "")
                full_filename = conf["package_path"] + filename
                if not Utils.is_file_exist(full_filename):
                    data = Utils.get_url(page["@id"])
                    if data:
                        Utils.save_data_as_file(full_filename, data)

                catalog_page = Utils.read_json_file(full_filename)
                for leaf in catalog_page["items"]:
                    commit_timestamp = Utils.to_timestamp(leaf["commitTimeStamp"])
                    if commit_timestamp > serial:
                        if commit_timestamp > self.updating_info["cur_serial"]:
                            self.updating_info["cur_serial"] = commit_timestamp
                        catalog_leafs.append(leaf["nuget:id"])
        return list(set(catalog_leafs))

    def save_updating_info(self):
        Utils.write_json_file(self.updating_info_filename, self.updating_info)

    def loading_updating_packages_from_files(self):
        updating_packages = []
        if "updating_names_file" in self.updating_info:
            for filename in self.updating_info["updating_names_file"]:
                if Utils.is_file_exist(filename + ".info"):
                    info = Utils.read_json_file(filename + ".info")
                else:
                    info = {"updated_packages_count": 0, "updated_file_count": 0, "updated_index": 0}
                packages = Utils.read_json_file(filename)
                self.updating_info["updated_packages_count"] += info["updated_packages_count"]
                self.updating_info["updated_file_count"] += info["updated_file_count"]
                updating_packages += packages[info["updated_index"]:]
        self.save_updating_info()
        return updating_packages

    def load_mirror_info(self):
        if not Utils.is_file_exist(self.updating_info_filename):
            self.save_updating_info()
        else:
            self.updating_info = Utils.read_json_file(self.updating_info_filename)
        print("mirror info '%s': %s" % (self.updating_info_filename, self.updating_info))

        if self.updating_info["cur_serial"] == 0:
            if conf["options"] == "fix":
                print("begin getting fixing packages....")
                updating_packages = self.changelog_since_serial(0)
                self.updating_info["cur_serial"] = self.updating_info["last_serial"]
            else:
                updating_packages = self.changelog_since_serial(self.updating_info["last_serial"])
                Utils.write_json_file(cur_dir + "all.json", updating_packages)
        else:
            print("continue last updating, loading updating info....")
            updating_packages = self.loading_updating_packages_from_files()
            print("reload mirror info: %s" % self.updating_info)

        if len(updating_packages) == 0:
            print("[exit]====> no need to update, exit ...")
            self.updating_info["cur_serial"] = 0
            self.save_updating_info()
            exit(0)

        print("=====> split updating %d packages into %s directory ...." % (len(updating_packages), self.updating_info["last_serial"]))
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
        sync = NugetSyncPackages(packages_filename)
        return sync.run()

    def run(self):
        try:
            self.load_mirror_info()
            pool = ThreadPool(self.thread_count)
            result = pool.map(NugetMirror.sync_packages, self.updating_info["updating_names_file"])
            pool.close()
            pool.join()

            if not exit_flag:
                for item in result:
                    self.updating_info["updated_packages_count"] += item["updated_packages_count"]
                    self.updating_info["updated_file_count"] += item["updated_file_count"]
                self.updating_info["last_serial"] = self.updating_info["cur_serial"]
                self.updating_info["cur_serial"] = 0
                self.updating_info["updating_names_file"] = []
                self.updating_info["updating_names_count"] = 0
                if os.path.exists(cur_dir + "fix"):
                    os.remove(cur_dir + 'fix')
            self.save_updating_info()
            print("[main exit]====>: %s" % self.updating_info)
        except SystemExit:
            pass
        except BaseException as ex:
            print("[main exit]==============> %s" % ex.message)
            traceback.print_exc()


if __name__ == "__main__":
    print("\n\n\n==============[start]: %s===============\n\n" % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
    if os.path.exists(cur_dir + "fix"):
        conf["options"] = "fix"
    Utils.create_dir(conf["package_path"])
    npm = NugetMirror()
    npm.run()
