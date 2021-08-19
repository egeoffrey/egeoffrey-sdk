#!/usr/bin/python3
import time
from sdk.python3.module.watchdog import Watchdog

# run the watchdog module which will load and start all the modules listed in EGEOFFREY_MODULES
watchdog = Watchdog("system", "watchdog")
watchdog.daemon = True
watchdog.start()

# keep running forever
while True:
    time.sleep(1)
