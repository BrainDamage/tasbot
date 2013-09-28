#!/usr/bin/env python
import socket
import os
import sys
import time

from utilities import hash_password


def receive(sock):
	buf = ""
	try:
		while not buf.strip("\r ").endswith("\n"):
			nbuf = sock.recv(512)
			if nbuf == "":
				return ([], [])
			buf += nbuf
	except Exception, e:
		print(e)
		return ([], [])
	commands = buf.strip("\r ").split("\n")
	return ([cmd.split(" ")[0].upper() for cmd in commands ], [cmd.split(" ")[1:] for cmd in commands])


def register(username,password):
	host = 'lobby.springrts.com'
	port = 8200
	phash = hash_password(password)
	reg = 'REGISTER %s %s\n'%(username, phash)
	sock = socket.socket()
	sock.connect((host, port))
	sock.send(reg)
	resp = receive(sock)
	login='LOGIN %s %s 0 * sock v 1       12345\n'%(username,phash)
	sock.send(login)
	while 'AGREEMENTEND' not in resp[0]:
		resp = receive(sock)
	sock.send('CONFIRMAGREEMENT\n')
	sock.send(login)
	sock.send('EXIT\n')
	sock.close()


if __name__ == '__main__':
	try:
		username = sys.argv[1]
		password = sys.argv[2]
	except Exception:
		print 'Usage sysock.argv[0] username password'
		sys.exit(-1)
	register(username,password)
