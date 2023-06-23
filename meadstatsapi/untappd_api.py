import logging
from typing import Dict

import requests

logger = logging.getLogger("untappd-api")

gunicorn_logger = logging.getLogger("gunicorn.error")
logger.handlers = gunicorn_logger.handlers
logger.setLevel(gunicorn_logger.level)


class UntappdAPI:
    """Untappd API"""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        host: str = "api.untappd.com",
        version: str = "v4",
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.endpoint = "https://" + host + "/" + version + "/"

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "meadstats"})

    def _do_get(self, method: str, params: Dict = None, access_token: str = None):
        """
        Internal function for executing GET requests
        :param method: API method
        :param access_token: Access token of user to send the request as
        :return: JSON data
        """
        payload = params if params else {}

        if access_token:
            payload["access_token"] = access_token
        else:
            payload["client_id"] = self.client_id
            payload["client_secret"] = self.client_secret

        url = self.endpoint + method

        logger.debug("Sending GET request to {}".format(url))

        response = self.session.get(url, params=payload)

        logger.debug("Status code: {}".format(response.status_code))

        response.raise_for_status()

        return response

    def authenticate(self, code: str, redirect_url: str):
        access_token_url = f"https://untappd.com/oauth/authorize/"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "response_type": "code",
            "redirect_url": redirect_url,
            "code": code,
        }

        response = self.session.get(access_token_url, params=payload)
        response.raise_for_status()
        response_json = response.json()

        untappd_access_token = response_json["response"]["access_token"]
        return untappd_access_token

    def user_info(
        self, username: str = None, compact: bool = False, access_token: str = None
    ):
        """
        Returns information about a user
        :param username: Username of user
        :param compact: You can pass True here only show the user infomation, and remove the "checkins", "media", "recent_brews", etc attributes
        :param access_token: Optionally pass a access_token if no username is provided
        :return: JSON data
        """
        logger.info(f"Getting user info for {username}")
        if username:
            method = "user/info/{}".format(username)
        else:
            if access_token:
                method = "user/info"
            else:
                raise Exception("Access token need to be provided if username is None")

        params = {}

        if compact:
            params["compact"] = "true"

        response = self._do_get(method, params, access_token)
        response_json = response.json()

        return response_json["response"]["user"], response

    def user_friends(
        self,
        username: str = None,
        offset: int = 0,
        limit: int = 25,
        access_token: str = None,
    ):
        """
        Returns list of users friends
        :param username: Username of user
        :param offset: Get friends starting from this number
        :param limit: Number of friends to get from offset. Max: 25
        :param access_token: Optionally pass a access_token if no username is provided
        :return: JSON data
        """
        logger.info(f"Getting friends info for {username}")
        if username:
            method = "user/friends/{}".format(username)
        else:
            if access_token:
                method = "user/friends"
            else:
                raise Exception("Access token need to be provided if username is None")

        params = {"offset": offset, "limit": limit}

        response = self._do_get(method, params, access_token)
        response_json = response.json()
        logger.warning(f"Response JSON: {response_json}")

        return response_json["response"], response

    def user_beers(
        self,
        username: str = None,
        offset: int = 0,
        limit: int = 50,
        access_token: str = None,
    ):
        """
        Returns list of users beer
        :param username: Username of user
        :param offset: Get beers starting from this number
        :param limit: Number of beers to get from offset. Max: 50
        :param access_token: Optionally pass a access_token if no username is provided
        :return: JSON data
        """
        logger.info(f"Getting beer list for user {username}")
        if username:
            method = "user/beers/{}".format(username)
        else:
            if access_token:
                method = "user/beers"
            else:
                raise Exception("Access token need to be provided if username is None")

        params = {"offset": offset, "limit": limit}

        response = self._do_get(method, params, access_token)
        response_json = response.json()

        return response_json["response"]["beers"], response

    def beer_info(self, beer_id: int, compact: bool = False):
        """
        Returns information about a beer
        :param beer_id: The Beer ID that you want to display checkins
        :param compact: You can pass True here only show the beer infomation, and remove the "checkins", "media", "variants", etc attributes
        :return: JSON data
        """
        logger.info(f"Getting beer info for {beer_id}")
        method = "beer/info/{}".format(beer_id)
        params = {}
        if compact:
            params["compact"] = "true"

        response = self._do_get(method, params)
        response_json = response.json()

        return response_json["beer"], response

    def brewery_info(self, brewery_id: int, compact: bool = False):
        """
        Returns information about a beer
        :param brewery_id: The Brewery ID that you want to display checkins
        :param compact: You can pass True here only show the brewery infomation, and remove the "checkins", "media", "beer_list", etc attributes
        :return: JSON data
        """
        logger.info(f"Getting brewery info for {brewery_id}")
        method = "brewery/info/{}".format(brewery_id)
        params = {}
        if compact:
            params["compact"] = "true"

        response = self._do_get(method, params)
        response_json = response.json()

        return response_json["brewery"], response

    def venue_info(self, venue_id: int, compact: bool = False):
        """
        Returns information about a beer
        :param venue_id: The venue ID that you want to display checkins
        :param compact: You can pass True here only show the venue infomation, and remove the "checkins", "media", "beer_list", etc attributes
        :return: JSON data
        """
        logger.info(f"Getting venue info for {venue_id}")
        method = "venue/info/{}".format(venue_id)
        params = {}
        if compact:
            params["compact"] = "true"

        response = self._do_get(method, params)
        response_json = response.json()

        return response_json["venue"], response

