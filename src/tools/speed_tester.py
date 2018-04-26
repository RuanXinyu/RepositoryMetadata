# -*- coding:utf-8 -*-
import time
import os
import sys
import datetime
import urllib2
import httplib
import re
import codecs

cur_dir = os.path.dirname(os.path.realpath(__file__)) + os.path.sep


def download_url(url):
    print("get url: %s" % url)
    start_time = time.time() * 1000
    data = urllib2.urlopen(url).read()
    total_time = time.time() * 1000 - start_time
    speed = len(data) / total_time
    return len(data) / 1000, total_time / 1000, speed


def get_speed(url, total_count=5, skip_count=1):
    data_len = 0
    total_time = 0
    speed = 0
    for i in range(0, total_count + skip_count):
       data_len_t, total_time_t, speed_t = download_url(url)
       if i >= skip_count:
           data_len += data_len_t
           total_time += total_time_t
           speed += speed_t
    return data_len/total_count, total_time/total_count, speed/total_count


def test_speed(data, name, mode="dict"):
    csv_filename = "%s_speed_result.csv" % name
    back_csv_filename = "%s_speed_result_back.csv" % name
    if os.path.exists(csv_filename):
        if os.path.exists(back_csv_filename):
            os.remove(back_csv_filename)
        os.rename(csv_filename, back_csv_filename)

    f = codecs.open(csv_filename, "wb", "utf_8_sig")
    f.write(u"站点,协议类型,文件类型,文件大小,下载耗时,下载速度\r\n")
    if mode == "dict":
        for filename in data["filenames"]:
            for domain in data["domains"]: 
                data_len, total_time, speed = get_speed(domain["url"] + filename["filename"])
                text = u"%s,%s,%dKB,%.2fS,%.1f\r\n" % (domain["text"], filename["text"], data_len, total_time, speed)
                print(text)
                f.write(text)
    else:
        for item in data:
            data_len, total_time, speed = get_speed(item["url"])
            text = u"%s,%dKB,%.2fS,%.1f\r\n" % (item["text"], data_len, total_time, speed)
            # print(text)
            f.write(text)

    f.close()
    print(u"test %s speed success" % name)


def huawei_test():
    data = [
        {"url": "http://repo.huaweicloud.com/repository/maven/com/couchbase/client/core-io/1.2.0/core-io-1.2.0.jar", "text": u"华为_CDN缓存,HTTP,大文件"},
        {"url": "http://mirrors.huaweicloud.com/repository/maven/com/couchbase/client/core-io/1.2.0/core-io-1.2.0.jar", "text": u"华为_Nginx缓存,HTTP,大文件"},
        {"url": "https://repo.huaweicloud.com/repository/maven/com/couchbase/client/core-io/1.2.0/core-io-1.2.0.jar", "text": u"华为_CDN缓存,HTTPS,大文件"},
        {"url": "https://mirrors.huaweicloud.com/repository/maven/com/couchbase/client/core-io/1.2.0/core-io-1.2.0.jar", "text": u"华为_Nginx缓存,HTTPS,大文件"},
        {"url": "https://mirrors.huaweicloud.com/repository/nuget/EntityFramework/6.2.0", "text": u"华为_Nexus缓存,HTTPS,大文件"},

        {"url": "http://repo.huaweicloud.com/repository/maven/ai/grakn/grakn-test/0.14.0/grakn-test-0.14.0.pom", "text": u"华为_CDN缓存,HTTP,小文件"},
        {"url": "http://mirrors.huaweicloud.com/repository/maven/ai/grakn/grakn-test/0.14.0/grakn-test-0.14.0.pom", "text": u"华为_Nginx缓存,HTTP,小文件"},
        {"url": "https://repo.huaweicloud.com/repository/maven/ai/grakn/grakn-test/0.14.0/grakn-test-0.14.0.pom", "text": u"华为_CDN缓存,HTTPS,小文件"},
        {"url": "https://mirrors.huaweicloud.com/repository/maven/ai/grakn/grakn-test/0.14.0/grakn-test-0.14.0.pom", "text": u"华为_Nginx缓存,HTTPS,小文件"},
        {"url": "https://mirrors.huaweicloud.com/repository/nuget/WcfClientPackageGenerator/0.0.6", "text": u"华为_Nexus缓存,HTTPS,小文件"},
    ]
    test_speed(data, "huawei", mode="list")
    

