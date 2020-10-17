import time

import requests
from http.client import responses


class YaUploader:
    def __init__(self, token: str, debug_mode=False):
        self.__debug_mode = debug_mode
        self.__token = token
        self.__api_base_url = 'https://cloud-api.yandex.net:443'
        self.__upload_scheme = '/v1/disk/resources/upload'
        self.__file_info_scheme = '/v1/disk/resources'
        self.__file_delete_scheme = '/v1/disk/resources'
        self.__list_scheme = '/v1/disk/resources/files'
        self.__folder_create_scheme = '/v1/disk/resources'
        self.__disk_info_scheme = '/v1/disk'
        self.__headers = {'User-Agent': 'Netology', 'Authorization': 'OAuth ' + self.__token}
        # below line needed for get_disk_info only
        self.__initialized = True
        # try to instantiate
        info = self.get_disk_info()
        if info['success']:
            self.__initialized = True
            self.__display_name = info['object']['user']['display_name']
            self.__status = f'{type(self).__name__} initialised with user: {self.__display_name}'
        else:
            self.__initialized = False
            self.__display_name = None
            self.__status = f'{type(self).__name__} init failed: ' + info['message']
        self.log(self.__status, True)

    def log(self, message, is_debug_msg=False, sep=' '):
        if self.__debug_mode or (not self.__debug_mode and not is_debug_msg):
            if type(message) in [list, dict, tuple, set]:
                print(*message, sep=sep)
            else:
                print(message, sep=sep)

    def is_initialized(self):
        return self.__initialized

    def get_status(self):
        return self.__status

    @staticmethod
    def convert_bytes(size, precision=2):
        suffixes = [' B', ' kB', ' mB', ' gB', ' tB']
        suffix_index = 0
        while size > 1024 and suffix_index < 4:
            suffix_index += 1  # increment the index of the suffix
            size = size / 1024.0  # apply the division
        return '%.*f%s' % (precision, size, suffixes[suffix_index])

    @staticmethod
    def get_response_content(response: requests.Response, path='', sep=','):
        """
        This method returns object from JSON response using specified path OR returns errors
        We can hide errors and make one logic for processing any responses
        :param response: response object
        :param path: path to JSON object, separated by comma
        :param sep: delimiter sign in path string
        :return: {'object': 'contains requested JSON object or None if response body empty',
                 'success': 'True if requested path found (if specified) and no error codes',
                 'message': 'contains error string if any or empty string'}
        """
        result = {'object': None, 'success': False, 'message': ''}
        if not (200 <= response.status_code < 300):
            result['message'] = f'Request error: {str(response.status_code)} ({responses[response.status_code]})'
            return result
        # to prevent json parsing error if body is empty, but only when lookup path doesn't specified
        if not path and len(response.content) == 0:
            result['success'] = True
            result['message'] = 'Response body is empty'
            return result
        try:
            result['object'] = response.json()
        except ValueError:
            result['object'] = None
            result['message'] = 'JSON decode error'
            return result
        # Yandex API error messages comes with error status codes, so it is hard and unnecessary to decode them,
        # as they duplicates HTTP error codes
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

    def get_disk_info(self):
        """
        Service method is suitable for quick check Yandex token
        :return: {'object': 'contains JSON object or None if response body empty',
                 'success': 'True if requested path found (if specified) and no error codes',
                 'message': 'contains error string if any or empty string'}
        """
        if not self.__initialized:
            self.log('Error: not initialized', True)
            return {'object': None, 'success': False, 'message': f'Error: {type(self).__name__} not initialized'}
        response = requests.get(self.__api_base_url + self.__disk_info_scheme, headers=self.__headers)
        return self.get_response_content(response)

    def create_folder(self, folder_name: str):
        """
        Creates folder at Yandex Disk with specified name
        :param folder_name: name of folder to be created
        :return: {'object': 'contains JSON object or None if response body empty',
                 'success': 'True if requested path found (if specified) and no error codes',
                 'message': 'contains error string if any or empty string'}
        """
        if not self.__initialized:
            self.log('Error: not initialized', True)
            return {'object': None, 'success': False, 'message': f'Error: {type(self).__name__} not initialized'}
        if not folder_name:
            folder_name = '/'
        params = {'path': folder_name}
        response = requests.put(self.__api_base_url + self.__folder_create_scheme,
                                params=params, headers=self.__headers)
        return self.get_response_content(response)

    def upload_local_file(self, file_path: str):
        """
        This method uploads local file to Yandex disk
        Description here: https://yandex.ru/dev/disk/api/reference/upload.html
        :param file_path: local file path
        :return: {'object': 'contains JSON object or None if response body empty',
                 'success': 'True if requested path found (if specified) and no error codes',
                 'message': 'contains error string if any or empty string'}
        """
        if not self.__initialized:
            self.log('Error: not initialized', True)
            return {'object': None, 'success': False, 'message': f'Error: {type(self).__name__} not initialized'}
        if not file_path:
            self.log('Error: file name is empty', True)
            return {'object': None, 'success': False, 'message': f'File name is empty'}
        # first we have to get upload link
        params = {'path': file_path, 'overwrite': True}
        response = requests.get(self.__api_base_url + self.__upload_scheme, params=params, headers=self.__headers)
        upload_link = self.get_response_content(response)
        if not upload_link['success']:
            return upload_link
        # using upload link let's actually start file uploading
        params = {'path': file_path}
        files = {'file': open(file_path, 'rb')}
        response = requests.put(upload_link['object']['href'],
                                params=params, headers=self.__headers, files=files)
        return self.get_response_content(response)

    def list_files(self, limit=20):
        """
        This method show files list at Yandex disk, where limit is for pagination purposes
        Description here: https://yandex.ru/dev/disk/api/reference/all-files.html
        :param limit: pagination limit
        :return: {'object': 'contains JSON object or None if response body empty',
                 'success': 'True if requested path found (if specified) and no error codes',
                 'message': 'contains error string if any or empty string'}
        """
        if not self.__initialized:
            self.log('Error: not initialized', True)
            return {'object': None, 'success': False, 'message': f'Error: {type(self).__name__} not initialized'}
        result = {'object': [], 'success': False, 'message': ''}
        offset = 0
        while True:
            self.log('requesting ' + str(limit) + ' files with offset ' + str(offset) + '...', True)
            params = {'limit': limit, 'fields': 'path, size', 'offset': offset}
            response = requests.get(self.__api_base_url + self.__list_scheme, params=params, headers=self.__headers)
            response = self.get_response_content(response)
            if not response['success']:
                # in case of partial loading 'success' will be True, but message will contain an error
                result['message'] = response['message']
                break
            items = response['object']['items']
            if len(items) < 1:
                result['success'] = response['success']
                break
            result['object'] += [f'{x["path"][5:]} ({self.convert_bytes(int(x["size"] ))})'
                                 for x in items]
            # if returned less files than we requested, means that no more files left
            if len(items) < limit:
                break
            offset += limit
        return result

    def upload_remote_file(self, file_path: str, url: str):
        """
        Uploads files to Yandex disk using url link
        :param file_path: file name with extension on disk where remote file to be stored
        :param url: url string from which file will be taken
        :return: {'object': 'contains JSON object or None if response body empty',
                 'success': 'True if requested path found (if specified) and no error codes',
                 'message': 'contains error string if any or empty string'}
        """
        if not self.__initialized:
            self.log('Error: not initialized', True)
            return {'object': None, 'success': False, 'message': f'Error: {type(self).__name__} not initialized'}
        if not url:
            self.log('Error: url is empty', True)
            return {'object': None, 'success': False, 'message': f'URL is empty'}
        params = {'path': file_path, 'url': url}
        response = requests.post(self.__api_base_url + self.__upload_scheme, params=params, headers=self.__headers)
        return self.get_response_content(response)

    def delete_file(self, file_path: str):
        """
        Delete file from Yandex Disk
        Description here: https://yandex.ru/dev/disk/api/reference/delete.html
        :param file_path: File or folder name at Yandex disk
        :return: {'object': 'contains JSON object or None if response body empty',
                 'success': 'True if requested path found (if specified) and no error codes',
                 'message': 'contains error string if any or empty string'}
        """
        if not self.__initialized:
            self.log('Error: not initialized', True)
            return {'object': None, 'success': False, 'message': f'Error: {type(self).__name__} not initialized'}
        if not file_path:
            self.log('Error: file/folder name is empty.', True)
            return {'object': None, 'success': False, 'message': f'File/folder name is empty'}
        params = {'path': file_path, 'permanently': True, 'force_async': False}
        response = self.get_response_content(requests.delete(self.__api_base_url + self.__file_delete_scheme,
                                                             params=params, headers=self.__headers))
        # if delete operation scheduled (code 202), otherwise will be 204
        if response['success'] and response['object']:
            self.get_operation_status(response['object']['href'])
        return response

    def get_file_info(self, file_path: str):
        """
        Get file info on Yandex disk, suitable for check file existence
        :param file_path: File of folder name on Yandex disk
        :return: {'object': 'contains JSON object or None if response body empty',
                 'success': 'True if requested path found (if specified) and no error codes',
                 'message': 'contains error string if any or empty string'}
        """
        if not self.__initialized:
            self.log('Error: not initialized', True)
            return {'object': None, 'success': False, 'message': f'Error: {type(self).__name__} not initialized'}
        if not file_path:
            file_path = '/'
        params = {'path': file_path}
        response = requests.get(self.__api_base_url + self.__file_info_scheme, params=params, headers=self.__headers)
        return self.get_response_content(response)

    def get_operation_status(self, url: str):
        """
        Waiting operation for checking async actions (copy, move, delete) on disk
        Description here: https://yandex.ru/dev/disk/api/reference/operations.html
        :param url: async operation URL
        :return: None
        """
        if not self.__initialized:
            self.log('Error: not initialized', True)
            return {'object': None, 'success': False, 'message': f'Error: {type(self).__name__} not initialized'}
        if not url:
            self.log('Error: URL is empty.', True)
            return {'object': None, 'success': False, 'message': f'URL is empty'}
        timer = 0.3
        while True:
            time.sleep(timer)
            self.log('Checking ' + url, True)
            response = self.get_response_content(requests.get(url, headers=self.__headers))
            # gives 10 attempts
            if (response['success'] and response['object']['status'] == 'in-progress') and timer < 3:
                # slightly increase wait time
                timer += 0.3
                self.log('Check failed. Next attempt after ' + str(timer) + ' sec', True)
            elif timer >= 3:
                return {'object': None, 'success': False, 'message': 'Timeout reached'}
            elif response['success'] and response['object']['status'] == 'success':
                return {'object': None, 'success': True, 'message': ''}
            elif response['success'] and response['object']['status'] == 'failed':
                return {'object': None, 'success': False, 'message': 'Operation was not successful'}
            else:
                continue
