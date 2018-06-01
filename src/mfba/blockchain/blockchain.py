import asyncio
from uuid import uuid1

from ..common import (
    log,
)
from ..consensus import (
    FBAConsensus as Consensus,
    Ballot,
)    
from ..network import (
    BaseServer,
    LocalTransport,
    Message,
    Node,
    Quorum,
)


class TestConsensus(Consensus):
    def reached_all_confirm(self, ballot_message):
        log.blockchain.info("Waiting for next message or Ctrl+C to exit.")

class Server(BaseServer):
    node = None
    consensus = None

    def __init__(self, node, consensus, *a, **kw):
        assert isinstance(node, Node)
        assert isinstance(consensus, Consensus)

        super(Server, self).__init__(*a, **kw)

        self.node = node
        self.consensus = consensus

    def __repr__(self):
        return '<Server: node=%(node)s consensus=%(consensus)s>' % self.__dict__

    def message_receive(self, data_list):
        super(Server, self).message_receive(data_list)

        for i in data_list:
            log.server.debug('%s: hand over message to consensus: %s', self.name, i)
            self.consensus.receive(i)


class Blockchain():    

    def __init__(self, node_config, validator_config, loop):
        
        self.quorum = Quorum(
            node_config.threshold,
            list(map(lambda x: Node(x.name, x.endpoint, None), validator_config)),
        )

        self.node = Node(node_config.name, node_config.endpoint, self.quorum)
        log.blockchain.debug('node created: %s', self.node)


        self.transport = LocalTransport(node_config.name, node_config.endpoint, loop)
        log.blockchain.debug('transport created: %s', self.transport)
        # final consensus among a certain number of quorums
        self.consensus = TestConsensus(self.node, self.quorum, self.transport)
        log.blockchain.debug('consensus created: %s', self.consensus)

        self.server = Server(self.node, self.consensus, node_config.name, transport=self.transport)
        log.blockchain.debug('server created: %s', self.server)

    def to_dict(self):
        return dict(
            node=self.node.to_dict(),
            consensus=self.consensus.to_dict(),
            quorum=self.quorum.to_dict(),
            transport=self.transport.to_dict(),
        )

    def start(self):
        self.server.start()

    def send(self, client):
        MESSAGE = Message.new(uuid1().hex)
        self.transport.send(self.node.endpoint, MESSAGE.serialize(client))
        log.blockchain.info('inject message %s -> n0: %s', client.name, MESSAGE)

    