# -*- coding: utf-8 -*-

import urllib
import urllib2


def download_file(url, filename, retry_times=2):
    times = 0
    while times < retry_times:
        times += 1
        try:
            return urllib.urlretrieve(url, filename)
        except BaseException as ex:
            print("url: " + url + ", " + ex.message)
    raise ValueError("[error]: download file failed, " + url)


def get_page(url, timeout=60, retry_times=2):
    times = 0
    while times < retry_times:
        times += 1
        try:
            data = urllib2.urlopen(url, timeout=timeout).read()
            return data
        except urllib2.URLError as ex:
            if times < retry_times:
                print("url: " + url + ", " + ex.message)
            else:
                raise ex

