import DNACenter


if __name__ == "__main__":
	username = input("Enter username: ")
	password = getpass.getpass("Enter password: ")
	url = input("Enter DNAC URL: ")

	session = DNACenter.DNACenter(username = username , password = password , base_url= url ,device_ip_addresses=[])
	

	session.command_runner(['show client summary'])
		
		
	#Iterate through all devices and print the show run command that was issued (prints line by line)
	for device_id, device in session.get_devices().items():

		for line in device.commands['show client summary']:
			print(line)
		


	

			
			

		
