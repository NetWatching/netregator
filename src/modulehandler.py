import threading
import json
from src.io import API, Config
from src.modules.module import Module
from src.device import Device
from src.utilities import Utilities
import time
import os
from decouple import config


class ModuleHander():
    def __init__(self):
        self._imported_modules = []
        self._workers = {}
        self._system_threads = {}
        self._known_system_threads = ["sendData", "checkDevices"]
        self._running = True
        self._api = API()
        self._utilities = Utilities()
        self._modules = Config("./src/config/modules.json")
        self.mainloop()

    def mainloop(self):
        try:
            self.start_system_thread()
            time.sleep(1)
            self.set_version()
            self.set_modules()
            while self._running:
                self.check_system_threads()
                time.sleep(5)
        except KeyboardInterrupt:
            os._exit(1)
        #self.stop_system_thread()

    def get_data_from_devices(self):
        while True:
            output = {}
            devices = []
            for deviceid in self._workers:
                c_data = self._workers[deviceid].data
                if c_data:
                    current_metadata = {"id": deviceid,
                                    "name": self._workers[deviceid].name}
                    current_metadata.update(c_data)
                    devices.append(current_metadata)
                self._workers[deviceid].clear_data()
            if devices != []:
                output["devices"] = devices
                print(json.dumps(output))
                # TODO: send data
                self._api.send_data(output)
                #print("--------------")
                #print("--------------")
                #print("--------------")
                #print("--------------")
                #print(output)
            time.sleep(5)

    def check_devices(self):
        while True:
            running_devices = self.get_running_devices()
            devices_to_start = self._utilities.compare_dict(running_devices, self._workers)
            devices_to_stop = self._utilities.compare_dict(self._workers, running_devices)
    
            # starts new Devices
            for c_id in devices_to_start:
                device_type = running_devices[c_id]["type"]
                ip = running_devices[c_id]["ip"]
                name = running_devices[c_id]["name"]
                timeout = running_devices[c_id]["timeout"]
                modules = running_devices[c_id]["modules"]
                self.start_device(Device(id=c_id, name=name, device_type=device_type, ip=ip, timeout=timeout, modules=modules))
                #print(running_devices[c_id])
    
            # stop devices
            for c_id in devices_to_stop:
                self.stop_device(self._workers[c_id].id, self._workers[c_id].name)
    
            # update timeout, modules and check for dead devices/threads and restart them
            for c_id in running_devices:
                #check if device is still running. if not, restart it.
                if not self._workers[c_id].is_alive() or not self._workers[c_id].running:
                    c_id = self._workers[c_id].id
                    name = self._workers[c_id].name
                    device_type = self._workers[c_id].device_type
                    ip = self._workers[c_id].ip
                    timeout = self._workers[c_id].timeout
                    modules = self._workers[c_id].modules
                    self.start_device(Device(id=c_id, name=name, device_type=device_type, ip=ip, timeout=timeout, modules=modules))
                # update timeout
                self._workers[c_id].timeout = running_devices[c_id]["timeout"]
                self._workers[c_id].modules = running_devices[c_id]["modules"]
            time.sleep(5)

    def start_device(self, device: Device):
        #code = f"global cmodule;cmodule = {device.type}(deviceid={device.id},devicetype='{device.type}',devicename='{device.name}',deviceip='{device.ip}', devicetimeout={device.timeout}, devicemodules={device.modules})"
        code = f"global c_device;c_device = Device(id={device.id}, name='{device.name}', ip='{device.ip}', device_type='{device.device_type}', timeout={device.timeout}, modules={device.modules})"
        exec(code, globals())
        self._workers[device.id] = c_device
        #self._workers[device.id].setDaemon(True)
        self._workers[device.id].start()
        print(f"Started device {device.name}")
        return True

    def start_system_thread(self, key=None):
        if key == "sendData" or key is None:
            self._system_threads["sendData"] = threading.Thread(target=self.get_data_from_devices, name="sendData", args=())
            self._system_threads["sendData"].start()
        if key == "checkDevices" or key is None:
            self._system_threads["checkDevices"] = threading.Thread(target=self.check_devices, name="checkDevices", args=())
            self._system_threads["checkDevices"].start()

    def stop_system_thread(self, key=None):
        if key is None:
            for c_key in self._known_system_threads:
                self._system_threads[c_key].terminate()

    def check_system_threads(self):
        for c_key in self._known_system_threads:
            if not self._system_threads[c_key].is_alive():
                self.start_system_thread(c_key)
        for c_key in self._utilities.compare_list(self._known_system_threads, self._system_threads):
            self.start_system_thread(c_key)

    def stop_device(self, device_id, device_name):
        self._workers[str(device_id)].running = False
        del self._workers[str(device_id)]
        print(f"Stopped device {device_name}")
        return True

    def get_running_devices(self):
        running_devices = self._api.get_running_threads()
        output = {}
        for c_device in running_devices:
            device_id = c_device["id"]
            del c_device["id"]
            output[device_id] = c_device
        #print(output)
        return output

    def set_version(self):
        self._api.send_version_string(config("VERSION"))

    def set_modules(self, validate_settings=True):
        output = []
        for modulename in self._modules.get_whole_file():
            output.append({
                "id": modulename,
                "config": {}
            })
        self._api.send_known_modules(output)