def maven_test():
    data = {        
        "filenames": [
            {"filename": "com/couchbase/client/core-io/1.2.0/core-io-1.2.0.jar", "text": u"大文件"},
            {"filename": "au/com/codeka/carrot/2.4.0/carrot-2.4.0.pom", "text": u"小文件"},
        ],
        "domains": [
            {"url": "http://repo.huaweicloud.com/repository/maven/", "text": u"华为CDN,HTTP"},
            {"url": "https://repo.huaweicloud.com/repository/maven/", "text": u"华为CDN,HTTPS"},
            {"url": "https://mirrors.huaweicloud.com/repository/maven/", "text": u"华为源站,HTTPS"},
            {"url": "http://mirrors.huaweicloud.com/repository/maven/", "text": u"华为源站,HTTP"},
            {"url": "http://maven.aliyun.com/nexus/content/groups/public/", "text": u"阿里,HTTP"},
            {"url": "http://mirrors.cloud.tencent.com/nexus/repository/maven-public/", "text": u"腾讯,HTTP"},
        ]
    }
    test_speed(data, "maven")


def npm_test():
    data = {        
        "filenames": [
            {"filename": "whiplash-ui-library/-/whiplash-ui-library-1.5.1.tgz", "text": u"大文件"},
            {"filename": "grunt-pages/-/grunt-pages-0.3.0.tgz", "text": u"小文件"},
            {"filename": "whiplash-ui-library", "text": u"元数据"},
        ],
        "domains": [
            {"url": "https://repo.huaweicloud.com/repository/npm/", "text": u"华为CDN,HTTPS"},
            {"url": "https://mirrors.huaweicloud.com/repository/npm/", "text": u"华为源站,HTTPS"},
            # {"url": "https://mirrors.huaweicloud.com/repository/npm2/", "text": u"华为自研,HTTPS"},
            {"url": "https://registry.npmjs.org/", "text": u"官方,HTTPS"},
            {"url": "https://registry.npm.taobao.org/", "text": u"阿里,HTTPS"},
        ]
    }
    test_speed(data, "npm")


