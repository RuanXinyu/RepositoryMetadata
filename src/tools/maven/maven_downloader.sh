#!/usr/bin/env bash
set -e

# arg1=start, arg2=end, format: %s.%N
function getTiming() {
    start_s=$(echo $1 | cut -d '.' -f 1)
    start_ns=$(echo $1 | cut -d '.' -f 2)
    end_s=$(echo $2 | cut -d '.' -f 1)
    end_ns=$(echo $2 | cut -d '.' -f 2)
    time=$(( ( 10#$end_s - 10#$start_s ) * 1000 + ( 10#$end_ns / 1000000 - 10#$start_ns / 1000000 ) ))
}

function change_settings() {
    sed -i "s@<localRepository>.*</localRepository>@<localRepository>"${cur_dir}/m2"</localRepository>@g" settings.xml
    if [[ "${1}" == "cdn_https" ]]; then
        maven_url="https://repo.huaweicloud.com/repository/maven/"
    elif [[ "${1}" == "huawei_https" ]]; then
        maven_url="https://mirrors.huaweicloud.com/repository/maven/"
    elif [[ "${1}" == "cdn_http" ]]; then
        maven_url="http://repo.huaweicloud.com/repository/maven/"
    elif [[ "${1}" == "huawei_http" ]]; then
        maven_url="http://mirrors.huaweicloud.com/repository/maven/"
    elif [[ "${1}" == "ali_http" ]]; then
        maven_url="http://maven.aliyun.com/nexus/content/groups/public/"
    elif [[ "${1}" == "tencent_https" ]]; then
        maven_url="http://mirrors.cloud.tencent.com/nexus/repository/maven-public/"
    else
        echo "please specified correct repository name, <cdn_https|huawei_https|cdn_http|huawei_http|ali_http|tencent_https>"
        exit 1
    fi
    sed -i "s@<url>.*</url>@<url>${maven_url}</url>@g" settings.xml
    cat settings.xml
}

function exec_maven_cmd() {
    echo "\n=============>start execute 'mvn compile --settings ./settings.xml' "
    echo "===============> rm -rf m2"
    rm -rf m2
    change_settings ${1}
    time="-"
    start=$(date +%s.%N)
    mvn compile --settings ./settings.xml
    end=$(date +%s.%N)
    getTiming $start $end
    echo "=============>end execute 'mvn compile --settings ./settings.xml' "
    echo "=============>total time(ms): ${time}"
}

function exec_maven_testsuite() {
    if [ ! -e maven_speed_result.csv ]; then
        echo -n $'\xEF\xBB\xBF' > maven_speed_result.csv
        echo "华为CDN_HTTPS,华为源站_HTTPS,华为CDN_HTTP,华为源站_HTTP,阿里_HTTP,腾讯_HTTP" >> maven_speed_result.csv
    fi
    for ((i=0;i<6;i++))
    do
        exec_maven_cmd "cdn_https"
        echo -e "${time},\c" >> maven_speed_result.csv
        exec_maven_cmd "huawei_https"
        echo -e "${time},\c" >> maven_speed_result.csv
        exec_maven_cmd "cdn_http"
        echo -e "${time},\c" >> maven_speed_result.csv
        exec_maven_cmd "huawei_http"
        echo -e "${time},\c" >> maven_speed_result.csv
        exec_maven_cmd "ali_http"
        echo -e "${time},\c" >> maven_speed_result.csv
        exec_maven_cmd "tencent_https"
        echo -e "${time},\c" >> maven_speed_result.csv
        echo "" >> maven_speed_result.csv
    done
}

cur_dir=$(dirname $0)
cd ${cur_dir}
exec_maven_testsuite
