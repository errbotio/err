
import logging
from errbot.backends.base import (
    Person,
    RoomDoesNotExistError
)
from slack_sdk.web import WebClient

log = logging.getLogger(__name__)


class SlackPerson(Person):
    """
    This class describes a person on Slack's network.
    """

    def __init__(self, webclient: WebClient, userid=None, channelid=None):
        if userid is not None and userid[0] not in ("U", "B", "W"):
            raise Exception(
                f"This is not a Slack user or bot id: {userid} (should start with U, B or W)"
            )

        if channelid is not None and channelid[0] not in ("D", "C", "G"):
            raise Exception(
                f"This is not a valid Slack channelid: {channelid} (should start with D, C or G)"
            )

        self._userid = userid
        self._channelid = channelid
        self._webclient = webclient
        self._username = None  # cache
        self._fullname = None
        self._email = None
        self._channelname = None
        self._email = None

    @property
    def userid(self):
        return self._userid

    @property
    def username(self):
        """Convert a Slack user ID to their user name"""
        if self._username:
            return self._username
        self._get_user_info()
        if self._username is None:
            return f"<{self._userid}>"
        return self._username

    @property
    def fullname(self):
        """Convert a Slack user ID to their full name"""
        if self._fullname:
            return self._fullname
        self._get_user_info()
        if self._fullname is None:
            return f"<{self._userid}>"
        return self._fullname

    @property
    def email(self):
        """Convert a Slack user ID to their user email"""
        if self._email:
            return self._email
        self._get_user_info()
        if self._email is None:
            return "<%s>" % self._userid
        return self._email

    def _get_user_info(self):
        """Cache all user info"""
        user = self._webclient.users_info(user=self._userid)["user"]

        if user is None:
            log.error("Cannot find user with ID %s" % self._userid)
            return

        self._email = user["profile"]["email"]
        self._fullname = user["real_name"]
        self._username = user["name"]

    @property
    def channelid(self):
        return self._channelid

    @property
    def channelname(self):
        """Convert a Slack channel ID to its channel name"""
        if self._channelid is None:
            return None

        if self._channelname:
            return self._channelname

        channel = [
            channel
            for channel in self._webclient.conversations_list()["channels"]
            if channel["id"] == self._channelid
        ]

        if not channel:
            raise RoomDoesNotExistError(f"No channel with ID {self._channelid} exists.")

        if not self._channelname:
            self._channelname = channel[0]["name"]
        return self._channelname

    @property
    def domain(self):
        raise NotImplementedError

    # Compatibility with the generic API.
    client = channelid
    nick = username

    # Override for ACLs
    @property
    def aclattr(self):
        # Note: Don't use str(self) here because that will return
        # an incorrect format from SlackMUCOccupant.
        return f"@{self.username}"

    person = aclattr

    def __unicode__(self):
        return f"@{self.username}"

    def __str__(self):
        return self.__unicode__()

    def __eq__(self, other):
        if not isinstance(other, SlackPerson):
            log.warning("tried to compare a SlackPerson with a %s", type(other))
            return False
        return other.userid == self.userid

    def __hash__(self):
        return self.userid.__hash__()
