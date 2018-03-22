# -*- coding:utf-8 -*-
import random
import time
import hashlib
import json
import os
import datetime
import urllib2
import httplib
import shutil
import re
import sys
import traceback
from multiprocessing.dummy import Pool as ThreadPool
from socket import error as SocketError
import errno

reload(sys)
sys.setdefaultencoding("utf-8")
cur_dir = os.path.dirname(os.path.realpath(__file__)) + os.path.sep
exit_flag = False
conf = {
    "central_url": "https://packagist.org",
    "package_path": "D:\\mirrors\\repository\\php\\",
    "provider_url": "/repository/php/p/%package%$%hash%.json",
    "hosted_domain": [
        {"name": "", "domain": "http://mirrors.huaweicloud.com:8081/repository/php", "rename": "http-mirrors.huaweicloud.com.json"},
        {"name": "_http_cdn", "domain": "http://repo.huaweicloud.com/repository/php", "rename": "http-repo.huaweicloud.com.json"},
        {"name": "_https", "domain": "https://mirrors.huaweicloud.com/repository/php", "rename": "https-mirrors.huaweicloud.com.json"},
        {"name": "_https_cdn", "domain": "https://repo.huaweicloud.com/repository/php", "rename": "https-repo.huaweicloud.com.json"},
    ],
    "download_urls": [
        "https://api\.github\.com/repos/[^/]*/[^/]*/zipball/.*",
        "https://github\.com/[^/]*/[^/]*/archive/.*\.zip",
        "https://github\.com/[^/]*/[^/]*/zipball/.*",
        "https://github\.com/[^/]*/[^/]*/releases/download/[^/]*/.*\.zip",
        "https://gitlab\.com/api/v3/projects/[^/]*/repository/archive\.zip.*",
        "https://gitlab\.com/api/v4/projects/[^/]*/repository/archive\.zip.*",
        "https://bitbucket\.org/[^/]*/[^/]*/get/.*\.zip",
    ],
    "download_urls_blacklist": [".*\.git", ]
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
        return timestamp * 1000 + d.microsecond / 1000

    @staticmethod
    def get_url(url, timeout=120, retry_times=2, ignore_codes=(404, 401, 403, 410, 451, 502)):
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


class ComposerSyncPackages:
    def __init__(self, packages_filename):
        self.packages_info_file = packages_filename + ".info"
        self.packages_file = packages_filename
        self.packages_updated_info_file = packages_filename + ".updated"
        self.packages_updated_info = []
        self.updating_info = {"filename": packages_filename, "updated_index": 0, "updated_packages_count": 0, "updated_file_count": 0}

    def load_packages(self):
        if not Utils.is_file_exist(self.packages_info_file):
            self.save_updating_info()
        self.updating_info = Utils.read_json_file(self.packages_info_file)
        print("load packages from '%s': %s" % (self.packages_file, self.updating_info))

        if Utils.is_file_exist(self.packages_updated_info_file):
            self.packages_updated_info = Utils.read_json_file(self.packages_updated_info_file)
        return Utils.read_json_file(self.packages_file)

    def save_updating_info(self):
        Utils.write_json_file(self.packages_info_file, self.updating_info)

    def save_packages_updated_info(self):
        Utils.write_json_file(self.packages_updated_info_file, self.packages_updated_info)

    @staticmethod
    def is_match_download_urls(url):
        for item in conf["download_urls"]:
            if re.match(item, url):
                return True
        for item in conf["download_urls_blacklist"]:
            if re.match(item, url):
                Utils.write_file(cur_dir + "black_download_url.txt", url + "\n", mode="a")
                return False
        Utils.write_file(cur_dir + "unkown_download_url.txt", url + "\n", mode="a")
        return False

    @staticmethod
    def check_exit_flag():
        lock_file = cur_dir + "exit"
        if os.path.exists(lock_file):
            os.remove(lock_file)
            raise BaseException("exit file is found, raise an exit exception")
        if exit_flag:
            raise BaseException("exit flag is true, raise an exit exception")

    def save_package(self, package):
        metadata_url = "%s/p/%s$%s.json" % (conf["central_url"], package["provider_name"], package["remote_sha256"])
        metadata_str = Utils.get_url(metadata_url)
        if not metadata_str:
            return
        metadata = json.loads(metadata_str)
        if metadata and "packages" in metadata and isinstance(metadata["packages"], dict):
            if "local_sha256" in package:
                local_metadata_filename = "%sp/%s$%s.json" % (conf["package_path"], package["provider_name"], package["local_sha256"])
                if Utils.is_file_exist(local_metadata_filename):
                    local_metadata = Utils.read_json_file(local_metadata_filename)
                else:
                    local_metadata = {"packages": {}}
            for name, versions in metadata["packages"].items():
                for version, value in versions.items():
                    self.check_exit_flag()
                    if "dist" not in value or not value["dist"] or version.find("dev-") != -1:
                        continue

                    # print("dist url: %s, %s, %s, %s" % (value["dist"]["url"], value["dist"]["reference"], value["dist"]["type"], value["dist"]["shasum"]))
                    url = value["dist"]["url"]
                    if not self.is_match_download_urls(url):
                        continue

                    if "local_sha256" in package:
                        if name in local_metadata["packages"] and version in local_metadata["packages"][name]:
                            local_version_value = local_metadata["packages"][name][version]
                            if "dist" in local_version_value and local_version_value["dist"]:
                                value["dist"]["url"] = local_version_value["dist"]["url"]
                                value["dist"]["shasum"] = local_version_value["dist"]["shasum"]
                                continue

                    filename = name + "-" + version
                    if "reference" in value["dist"] and value["dist"]["reference"] and value["dist"]["reference"] != "":
                        filename += "-" + value["dist"]["reference"][0:8]
                    if "type" in value["dist"] and value["dist"]["type"] and value["dist"]["type"] != "":
                        filename += "." + value["dist"]["type"]
                    filename = "dist/" + package["provider_name"] + "/" + filename.replace("/", "-")
                    full_filename = conf["package_path"] + filename
                    if not Utils.is_file_exist(full_filename):
                        data = Utils.get_url(url, timeout=480)
                        if data:
                            Utils.save_data_as_file(full_filename, data)
                            print("save file: %s" % full_filename)
                            self.updating_info["updated_file_count"] += 1
                            self.save_updating_info()

                    if Utils.is_file_exist(full_filename):
                        local_sha1 = Utils.hash("sha1", filename=full_filename)
                        # if "shasum" in value["dist"] and value["dist"]["shasum"] and value["dist"]["shasum"] != "" and value["dist"]["shasum"] != local_sha1:
                        #     print("sha1 error: %s, remote: %s, local: %s" % (full_filename, value["dist"]["shasum"], local_sha1))
                        #     os.remove(full_filename)
                        #     exit(-1)
                        value["dist"]["url"] = conf["hosted_domain"][0]["domain"] + "/" + filename
                        value["dist"]["shasum"] = local_sha1

        info = {"provider_name": package["provider_name"], "include_name": package["include_name"], "remote_cur_sha256": package["remote_sha256"]}
        for hosted_domain in conf["hosted_domain"]:
            metadata_str = json.dumps(metadata)
            metadata_str = metadata_str.replace(conf["hosted_domain"][0]["domain"], hosted_domain["domain"])
            metadata_sha2 = Utils.hash("sha256", metadata_str)
            metadata_filename = "%sp/%s$%s.json" % (conf["package_path"], package["provider_name"], metadata_sha2)
            cur_sha256_name = "local_cur_sha256" + hosted_domain["name"]
            if not Utils.is_file_exist(metadata_filename):
                Utils.save_data_as_file(metadata_filename, metadata_str)
            info[cur_sha256_name] = metadata_sha2
        self.packages_updated_info.append(info)
        self.save_packages_updated_info()

    def run(self):
        time.sleep(random.randint(1, 10))
        try:
            updating_packages = self.load_packages()
            for index in range(self.updating_info["updated_index"], len(updating_packages)):
                print("save_package: '%s'(index=%d) from '%s'" % (updating_packages[index], index, self.packages_file))
                self.save_package(updating_packages[index])

                self.updating_info["updated_packages_count"] += 1
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


class ComposerMirror:
    def __init__(self, thread_count=25):
        self.cur_dir = os.path.dirname(os.path.realpath(__file__)) + os.path.sep
        self.updating_info_filename = self.cur_dir + "updating_info.json"
        self.thread_count = thread_count
        self.updating_info = {"last_serial": 0, "cur_serial": 0, "updated_packages_count": 0, "updated_file_count": 0,
                              "provider_includes": {}, "updating_names_file": []}

    def get_updating_packages(self):
        # new_top_packages_str = get_url("https://packagist.org/packages.json")
        new_top_packages_str = Utils.get_url("%s/packages.json" % conf["central_url"])
        new_provider_includes = json.loads(new_top_packages_str)["provider-includes"]
        provider_includes = self.updating_info["provider_includes"]

        changed_providers = []
        for include_name, new_include_value in new_provider_includes.items():
            if include_name not in provider_includes:
                provider_includes[include_name] = {"providers": {}}

            provider_includes[include_name]["remote_cur_sha256"] = new_include_value["sha256"]
            if "remote_last_sha256" in provider_includes[include_name] and new_include_value["sha256"] == provider_includes[include_name]["remote_last_sha256"]:
                continue

            provider_url = "%s/%s" % (conf["central_url"], include_name.replace("%hash%", new_include_value["sha256"]))
            new_providers_str = Utils.get_url(provider_url)
            if not new_providers_str:
                print("[error]====> provider 404, exit, %s" % provider_url)
                exit(0)

            providers = provider_includes[include_name]["providers"]
            new_providers = json.loads(new_providers_str)["providers"]
            print("url: %s, count: %d" % (provider_url, len(new_providers)))
            for provider_name, provider_value in new_providers.items():
                if provider_name not in providers:
                    providers[provider_name] = {"remote_cur_sha256": provider_value["sha256"]}
                else:
                    providers[provider_name]["remote_cur_sha256"] = provider_value["sha256"]

            for provider_name, provider_value in providers.items():
                if provider_name not in new_providers:
                    del providers[provider_name]
                    continue
                if "remote_last_sha256" in provider_value and provider_value["remote_cur_sha256"] == provider_value["remote_last_sha256"]:
                    continue
                info = {"include_name": include_name, "provider_name": provider_name, "remote_sha256": provider_value["remote_cur_sha256"]}
                local_name = "local_cur_sha256" + conf["hosted_domain"][0]["name"]
                if local_name in provider_value:
                    info["local_sha256"] = provider_value[local_name]
                changed_providers.append(info)
        return changed_providers

    def print_updating_info(self):
        print("mirror info '%s': cur_serial=%d, updated_packages_count=%d, updated_file_count=%d, updating_names_count=%d" % (
            self.updating_info_filename,
            self.updating_info["cur_serial"],
            self.updating_info["updated_packages_count"],
            self.updating_info["updated_file_count"],
            self.updating_info["updating_names_count"]
        ))

    def save_updating_info(self):
        print("saving updating info file: %s" % self.updating_info_filename)
        if Utils.is_file_exist(self.updating_info_filename):
            shutil.copyfile(self.updating_info_filename, self.updating_info_filename + ".back")
        Utils.write_json_file(self.updating_info_filename, self.updating_info)

    def get_updating_packages_from_files(self):
        if "updating_names_file" not in self.updating_info:
            return

        updating_packages = []
        for filename in self.updating_info["updating_names_file"]:
            if Utils.is_file_exist(filename + ".info"):
                info = Utils.read_json_file(filename + ".info")
            else:
                info = {"updated_packages_count": 0, "updated_file_count": 0, "updated_index": 0}

            packages = Utils.read_json_file(filename)
            self.updating_info["updated_packages_count"] += info["updated_packages_count"]
            self.updating_info["updated_file_count"] += info["updated_file_count"]
            updating_packages += packages[info["updated_index"]:]
        return updating_packages

    def load_updated_packages_from_files(self):
        if "updating_names_file" not in self.updating_info:
            return

        lock_file = os.path.dirname(self.updating_info["updating_names_file"][0]) + os.path.sep + "lock"
        if os.path.exists(lock_file):
            print("lock file is found, skip loading updated packages from files")
            return

        print("========================================> load updated packages from files")
        for filename in self.updating_info["updating_names_file"]:
            if not os.path.exists(filename + ".updated"):
                continue

            updated_info = Utils.read_json_file(filename + ".updated")
            for item in updated_info:
                provider = self.updating_info["provider_includes"][item["include_name"]]["providers"][item["provider_name"]]
                for hosted_domain in conf["hosted_domain"]:
                    last_sha256_name = "local_last_sha256" + hosted_domain["name"]
                    cur_sha256_name = "local_cur_sha256" + hosted_domain["name"]
                    if cur_sha256_name in provider and item[cur_sha256_name] == provider[cur_sha256_name]:
                        continue

                    if last_sha256_name in provider and provider[last_sha256_name]:
                        last_metadata_filename = "%sp/%s$%s.json" % (conf["package_path"], item["provider_name"], provider[last_sha256_name])
                        if Utils.is_file_exist(last_metadata_filename):
                            os.remove(last_metadata_filename)
                        provider[last_sha256_name] = None

                    if cur_sha256_name in provider and provider[cur_sha256_name]:
                        provider[last_sha256_name] = provider[cur_sha256_name]
                    provider[cur_sha256_name] = item[cur_sha256_name]
                    self.updating_info["provider_includes"][item["include_name"]]["is_changed" + hosted_domain["name"]] = True
                provider["remote_last_sha256"] = item["remote_cur_sha256"]
            # Utils.write_file(cur_dir + "updated_packages.list", "\n".join([json.dumps(item) for item in updated_info]), mode="a")
        self.save_updating_info()
        Utils.write_file(lock_file, "")
        print("========================================> load updated packages from files successfully")
        self.generate_metadata_files()

    def generate_metadata_files(self):
        print("=================================> generate metadata files")
        for hosted_domain in conf["hosted_domain"]:
            packages_init_json = {
                "packages": [],
                "providers-url": conf["provider_url"],
                "search": "https://packagist.org/search.json?q=%query%&type=%type%",
                "provider-includes": {}
            }

            for include_name, include_value in self.updating_info["provider_includes"].items():
                cur_sha256_name = "local_cur_sha256" + hosted_domain["name"]
                last_sha256_name = "local_last_sha256" + hosted_domain["name"]
                is_changed_name = "is_changed" + hosted_domain["name"]
                if is_changed_name not in include_value or not include_value[is_changed_name]:
                    if cur_sha256_name in include_value:
                        packages_init_json["provider-includes"][include_name] = {"sha256": include_value[cur_sha256_name]}
                    continue
                include_value[is_changed_name] = False

                all_valid_providers = {"providers": {}}
                for provider_name, provider_value in include_value["providers"].items():
                    if cur_sha256_name in provider_value and provider_value[cur_sha256_name] is not None:
                        all_valid_providers["providers"][provider_name] = {"sha256": provider_value[cur_sha256_name]}

                if last_sha256_name in include_value and include_value[last_sha256_name]:
                    last_metadata_filename = "%s%s" % (conf["package_path"], include_name.replace("%hash%", include_value[last_sha256_name]))
                    if Utils.is_file_exist(last_metadata_filename):
                        os.remove(last_metadata_filename)
                    include_value[last_sha256_name] = None

                all_valid_providers_str = json.dumps(all_valid_providers)
                all_valid_providers_sha256 = Utils.hash("sha256", all_valid_providers_str)
                filename = "%s%s" % (conf["package_path"], include_name.replace("%hash%", all_valid_providers_sha256))
                if cur_sha256_name in include_value and all_valid_providers_sha256 == include_value[cur_sha256_name]:
                    continue

                if cur_sha256_name in include_value:
                    include_value[last_sha256_name] = include_value[cur_sha256_name]
                include_value[cur_sha256_name] = all_valid_providers_sha256
                Utils.save_data_as_file(filename, all_valid_providers_str)

                packages_init_json["provider-includes"][include_name] = {"sha256": include_value[cur_sha256_name]}

            Utils.save_data_as_file("%spackages%s.json" % (conf["package_path"], hosted_domain["name"]), json.dumps(packages_init_json))
            Utils.save_data_as_file("%s%s" % (conf["package_path"], hosted_domain["rename"]), json.dumps(packages_init_json))
        print("=================================> generate metadata files successfully")

    def load_mirror_info(self):
        if not Utils.is_file_exist(self.updating_info_filename):
            self.save_updating_info()
        else:
            self.updating_info = Utils.read_json_file(self.updating_info_filename)
        self.print_updating_info()
        # return

        if self.updating_info["cur_serial"] == 0:
            self.updating_info["cur_serial"] = int(time.time() * 1000)
            updating_packages = self.get_updating_packages()
        else:
            print("continue last updating, loading updating info....")
            updating_packages = self.get_updating_packages_from_files()
            self.load_updated_packages_from_files()
            self.print_updating_info()

        if len(updating_packages) == 0:
            print("[exit]====> no need to update, exit ...")
            self.updating_info["cur_serial"] = 0
            self.save_updating_info()
            exit(0)

        print("=====> split updating %d packages into %s directory ...." % (len(updating_packages), self.updating_info["last_serial"]))
        self.updating_info["updating_names_file"] = self.split_packages(updating_packages)
        self.updating_info["updating_names_count"] = len(updating_packages)
        self.save_updating_info()
        self.print_updating_info()

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
            Utils.write_json_file(filename, data)
            names.append(filename)
        return names

    @staticmethod
    def sync_packages(packages_filename):
        sync = ComposerSyncPackages(packages_filename)
        return sync.run()

    def run(self):
        try:
            self.load_mirror_info()
            pool = ThreadPool(self.thread_count)
            pool.map(ComposerMirror.sync_packages, self.updating_info["updating_names_file"])
            pool.close()
            pool.join()

            self.load_updated_packages_from_files()
            if not exit_flag:
                for include in self.updating_info["provider_includes"].values():
                    include["remote_last_sha256"] = include["remote_cur_sha256"]

                self.updating_info["last_serial"] = self.updating_info["cur_serial"]
                self.updating_info["cur_serial"] = 0
                self.updating_info["updating_names_file"] = []
                self.updating_info["updating_names_count"] = 0
                self.save_updating_info()
        except BaseException as ex:
            print("[main exit]==============> %s" % ex.message)
            traceback.print_exc()
        except SystemExit:
            pass

    @staticmethod
    def find_package(package_name):
        total_packages = 0
        includes = Utils.read_json_file(conf["package_path"] + "packages.json")
        for include_name, include_value in includes["provider-includes"].items():
            filename = "%s%s" % (conf["package_path"], include_name.replace("%hash%", include_value["sha256"]))
            providers = Utils.read_json_file(filename)["providers"]
            count = len(providers)
            total_packages += count
            print("include name: %s, count: %d" % (include_name, count))
            if package_name in providers:
                metadata_filename = "%sp/%s$%s.json" % (conf["package_path"], package_name, providers[package_name]["sha256"])
                print("found: %s, %s" % (filename, metadata_filename))
        print("total package count: %d" % total_packages)

    @staticmethod
    def check_metadata():
        updating_info = Utils.read_json_file(cur_dir + "updating_info.json")
        for hosted_domain in conf["hosted_domain"]:
            for include_name, include_value in updating_info["provider_includes"].items():
                cur_sha256_name = "local_cur_sha256" + hosted_domain["name"]
                last_sha256_name = "local_last_sha256" + hosted_domain["name"]

                for provider_name, provider_value in include_value["providers"].items():
                    if cur_sha256_name in provider_value and provider_value[cur_sha256_name] is not None:
                        cur_metadata_filename = "%sp/%s$%s.json" % (conf["package_path"], provider_name, provider_value[cur_sha256_name])
                        if not os.path.exists(cur_metadata_filename):
                            print(cur_metadata_filename)

                    if last_sha256_name in provider_value and provider_value[last_sha256_name] is not None:
                        last_metadata_filename = "%sp/%s$%s.json" % (conf["package_path"], provider_name, provider_value[last_sha256_name])
                        if not os.path.exists(last_metadata_filename):
                            print(last_metadata_filename)


if __name__ == "__main__":
    print("\n\n\n==============[start]===============\n\n")
    if len(sys.argv) == 3 and sys.argv[1] == "find":
        ComposerMirror.find_package(sys.argv[2])
    elif len(sys.argv) == 2 and sys.argv[1] == "check_metadata":
        ComposerMirror.check_metadata()
    else:
        Utils.create_dir(conf["package_path"])
        composer = ComposerMirror()
        composer.run()