def pypi_test():
    data = [
        {"url": "https://repo.huaweicloud.com/repository/pypi/packages/c7/b3/e417c7c5192ee32f6b551c3ab181ad3b635a0bae11683934b17b8cc0c93a/pipenv-0.1.5.tar.gz", "text": u"华为CDN,HTTPS,小文件"},
        {"url": "https://mirrors.huaweicloud.com/repository/pypi/packages/c7/b3/e417c7c5192ee32f6b551c3ab181ad3b635a0bae11683934b17b8cc0c93a/pipenv-0.1.5.tar.gz", "text": u"华为源站,HTTPS,小文件"},
        {"url": "http://repo.huaweicloud.com/repository/pypi/packages/c7/b3/e417c7c5192ee32f6b551c3ab181ad3b635a0bae11683934b17b8cc0c93a/pipenv-0.1.5.tar.gz", "text": u"华为CDN,HTTP,小文件"},
        {"url": "http://mirrors.huaweicloud.com/repository/pypi/packages/c7/b3/e417c7c5192ee32f6b551c3ab181ad3b635a0bae11683934b17b8cc0c93a/pipenv-0.1.5.tar.gz", "text": u"华为源站,HTTP,小文件"},
        # {"url": "https://mirrors.huaweicloud.com/repository/pypi2/packages/c7/b3/e417c7c5192ee32f6b551c3ab181ad3b635a0bae11683934b17b8cc0c93a/pipenv-0.1.5.tar.gz", "text": u"华为自研,HTTPS,小文件"},
        {"url": "https://files.pythonhosted.org/packages/c7/b3/e417c7c5192ee32f6b551c3ab181ad3b635a0bae11683934b17b8cc0c93a/pipenv-0.1.5.tar.gz", "text": u"官方,HTTPS,小文件"},
        {"url": "http://mirrors.aliyun.com/pypi/packages/c7/b3/e417c7c5192ee32f6b551c3ab181ad3b635a0bae11683934b17b8cc0c93a/pipenv-0.1.5.tar.gz", "text": u"阿里,HTTP,小文件"},
        {"url": "http://mirrors.cloud.tencent.com/pypi/packages/c7/b3/e417c7c5192ee32f6b551c3ab181ad3b635a0bae11683934b17b8cc0c93a/pipenv-0.1.5.tar.gz", "text": u"腾讯,HTTP,小文件"},

        {"url": "https://repo.huaweicloud.com/repository/pypi/simple/django/", "text": u"华为CDN,HTTPS,元数据"},
        {"url": "https://mirrors.huaweicloud.com/repository/pypi/simple/django/", "text": u"华为源站,HTTPS,元数据"},
        {"url": "http://repo.huaweicloud.com/repository/pypi/simple/django/", "text": u"华为CDN,HTTP,元数据"},
        {"url": "http://mirrors.huaweicloud.com/repository/pypi/simple/django/", "text": u"华为源站,HTTP,元数据"},
        # {"url": "https://mirrors.huaweicloud.com/repository/pypi2/simple/django/", "text": u"华为自研,HTTPS,元数据"},
        {"url": "https://pypi.org/simple/django/", "text": u"官方,HTTPS,元数据"},
        {"url": "http://mirrors.aliyun.com/pypi/simple/django/", "text": u"阿里,HTTP,元数据"},
        {"url": "http://mirrors.cloud.tencent.com/pypi/simple/django/", "text": u"腾讯,HTTP,元数据"},

        {"url": "https://repo.huaweicloud.com/repository/pypi/packages/14/17/01d0d5493d164a539e02a6d83e3e260f9101ceea5fe63e5cf327c77ad7be/hisparc-sapphire-0.12.6.tar.gz", "text": u"华为CDN,HTTPS,大文件"},
        {"url": "https://mirrors.huaweicloud.com/repository/pypi/packages/14/17/01d0d5493d164a539e02a6d83e3e260f9101ceea5fe63e5cf327c77ad7be/hisparc-sapphire-0.12.6.tar.gz", "text": u"华为源站,HTTPS,大文件"},
        {"url": "http://repo.huaweicloud.com/repository/pypi/packages/14/17/01d0d5493d164a539e02a6d83e3e260f9101ceea5fe63e5cf327c77ad7be/hisparc-sapphire-0.12.6.tar.gz", "text": u"华为CDN,HTTP,大文件"},
        {"url": "http://mirrors.huaweicloud.com/repository/pypi/packages/14/17/01d0d5493d164a539e02a6d83e3e260f9101ceea5fe63e5cf327c77ad7be/hisparc-sapphire-0.12.6.tar.gz", "text": u"华为源站,HTTP,大文件"},
        # {"url": "https://mirrors.huaweicloud.com/repository/pypi2/packages/14/17/01d0d5493d164a539e02a6d83e3e260f9101ceea5fe63e5cf327c77ad7be/hisparc-sapphire-0.12.6.tar.gz", "text": u"华为自研,HTTPS,大文件"},
        {"url": "https://files.pythonhosted.org/packages/14/17/01d0d5493d164a539e02a6d83e3e260f9101ceea5fe63e5cf327c77ad7be/hisparc-sapphire-0.12.6.tar.gz", "text": u"官方,HTTPS,大文件"},
        {"url": "http://mirrors.aliyun.com/pypi/packages/14/17/01d0d5493d164a539e02a6d83e3e260f9101ceea5fe63e5cf327c77ad7be/hisparc-sapphire-0.12.6.tar.gz", "text": u"阿里,HTTP,大文件"},
        {"url": "http://mirrors.cloud.tencent.com/pypi/packages/14/17/01d0d5493d164a539e02a6d83e3e260f9101ceea5fe63e5cf327c77ad7be/hisparc-sapphire-0.12.6.tar.gz", "text": u"腾讯,HTTP,大文件"},

    ]
    test_speed(data, "pypi", mode="list")


def nuget_test():
    data = [
        {"url": "https://repo.huaweicloud.com/repository/nuget/EntityFramework/6.2.0", "text": u"华为CDN,HTTPS,大文件"},
        {"url": "https://mirrors.huaweicloud.com/repository/nuget/EntityFramework/6.2.0", "text": u"华为源站,HTTPS,大文件"},
        {"url": "https://www.nuget.org/api/v2/package/EntityFramework/6.2.0", "text": u"官方,HTTPS,大文件"},

        {"url": "https://repo.huaweicloud.com/repository/nuget/CloudConvertWrapper/0.0.1", "text": u"华为CDN,HTTPS,小文件"},
        {"url": "https://mirrors.huaweicloud.com/repository/nuget/CloudConvertWrapper/0.0.1", "text": u"华为源站,HTTPS,小文件"},
        {"url": "https://www.nuget.org/api/v2/package/CloudConvertWrapper/0.0.1", "text": u"官方,HTTPS,小文件"},

        {"url": "https://repo.huaweicloud.com/repository/nuget/FindPackagesById()?id=%27jquery%27&semVerLevel=2.0.0", "text": u"华为CDN,HTTPS,元数据"},
        {"url": "https://mirrors.huaweicloud.com/repository/nuget/FindPackagesById()?id=%27jquery%27&semVerLevel=2.0.0", "text": u"华为源站,HTTPS,元数据"},
        {"url": "https://www.nuget.org/api/v2/FindPackagesById()?id=%27jquery%27&semVerLevel=2.0.0", "text": u"官方,HTTPS,元数据"},
    ]
    test_speed(data, "nuget", mode="list")


