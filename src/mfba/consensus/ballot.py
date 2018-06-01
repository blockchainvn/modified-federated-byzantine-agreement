import json
import datetime
import enum

from ..common import (
    BaseEnum,
    log,
)

from ..network import (
    Message,
    Node,
    Quorum,
)

from .state import State

class BallotVoteResult(BaseEnum):
    agree = 'Y'
    disagree = 'N'        
    none = enum.auto()  

class Ballot:
    # class AlreadyVotedError(Exception):
    #     pass

    class InvalidBallotError(Exception):
        pass

    class NotExpectedBallotError(Exception):
        pass

    timestamp = None
    state = None
    name = None
    message = None
    voted = None
    is_broadcasted = None
    node_result = None

    def __init__(self, node, state, node_result=BallotVoteResult.none, timestamp=None):
        assert isinstance(node, Node)
        assert isinstance(node.quorum, Quorum)
        assert isinstance(state, State)

        self.node = node
        self.state = state
        self.state_history = [State.none]
        self.message = None
        self.voted = dict()
        self.vote_history = dict()
        self.is_broadcasted = False
        self.node_result = node_result

        if timestamp is None: 
            self.timestamp = str(datetime.datetime.now())
        else:
            self.timestamp = timestamp

    def __repr__(self):
        return '<Ballot: timestamp=%(timestamp)s node=%(node)s state=%(state)s voted=%(voted)s node_result=%(node_result)s is_broadcasted=%(is_broadcasted)s>' % self.__dict__

    def to_dict(self):
        vh = dict()
        for state, voted in self.vote_history.items():
            copied = dict()
            for node_name, result in voted.items():
                copied[node_name] = result.name

            vh[state] = copied

        return dict(
            timestamp=self.timestamp,
            node=self.node.to_dict(simple=True),
            state=self.state.name,
            state_history=list(map(lambda x: x.name, self.state_history)),
            node_result=self.node_result.name,
            message=self.message.to_dict(),
            vote_history=vh,
        )

    def is_valid_ballot_message(self, ballot_message):
        # if self.state != ballot_message.state:
        #     return False

        if ballot_message.message is None:
            return False

        if self.message != ballot_message.message:
            return False

        return True

    def initialize_state(self):
        self.state = State.init
        self.message = None
        self.voted = dict()
        self.is_broadcasted = False
        self.node_result = None

        log.ballot.warning('%s: ballot is initialized', self.node.name)

        return

    def change_state(self, state):
        assert isinstance(state, State)

        log.ballot.warning(
            '%s: state changed `%s` -> `%s`',
            self.node.name, self.state.name, state.name,
        )
        self.state_history.append(state)
        if self.state.value in self.voted:
            self.vote_history[self.state.name] = self.voted[self.state.value]

        self.state = state
        self.voted = dict()
        self.is_broadcasted = False

        return

    def serialize_ballot_message(self):
        return BallotMessage(
            self.node,
            self.state,
            self.message,
            self.node_result,
        ).serialize()

    def set_message(self, message):
        assert isinstance(message, Message)

        self.message = message
        self.voted = dict()

        return

    def is_empty(self):
        return self.message is None

    def is_voted(self, node):
        return node.name in self.voted

    def vote(self, node, result, state):
        assert isinstance(node, Node)

        if self.state > state:
            log.ballot.debug(
                '%s: same message and previous state: %s: %s',
                self.node.name,
                state,
            )

            return

        self.voted.setdefault(state.value, dict())

        # if node.name in self.voted:
        #     raise Ballot.AlreadyVotedError('node, %s already voted' % node_name)
        #     return
        if node.name in self.voted[state.value]:
            # existing vote will be overrided
            log.ballot.debug('%s: already voted?: %s', self.node.name)

        self.voted[state.value][node.name] = result
        log.ballot.info('%s: %s voted for %s', self.node.name, node, self.message)

        return


    # if above the threshold then the consensus of the quorum is finalizied
    def check_threshold(self):
        voted = self.voted.copy()

        states = sorted(voted.keys(), reverse=True)
        if len(states) < 1:
            return (self.state, False)

        for state_value in states:
            if state_value < self.state.value:
                del self.voted[state_value]
                continue

            target = voted[state_value]

            agreed_votes = list(filter(lambda x: x == BallotVoteResult.agree, target.values()))

            # agreed votes is above the minimum quorum defined by the threshold
            is_passed = len(agreed_votes) >= self.node.quorum.minimum_quorum
            log.ballot.info(
                '%s: threshold checked: threshold=%s voted=%s minimum_quorum=%s agreed=%d is_passed=%s',
                self.node.name,
                self.node.quorum.threshold,
                sorted(map(lambda x: (x[0], x[1].value), target.items())),
                self.node.quorum.minimum_quorum,
                len(agreed_votes),
                is_passed,
            )

            if is_passed:
                return (State.from_value(state_value), is_passed)

        return (self.state, is_passed)


class BallotMessage:
    class InvalidBallotMessageError(Exception):
        pass

    state = None
    message = None
    result = None

    def __init__(self, node, state, message, result):
        assert isinstance(node, Node)
        assert isinstance(state, State)
        assert isinstance(message, Message)
        assert isinstance(result, BallotVoteResult)

        self.node = node
        self.state = state
        self.message = message
        self.result = result

    def __repr__(self):
        return '<BallotMessage: node=%(node)s state=%(state)s result=%(result)s message=%(message)s>' % self.__dict__

    def serialize(self):
        return json.dumps(dict(
            type_name='ballot-message',
            node=self.node.name,
            state=self.state.name,
            message=self.message.to_message_dict(),
            result=self.result.name,
        )) + '\r\n\r\n'

    @classmethod
    def from_json(cls, data):
        try:
            o = json.loads(data)
        except json.decoder.JSONDecodeError as e:
            raise cls.InvalidBallotMessageError(e)

        if 'type_name' not in o or o['type_name'] != 'ballot-message':
            raise cls.InvalidBallotMessageError('`type_name` is not "ballot-message"')

        message = None
        try:
            message = Message.from_dict(o)
        except Message.InvalidMessageError as e:
            raise cls.InvalidBallotMessageError(e)

        return cls(
            Node(o['node'], None, None),
            State.from_name(o['state']),
            message,
            BallotVoteResult.from_name(o['result']),
        )

    def get_message(self):
        return self.message


