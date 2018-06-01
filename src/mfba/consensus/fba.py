import json

from ..network import (
    BaseTransport,
    Message,
    Node,
    Quorum,        
)

from ..common import (
    log,
)

from .ballot import Ballot, BallotMessage, BallotVoteResult
from .state import State
from .storage import Storage

class FBAConsensus:
    name = None
    quorum = None
    ballot = None

    storage = None

    def __init__(self, node, quorum, transport):
        assert isinstance(node, Node)
        assert isinstance(quorum, Quorum)
        assert isinstance(transport, BaseTransport)

        self.node = node
        self.quorum = quorum
        self.transport = transport
        self.storage = Storage(self.node)

        self.ballot = Ballot(self.node, State.none, None)
        self.ballot.change_state(State.init)

        log.consensus.debug(
            '%s: initially set state to %s',
            self.node.name, self.ballot.state,
        )

    def __repr__(self):
        return '<Consensus: node=%(node)s quorum=%(quorum)s transport=%(transport)s>' % self.__dict__

    def validate_message(self, message):
        assert isinstance(message, Message)

        # TODO implement
        is_validated = True

        return is_validated

    def receive(self, data):
        log.consensus.debug('%s: received data: %s', self.node.name, data)

        try:
            loaded = load_message(data)
        except Message.InvalidMessageError as e:
            log.consensus.error('unknown data was received: %s', e)
            return
        else:
            log.consensus.debug('%s: received data is %s', self.node.name, loaded)
            if not isinstance(loaded, (Message, BallotMessage)):
                log.consensus.debug('%s: unknown instance found, `%s`', self.node.name, loaded)
                return

        if self.storage.is_exists(loaded.get_message()):
            log.consensus.debug('%s: already stored: %s', self.node.name, loaded)

            return

        if isinstance(loaded, Message):
            return self._handle_message(loaded)

        if isinstance(loaded, BallotMessage):
            return self._handle_ballot_message(loaded)

    def broadcast(self, ballot_message, skip_nodes=None):
        assert type(skip_nodes) in (list, tuple) if skip_nodes is not None else True

        for node in self.quorum.validators:
            if skip_nodes is not None and node in skip_nodes:
                continue

            self.transport.send(
                node.endpoint,
                ballot_message,
            )

        self.ballot.is_broadcasted = True

        return

    def _handle_message(self, message):
        assert message.node is not None

        log.consensus.debug('%s: received message: %s', self.node.name, message)

        if self.ballot.state != State.init:
            log.consensus.debug(
                '%s: ballot state is not `init`, this message will be in stacked in pending storage',
                self.node.name,
                message,
            )
            self.storage.add_pending(message.copy())

            return

        if self.ballot.state == State.init:
            if self.ballot.is_empty():
                self.ballot.set_message(message.copy())
            else:
                self.storage.add_pending(message.copy())

                return

        result = BallotVoteResult.disagree
        if self.validate_message(message):
            result = BallotVoteResult.agree

        self.ballot.node_result = result
        self.ballot.vote(self.node, self.ballot.node_result, State.init)

        ballot_message = self.ballot.serialize_ballot_message()
        log.consensus.debug('%s: broadcast ballot_message initially: %s', self.node.name, ballot_message.strip())

        self.broadcast(ballot_message, skip_nodes=(message.node,))

        return False

    def _handle_ballot_message(self, ballot_message):
        log.consensus.debug(
            '%s: %s: received ballot_message: %s',
            self.node.name,
            self.ballot.state,
            ballot_message,
        )

        # if ballot_message is from unknown node, just ignore it
        if not self.quorum.is_inside(ballot_message.node):
            log.consensus.debug(
                '%s: message from outside quorum: %s',
                self.node.name,
                ballot_message,
            )
            return

        # if ballot_message.state is older than state of node, just ignore it
        if ballot_message.state < self.ballot.state:
            return

        is_ballot_empty = self.ballot.is_empty()
        log.consensus.debug('%s: ballot is empty?: %s', self.node.name, is_ballot_empty)
        if is_ballot_empty:  # ballot is empty, just embrace ballot
            self.ballot.set_message(ballot_message.message)

        is_valid_ballot_message = self.ballot.is_valid_ballot_message(ballot_message)

        log.consensus.debug('%s: ballot_message is valid?: %s', self.node.name, is_valid_ballot_message)
        if not is_valid_ballot_message:
            log.consensus.error(
                '%s: unexpected ballot_message was received: expected != given\n%s\n%s',
                self.node.name,
                self.ballot.__dict__,
                ballot_message.__dict__,
            )
            return

        self.ballot.vote(ballot_message.node, ballot_message.result, ballot_message.state)

        state, is_passed_threshold = self.ballot.check_threshold()

        # if new state was already agreed from other validators, the new ballot
        # will be accepted
        if is_passed_threshold and state != self.ballot.state:
            self.ballot.change_state(state)

        log.consensus.debug(
            '%s: is passed threshold?: %s: %s',
            self.node.name,
            is_passed_threshold,
            ballot_message,
        )

        fn = getattr(self, '_handle_%s' % self.ballot.state.name)
        result = fn(ballot_message, is_passed_threshold)

        if result is not True:
            return

        next_state = self.ballot.state.get_next()
        if next_state is None:
            return

        self.ballot.change_state(next_state)

        if next_state == State.all_confirm:
            self._handle_all_confirm(ballot_message, None)
            return

        result = BallotVoteResult.disagree
        if self.validate_message(ballot_message.message):
            result = BallotVoteResult.agree

        self.ballot.node_result = result
        self.ballot.vote(self.node, self.ballot.node_result, self.ballot.state)

        self.broadcast(self.ballot.serialize_ballot_message())

        log.consensus.debug('%s: new ballot broadcasted: %s', self.node.name, self.ballot)

        return

    def _handle_init(self, ballot_message, is_passed_threshold):
        assert isinstance(ballot_message, BallotMessage)

        if self.ballot.node_result is None:
            result = BallotVoteResult.disagree
            if self.validate_message(ballot_message.message):
                result = BallotVoteResult.agree

            self.ballot.node_result = result
            self.ballot.vote(self.node, result, self.ballot.state)

        if not self.ballot.is_broadcasted:
            self.broadcast(self.ballot.serialize_ballot_message())

            log.consensus.debug('%s: new ballot broadcasted: %s', self.node.name, self.ballot)

        if is_passed_threshold:
            return True

        return False

    def _handle_sign(self, ballot_message, is_passed_threshold):
        if is_passed_threshold:
            return True

        return False

    _handle_accept = _handle_sign

    def _handle_all_confirm(self, ballot_message, is_passed_threshold):
        log.consensus.info('%s: %s: %s', self.node.name, self.ballot.state, ballot_message)

        self.storage.add(self.ballot)

        self.ballot.initialize_state()

        # FIXME this is for simulation purpose
        self.reached_all_confirm(ballot_message)

        return

    def reached_all_confirm(self, ballot_message):
        pass


def load_message(data):
    try:
        o = json.loads(data)
    except json.decoder.JSONDecodeError as e:
        raise Message.InvalidMessageError(e)

    if 'type_name' not in o:
        raise Message.InvalidMessageError('field, `type_name` is missing: %s', o)

    if o['type_name'] == 'message':
        return Message.from_json(data)

    if o['type_name'] == 'ballot-message':
        return BallotMessage.from_json(data)
