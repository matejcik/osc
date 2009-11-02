import ar
import re
import tarfile
import packagequery

class DebError(packagequery.PackageError):
    pass

class DebQuery(packagequery.PackageQuery):
    def __init__(self, fh):
        self.__file = fh
        self.filename_suffix = 'deb'
        self.fields = {}

    def read(self):
        arfile = ar.Ar(fh = self.__file)
        arfile.read()
        debbin = arfile.get_file('debian-binary')
        if debbin is None:
            raise DebError('no debian binary')
        if debbin.read() != '2.0\n':
            raise DebError('invalid debian binary format')
        control = arfile.get_file('control.tar.gz')
        if control is None:
            raise DebError('missing control.tar.gz')
        tar = tarfile.open(fileobj = control)
        try:
            control = tar.extractfile('./control')
        except KeyError:
            raise DebError('missing \'control\' file in control.tar.gz')
        self.__parse_control(control)

    def __parse_control(self, control):
        data = control.readline().strip()
        while data:
            field, val = re.split(':\s*', data.strip(), 1)
            data = control.readline()
            while data and re.match('\s+', data):
                val += '\n' + data.strip()
                data = control.readline().rstrip()
            # a hyphen is not allowed in dict keys
            self.fields[field.replace('-', '_').lower()] = val
        versrel = self.fields['version'].rsplit('-', 1)
        if len(versrel) == 2:
            self.fields['version'] = versrel[0]
            self.fields['release'] = versrel[1]
        else:
            self.fields['release'] = '0'
        verep = self.fields['version'].split(':', 1)
        if len(verep) == 2:
            self.fields['epoch'] = verep[0]
            self.fields['version'] = verep[1]
        else:
            self.fields['epoch'] = '0'
        self.fields['provides'] = [ i.strip() for i in re.split(',\s*', self.fields.get('provides', '')) if i ]
        self.fields['depends'] = [ i.strip() for i in re.split(',\s*', self.fields.get('depends', '')) if i ]
        self.fields['pre_depends'] = [ i.strip() for i in re.split(',\s*', self.fields.get('pre_depends', '')) if i ]
        # add self provides entry
        self.fields['provides'].append('%s = %s' % (self.name(), '-'.join(versrel)))

    def vercmp(self, debq):
        res = cmp(int(self.epoch()), int(debq.epoch()))
        if res != 0:
            return res
        res = DebQuery.debvercmp(self.version(), debq.version())
        if res != 0:
            return res
        res = DebQuery.debvercmp(self.release(), debq.release())
        return res

    def name(self):
        return self.fields['package']

    def version(self):
        return self.fields['version']

    def release(self):
        return self.fields['release']

    def epoch(self):
        return self.fields['epoch']

    def arch(self):
        return self.fields['architecture']

    def description(self):
        return self.fields['description']

    def provides(self):
        return self.fields['provides']

    def requires(self):
        return self.fields['depends']

    def getTag(self, num):
        return self.fields.get(num, None)

    @staticmethod
    def query(filename):
        f = open(filename, 'rb')
        debq = DebQuery(f)
        debq.read()
        f.close()
        return debq

    @staticmethod
    def debvercmp(ver1, ver2):
        """
        implementation of dpkg's version comparison algorithm
        """
        # 32 is arbitrary - it is needed for the "longer digit string wins" handling
        # (found this nice approach in Build/Deb.pm (build package))
        ver1 = re.sub('(\d+)', lambda m: (32 * '0' + m.group(1))[-32:], ver1)
        ver2 = re.sub('(\d+)', lambda m: (32 * '0' + m.group(1))[-32:], ver2)
        vers = map(lambda x, y: (x or '', y or ''), ver1, ver2)
        for v1, v2 in vers:
            if v1 == v2:
                continue
            if (v1.isalpha() and v2.isalpha()) or (v1.isdigit() and v2.isdigit()):
                res = cmp(v1, v2)
                if res != 0:
                    return res
            else:
                if v1 == '~' or not v1:
                    return -1
                elif v2 == '~' or not v2:
                    return 1
                ord1 = ord(v1)
                if not (v1.isalpha() or v1.isdigit()):
                    ord1 += 256
                ord2 = ord(v2)
                if not (v2.isalpha() or v2.isdigit()):
                    ord2 += 256
                if ord1 > ord2:
                    return 1
                else:
                    return -1
        return 0

if __name__ == '__main__':
    import sys
    try:
        debq = DebQuery.query(sys.argv[1])
    except DebError, e:
        print e.msg
        sys.exit(2)
    print debq.name(), debq.version(), debq.release(), debq.arch()
    print debq.description()
    print '##########'
    print '\n'.join(debq.provides())
    print '##########'
    print '\n'.join(debq.requires())