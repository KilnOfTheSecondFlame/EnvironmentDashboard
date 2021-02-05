from threading import Thread
import bme680
import time
import datetime
import os
import configparser


class EnvironmentSensor(Thread):
    def __init__(self, poll_time=5, debug=False):
        Thread.__init__(self)
        config = configparser.ConfigParser()
        config.read('config.conf')
        humidity_offset = config['PiEnvironmentSensor']['humidity_offset']

        # Poll time in minutes
        self.__poll_time = poll_time
        self.__debug = debug
        self.__stop = False

        # Prepare sensor
        self.__sensor = bme680.BME680()
        self.__sensor.set_humidity_oversample(bme680.OS_2X)
        self.__sensor.set_pressure_oversample(bme680.OS_4X)
        self.__sensor.set_temperature_oversample(bme680.OS_8X)
        self.__sensor.set_filter(bme680.FILTER_SIZE_3)

        self.__sensor.set_gas_status(bme680.DISABLE_GAS_MEAS)

        # Humidity offset due to other sensor
        self.HUMIDITY_OFFSET = humidity_offset

        if not os.path.isfile('environment.log'):
            with open('environment.log', 'w') as environment_log:
                environment_log.write('Time,Temperature,Pressure,Humidity\n')

    def poll_sensor(self):
        while not self.__stop:
            if self.__sensor.get_sensor_data():
                with open('environment.log', 'a') as environment_log:
                    environment_log.write(str(datetime.datetime.now()) +
                                          ',' + str(self.__sensor.data.temperature) +
                                          ',' + str(self.__sensor.data.pressure) +
                                          ',' + str(self.__sensor.data.humidity + self.HUMIDITY_OFFSET) +
                                          '\n')
            if self.__debug:
                print('{} Sensor polled'.format(datetime.datetime.now()))
            time.sleep(self.__poll_time * 60)

    def run(self):
        self.poll_sensor()

    def stop(self):
        self.__stop = True
