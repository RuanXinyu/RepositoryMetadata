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

function change_npmrc() {
    if [[ "${1}" == "cdn_https" ]]; then
        url="https://repo.huaweicloud.com/repository/npm/"
    elif [[ "${1}" == "huawei_https" ]]; then
        url="https://mirrors.huaweicloud.com/repository/npm/"
    elif [[ "${1}" == "office_https" ]]; then
        url="https://registry.npmjs.org/"
    elif [[ "${1}" == "ali_https" ]]; then
        url="https://registry.npm.taobao.org/"
    else
        echo "please specified correct repository name, <cdn_https|huawei_https|office_https|ali_https|>"
        exit 1
    fi
    echo "registry = ${url}" > .npmrc
    cat .npmrc
    cp -a .npmrc ~/.npmrc 
}

function exec_npm_cmd() {
    echo "\n=============>start execute 'npm install @angular/cli' "
    echo "===============> rm -rf node_modules"
    rm -rf node_modules package-lock.json
    mkdir node_modules
    cp -a node-sass node_modules/node-sass
    npm cache clean -f
    change_npmrc ${1}
    npm cache clean -f
    time="-"
    start=$(date +%s.%N)
    npm install @angular/cli
    end=$(date +%s.%N)
    getTiming $start $end
    echo "=============>end execute 'npm install @angular/cli' "
    echo "=============>total time(ms): ${time}"
}

function exec_npm_testsuite() {
    if [ ! -e npm_speed_result.csv ]; then
        echo -n $'\xEF\xBB\xBF' > npm_speed_result.csv
        echo "华为CDN_HTTPS,华为源站_HTTPS,阿里_HTTPS,官方_HTTPS" >> npm_speed_result.csv
    fi
    cp -a ~/.npmrc ~/.npmrc.back 
    # for ((i=0;i<4;i++))
    # do
        # exec_npm_cmd "cdn_https"
        # echo -e "${time},\c" >> npm_speed_result.csv
        # exec_npm_cmd "huawei_https"
        # echo -e "${time},\c" >> npm_speed_result.csv
        # exec_npm_cmd "ali_https"
        # echo -e "${time},\c" >> npm_speed_result.csv
        exec_npm_cmd "office_https"
        echo -e "${time},\c" >> npm_speed_result.csv
        echo "" >> npm_speed_result.csv
    # done
    cp -a ~/.npmrc.back ~/.npmrc
}

cur_dir=$(dirname $0)
cd ${cur_dir}
exec_npm_testsuite
