import datetime
import os

from sdk.python3.module.module import Module
from sdk.python3.module.helpers.cache import Cache
from sdk.python3.module.helpers.scheduler import Scheduler
from sdk.python3.module.helpers.message import Message

import sdk.python3.utils.numbers
import sdk.python3.utils.exceptions as exception

# service common functionalities
class Service(Module):
    # What to do when initializing
    def __init__(self, scope, name):
        # call superclass function
        super(Service, self).__init__(scope, name)
        # initialize internal cache
        self.cache = Cache()
        # scheduler is needed for polling sensors
        if self.scheduler is None:
            self.scheduler = Scheduler(self)
        # map sensor_id with scheduler job_id
        self.__jobs = {}
        # map sensor_id with service's configuration
        self.sensors = {}
        # for pull services, if polling at startup
        self.poll_at_startup = bool(int(os.getenv("EGEOFFREY_POLL_SENSORS_AT_STARTUP", True)))
        
    # function to run when scheduling a job
    def __poll_sensor(self, sensor_id, configuration):
        # simulate a message from the hub to trigger the sensor
        message = Message(self)
        message.sender = "controller/hub"
        message.recipient = self.fullname
        message.command = "IN"
        message.args = sensor_id
        message.set_data(configuration)
        self.on_message(message)

    # unschedule a job
    def __remove_schedule(self, sensor_id):
        # if already scheduled, stop it
        if sensor_id in self.__jobs:
            try:
                for job in self.scheduler.get_jobs():
                    if job.id == self.__jobs[sensor_id]:
                        self.scheduler.remove_job(self.__jobs[sensor_id])
            except Exception as e:
                self.log_error("Unable to remove scheduled job for sensor "+sensor_id+": "+exception.get(e))
            del self.__jobs[sensor_id]
        
    # schedule a job for polling a sensor
    def __add_schedule(self, sensor_id, schedule, configuration):
        # clean it up first
        self.__remove_schedule(sensor_id)
        # "schedule" contains apscheduler settings for this sensor
        job = schedule
        # add extra-delay picked randomly in a [-15,+15] seconds window
        job["jitter"] = 15
        # add function to call and args
        job["func"] = self.__poll_sensor
        job["args"] = [sensor_id, configuration]
        # schedule the job for execution
        try:
            self.__jobs[sensor_id] = self.scheduler.add_job(job).id
        except Exception as e:
            self.log_error("Unable to scheduled job for sensor "+sensor_id+": "+exception.get(e))
        # if schedule trigger is interval, run also the job immediately
        if schedule["trigger"] == "interval" and self.poll_at_startup:
            poll_now_job = {}
            poll_now_job["trigger"] = "date"
            poll_now_job["run_date"] = datetime.datetime.now() + datetime.timedelta(seconds=sdk.python3.utils.numbers.randint(5,20))
            poll_now_job["func"] = self.__poll_sensor
            poll_now_job["args"] = [sensor_id, configuration]
            self.scheduler.add_job(poll_now_job)
            
    # What to do just after starting (subclass may implement)
    def on_post_start(self):
        # request all sensors' configuration so to filter sensors of interest
        self.add_configuration_listener("sensors/#", 1)

    # register an pull/push sensor
    def register_sensor(self, message, validate=[]):
        sensor_id = message.args.replace("sensors/","")
        sensor = message.get_data()
        # no service associated to this sensor, do nothing
        if "service" not in sensor:
            # check if the sensor was previously registered with us, if so unregister it
            self.unregister_sensor(message)
            return
        # the sensor is associated to a different service, ignore it
        if sensor["service"]["name"] != self.name:
            # check if the sensor was previously registered with us, if so unregister it
            self.unregister_sensor(message)
            return
        # the sensor is disabled, ignore it
        if "disabled" in sensor and sensor["disabled"]: 
            # check if the sensor was previously enabled, if so unregister it
            self.unregister_sensor(message)
            return
        # get and check the service configuration
        service = message.get("service")
        if not self.is_valid_configuration(["configuration"], service): 
            return
        # in pull mode we need to schedule sensor's polling
        if service["mode"] == "pull":
            # ensure a schedule configuration is set
            if not self.is_valid_configuration(["schedule"], service): 
                return
            # schedule for polling the sensor
            self.log_debug("registered pull sensor "+sensor_id+" polling at "+str(service["schedule"])+" with configuration "+str(service["configuration"]))
            self.__add_schedule(sensor_id, service["schedule"], service["configuration"])
        # in push mode the sensor will generate new measures without us to do anything
        elif service["mode"] == "push":
            # ensure the configuration is valid
            if not self.is_valid_configuration(validate, service["configuration"]): 
                return
            self.log_debug("registered push sensor "+sensor_id+" with configuration "+str(service["configuration"]))
        # invalid mode
        else:
            return
        # keep track of the sensor's configuration
        self.sensors[sensor_id] = service["configuration"]
        return sensor_id

    # unregister a sensor
    def unregister_sensor(self, message):
        sensor_id = message.args.replace("sensors/","")
        # a sensor has been deleted
        if sensor_id in self.sensors:
            # remove scheduler if pull sensor
            if sensor_id in self.__jobs:
                self.__remove_schedule(sensor_id)
            del self.sensors[sensor_id]
            self.log_debug("unregistered sensor "+sensor_id)
        return sensor_id