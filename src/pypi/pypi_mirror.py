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
import urlparse
import httplib
import shutil
import socket
import socks
import traceback
import re
from multiprocessing.dummy import Pool as ThreadPool
from socket import error as SocketError
import errno


reload(sys)
sys.setdefaultencoding("utf-8")
cur_dir = os.path.dirname(os.path.realpath(__file__)) + os.path.sep
exit_flag = False
conf = {
    "store_path": "D:\\mirrors\\repository\\pypi",
    "simple_path": "D:\\mirrors\\repository\\pypi\\simple\\",
    "origin_domain": "pypi.org",
    "hosted_domain": "mirrors.huaweicloud.com/repository/pypi",
    "rpc_use_proxy": False,
    "options": "update"
}
default_sockets = socket.socket
socks.setdefaultproxy(socks.PROXY_TYPE_HTTP, "xxxx", 8080, True, "xxx", "xxx")


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
        return timestamp * 1000 + d.microsecond / 1000 % 1000

    @staticmethod
    def get_url(url, timeout=120, retry_times=2, ignore_codes=(400, 404, )):
        times = 0
        print("get url: %s" % url)
        while times < retry_times:
            times += 1
            try:
                request = urllib2.urlopen(url, timeout=timeout)
                request_info = request.info()
                data = request.read()
                x_pypi_last_serial = int(request_info["x-pypi-last-serial"]) if "x-pypi-last-serial" in request_info else 0
                return data, x_pypi_last_serial
            except (urllib2.URLError, httplib.HTTPException, httplib.IncompleteRead) as ex:
                if times >= retry_times:
                    if hasattr(ex, 'code') and ex.code in ignore_codes:
                        print("[warning]====> url(%s), code(%d): %s" % (url, ex.code, ex.reason))
                        Utils.write_file(cur_dir + str(ex.code) + ".error", url + "\n", mode="a")
                        return None, 0
                    print("[error]====> url(%s): %s" % (url, ex.message))
                    raise ex
            except httplib.BadStatusLine as ex:
                if times >= retry_times:
                    print("[warning]====> url(%s): %s" % (url, ex.message))
                    Utils.write_file(cur_dir + "bad_status_line.error", url + "\n", mode="a")
                    return None, 0
            # except SocketError as ex:
            #     if times >= retry_times:
            #         if ex.errno == errno.ECONNRESET:
            #             print("[warning]====> url(%s): %s" % (url, ex.message))
            #             Utils.write_file(cur_dir + "connect_reset.error", url + "\n", mode="a")
            #             return None, 0
            #         else:
            #             raise ex
            except BaseException as ex:
                if times >= retry_times:
                    print("[error]====> url(%s): %s" % (url, ex.message))
                    raise ex
            print("[retry]====> get url: %s" % url)


class PypiSyncPackages:
    def __init__(self, packages_filename):
        self.packages_file = packages_filename
        self.packages_info_file = packages_filename + ".info"
        self.updating_info = {"filename": packages_filename, "updated_index": 0, "updated_packages_count": 0, "updated_file_count": 0, "retry_packages":[]}

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
        index_data, serial = Utils.get_url("https://pypi.org/simple/%s/" % package["name"])
        if not index_data:
            return
        if serial != 0 and serial < package["serial"]:
            self.updating_info["retry_packages"].append(package)
            return

        urls = re.findall('href="([^"]*)"', index_data)
        for url in urls:
            self.check_exit_flag()
            url_prefix = "https://files.pythonhosted.org/packages/"
            if not url.startswith(url_prefix):
                raise BaseException("[error]====> download url is not match: %s " % url)

            url_data = urlparse.urlsplit(url)
            filename = conf["store_path"] + url_data[2]
            if Utils.is_file_exist(filename):
                continue
            if not url_data[4] or not url_data[4].startswith("sha256="):
                raise BaseException("[error]====> no sha256 value is found in url: %s " % url)
            sha256 = url_data[4][len("sha256="):]

            data = Utils.get_url(url, timeout=240)
            if data:
                Utils.save_data_as_file(filename, data)
                print("save file: %s" % filename)
                local_sha256 = Utils.hash("sha256", data)
                if sha256 != local_sha256:
                    print("sha256 error: %s, remote: %s, local: %s" % (filename, sha256, local_sha256))
                    os.remove(filename)
                    raise BaseException("[error]====> sha256 error")
                self.updating_info["updated_file_count"] += 1
                self.save_updating_info()

        package_name = re.sub(r"[-_.]+", "-", package["name"]).lower()
        package_path = conf["simple_path"] + package_name + os.path.sep
        if not Utils.is_file_exist(package_path + "json"):
            self.updating_info["updated_packages_count"] += 1
        metadata, serial = Utils.get_url("https://pypi.org/pypi/%s/json" % package["name"])
        if serial != 0 and serial < package["serial"]:
            self.updating_info["retry_packages"].append(package)
            return
        if metadata:
            Utils.save_data_as_file(package_path + "json", metadata)
        Utils.save_data_as_file(package_path + "index.html", index_data.replace("https://files.pythonhosted.org/", "../../"))

    def run(self):
        time.sleep(random.randint(1, 10))
        try:
            updating_packages = self.load_packages()
            for index in range(self.updating_info["updated_index"], len(updating_packages)):
                print("save package: '%s'(index=%d) from '%s'" % (updating_packages[index], index, self.packages_file))
                self.save_package(updating_packages[index])
                if
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


