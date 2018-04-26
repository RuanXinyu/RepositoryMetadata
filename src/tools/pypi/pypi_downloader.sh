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

function change_pip_ini() {
    if [[ "${1}" == "cdn_https" ]]; then
        url="https://repo.huaweicloud.com/repository/pypi/simple/"
        domain="repo.huaweicloud.com"
    elif [[ "${1}" == "huawei_https" ]]; then
        url="https://mirrors.huaweicloud.com/repository/pypi/simple/"
        domain="mirrors.huaweicloud.com"
    elif [[ "${1}" == "cdn_http" ]]; then
        url="http://repo.huaweicloud.com/repository/pypi/simple/"
        domain="repo.huaweicloud.com"
    elif [[ "${1}" == "huawei_http" ]]; then
        url="http://mirrors.huaweicloud.com/repository/pypi/simple/"
        domain="mirrors.huaweicloud.com"
    elif [[ "${1}" == "office_https" ]]; then
        url="https://pypi.org/simple/"
        domain="pypi.org"
    elif [[ "${1}" == "ali_http" ]]; then
        url="http://mirrors.aliyun.com/pypi/simple/"
        domain="mirrors.aliyun.com"
    elif [[ "${1}" == "tencent_http" ]]; then
        url="http://mirrors.cloud.tencent.com/pypi/simple/"
        domain="mirrors.cloud.tencent.com"
    else
        echo "please specified correct repository name, <cdn_https|huawei_https|cdn_http|huawei_http|office_https|ali_http|tencent_http>"
        exit 1
    fi
    

    echo "[global]" > pip.ini
    echo "index-url = ${url}" >> pip.ini
    echo "trusted-host = ${domain}" >> pip.ini
    cat pip.ini
    cp -a pip.ini ~/pip/pip.ini 
}

function exec_pip_cmd() {
    echo "\n=============>start execute 'pip install --target=./packages --no-cache-dir -r requirements.txt' "
    echo "===============> rm -rf packages"
    rm -rf packages
    change_pip_ini ${1}
    time="-"
    start=$(date +%s.%N)
    pip install --target=./packages --no-cache-dir -r requirements.txt
    rm -rf packages
    pip install --target=./packages --no-cache-dir pnc-cli
    end=$(date +%s.%N)
    getTiming $start $end
    echo "=============>end execute 'pip install --target=./packages --no-cache-dir -r requirements.txt' "
    echo "=============>total time(ms): ${time}"
}

function exec_pip_testsuite() {
    if [ ! -e pip_speed_result.csv ]; then
        echo -n $'\xEF\xBB\xBF' > pip_speed_result.csv
        echo "华为CDN_HTTPS,华为源站_HTTPS,华为CDN_HTTP,华为源站_HTTP,阿里_HTTP,腾讯_HTTP,官方_HTTPS" >> pip_speed_result.csv
    fi
    cp -a ~/pip/pip.ini ~/pip/pip.ini.back 
    for ((i=0;i<4;i++))
    do
        exec_pip_cmd "cdn_https"
        echo -e "${time},\c" >> pip_speed_result.csv
        exec_pip_cmd "huawei_https"
        echo -e "${time},\c" >> pip_speed_result.csv
        exec_pip_cmd "cdn_http"
        echo -e "${time},\c" >> pip_speed_result.csv
        exec_pip_cmd "huawei_http"
        echo -e "${time},\c" >> pip_speed_result.csv
        exec_pip_cmd "ali_http"
        echo -e "${time},\c" >> pip_speed_result.csv
        exec_pip_cmd "tencent_http"
        echo -e "${time},\c" >> pip_speed_result.csv
        # exec_pip_cmd "office_https"
        # echo -e "${time},\c" >> pip_speed_result.csv
        echo "" >> pip_speed_result.csv
    done
    cp -a ~/pip/pip.ini.back ~/pip/pip.ini
}

cur_dir=$(dirname $0)
cd ${cur_dir}
exec_pip_testsuite
