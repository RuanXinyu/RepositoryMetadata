# -*- coding:utf-8 -*-
import random
import time
import hashlib
import json
import os
import datetime
import urllib2
import shutil
import re
from multiprocessing.dummy import Pool as ThreadPool

cur_dir = os.path.dirname(os.path.realpath(__file__)) + os.path.sep
conf = {
    # "central_url": "https://packagist.phpcomposer.com",
    "central_url": "https://packagist.org",
    "package_path": "D:\\mirrors\\repository\\php\\",
    "provider_url": "/repository/php/p/%package%$%hash%.json",
    "hosted_domain": [
        {"name": "", "domain": "http://mirrors.huaweicloud.com:8081/repository/php"},
        {"name": "_https_cdn", "domain": "https://repo.huaweicloud.com/repository/php"},
        {"name": "_http", "domain": "http://mirrors.huaweicloud.com/repository/php"},
        {"name": "_http_cdn", "domain": "http://repo.huaweicloud.com/repository/php"},
    ],
    "download_urls": [
        "https://api\.github\.com/repos/[^/]*/[^/]*/zipball/.*",
        "https://gitlab\.com/api/v3/projects/[^/]*/repository/archive\.zip.*",
        "https://bitbucket\.org/[^/]*/[^/]*/get/.*\.zip",
    ],
    "download_urls_blacklist": [".*\.git", ]
}


def get_url(url, timeout=120, retry_times=3, ignore_codes=(404,)):
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


def sha1(data):
    h = hashlib.new("sha1")
    h.update(data)
    return h.hexdigest()


def sha2(data):
    h = hashlib.new("sha256")
    h.update(data)
    return h.hexdigest()


def save_data_as_file(filename, data):
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(os.path.dirname(filename))
    with open(filename, 'wb') as f:
        f.write(data)


def create_dir(name):
    if not os.path.exists(name):
        os.makedirs(os.path.dirname(name))


def to_timestamp(date_str):
    format = '%Y-%m-%dT%H:%M:%S.%fZ' if date_str.find(".") != -1 else '%Y-%m-%dT%H:%M:%S'
    d = datetime.datetime.strptime(date_str, format)
    t = d.timetuple()
    timestamp = int(time.mktime(t))
    return timestamp * 1000 + d.microsecond / 1000


