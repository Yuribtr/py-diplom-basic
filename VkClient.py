import time
from urllib.parse import urlencode
from http.client import responses
import requests


class VkClient:
    __API_BASE_URL = 'https://api.vk.com/method/'

    def __init__(self, token: str, user_id=None, version: str = '5.124', debug_mode=False):
        self.__debug_mode = debug_mode
        self.__vksite = 'https://vk.com/'
        self.__token = token
        self.__version = version
        self.__headers = {'User-Agent': 'Netology'}
        self.__params = {'access_token': self.__token, 'v': self.__version}
        self.__delay = 0.3
        # below line needed for get_users only
        self.__initialized = True
        # try to instantiate
        user = self.get_users(user_ids=user_id)
        is_deactivated = False
        if user['success']:
            is_deactivated = user['object'][0].get('deactivated', False)
        if user['success'] and not is_deactivated:
            self.__initialized = True
            self.__user_id = str(user['object'][0]['id'])
            self.__first_name = user['object'][0]['first_name']
            self.__last_name = user['object'][0]['last_name']
            self.__domain = user['object'][0]['domain']
            self.__status = f'{type(self).__name__} initialised with user: ' \
                            f'{self.__first_name} {self.__last_name} (#{self.__user_id})'
        else:
            self.__initialized = False
            self.__user_id = None
            self.__first_name = None
            self.__last_name = None
            self.__domain = None
            if is_deactivated:
                user['message'] = 'User ' + str(is_deactivated)
            # error message will be in status
            self.__status = f'{type(self).__name__} init failed: ' + user['message']
        self.log(self.__status, True)

    def log(self, message, is_debug_msg=False, sep=' '):
        if self.__debug_mode or (not self.__debug_mode and not is_debug_msg):
            if type(message) in [list, dict, tuple, set]:
                print(*message, sep=sep)
            else:
                print(message, sep=sep)

    def is_initialized(self):
        return self.__initialized

    def get_id(self):
        return self.__user_id

    def get_fname(self):
        return self.__first_name

    def get_lname(self):
        return self.__last_name

    def get_domain(self):
        return self.__domain

    def get_status(self):
        return self.__status

    def __str__(self):
        if not self.__user_id:
            return self.__status
        return self.__vksite + self.__domain

    def __and__(self, other):
        if type(other).__name__ != type(self).__name__:
            return False
        mutual = self.get_mutual_friends(friends_ids=[other.get_id()], user_id=self.get_id())
        if not mutual['success']:
            return False
        result = []
        for friend in mutual['object']:
            self.log(f'Let\'s get {len(friend["common_friends"])} mutual friends...', True)
            for x in friend['common_friends']:
                result.append(VkClient(self.__token, x))
                # to prevent ban from server
                time.sleep(self.__delay)
        return result

    @staticmethod
    def get_auth_link(app_id: str, scope='status'):
        """
        This method gives link which can be used in browser to get VK authentication token. After moving by
        link in browser, you'll be redirected to another page, and parameter "access_token" will be in URL.
        :param app_id: APP ID received during creation "standalone" app at https://vk.com/apps?act=manage
        :param scope: one or more statuses from https://vk.com/dev/permissions joined in string with comma delimiter
        :return: link for usage in browser
        """
        oauth_api_base_url = 'https://oauth.vk.com/authorize'
        redirect_uri = 'https://oauth.vk.com/blank.html'
        oauth_params = {
            'redirect_uri': redirect_uri,
            'scope': scope,
            'response_type': 'token',
            'client_id': app_id
        }
        return '?'.join([oauth_api_base_url, urlencode(oauth_params)])

    @staticmethod
    def prepare_params(params):
        """
        This static method normalize all parameters that can be passed as integer or mixed list of integers and strings,
        and makes from them one string that can be accepted as request parameter
        :param params: integer, string or list of integers and string
        :return: string with values separated by commas
        """
        result = ''
        if type(params) is int:
            result = str(params)
        elif type(params) is str:
            result = params
        elif type(params) is list:
            result = ','.join([str(x) for x in params])
        return result

    @staticmethod
    def get_response_content(response: requests.Response, path='response', sep=','):
        """
        This method returns object from JSON response using specified path OR returns errors
        We can hide errors and make one logic for processing any responses
        :param response: response object
        :param path: path to JSON object, separated by comma
        :param sep: delimiter sign in path string
        :return: {'object': 'contains found JSON object or None if response body empty',
                 'success': 'True if requested path found (if specified) and no error codes',
                 'message': 'contains error string if any or empty string'}
        """
        result = {'object': None, 'success': False, 'message': ''}
        if not (200 <= response.status_code < 300):
            result['message'] = f'Request error: {str(response.status_code)} ({responses[response.status_code]})'
            return result
        # to prevent json parsing error if body is empty, but only when lookup path doesn't specified
        if (path == '' or path is None) and len(response.content) == 0:
            result['success'] = True
            result['message'] = 'Response body is empty'
            return result
        try:
            result['object'] = response.json()
        except ValueError:
            result['object'] = None
            result['message'] = 'JSON decode error'
            return result
        # try to get VK error message if present, otherwise return null API error description
        if result['object'].get('error'):
            result['message'] = 'API error: ' + result['object'].get('error', {'error_msg': None})['error_msg']
            result['object'] = None
            return result
        # Let's extract nested object using string path
        for key in path.split(sep):
            # correcting some small mistypes in path (spaces, multiple delimiters)
            if key == '':
                continue
            # If we found list in JSON we can no longer go forward, so we stop and return what we have
            if type(result['object']) is list:
                result['success'] = True
                return result
            else:
                found = result['object'].get(key.strip())
            # if any part of path doesn't found, we return null object
            if found is None:
                result['object'] = None
                result['message'] = 'Object not found'
                return result
            result['object'] = found
        result['success'] = True
        return result

    def get_user_photos(self,
                        user_id: str = None, album_id='profile', photo_sizes=True, count=50, offset=0, extended=True):
        """
        Receive all photos links in JSON format.
        Description here: https://vk.com/dev/photos.get
        :param user_id: ID of user, if None - your token's account ID will be taken
        :param album_id: one of album type: wall, profile, saved
        :param photo_sizes: True, if needed additional info abt photos
        :param count: images per request
        :param offset: offset from which count images
        :param extended: True, if needed likes, comments, tags, reposts
        :return: {'object': 'contains JSON object or None if response body empty',
                 'success': 'True if requested path found (if specified) and no error codes',
                 'message': 'contains error string if any or empty string'}
        """
        if not self.__initialized:
            self.log('Error: not initialized.', True)
            return {'object': None, 'success': False, 'message': f'Error: {type(self).__name__} not initialized'}
        params = {'photo_sizes': photo_sizes, 'count': count, 'offset': offset, 'extended': extended}
        if not user_id:
            user_id = self.__user_id
        params.update({'user_id': self.prepare_params(user_id)})
        if album_id:
            params.update({'album_id': self.prepare_params(album_id)})
        response = requests.get(self.__API_BASE_URL + 'photos.get',
                                params={**self.__params, **params}, headers=self.__headers)
        return self.get_response_content(response, path='response')

    def get_user_status(self, user_id: str = None):
        """
        This method gets user status
        :user_id: ID of user, if None - your token's account ID will be taken
        :return: {'object': 'contains JSON object or None if response body empty',
                 'success': 'True if requested path found (if specified) and no error codes',
                 'message': 'contains error string if any or empty string'}
        """
        if not self.__initialized:
            self.log('Error: not initialized.', True)
            return {'object': None, 'success': False, 'message': f'Error: {type(self).__name__} not initialized'}
        if not user_id:
            user_id = self.__user_id
        params = {}
        if user_id:
            params = {'user_id': self.prepare_params(user_id)}
        response = requests.get(self.__API_BASE_URL + 'status.get',
                                params={**self.__params, **params}, headers=self.__headers)
        return self.get_response_content(response, path='response,text')

    def get_users(self, fields: [str] = None, user_ids: [str] = None):
        """
        This method receive users info by their ID's
        Description here: https://vk.com/dev/users.get
        :param fields: list additional fields of users in strings to be requested
        :param user_ids: list of one or more user IDs in strings form
        :return: {'object': 'contains JSON object or None if response body empty',
                 'success': 'True if requested path found (if specified) and no error codes',
                 'message': 'contains error string if any or empty string'}
        """
        if fields is None:
            fields = ['domain']
        if not self.__initialized:
            self.log('Error: not initialized.', True)
            return {'object': None, 'success': False, 'message': f'Error: {type(self).__name__} not initialized'}
        params = {}
        if fields:
            params.update({'fields': self.prepare_params(fields)})
        if user_ids:
            params.update({'user_ids': self.prepare_params(user_ids)})
        response = requests.get(self.__API_BASE_URL + 'users.get',
                                params={**self.__params, **params}, headers=self.__headers)
        return self.get_response_content(response)

    def get_mutual_friends(self, friends_ids=None, user_id=None):
        """
        This method returns target users and their common friends with specified user
        Description here: https://vk.com/dev/friends.getMutual
        :param user_id: user ID with whom we'll compare other users, if None - your token's account ID will be taken
        :param friends_ids: list of one or more friends user IDs in strings form
        :return: {'object': 'contains JSON object or None if response body empty',
                 'success': 'True if requested path found (if specified) and no error codes',
                 'message': 'contains error string if any or empty string'}
        """
        if not self.__initialized:
            self.log('Error: not initialized.', True)
            return {'object': None, 'success': False, 'message': f'Error: {type(self).__name__} not initialized'}
        if not user_id:
            user_id = self.__user_id
        params = {}
        if friends_ids:
            params.update({'target_uids': self.prepare_params(friends_ids)})
        if user_id:
            params.update({'source_uid': user_id})
        response = requests.get(self.__API_BASE_URL + 'friends.getMutual',
                                params={**self.__params, **params}, headers=self.__headers)
        return self.get_response_content(response, path='response')
