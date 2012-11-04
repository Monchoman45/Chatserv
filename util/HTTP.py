#!/usr/local/bin/python3
import http.client, http.cookiejar, urllib.request, urllib.parse, urllib.error

def _request(method, url, body = '', headers = None):
	if headers == None: headers = {}
	if url.startswith('http://'): url = url[7:]
	slash = url.find('/')
	if slash != -1:
		host = url[:slash]
		path = url[slash:]
	else:
		host = url
		path = '/'
	sock = http.client.HTTPConnection(host)
	sock.request(method, path, body, headers)
	return sock.getresponse()

def get(url, params = {}, headers = {'Content-Type': 'application/x-www-form-urlencoded'}):
	if 'Content-Type' not in headers: headers['Content-Type'] = 'application/x-www-form-urlencoded'
	if params:
		if '?' not in url: url += '?'
		else: url += '&'
		for i in params:
			if not isinstance(params[i], str) and hasattr(params[i], '__iter__'):
				for param in params[i]:
					url += urllib.parse.quote(i)
					if '[]' in i: url += '%5B%5D'
					url += '=' + urllib.parse.quote(param) + '&'
			else: url += urllib.parse.quote(i) + '=' + urllib.parse.quote(str(params[i])) + '&'
		url = url[:-1]
	return _request('GET', url, '', headers)

def head(url, params = {}, headers = {'Content-Type': 'application/x-www-form-urlencoded'}): #HEAD == GET except no response body
	if 'Content-Type' not in headers: headers['Content-Type'] = 'application/x-www-form-urlencoded'
	if params:
		if '?' not in url: url += '?'
		else: url += '&'
		for i in params:
			if not isinstance(params[i], str) and hasattr(params[i], '__iter__'):
				for param in params[i]:
					url += urllib.parse.quote(i)
					if '[]'in i: url += '%5B%5D'
					url += '=' + urllib.parse.quote(param) + '&'
			else: url += urllib.parse.quote(i) + '=' + urllib.parse.quote(str(params[i])) + '&'
		url = url[:-1]
	return _request('HEAD', url, '', headers)

def post(url, params = {}, headers = {'Content-Type': 'application/x-www-form-urlencoded'}):
	if 'Content-Type' not in headers: headers['Content-Type'] = 'application/x-www-form-urlencoded'
	body = ''
	for i in params:
		if not isinstance(params[i], str) and hasattr(params[i], '__iter__'):
			for param in params[i]:
				body += '&' + urllib.parse.quote(i)
				if '[]' in i: body += '%5B%5D'
				body += '=' + urllib.parse.quote(param)
		else: body += '&' + urllib.parse.quote(i) + '=' + urllib.parse.quote(str(params[i]))
	return _request('POST', url, body[1:], headers)

