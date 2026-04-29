import requests
import re
import json

class Request:

    def __init__(self):
        self.headers = None
        self.cookies = None
        self.response_headers = None
        self.response_cookies = None
    def request(self, url, type='GET', data=None):
        page = None
        parameters = None
        if type == 'POST' or type == 'PUT':
            page = requests.post(url, data, headers=self.headers, cookies=self.cookies, allow_redirects=True)
        else:
            page = requests.get(url, parameters, headers=self.headers, cookies=self.cookies, allow_redirects=True)

        self.response_headers = page.headers
        self.response_cookies = page.cookies

        return page.content