class PypiMirror:
    def __init__(self, thread_count=25):
        self.client = xmlrpclib.ServerProxy('https://pypi.org/pypi')
        self.cur_dir = os.path.dirname(os.path.realpath(__file__)) + os.path.sep
        self.updating_info_filename = self.cur_dir + "updating_info.json"
        self.thread_count = thread_count
        self.updating_info = {"serial": 0, "updated_packages_count": 0, "updated_file_count": 0}

    @staticmethod
    def set_proxy(set=True):
        if conf["rpc_use_proxy"]:
            socket.socket = socks.socksocket if set else default_sockets

    def get_all_packages(self):
        filename = conf["simple_path"] + ".all"
        if Utils.is_file_exist(filename):
            return Utils.read_json_file(filename)
        else:
            self.set_proxy(True)
            packages = self.client.list_packages_with_serial()
            self.set_proxy(False)
            Utils.write_json_file(filename, packages)

            index_data = Utils.get_url("https://pypi.org/simple/")
            index_data = re.sub("/simple/", "/repository/pypi/simple/", index_data)
            Utils.save_data_as_file(conf["simple_path"] + "index.html", index_data)
            return packages

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
                    if item["name"] not in updating_packages or item["serial"] > updating_packages[item["name"]]:
                        updating_packages[item["name"]] = item["serial"]
        return updating_packages

    @staticmethod
    def has_new_packages(part, total):
        for name in part.keys():
            if name not in total:
                return True
        return False

    def load_mirror_info(self):
        if not Utils.is_file_exist(self.updating_info_filename):
            self.save_updating_info()
        else:
            self.updating_info = Utils.read_json_file(self.updating_info_filename)

        print("get last_serial ...")
        self.set_proxy(True)
        cur_serial = self.client.changelog_last_serial()
        self.set_proxy(False)
        updating_packages = {}
        if self.updating_info["serial"] == 0:
            print("====> get all packages ....")
            updating_packages = self.get_all_packages()
        else:
            print("====> get changelog_since_serial %d ...." % self.updating_info["serial"])
            self.set_proxy(True)
            data = self.client.changelog_since_serial(self.updating_info["serial"])
            self.set_proxy(False)
            print(json.dumps(data, indent=2))
            for name, version, action_time, action, serial in data:
                if name not in updating_packages or serial > updating_packages[name]:
                    updating_packages[name] = serial
        print("updating packages from last serial: %d" % len(updating_packages))

        print("loading last updating info....")
        self.loading_updating_packages_from_files(updating_packages)
        print("updating packages from last serial: %d" % len(updating_packages))

        if len(updating_packages) == 0:
            print("[exit]====> no need to update, exit ...")
            exit(0)

        all_packages = self.get_all_packages()
        if self.has_new_packages(updating_packages, all_packages):
            os.remove(conf["simple_path"] + ".all")
            self.get_all_packages()

        updating_packages = [{"name": name, "serial": serial} for name, serial in updating_packages.items()]
        print("=====> split updating %d packages into directory ...." % (len(updating_packages)))
        self.updating_info["updating_names_file"] = self.split_packages(updating_packages)
        self.updating_info["serial"] = cur_serial
        print("mirror info: %s" % self.updating_info)
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
        sync = PypiSyncPackages(packages_filename)
        return sync.run()

    def run(self):
        try:
            self.load_mirror_info()
            pool = ThreadPool(self.thread_count)
            result = pool.map(PypiMirror.sync_packages, self.updating_info["updating_names_file"])
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
    Utils.create_dir(conf["simple_path"])
    pypi = PypiMirror()
    pypi.run()
