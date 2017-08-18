from osc import conf

import os.path
import logging
import requests
from urllib.parse import urlsplit, urlunsplit
from xml.etree import cElementTree as ET

log = logging.getLogger(__name__)

class Api():
    """
    Base osclib class that represents a connection to the OBS API.

    This provides various methods that can perform HTTP requests to the API
    and return results in various formats.

    No "business logic" should be included here.
    """
    def __init__(self, apiurl, username=None, password=None):
        self.apiurl = apiurl
        self.username = username
        self.password = password
        if self.username is None and self.password is None:
            try:
                self.username = conf.config['api_host_options'][apiurl]['user']
                self.password = conf.config['api_host_options'][apiurl]['pass']
            except KeyError as e:
                raise Exception("No authentication found for apiurl {}".format(apiurl)) from e
        elif self.username is None or self.password is None:
            raise Exception("Must specify both username and password")

    def request(self, path, query=None, method="GET", data=None):
        if isinstance(path, list):
            path = '/'.join(path)

        scheme, netloc, root = urlsplit(self.apiurl)[:3]
        url = urlunsplit((scheme, netloc, "{}/{}".format(root, path), None, None))

        if method == "GET" and data is not None:
            method = "POST"

        log.info("http request: {} {} {}".format(method, path, query))

        auth = (self.username, self.password)

        return requests.request(method, url, auth=auth, params=query, data=data, stream=True)

    def get_xml(self, path, query=None):
        resp = self.request(path, query=query)
        resp.raise_for_status()
        return ET.fromstring(resp.text)

    def download(self, path, query=None, directory=None, filename=None):
        if filename is None:
            if isinstance(path, list):
                filename = path[-1]
            else:
                filename = os.path.basename(path)
        if directory is not None:
            filename = os.path.join(directory, filename)

        resp = self.request(path, query=query)
        resp.raise_for_status()
        with open(filename, "wb") as target:
            for chunk in resp.iter_content():
                target.write(chunk)

    def upload(self, filename, path, query=None, method="PUT"):
        return self.request(path, query=query, method=method, data=open(filename, 'rb'))


def default_api():
    """Get the default API based on .oscrc"""
    conf.get_config()
    apiurl = conf.config['apiurl']
    return Api(apiurl)
