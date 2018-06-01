from .endpoint import Endpoint

class Node:
    name = None
    endpoint = None
    quorum = None

    def __init__(self, name, endpoint_string, quorum):
        self.name = name
        self.endpoint = Endpoint.from_uri(endpoint_string)

        if quorum is not None and quorum.is_inside(self):
            quorum.remove(self)

        self.quorum = quorum

    def __repr__(self):
        return '<Node: %s>' % self.name

    def __eq__(self, name):
        return self.name == name

    def to_dict(self, simple=True):
        return dict(
            name=self.name,
            endpoint=self.endpoint.to_dict(simple),
            quorum=self.quorum.to_dict(simple) if self.quorum is not None else None,
        )