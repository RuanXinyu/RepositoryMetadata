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

function change_nuget_conf() {
    if [[ "${1}" == "cdn_https" ]]; then
        url="https://repo.huaweicloud.com/repository/nuget/"
        version="2"
    elif [[ "${1}" == "huawei_https" ]]; then
        url="https://mirrors.huaweicloud.com/repository/nuget/"
        version="2"
    elif [[ "${1}" == "office_v2_https" ]]; then
        url="https://www.nuget.org/api/v2/"
        version="2"
    elif [[ "${1}" == "office_v3_https" ]]; then
        url="https://api.nuget.org/v3/index.json"
        version="3"
    elif [[ "${1}" == "cnblogs_v3_https" ]]; then
        url="https://nuget.cnblogs.com/v3/index.json"
        version="3"
    else
        echo "please specified correct repository name, <cdn_https|huawei_https|office_v2_https|office_v3_https|cnblogs_v3_https>"
        exit 1
    fi
    
    sed -i "s@value=\".*\" protocolVersion=\".\"@value=\"${url}\" protocolVersion=\"${version}\"@g" NuGet.Config
    cat NuGet.Config
}

function exec_nuget_cmd() {
    echo "\n=============>start execute 'nuget install -OutputDirectory packages -NoCache -DirectDownload -Verbosity detailed -ConfigFile NuGet.Config BootstrapMvc.Mvc6' "
    echo "===============> rm -rf packages"
    rm -rf packages
    change_nuget_conf ${1}
    time="-"
    start=$(date +%s.%N)
    nuget install -OutputDirectory packages -NoCache -DirectDownload -Verbosity detailed -ConfigFile NuGet.Config BootstrapMvc.Mvc6
    nuget install -OutputDirectory packages -NoCache -DirectDownload -Verbosity detailed -ConfigFile NuGet.Config packages.config
    end=$(date +%s.%N)
    getTiming $start $end
    echo "=============>end execute 'nuget install -OutputDirectory packages -NoCache -DirectDownload -Verbosity detailed -ConfigFile NuGet.Config BootstrapMvc.Mvc6' "
    echo "=============>total time(ms): ${time}"
}

function exec_nuget_testsuite() {
    if [ ! -e nuget_speed_result.csv ]; then
        echo -n $'\xEF\xBB\xBF' > nuget_speed_result.csv
        echo "华为CDN_HTTPS,华为源站_HTTPS,官方V2_HTTPS,官方V3_HTTPS,博客园V3_HTTPS" >> nuget_speed_result.csv
    fi
    for ((i=0;i<4;i++))
    do
        exec_nuget_cmd "cdn_https"
        echo -e "${time},\c" >> nuget_speed_result.csv
        exec_nuget_cmd "huawei_https"
        echo -e "${time},\c" >> nuget_speed_result.csv
        exec_nuget_cmd "office_v2_https"
        echo -e "${time},\c" >> nuget_speed_result.csv
        exec_nuget_cmd "office_v3_https"
        echo -e "${time},\c" >> nuget_speed_result.csv
        exec_nuget_cmd "cnblogs_v3_https"
        echo -e "${time},\c" >> nuget_speed_result.csv
        echo "" >> nuget_speed_result.csv
    done
}

cur_dir=$(dirname $0)
cd ${cur_dir}
exec_nuget_testsuite
