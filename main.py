from functions import ip_scan_diapason, start_get_printer_info
from config import ip_network_diapason
import json
import time


t = time.time()

if __name__ == '__main__':
    ip_scan_diapason(ip_diapason=ip_network_diapason)
    start_get_printer_info(time=t)
    while True:
        if time.time() - t > 7000:
            print("Start scan", t)
            ip_scan_diapason(ip_diapason=ip_network_diapason)
            t = time.time()
            print("Scan", t)

        if time.time() - t > 1000:
            start_get_printer_info(t)
            t = time.time()