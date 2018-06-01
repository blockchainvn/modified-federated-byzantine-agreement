from ..common import (
    log,
)

from ..network import (
    Node,
    Message,
)

from .state import State
from .ballot import Ballot

class Storage:
    messages = None
    message_ids = None

    ballot_history = None

    pending = None
    pending_ids = None

    def __init__(self, node):
        assert isinstance(node, Node)

        self.node = node

        self.messages = list()
        self.message_ids = list()

        self.pending = list()
        self.pending_ids = list()

        self.ballot_history = dict()

    def add(self, ballot):
        assert isinstance(ballot, Ballot)
        assert not ballot.is_empty()
        assert ballot.state == State.all_confirm

        self.messages.append(ballot.message)
        self.message_ids.append(ballot.message.message_id)
        self.ballot_history[ballot.message.message_id] = ballot.to_dict()

        log.storage.info('%s: ballot was added: %s', self.node.name, ballot)

        return

    def is_exists(self, message):
        return message.message_id in self.message_ids

    def add_pending(self, message):
        assert isinstance(message, Message)

        self.pending.append(message)
        self.pending_ids.append(message.message_id)

        log.storage.info('%s: message was added to pending: %s', self.node.name, message)

        return

    def is_exists_pending(self, message):
        return message.message_id in self.pending_ids