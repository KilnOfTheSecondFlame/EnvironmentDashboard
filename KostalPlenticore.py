import datetime
import random
import string
import base64
import json
import time
import requests
import hashlib
import os
import hmac
from threading import Thread
from Crypto.Cipher import AES


def random_string(string_length):
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for i in range(string_length))


def get_PBKDF2_hash(password, byted_salt, rounds):
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), byted_salt, rounds)


class KostalPlenticore:
    def __init__(self, ip, password):
        self.BASE_URL = "http://" + ip + "/api/v1"
        self.PASSWORD = password
        self.ME = ''
        self.headers = {}

    def login(self):
        user_type = "user"
        auth_start = "/auth/start"
        auth_finish = "/auth/finish"
        auth_create_session = "/auth/create_session"
        me = "/auth/me"

        u = random_string(12)
        u = base64.b64encode(u.encode('utf-8')).decode('utf-8')

        step1 = {
            "username": user_type,
            "nonce": u
        }
        step1 = json.dumps(step1)
        url = self.BASE_URL + auth_start
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        response = requests.post(url, data=step1, headers=headers)
        response = json.loads(response.text)

        i = response['nonce']
        e = response['transactionId']
        o = response['rounds']
        a = response['salt']
        bit_salt = base64.b64decode(a)

        r = get_PBKDF2_hash(self.PASSWORD, bit_salt, o)
        s = hmac.new(r, "Client Key".encode('utf-8'), hashlib.sha256).digest()
        c = hmac.new(r, "Server Key".encode('utf-8'), hashlib.sha256).digest()
        _ = hashlib.sha256(s).digest()
        d = "n=user,r=" + u + ",r=" + i + ",s=" + a + ",i=" + str(o) + ",c=biws,r=" + i
        g = hmac.new(_, d.encode('utf-8'), hashlib.sha256).digest()
        p = hmac.new(c, d.encode('utf-8'), hashlib.sha256).digest()
        f = bytes(a ^ b for (a, b) in zip(s, g))
        proof = base64.b64encode(f).decode('utf-8')

        step2 = {
            "transactionId": e,
            "proof": proof
        }
        step2 = json.dumps(step2)

        url = self.BASE_URL + auth_finish
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        response = requests.post(url, data=step2, headers=headers)
        response = json.loads(response.text)

        token = response['token']
        signature = response['signature']

        login_hash = hmac.new(_, "Session Key".encode('utf-8'), hashlib.sha256)
        login_hash.update(d.encode('utf-8'))
        login_hash.update(s)
        p = login_hash.digest()
        protocol_key = p
        t = os.urandom(16)

        e2 = AES.new(protocol_key, AES.MODE_GCM, t)
        e2, authtag = e2.encrypt_and_digest(token.encode('utf-8'))

        step3 = {
            "transactionId": e,
            "iv": base64.b64encode(t).decode('utf-8'),
            "tag": base64.b64encode(authtag).decode("utf-8"),
            "payload": base64.b64encode(e2).decode('utf-8')
        }
        step3 = json.dumps(step3)

        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        url = self.BASE_URL + auth_create_session
        response = requests.post(url, data=step3, headers=headers)
        response = json.loads(response.text)
        session_id = response['sessionId']

        # create a new header with the new Session-ID for all further requests
        self.headers = {'Content-type': 'application/json', 'Accept': 'application/json',
                        'authorization': "Session " + session_id}
        url = self.BASE_URL + me
        response = requests.get(url=url, headers=self.headers)
        response = json.loads(response.text)
        self.ME = response
        auth_ok = response['authenticated']
        if not auth_ok:
            return response
        else:
            return "Login successful"

    def logout(self):
        url = self.BASE_URL + "/auth/logout"
        response = requests.post(url=url, headers=self.headers)
        if response.status_code == 200:
            response = 'Logout successful'
        else:
            response = 'Logout Request Error'
        return response

    def get_info(self):
        url = self.BASE_URL + "/info/version"
        response = requests.get(url=url, headers=self.headers)
        response = json.loads(response.text)
        return response

        # Customized request

    def get_process_data(self, moduleid, prossdata):
        url = self.BASE_URL + "/processdata"
        data_request = {
            "moduleid": moduleid,
            "processdataids": prossdata
        }
        data_request = json.dumps(data_request)
        response = requests.post(url=url, data=data_request, headers=self.headers)
        response = json.loads(response.text)
        return response[0]['processdata']

    def get_battery_percent(self):
        url = self.BASE_URL + "/processdata"
        data_request = {
            "moduleid": "devices:local:battery",
            "processdataids": ['SoC']
        }
        data_request = json.dumps(data_request)
        response = requests.post(url=url, data=data_request, headers=self.headers)
        response = json.loads(response.text)
        return response[0]['processdata'][0]['value']

    def get_solar_power(self):
        url = self.BASE_URL + "/processdata"
        data_request = {
            "moduleid": "devices:local",
            "processdataids": ['Dc_P']
        }
        data_request = json.dumps(data_request)
        response = requests.post(url=url, data=data_request, headers=self.headers)
        response = json.loads(response.text)
        return response[0]['processdata'][0]['value']

    def get_home_power_consumption(self):
        url = self.BASE_URL + "/processdata"
        data_request = {
            "moduleid": "devices:local",
            "processdataids": ['HomeOwn_P']
        }
        data_request = json.dumps(data_request)
        response = requests.post(url=url, data=data_request, headers=self.headers)
        response = json.loads(response.text)
        return response[0]['processdata'][0]['value']

    def get_log_data(self, begin_date, end_date):
        url = self.BASE_URL + "/logdata/download"
        data_request = {
            "begin": str(begin_date),
            "end": str(end_date)
        }
        data_request = json.dumps(data_request)
        response = requests.post(url=url, data=data_request, headers=self.headers)
        return response.content.decode('utf-8')


class SolarPoller(Thread):
    def __init__(self, ip, password, poll_time=5, debug=False):
        Thread.__init__(self)
        # Poll time in minutes
        self.__poll_time = poll_time
        self.__debug = debug
        self.__stop = False
        self.__plenticore = KostalPlenticore(ip, password)

    def poll_solar(self):
        while not self.__stop:
            response = self.__plenticore.login()
            if self.__debug:
                print('{} {}'.format(str(datetime.datetime.now()), response))
            date_now = datetime.datetime.now()
            date_now = date_now.date()
            date_yesterday = date_now - datetime.timedelta(1)
            if self.__debug:
                print('{} Fetching data from Plenticore'.format(str(datetime.datetime.now())))
            tsv = self.__plenticore.get_log_data(date_yesterday, date_now)
            csv = tsv.replace('\t', ',')
            with open('temp.csv', 'w') as temp_csv:
                temp_csv.write(csv)
            response = self.__plenticore.logout()
            if self.__debug:
                print('{} {}'.format(str(datetime.datetime.now()), response))
            time.sleep(self.__poll_time * 60)

    def run(self):
        self.poll_solar()

    def stop(self):
        self.__stop = True

