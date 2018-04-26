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

function change_gemrc() {
    if [[ "${1}" == "cdn_https" ]]; then
        url="https://repo.huaweicloud.com/repository/rubygems/"
    elif [[ "${1}" == "huawei_https" ]]; then
        url="http://mirrors.huaweicloud.com/repository/rubygems/"
    elif [[ "${1}" == "tencent_http" ]]; then
        url="http://mirrors.cloud.tencent.com/rubygems/"
    elif [[ "${1}" == "tuna_https" ]]; then
        url="https://mirrors.tuna.tsinghua.edu.cn/rubygems/"
    elif [[ "${1}" == "office_https" ]]; then
        url="https://rubygems.org/"
    elif [[ "${1}" == "rubychina_https" ]]; then
        url="https://gems.ruby-china.org/"
    else
        echo "please specified correct repository name, <cdn_https|huawei_https|tencent_http|office_https|rubychina_https>"
        exit 1
    fi
    
    sed -i "5c - ${url}" .gemrc
    sed -i "13c source '${url}'" Gemfile
    cat .gemrc
    cp -a .gemrc ~/.gemrc 
}

function exec_gem_cmd() {
    echo "\n=============>start execute 'bundle install --no-local --no-cache --force --verbose --path=./gems' "
    echo "===============> rm -rf .bundle gems Gemfile.lock"
    rm -rf .bundle gems Gemfile.lock
    gem sources -c
    gem cleanup
    gemdir=$(gem environment gemdir)
    rm -rf ${gemdir}
    change_gemrc ${1}
    gem sources -u
    time="-"
    start=$(date +%s.%N)
    # bundle install --no-local --no-cache --force --verbose --path=./gems
    gem install -f -i gems jquery-rails sass-rails rspec-core fog-aws fog-core fog-google fog-local fog-openstack fog-rackspace fog-aliyun google-api-client unf seed-fu html-pipeline deckar01-task_list gitlab-markup rdoc org-ruby creole asciidoctor asciidoctor-plantuml rouge truncato bootstrap_form nokogiri diffy 
    end=$(date +%s.%N)
    getTiming $start $end
    echo "=============>end execute 'bundle install --no-local --no-cache --force --verbose --path=./gems' "
    echo "=============>total time(ms): ${time}"
}

function exec_gem_testsuite() {
    if [ ! -e gem_speed_result.csv ]; then
        echo -n $'\xEF\xBB\xBF' > gem_speed_result.csv
        # echo "华为CDN_HTTPS,华为源站_HTTPS,腾讯_HTTP,Ruby中国_HTTP,官方_HTTPS" >> gem_speed_result.csv
        echo "华为CDN_HTTPS,华为源站_HTTPS,Ruby中国_HTTPS" >> gem_speed_result.csv
    fi
    # cp -a ~/.gemrc ~/.gemrc.back 
    for ((i=0;i<6;i++))
    do
        exec_gem_cmd "cdn_https"
        echo -e "${time},\c" >> gem_speed_result.csv
        exec_gem_cmd "huawei_https"
        echo -e "${time},\c" >> gem_speed_result.csv
        exec_gem_cmd "rubychina_https"
        echo -e "${time},\c" >> gem_speed_result.csv
        # exec_gem_cmd "tencent_http"
        # echo -e "${time},\c" >> gem_speed_result.csv
        # exec_gem_cmd "office_https"
        # echo -e "${time},\c" >> gem_speed_result.csv
        echo "" >> gem_speed_result.csv
    done
    # cp -a ~/.gemrc.back ~/.gemrc
}

cur_dir=$(dirname $0)
cd ${cur_dir}
exec_gem_testsuite
# exec_gem_cmd "tuna_https"
