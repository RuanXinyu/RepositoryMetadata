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

function change_composer_conf() {
    if [[ "${1}" == "cdn_https" ]]; then
        url="https://repo.huaweicloud.com/repository/php/"
    elif [[ "${1}" == "huawei_https" ]]; then
        url="https://mirrors.huaweicloud.com/repository/php/"
    elif [[ "${1}" == "office_https" ]]; then
        url="https://packagist.org/"
    elif [[ "${1}" == "composer_china_https" ]]; then
        url="https://packagist.phpcomposer.com/"
    else
        echo "please specified correct repository name, <cdn_https|huawei_https|office_https|composer_china_https>"
        exit 1
    fi
    
    sed -i "s@\"url\": \".*\"@\"url\": \"${url}\"@g" composer.json
    cat composer.json
}

function exec_composer_cmd() {
    echo "\n=============>start execute 'composer install -vvv' "
    echo "===============> rm -rf vendor composer.lock"
    rm -rf vendor composer.lock
    composer clear-cache -vvv
    change_composer_conf ${1}
    time="-"    
    start=$(date +%s.%N)
    composer install -vvv
    end=$(date +%s.%N)
    getTiming $start $end
    echo "=============>end execute 'composer install -vvv' "
    echo "=============>total time(ms): ${time}"
}

function exec_composer_testsuite() {
    if [ ! -e composer_speed_result.csv ]; then
        echo -n $'\xEF\xBB\xBF' > composer_speed_result.csv
        echo "华为CDN_HTTPS,华为源站_HTTPS,Composer中国_HTTPS,官方_HTTPS" >> composer_speed_result.csv
    fi
    for ((i=0;i<4;i++))
    do
        exec_composer_cmd "cdn_https"
        echo -e "${time},\c" >> composer_speed_result.csv
        exec_composer_cmd "huawei_https"
        echo -e "${time},\c" >> composer_speed_result.csv
        exec_composer_cmd "composer_china_https"
        echo -e "${time},\c" >> composer_speed_result.csv
        # exec_composer_cmd "office_https"
        # echo -e "${time},\c" >> composer_speed_result.csv
        echo "" >> composer_speed_result.csv
    done
}

cur_dir=$(dirname $0)
cd ${cur_dir}
exec_composer_cmd "cdn_https"
exec_composer_cmd "cdn_https"
exec_composer_cmd "cdn_https"
exec_composer_testsuite
