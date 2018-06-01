import math
from .node import Node

class Quorum:
    validators = None
    threshold = None

    def __init__(self, threshold, validators):
        assert type(threshold) in (float, int)
        assert threshold <= 100 and threshold > 0  # threshold must be percentile
        assert len(
            list(filter(lambda x: not isinstance(x, Node), validators))
        ) < 1

        self.threshold = threshold
        self.validators = validators

    def __repr__(self):
        return '<Quorum: threshold=%(threshold)s validators=%(validators)s>' % self.__dict__

    def is_inside(self, node):
        return len(list(filter(lambda x: x.name == node.name, self.validators))) > 0

    # remove node from quorum
    def remove(self, node):
        if not self.is_inside(node):
            return

        self.validators = filter(lambda x: x != node, self.validators)
        return

    # add node to quorum
    def insert(self, node):
        self.validators.append(node)        

    @property
    def minimum_quorum(self):
        '''
        the required minimum quorum will be round *up*
        '''
        return math.ceil((len(self.validators) + 1) * (self.threshold / 100))

    def to_dict(self, simple=True):
        return dict(
            validators=list(map(lambda x: x.to_dict(simple), self.validators)),
            threshold=self.threshold,
        )
