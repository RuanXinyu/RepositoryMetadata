#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

conf = {
    "base_path": "D:\\mirrors\\repository\\npm_private"
}


class NpmRepoHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        filename = conf["base_path"] + self.path
        if os.path.exists(filename):
            self.send_response(200)
            self.end_headers()
            with open(filename, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()

    def do_PUT(self):
        filename = conf["base_path"] + self.path
        folder_name = os.path.dirname(filename)
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        self.send_response(200)
        self.end_headers()
        with open(filename, "wb+") as f:
            data = self.rfile.read(int(self.headers['content-length']))
            f.write(data)


if __name__ == "__main__":
    http_server = HTTPServer(('', int(8082)), NpmRepoHandler)
    http_server.serve_forever()