class ComposerSyncPackages:
    def __init__(self, packages_filename):
        self.packages_info_file = packages_filename + ".info"
        self.packages_file = packages_filename
        self.packages_updated_info_file = packages_filename + ".updated"
        self.packages_updated_info = []
        self.updating_info = {"filename": packages_filename, "updated_index": 0, "updated_packages_count": 0, "updated_file_count": 0}

    def load_packages(self):
        if not os.path.exists(self.packages_info_file):
            self.save_updating_info()
        with open(self.packages_info_file, "r") as f:
            self.updating_info = json.load(f)
            print("load packages from '%s': %s" % (self.packages_file, self.updating_info))

        if os.path.exists(self.packages_updated_info_file):
            with open(self.packages_updated_info_file, "r") as f:
                self.packages_updated_info = json.load(f)

        with open(self.packages_file, "r") as f:
            return json.load(f)

    def save_updating_info(self):
        with open(self.packages_info_file, "w") as f:
            json.dump(self.updating_info, f)

    def save_packages_updated_info(self):
        with open(self.packages_updated_info_file, "w") as f:
            json.dump(self.packages_updated_info, f)

    @staticmethod
    def is_match_download_urls(url):
        for item in conf["download_urls"]:
            if re.match(item, url):
                return True
        for item in conf["download_urls_blacklist"]:
            if re.match(item, url):
                return True
        with open(cur_dir + "unkown_download_url.txt", 'a') as f:
            f.write(url + "\n")
        return False

    def save_package(self, package):
        metadata_url = "%s/p/%s$%s.json" % (conf["central_url"], package["provider_name"], package["remote_sha256"])
        metadata_str = get_url(metadata_url)
        if not metadata_str:
            return
        metadata = json.loads(metadata_str)
        if metadata and "packages" in metadata and isinstance(metadata["packages"], dict):
            if package["provider_name"] in metadata["packages"]:
                versions = metadata["packages"][package["provider_name"]]
            else:
                versions = metadata["packages"][metadata["packages"].keys()[0]]

            for version, value in versions.items():
                if "dist" not in value or not value["dist"]:
                    continue

                # print("dist url: %s, %s, %s, %s" % (value["dist"]["url"], value["dist"]["reference"], value["dist"]["type"], value["dist"]["shasum"]))
                url = value["dist"]["url"]
                if not self.is_match_download_urls(url):
                    continue

                filename = package["provider_name"] + "-" + version
                if "reference" in value["dist"] and value["dist"]["reference"] and value["dist"]["reference"] != "":
                    filename += "-" + value["dist"]["reference"][0:8]
                if "type" in value["dist"] and value["dist"]["type"] and value["dist"]["type"] != "":
                    filename += "." + value["dist"]["type"]
                filename = "dist/" + package["provider_name"] + "/" + filename.replace("/", "-")
                full_filename = conf["package_path"] + filename
                # if os.path.exists(full_filename):
                #     continue

                data = get_url(url, timeout=480)
                if data:
                    save_data_as_file(full_filename, data)
                    print("save file: %s" % full_filename)
                    local_sha1 = sha1(data)
                    if "shasum" in value["dist"] and value["dist"]["shasum"] and value["dist"]["shasum"] != "" and value["dist"]["shasum"] != local_sha1:
                        print("sha1 error: %s, remote: %s, local: %s" % (full_filename, value["dist"]["shasum"], local_sha1))
                        os.remove(full_filename)
                        exit(-1)
                    value["dist"]["url"] = conf["hosted_domain"][0]["domain"] + "/" + filename
                    value["dist"]["shasum"] = local_sha1
                    self.updating_info["updated_file_count"] += 1
                    self.save_updating_info()

        info = {"provider_name": package["provider_name"], "include_name": package["include_name"], "remote_cur_sha256": package["remote_sha256"]}
        for hosted_domain in conf["hosted_domain"]:
            metadata_str = json.dumps(metadata)
            metadata_str = metadata_str.replace(conf["hosted_domain"][0]["domain"], hosted_domain["domain"])
            metadata_sha2 = sha2(metadata_str)
            metadata_filename = "%sp/%s$%s.json" % (conf["package_path"], package["provider_name"], metadata_sha2)
            cur_sha256_name = "local_cur_sha256" + hosted_domain["name"]
            if not os.path.exists(metadata_filename):
                save_data_as_file(metadata_filename, metadata_str)
            info[cur_sha256_name] = metadata_sha2

        self.updating_info["updated_packages_count"] += 1
        self.save_updating_info()
        self.packages_updated_info.append(info)

    def run(self):
        time.sleep(random.randint(1, 10))
        updating_packages = self.load_packages()
        for index in range(self.updating_info["updated_index"], len(updating_packages)):
            print("save_package: '%s'(index=%d) from '%s'" % (updating_packages[index], index, self.packages_file))
            self.save_package(updating_packages[index])

            self.updating_info["updated_index"] += 1
            self.updating_info["updated_time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            self.save_packages_updated_info()
            self.save_updating_info()
            print(self.updating_info)
        return self.updating_info


class ComposerMirror:
    def __init__(self, thread_count=10):
        self.cur_dir = os.path.dirname(os.path.realpath(__file__)) + os.path.sep
        self.updating_info_filename = self.cur_dir + "updating_info.json"
        self.thread_count = thread_count
        self.updating_info = {"last_serial": 0, "cur_serial": 0, "updated_packages_count": 0, "updated_file_count": 0,
                              "provider_includes": {}, "updating_names_file": []}

    def get_updating_packages(self):
        # new_top_packages_str = get_url("https://packagist.org/packages.json")
        new_top_packages_str = get_url("%s/packages.json" % conf["central_url"])
        new_provider_includes = json.loads(new_top_packages_str)["provider-includes"]
        provider_includes = self.updating_info["provider_includes"]

        changed_providers = []
        for include_name, new_include_value in new_provider_includes.items():
            provider_url = "%s/%s" % (conf["central_url"], include_name.replace("%hash%", new_include_value["sha256"]))
            new_providers_str = get_url(provider_url)
            if not new_providers_str:
                print("404, exit, %s" % provider_url)
                exit(0)

            if include_name not in provider_includes:
                provider_includes[include_name] = {"providers": {}}
            providers = provider_includes[include_name]["providers"]

            new_providers = json.loads(new_providers_str)["providers"]
            for provider_name, provider_value in new_providers.items():
                providers[provider_name] = {"remote_cur_sha256": provider_value["sha256"]}

            for provider_name, provider_value in providers.items():
                if "remote_last_sha256" in provider_value and provider_value["remote_cur_sha256"] == provider_value["remote_last_sha256"]:
                    continue
                changed_providers.append({"include_name": include_name,
                                          "provider_name": provider_name,
                                          "remote_sha256": provider_value["remote_cur_sha256"]})
        return changed_providers

    def print_updating_info(self):
        print("mirror info '%s': cur_serial=%d, updated_packages_count=%d, updated_file_count=%d" % (
            self.updating_info_filename,
            self.updating_info["cur_serial"],
            self.updating_info["updated_packages_count"],
            self.updating_info["updated_file_count"]
        ))

    def save_updating_info(self):
        print("saving updating info file: %s" % self.updating_info_filename)
        with open(self.updating_info_filename, "w") as f:
            json.dump(self.updating_info, f)

    def loading_updating_packages_from_files(self):
        if "updating_names_file" not in self.updating_info:
            return

        updating_packages = []
        for filename in self.updating_info["updating_names_file"]:
            if os.path.exists(filename + ".info"):
                with open(filename + ".info", "r") as f:
                    info = json.load(f)
            else:
                info = {"updated_packages_count": 0, "updated_file_count": 0, "updated_index": 0}

            with open(filename, "r") as f:
                packages = json.load(f)
            self.updating_info["updated_packages_count"] += info["updated_packages_count"]
            self.updating_info["updated_file_count"] += info["updated_file_count"]
            updating_packages += packages[info["updated_index"]:]

            if info["updated_packages_count"] <= 0:
                continue
            with open(filename + ".updated", "r") as f:
                updated_info = json.load(f)
            for item in updated_info:
                provider = self.updating_info["provider_includes"][item["include_name"]]["providers"][item["provider_name"]]

                # delete last metadata file
                for hosted_domain in conf["hosted_domain"]:
                    last_sha256_name = "local_last_sha256" + hosted_domain["name"]
                    if last_sha256_name in provider and provider[last_sha256_name]:
                        last_metadata_filename = "%sp/%s$%s.json" % (conf["package_path"], item["provider_name"], provider[last_sha256_name])
                        if os.path.exists(last_metadata_filename):
                            os.remove(last_metadata_filename)
                        provider[last_sha256_name] = None

                # update current sha256
                for hosted_domain in conf["hosted_domain"]:
                    last_sha256_name = "local_last_sha256" + hosted_domain["name"]
                    cur_sha256_name = "local_cur_sha256" + hosted_domain["name"]
                    if cur_sha256_name in provider and item[cur_sha256_name] == provider[cur_sha256_name]:
                        continue
                    if cur_sha256_name in provider and provider[cur_sha256_name]:
                        provider[last_sha256_name] = provider[cur_sha256_name]
                    provider[cur_sha256_name] = item[cur_sha256_name]
                    self.updating_info["provider_includes"][item["include_name"]]["is_changed" + hosted_domain["name"]] = True
                provider["remote_last_sha256"] = item["remote_cur_sha256"]

        # save metadata as file
        for hosted_domain in conf["hosted_domain"]:
            packages_init_json = {
                "packages": [],
                "notify": "https://packagist.org/downloads/%package%",
                "notify-batch": "https://packagist.org/downloads/",
                "providers-url": conf["provider_url"],
                "search": "https://packagist.org/search.json?q=%query%&type=%type%",
                "provider-includes": {}
            }

            for include_name, include_value in self.updating_info["provider_includes"].items():
                is_changed_name = "is_changed" + hosted_domain["name"]
                if is_changed_name not in include_value or not include_value[is_changed_name]:
                    continue
                include_value[is_changed_name] = False

                cur_sha256_name = "local_cur_sha256" + hosted_domain["name"]
                last_sha256_name = "local_last_sha256" + hosted_domain["name"]
                all_valid_providers = {"providers": {}}
                for provider_name, provider_value in include_value["providers"].items():
                    if cur_sha256_name in provider_value and provider_value[cur_sha256_name] is not None:
                        all_valid_providers["providers"][provider_name] = {"sha256": provider_value[cur_sha256_name]}

                if last_sha256_name in include_value:
                    last_metadata_filename = "%s%s" % (conf["package_path"], include_name.replace("%hash%", include_value[last_sha256_name]))
                    if os.path.exists(last_metadata_filename):
                        os.remove(last_metadata_filename)
                    include_value[last_sha256_name] = None

                all_valid_providers_str = json.dumps(all_valid_providers)
                all_valid_providers_sha256 = sha2(all_valid_providers_str)
                if cur_sha256_name in include_value and all_valid_providers_sha256 == include_value[cur_sha256_name]:
                    continue

                if cur_sha256_name in include_value:
                    include_value[last_sha256_name] = include_value[cur_sha256_name]
                include_value[cur_sha256_name] = all_valid_providers_sha256

                filename = "%s%s" % (conf["package_path"], include_name.replace("%hash%", include_value[cur_sha256_name]))
                save_data_as_file(filename, all_valid_providers_str)

                packages_init_json["provider-includes"][include_name] = {"sha256": include_value[cur_sha256_name]}

            save_data_as_file("%spackages%s.json" % (conf["package_path"], hosted_domain["name"]), json.dumps(packages_init_json))
        self.save_updating_info()
        return updating_packages

    def load_mirror_info(self):
        if not os.path.exists(self.updating_info_filename):
            self.save_updating_info()
        else:
            with open(self.updating_info_filename, "r") as f:
                self.updating_info = json.load(f)
        self.print_updating_info()
        # return

        if self.updating_info["cur_serial"] == 0:
            self.updating_info["cur_serial"] = int(time.time() * 1000)
            updating_packages = self.get_updating_packages()
        else:
            print("continue last updating, loading updating info....")
            updating_packages = self.loading_updating_packages_from_files()
            self.print_updating_info()

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
        sync = ComposerSyncPackages(packages_filename)
        return sync.run()

    def run(self):
        self.load_mirror_info()
        pool = ThreadPool(self.thread_count)
        pool.map(ComposerMirror.sync_packages, self.updating_info["updating_names_file"])
        pool.close()
        pool.join()

        self.loading_updating_packages_from_files()
        self.updating_info["last_serial"] = self.updating_info["cur_serial"]
        self.updating_info["cur_serial"] = 0
        self.updating_info["updating_names_file"] = []
        self.updating_info["updating_names_count"] = 0
        self.save_updating_info()


if __name__ == "__main__":
    create_dir(conf["package_path"])
    composer = ComposerMirror()
    composer.run()
