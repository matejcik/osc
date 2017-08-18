import os.path

from xml.etree import ElementTree as ET
from hashlib import md5

from .util import split_package

BUFSIZE = 65536

def _xml_from_filelist(filelist):
    root = ET.Element("directory")
    for name in sorted(filelist):
        digest = md5()
        with open(name, "rb") as f:
            for chunk in iter(lambda: f.read(BUFSIZE), b""):
                digest.update(chunk)
        ET.SubElement(root, "entry", name=os.path.basename(name), md5=digest.hexdigest())
    return root

def branch(api, source, target=None, **kwargs):
    source = split_package(source)
    path = ['source', *source]
    query = {'cmd': 'branch'}

    if target is not None:
        target = split_package(target)
        query['target_project'] = target.project
        query['target_package'] = target.package

    query.update(kwargs)
    r = api.request(path, query, method="POST")
    xml = ET.fromstring(r.text)
    if not r.ok:
        print (r.text)
        summary = xml.find("summary")
        raise Exception("branch failed with code {}: {}".format(
            r.status_code,
            summary is not None and summary.text or "reason unspecified"
        ))
    else:
        data = { i.get("name"): i.text for i in xml.findall("data") }
        ret_source = split_package(data.get(x, None) for x in ("sourceproject", "sourcepackage"))
        ret_target = split_package(data.get(x, None) for x in ("targetproject", "targetpackage"))
        return xml, ret_source, ret_target


def commit(api, package, filelist, user, message, **query):
    package = split_package(package)
    flist = _xml_from_filelist(filelist)
    query.update({
        "cmd": "commit",
        "user": user,
        "comment": message,
    })

    try:
        for name in filelist:
            with open(name, "rb") as upload:
                r = api.request(["source", *package, os.path.basename(name)], method="PUT",
                        query={"rev": "upload"}, data=upload)
                r.raise_for_status()

        r = api.request(["source", *package], query=query, method="POST")
        r.raise_for_status()

    except:
        api.request(["source", *package], query={"cmd": "deleteuploadrev"}, method="POST")
        raise
