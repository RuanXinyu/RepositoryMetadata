# -*- coding: utf-8 -*-

import threading
import time

def aaa():
    return 1


class SerialThread(threading.Thread):
    def __init__(self):
        self.data = {}
        super(SerialThread, self).__init__()

    def get_data(self):
        return self.data


class SerialThreadPool(threading.Thread):
    def __init__(self, data, data_generator, thread_generator, data_handler, pool_count=10):
        self.data = data
        self.index = 0
        self.is_stop = False
        self.data_generator = data_generator
        self.thread_generator = thread_generator
        self.data_handler = data_handler
        self.pool_count = pool_count
        super(SerialThreadPool, self).__init__()

    @staticmethod
    def arr_generater(arr, index):
        if index >= len(arr):
            return None
        return arr[index]

    def next_thread(self):
        item = self.data_generator(self.data, self.index)
        if item is None:
            self.is_stop = True
        t = self.thread_generator(item, self.index)
        t.setDaemon(True)
        t.start()
        self.index += 1
        return t

    def run(self):
        while not self.is_stop:
            pool = []
            for i in range(self.pool_count):
                if len(pool) <= i:
                    pool.append(self.next_thread())

                if not pool[i].isAlive():
                    self.data_handler(pool[i].get_data())
                    tmp = pool[i]
                    pool[i] = self.next_thread()
                    del tmp
            time.sleep(1)

    def stop(self):
        self.is_stop = True
