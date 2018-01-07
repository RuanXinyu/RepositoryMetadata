#!/bin/sh

netstat -lntp | grep 5984
if [[ $? != "0" ]]; then
    echo "start couchdb ... "
    service couchdb start
    sleep 10
fi

ps -ef | grep metadata_sync_tools.py | grep -v grep
if [[ $? != "0" ]]; then
    cd /root/mirrors/github/RepositoryMetadata/src/nuget
    echo "start nuget metadata_sync_tools.py ...." | tee output.txt
    nohup python metadata_sync_tools.py >> output.txt &
fi