def rubygems_test():
    data = [
        {"url": "https://repo.huaweicloud.com/repository/rubygems/gems/sql_search_n_sort-2.1.0.gem", "text": u"华为CDN,HTTPS,大文件"},
        {"url": "https://mirrors.huaweicloud.com/repository/rubygems/gems/sql_search_n_sort-2.1.0.gem", "text": u"华为源站,HTTPS,大文件"},
        {"url": "https://rubygems.org/gems/sql_search_n_sort-2.1.0.gem", "text": u"官方,HTTPS,大文件"},
        {"url": "https://gems.ruby-china.org/gems/sql_search_n_sort-2.1.0.gem", "text": u"Ruby中国,HTTPS,大文件"},
        {"url": "http://mirrors.cloud.tencent.com/rubygems/gems/sql_search_n_sort-2.1.0.gem", "text": u"腾讯,HTTP,大文件"},

        {"url": "https://repo.huaweicloud.com/repository/rubygems/gems/jquery-0.0.1.gem", "text": u"华为CDN,HTTPS,小文件"},
        {"url": "https://mirrors.huaweicloud.com/repository/rubygems/gems/jquery-0.0.1.gem", "text": u"华为源站,HTTPS,小文件"},
        {"url": "https://rubygems.org/gems/jquery-0.0.1.gem", "text": u"官方,HTTPS,小文件"},
        {"url": "https://gems.ruby-china.org/gems/jquery-0.0.1.gem", "text": u"Ruby中国,HTTPS,小文件"},
        {"url": "http://mirrors.cloud.tencent.com/rubygems/gems/jquery-0.0.1.gem", "text": u"腾讯,HTTP,小文件"},

        {"url": "https://repo.huaweicloud.com/repository/rubygems/specs.4.8.gz", "text": u"华为CDN,HTTPS,元数据"},
        {"url": "https://mirrors.huaweicloud.com/repository/rubygems/specs.4.8.gz", "text": u"华为源站,HTTPS,元数据"},
        # {"url": "https://mirrors.huaweicloud.com/repository/rubygems/api/v1/dependencies?gems=jquery", "text": u"华为源站,HTTPS,元数据"},
        {"url": "https://rubygems.org/specs.4.8.gz", "text": u"官方,HTTPS,元数据"},
        {"url": "https://gems.ruby-china.org/specs.4.8.gz", "text": u"Ruby中国,HTTPS,元数据"},
        {"url": "http://mirrors.cloud.tencent.com/rubygems/specs.4.8.gz", "text": u"腾讯,HTTP,元数据"},
    ]
    test_speed(data, "rubygems", mode="list")


def composer_test():
    data = [
        {"url": "https://repo.huaweicloud.com/repository/php/dist/symfony/symfony/symfony-symfony-v2.1.12-f73944e6.zip", "text": u"华为CDN,HTTPS,大文件"},
        {"url": "https://mirrors.huaweicloud.com/repository/php/dist/symfony/symfony/symfony-symfony-v2.1.12-f73944e6.zip", "text": u"华为源站,HTTPS,大文件"},
        {"url": "https://files.phpcomposer.com/files/symfony/symfony/f73944e6536262eb3d3cf3e7db47ecc5d953844d.zip", "text": u"Composer中国,HTTPS,大文件"},

        {"url": "https://repo.huaweicloud.com/repository/php/dist/perchten/rmrdir/perchten-rmrdir-1.0.2-ce8b95e5.zip", "text": u"华为CDN,HTTPS,小文件"},
        {"url": "https://mirrors.huaweicloud.com/repository/php/dist/perchten/rmrdir/perchten-rmrdir-1.0.2-ce8b95e5.zip", "text": u"华为源站,HTTPS,小文件"},
        {"url": "https://files.phpcomposer.com/files/perchten/php-rmrdir/ce8b95e509d64f339a10c3475a13ad687f1e6905.zip", "text": u"Composer中国,HTTPS,小文件"},
    ]
    test_speed(data, "composer", mode="list")


if __name__ == "__main__":
    # huawei_test()
    # maven_test()
    # npm_test()
    # pypi_test()
    # nuget_test()
    # rubygems_test()
    composer_test()
