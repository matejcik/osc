import osclib.api
import osc.conf
import os
import os.path
import vcr
import pytest
import requests

TESTROOT = os.path.join(pytest.config.rootdir, "osclib-tests")
OSCRC    = os.path.join(TESTROOT, "oscrc", "oscrc_test_api")
VCRROOT  = os.path.join(TESTROOT, "fixtures", "vcr")

def test_default_api(monkeypatch):
    """
    default_api() should return a valid Api instance based on oscrc
    """
    monkeypatch.setenv("OSC_CONFIG", OSCRC)

    api = osclib.api.default_api()
    assert isinstance(api, osclib.api.Api)
    assert api.apiurl == "https://obs.example.com"
    assert api.username == "grace"

def test_new_api():
    """
    new Api instances should properly read authentication info
    from osc config, or accept it from arguments.
    """
    osc.conf.get_config(override_conffile=OSCRC)

    api = osclib.api.Api("https://obs.example.com")
    assert api.username == "grace"

    api = osclib.api.Api("https://obs.example.org")
    assert api.username == "sally"

    api = osclib.api.Api("https://notobs.example.org", username="deborah", password="estrin")
    assert api.apiurl == "https://notobs.example.org"
    assert api.username == "deborah"
    assert api.password == "estrin"

    with pytest.raises(Exception):
        osclib.api.Api("https://notobs.example.org")

    with pytest.raises(Exception):
        osclib.api.Api("https://obs.example.com", password="onlypassword")

@vcr.use_cassette(os.path.join(VCRROOT, "test_request.yaml"), filter_headers=['authorization'])
def test_request():
    """
    Let's download a thing from the api.

    This test assumes that the user running it has a valid oscrc file
    with entries for api.opensuse.org.
    """
    # first clear out osc.conf settings
    osc.conf.get_config()

    # download a thing
    api = osclib.api.Api("https://api.opensuse.org")
    r = api.request(["source", "openSUSE:Factory", "osc"])
    assert isinstance(r, requests.Response)
    assert 'name="osc"' in r.text

    # check that we get to handle bad status
    r = api.request(["source", "openSUSE:Factory", "does not exist"])
    assert not r.ok

    # check that method, query and data is supported
    r = api.request(["source", "openSUSE:Factory", "does not exist"],
            method="POST",
            query={"hello": "world"},
            data="see a thing")
    assert isinstance(r, requests.Response)
    assert not r.ok

@vcr.use_cassette(os.path.join(VCRROOT, "test_request.yaml"), filter_headers=['authorization'])
def test_get_xml():
    """
    get_xml() should return a xml document, or raise an exception

    TODO maybe get_xml should always return xml document?

    This test assumes that the user running it has a valid oscrc file
    with entries for api.opensuse.org.
    """
    # first clear out osc.conf settings
    osc.conf.get_config()

    api = osclib.api.Api("https://api.opensuse.org")
    root = api.get_xml(["source", "openSUSE:Factory", "osc"])
    assert root is not None
    assert root.tag == "directory"
    assert root.get("name") == "osc"

    with pytest.raises(requests.exceptions.HTTPError):
        root = api.get_xml(["source", "openSUSE:Factory", "does not exist"])
