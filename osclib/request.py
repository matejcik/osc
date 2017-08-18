from .util import split_package

from osc import conf

DEFAULT_SEARCH_STATES = ("new", "review", "declined")

def search(api, source=None, target=None, user=None, req_type=None, state=DEFAULT_SEARCH_STATES):
    if not source and not target and not user:
        raise ValueError("You must specify at least one of source, target, user.")

    xpath = []
    _xval = lambda attr, value: "{}='{}'".format(attr, value)
    _xif  = lambda attr, value: value and [_xval(attr, value)] or []

    # query by state
    if not state == "all":
        if isinstance(state, str): state = [state]
        state_query = " or ".join([_xval("state/@name", s) for s in state])
        xpath.append(state_query)

    # query by user
    if user:
        xpath.append(_xval("state/@who", user) + " or " + _xval("history/@who", user))

    # query by source and target
    if source:
        pkg = split_package(source)
        xpath += _xif("action/source/@project", pkg.project)
        xpath += _xif("action/source/@package", pkg.package)
    if target:
        pkg = split_package(target)
        xpath += _xif("action/target/@project", pkg.project)
        xpath += _xif("action/target/@package", pkg.package)

    # query by type
    xpath += _xif("action/@type", req_type)

    if not xpath:
        raise err.WrongArgs("Something went wrong, the query string is empty.")

    xpathstr = "(" + ") and (".join(xpath) + ")"
    if conf.config['verbose'] > 1:
        print("[ {} ]".format(xpath))

    xmlresult = api.xml("/search/request", match=xpathstr)
    collection = xmlresult["request"]
    return [Request().read(r) for r in xmlresult["request"].findall("request")]
