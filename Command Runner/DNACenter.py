import requests
import json
from collections import defaultdict
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests.auth import HTTPBasicAuth
import time


requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class Device (object):
	def __init__( self, device_id, hostname, ip, location, os, serial ):
		self.__device_id = device_id
		self.__hostname = hostname
		self.__ip = ip
		self.__location = location
		if self.__location is None:
			self.__location = 'N/A'

		self.__os_version = os
		self.__serial = serial
		self.commands = {}


	def get_device_id(self):
		return self.__device_id

	def get_hostname(self):
		return self.__hostname

	def get_ip(self):
		return self.__ip

	def get_location(self):
		return self.__location

	def get_os_version(self):
		return self.__os_version

	def get_serial(self):
		return self.__serial

	def print_commands(self):
		for line in self.commands:
			print(line)



class DNACenter (object):

	def __init__(self, username, password, base_url, device_ip_addresses):
		#PUBLIC Properties
		self.username = username
		self.password = password
		self.base_url = base_url
		self.device_ip_addresses = device_ip_addresses
		#PRIVATE Properies
		self.__auth_token = self.__get_auth_token()
		self.__devices = {}
		self.__device_ids = []
		self.__get_devices()
		#DISABLE REQUESTS WARNINGS
		requests.packages.urllib3.disable_warnings()


	def __get_auth_token(self):
		r = requests.request("POST",'%s/dna/system/api/v1/auth/token'%self.base_url,auth=HTTPBasicAuth(self.username, self.password), verify=False)
		if r.status_code == 200:
			response = r.json()

			return response['Token']

		else:
			raise Exception(r.status_code)


	"""

	PRIVATE CLASS METHODS

	"""

	def __dna_headers(self):
		return {'Content-Type':'application/json', 'x-auth-token': self.__auth_token}



	def __get_command_runner_task(self, task_id):
		while True:
			r = requests.get("%s/dna/intent/api/v1/task/%s"%(self.base_url,task_id), headers=self.__dna_headers(), verify=False)
			response = r.json()


			if r.status_code == 200 or r.status_code == 202:
				progress = r.json()['response']['progress']


			else:
				break

			if "fileId" in progress:  # keep checking for task completion
				break

			

			
		file_id = json.loads(progress)
		file_id = file_id['fileId']
		print("FILE_ID:", file_id)



		return self.__get_cmd_output(file_id)


	def __get_cmd_output(self, file_id):
		while True:
			print("PAUSING PROGRAM FOR 10 SECONDS TO WAIT FOR COMMANDS TO PUSH OUT OF PIPELINE")
			time.sleep(10)
			r = requests.get("%s/dna/intent/api/v1/file/%s"%(self.base_url,file_id), headers=self.__dna_headers(), verify=False)
			try:
				if r.status_code == 200 or r.status_code == 202:
					response = r.json()
					print("RESPONSE LEN: ", len(response))
					print("DEVICES LEN: ", len(self.__devices))
					if len(response) < len(self.__devices):
						continue
					else:
						break
				else:
					print("EXITED WITH STATUS CODE: ", r.status_code)
					break
			except:
				continue
		if r.status_code == 200 or r.status_code == 202:
			response = r.json()
			
			return response
							

				


	def __run_show_command_on_devices(self, list_of_commands):
		"""
		Uses the Cisco DNA Center Command Runner API to run the following commands:
			*NOTE: Command Runner API allows up to 5 commands at once.*

			First Iteration:
				1. show post
				2. show inventory
				3. show power detail
				4. show platform hardware chassis power-supply detail all

			Second Iteration:
				1. show etherchannel summary
				2. show ip dhcp snooping statistics detail


		Retrives the following output from 'show post':
			1. device's (Catalyst Switch) device Uuid
			2. Component tests that were run
			3. Status (Pass/Fail) of the each individual test that was run.

		Retrieves the following output from 'show version | include Serial Number':
			1. The Component Serial Number

		

		Return Value:
			dictionary 

		"""
		chunks = [list_of_commands[x:x+5] for x in range(0, len(list_of_commands), 5)]
		i = 0
		for commands in chunks:

			payload = {
						 "name" : "command set " + str(i),
						 "commands" : commands,
						 "deviceUuids" : self.__device_ids}

			r = requests.request("POST",'%s/api/v1/network-device-poller/cli/read-request'%self.base_url, headers=self.__dna_headers(), data=json.dumps(payload), verify=False)
			response = r.json()


			if r.status_code == 200 or r.status_code == 202:
				i += 1
				yield self.__get_command_runner_task(response['response']['taskId'])

			else:

				
				yield "Error! HTTP %s Response: %s" % (r.status_code, response['response']['message'])




	def __get_devices(self):
		
		for ip_address in self.device_ip_addresses:
			print(ip_address)
			r = requests.request("GET",'%s/api/v1/network-device?managementIpAddress=%s'%(self.base_url,ip_address), headers=self.__dna_headers(), verify=False)
			if r.status_code == 200:
				for device in r.json()['response']:
					self.__device_ids.append(device['id'])
					self.__devices[device['id']] = Device(device['id'], device['hostname'], device['managementIpAddress'], device['location'], device['softwareVersion'], device['serialNumber'])


	"""
	
	PUBLIC CLASS METHODS

	"""


	def command_runner(self, commands):
		for data in self.__run_show_command_on_devices(commands):
			for output in data:
				devices = self.__devices
				device = devices[output['deviceUuid']]
				for key,value in output['commandResponses']['SUCCESS'].items():
					device.commands[key] = list()
					for line in output['commandResponses']['SUCCESS'][key].split("\n"):
						device.commands[key].append(line)
				





	

	def get_devices(self):
		return self.__devices


