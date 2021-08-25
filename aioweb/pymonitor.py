# -*- coding: UTF-8 -*-
"""
Automatic restart web app when project code changes.
"""
import os
import subprocess
import sys
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


def monitor_log(s):
    print('[Monitor] %s' % s)


class MyFileSystemEventHandler(FileSystemEventHandler):
    def __init__(self, func):
        super(MyFileSystemEventHandler, self).__init__()
        self.restart = func

    def on_any_event(self, event):
        if event.src_path.endswith('.py'):
            monitor_log('Python src file changed: %s' % event.src_path)
            self.restart()


command = ['echo', 'ok']
process = None


def kill_process():
    global process
    if process is not None:
        monitor_log('Kill process [%s]...' % process.pid)
        process.kill()
        process.wait()
        monitor_log('Process ended with code %s.' % process.returncode)
        process = None


def start_process():
    global process, command
    monitor_log('Start process %s...' % ' '.join(command))
    process = subprocess.Popen(command, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)


def restart_process():
    kill_process()
    start_process()


def start_watch(dir_path, callback):
    observer = Observer()
    observer.schedule(MyFileSystemEventHandler(restart_process), dir_path, recursive=True)
    observer.start()
    monitor_log('Watching directory %s...' % dir_path)
    start_process()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
