#!/bin/bash

netstat -lntp | grep 5984
if [[ $? != "0" ]]; then
    echo "start couchdb ... "
    service couchdb start
    sleep 10
fi

ps -ef | grep metadata_sync_tools.py | grep -v grep
if [[ $? != "0" ]]; then
    cd /home/ruandy/workspace/couchdb/RepositoryMetadata/src/nuget
    echo "start nuget nuget_metadata_sync_tools.py ...." | tee output.txt
    python nuget_metadata_sync_tools.py >> output.txt
fi
