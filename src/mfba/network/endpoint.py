import urllib.parse

class Endpoint:
    scheme = None
    host = None
    port = None

    def __init__(self, scheme, host, port):
        self.scheme = scheme
        self.host = host
        self.port = port

    def __str__(self):
        return '<Endpoint: %(scheme)s://%(host)s:%(port)d>' % self.__dict__

    @classmethod
    def from_uri(cls, uri):
        parsed = urllib.parse.urlparse(uri)

        return cls(parsed.scheme, parsed.hostname, parsed.port)

    @property
    def uri(self):
        return '%(scheme)s://%(host)s:%(port)d' % self.__dict__

    def to_dict(self, simple=True):
        if simple:
            return '%(scheme)s://%(host)s:%(port)s' % self.__dict__

        return dict(
            scheme=self.scheme,
            host=self.host,
            port=self.port,
        )