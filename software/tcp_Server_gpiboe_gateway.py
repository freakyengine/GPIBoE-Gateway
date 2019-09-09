#!/usr/bin/python3

# last modified 2019/09

## DOC -------------------------------------------------------------------------
# A simple TCP server for bringing the GPIB I/O functionality to the network.
# Works with a simple, text based protocol with '\n' as message terminator:
# Send format:   <W/R/T>|<gpibAddress>|<dataToWrite>\n
# Return format: <status>|<optional_data>\n


import socket
import asyncio
import GPIB

async def handle_tcpip_connection(reader, writer):
	client_ipaddress = writer.get_extra_info('peername') # for debugging purpose
	print(f"Client connected from {client_ipaddress!r}") # for debugging purpose
	
	while(True):
		rx_data = await reader.readline()
		if(rx_data == b''):
			break
		
		try:
			rx_message = rx_data.decode()
			if not (rx_message[-1] == '\n'):
				tx_message = '-3|incomplete command received. receive buffer overflow?'
			else:
				# -- GPIB code starts here
				print(f"Received {rx_message!r}") # for debugging purpose
				
				gpib_cmd = rx_message.split('|')
				
				gpib = GPIB.GPIB() # create GPIB IF
				gpib.Init()
				gpib.Remote(1)
				
				if(gpib_cmd[0] == 'R'):
					status = gpib.Read(int(gpib_cmd[1]))
					tx_message = str(status[0]) + '|' + status[1]
					
				elif(gpib_cmd[0] == 'W'):
					status = gpib.Write(int(gpib_cmd[1]),gpib_cmd[2])
					if status[0] == 0:
						tx_message = str(status[0])
					else:
						tx_message = str(status[0]) + '|' + status[1]
						
				elif(gpib_cmd[0] == 'T'):
					status = gpib.Trigger(gpib_cmd[1])
					if status[0] == 0:
						tx_message = str(status[0])
					else:
						tx_message = str(status[0]) + '|' + status[1]
						
				else:
					tx_message = '-3|unsupported command received'
				
				gpib.Remote(0)
				del gpib	# delete GPIB IF
				
		except Exception as err:
			tx_message = '-1|general error: ' + str(err.args[0])
		finally:
			if not tx_message[-1] == '\n':
				tx_message += '\n'
			
			tx_data = tx_message.encode()
			writer.write(tx_data)
			await writer.drain()

	print('Connection closed') # for debugging purpose
	writer.close()

async def main():
	# create tcp server
	gpib_gateway_server = await asyncio.start_server(
			handle_tcpip_connection, # callback function
			host='0.0.0.0',	# IP to bind listener to
			port=5025, # port to bind listener to
			family=socket.AF_INET, # IPv4 socket only
			backlog=1 # number of concurrent connections
			)

	addr = gpib_gateway_server.sockets[0].getsockname()
	print(f'Serving on {addr}')

	async with gpib_gateway_server:
			await gpib_gateway_server.serve_forever()


asyncio.run(main())

