# -*- coding: utf-8 -*-
import codecs
import couchdb
import re

if __name__ == "__main__":
    server = couchdb.Server('http://admin:admin@127.0.0.1:5984/')
    db = server['nuget']

    with codecs.open("nuget_list", "w+", "utf-8") as f:
        text = ''
        count = 0
        for doc_id in db:
            count += 1
            if "id" in db[doc_id]:
                url = db[doc_id]["id"]
                m = re.search("Id='([^']*)',Version='([^']*)'", url)
                text += unicode(m.group(1)) + u" " + unicode(m.group(2)) + u"\n"
            if count % 1000 == 0:
                print(count)
                f.write(text)
                text = ''
