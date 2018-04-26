#!/usr/bin/env bash

function http() {
    for i in 1 2 3 4 5; do
        curl -k -u 'test:devcloud' "$1" > /dev/null 2>&1
        if [[ "$?" == "0" ]]; then
            return 0
        fi
    done
    return 1
}

function download_package_content() {
    http "https://mirrors.huaweicloud.com/repository/nuget/Packages(Id='$1',Version='$2')"
    http "https://mirrors.huaweicloud.com/repository/nuget/$1/$2"
}

function download_package_from_file() {
    filename="$1"
    index_filename="index_${filename}"
    cd $(dirname "$0" )
    if [ -f "${index_filename}" ]; then
        index=$(cat "${index_filename}")
    else
        index=1
    fi

    echo "====>start sync from ${filename} at ${index} line....." >> sync.log
    total_line=$(cat ${filename} | wc -l)
    while (( $index <= $total_line )); do
        pkg_info=$(awk "NR==$index {print \$0}" ${filename})
        download_package_content ${pkg_info}
        let index=index+1
        echo ${index} > ${index_filename}
    done
    echo "<====${filename} is synced ok, file line: ${total_line}, sync line: ${index}" >> sync.log
}

for file in $(ls nuget_list*); do
    download_package_from_file ${file} &
done
