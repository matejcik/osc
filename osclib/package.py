import os.path

from xml.etree import ElementTree as ET
from hashlib import md5
from cached_property import cached_property

from .util import split_package

BUFSIZE = 65536

def list(api, project):
    x = api.get_xml(['source', project])
    return [Package(api, project, node.get("name")) for node in x.findall("entry")]

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


def upload(api, package, filename, target=None, data=None):
    package = split_package(package)
    if target is None:
        target = os.path.basename(filename)

    fileobj = None
    if data is None:
        fileobj = open(filename, "rb")

    try:
        r = api.request(["source", *package, target], method="PUT", data=fileobj or data,
                query={"rev": "upload"})
        r.raise_for_status()
    finally:
        if fileobj is not None:
            fileobj.close()


def commit(api, package, user, message, filelist=(), **query):
    package = split_package(package)
    #flist = _xml_from_filelist(filelist)
    query.update({
        "cmd": "commit",
        "user": user,
        "comment": message,
    })

    try:
        for name in filelist:
            upload(api, package, name)

        r = api.request(["source", *package], query=query, method="POST")
        r.raise_for_status()

    except:
        api.request(["source", *package], query={"cmd": "deleteuploadrev"}, method="POST")
        raise


def sourceinfos(api, packages):
    projects = {}
    infos = {}

    for pkg in packages:
        pkg = split_package(pkg)
        projects.setdefault(pkg.project, []).append(pkg)

    for project, pkgs in projects.items():
        names = { pkg.name : pkg for pkg in pkgs }
        if len(names) > 25:
            pkgs = ()
        else:
            pkgs = tuple(("package", name) for name in names)
        x = api.get_xml(["source", project], query=(("view", "info"), ("nofilename", 1)) + pkgs)
        for si in x.findall("sourceinfo"):
            pkgname = si.get("package")
            if pkgname not in names:
                continue
            pkg = names[pkgname]
            infos[pkgname] = si
            if isinstance(pkg, Package):
                pkg.sourceinfo = si

    return infos


def get_sourceinfo(api, package):
    return sourceinfos(api, [package]).get(package.name)


def get_info(api, pkg):
    pkg = split_package(pkg)
    return api.get_xml(["source", pkg.project, pkg.name])


def get_meta(api, pkg):
    pkg = split_package(pkg)
    return api.get_xml(["source", pkg.project, pkg.name])


def package_from_xml(api, xml):
    if xml is None:
        return None
    project = xml.get("project")
    name = xml.get("package")
    if project is not None and name is not None:
        return Package(api, project, name)
    else:
        return None


class Package:

    # TODO look into util.py and resolve the ugly, ugly mess
    # that is PackagePath, before it spreads
    def __init__(self, api, project, name, eager=False):
        self.project = project
        self.name = name
        self.api = api

        if eager:
            self.info
            self.meta
            self.sourceinfo

    def __repr__(self):
        return "<Package {}/{} on {}>".format(self.project, self.name, self.api)

    def __str__(self):
        return "{}/{}".format(self.project, self.name)

    def _tuple(self):
        return (self.api, self.project, self.name)

    def __eq__(self, other):
        return self._tuple() == other._tuple()

    def __hash__(self):
        return hash(self._tuple())

    @cached_property
    def info(self):
        return get_info(self.api, self)

    @cached_property
    def meta(self):
        return get_meta(self.api, self)

    @cached_property
    def sourceinfo(self):
        return get_sourceinfo(self.api, self)

    @cached_property
    def link_target(self):
        return package_from_xml(self.api, self.info.find("linkinfo"))

    @cached_property
    def devel(self):
        return package_from_xml(self.api, self.meta.find("devel"))
