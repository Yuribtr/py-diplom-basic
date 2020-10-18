import time
import pathlib as pl
from VkClient import VkClient
from YaUploader import YaUploader
import json


class ImageSaver:
    def __init__(self, token_vk: str, token_ya: str, uid_vk, debug_mode=False):
        self.__debug_mode = debug_mode
        self.log('\nCreating ImageSaver...', True)
        self.__client = VkClient(token_vk, uid_vk, debug_mode=debug_mode)
        self.__uploader = YaUploader(token_ya, debug_mode=debug_mode)
        self.__types = {'s': 1, 'm': 2, 'x': 3, 'o': 4, 'p': 5, 'q': 6, 'r': 7, 'y': 8, 'z': 9, 'w': 10}
        if self.__client.is_initialized() and self.__uploader.is_initialized():
            self.__status = f'{type(self).__name__} initialised.'
            self.__initialized = True
        else:
            self.__status = f'{type(self).__name__} init failed.'
            self.__initialized = False
        self.log(self.__status, True)

    @staticmethod
    def get_auth_link(app_id: str, scope='status'):
        return VkClient.get_auth_link(app_id=app_id, scope=scope)

    def is_initialized(self):
        return self.__initialized

    def is_client_initialized(self):
        return self.__client.is_initialized()

    def is_uploader_initialized(self):
        return self.__uploader.is_initialized()

    def log(self, message, is_debug_msg=False, sep=' '):
        if self.__debug_mode or (not self.__debug_mode and not is_debug_msg):
            if type(message) in [list, dict, tuple, set]:
                print(*message, sep=sep)
            else:
                print(message, sep=sep)

    def get_images_links(self, vk_id=None, album_id='profile', max_qty=10):
        """
        Gets user photos for specified user and album
        Description here: https://vk.com/dev/photos.get
        :param max_qty: maximum photos to be returned
        :param vk_id: VK user ID, otherwise will be taken user ID during class instance init
        :param album_id: one of album type: wall, profile, saved
        :return: list with sublists ['likes': str, 'img url': str, 'extension': str, 'size type': str] or empty list
        """
        result = []
        if not self.__initialized:
            self.log('Error: not initialized.', True)
            return result
        images = []
        offset = 0
        # adapting count to minimize request's quantity (max returned items count per request is 1000)
        count = max_qty if max_qty <= 1000 else 1000
        self.log(f'\nRequesting max {count} {album_id} images links from VK {album_id}...', True)
        while True:
            user_photos = self.__client.get_user_photos(user_id=vk_id, album_id=album_id, count=count, offset=offset)
            if not user_photos['success']:
                self.log(f'Loading image links failed: {user_photos["message"]}', True)
                break
            items_count = len(user_photos['object']['items'])
            self.log(f'Loaded {items_count} images links from VK', True)
            # if we reached the end
            if items_count == 0:
                break
            images += user_photos['object']['items']
            # if returned less items than requested, suppose that we reached the end
            # or if next iteration will return more items than we requested
            if items_count < count or count + offset >= max_qty:
                break
            offset += count
            # prevent ban from service
            time.sleep(0.3)
        self.log(f'Loading images links finished', True)
        likes_set = set()
        # let's cut images to match exact max_count items
        for item in images[:max_qty]:
            # let's detect images with the maximum resolution, based on dimensions or on type if dimensions is absent
            img_url = ''
            img_url_fallback = ''
            # this needed as fallback if all resolutions will be zero
            max_type = -1
            size_type_letter = ''
            # even if we will be unable to detect max resolution link, we will always take the first one
            max_res = -1
            for size in item['sizes']:
                res = size['height'] * size['width']
                if max_res < res:
                    max_res = res
                    img_url = size['url']
                # fallback only
                size_type = self.__types.get(size['type'], 0)
                if max_type < size_type:
                    max_type = size_type
                    size_type_letter = size['type']
                    # below line needed to prevent additional loop through sizes list in case of fallback
                    img_url_fallback = size['url']
            # fallback if unable to detect resolutions
            # for images older than 2012 year https://vk.com/dev/objects/photo_sizes
            if max_res == 0:
                img_url = img_url_fallback
            # save likes, img url, file extension and size type in sublist
            likes_count = str(item['likes']['count'])
            # let's check if same filename already added and rename it
            if likes_count in likes_set:
                i = 1
                postfix = '_'
                while f'{likes_count}{postfix}{i}' in likes_set:
                    i += 1
                likes_count += f'{postfix}{i}'
            likes_set.add(likes_count)
            result.append([likes_count, pl.Path(img_url).suffix, img_url, size_type_letter])
        return result

    def create_folder(self, folder_name: str):
        """
        Create folder at Yandex Disk
        :param folder_name: folder name to be created
        :return: {'object': 'contains JSON object or None if response body empty',
                 'success': 'True if requested path found (if specified) and no error codes',
                 'message': 'contains error string if any or empty string'}
        """
        if not self.__initialized:
            self.log('Error: not initialized', True)
            return {'object': None, 'success': False, 'message': 'Error: not initialized'}
        result = self.__uploader.create_folder(folder_name)
        if result['success']:
            self.log(f'\nFolder created: {result["object"]["href"]}', True)
        else:
            self.log(f'\nError creating folder. {result["message"]}', True)
        return result

    def upload_remote_files(self, folder: str, files: list, log_file_path: str = None):
        """
        Uploads files to Yandex disk using url link
        :param log_file_path: name of log file that contains images info
        :param folder: file name with extension on disk where remote file to be stored
        :param files: list of remote files as sublists ['likes':int, 'img url':str, 'extension':str, 'size type':str]
        :return: {'object': 'contains JSON object or None if response body empty',
                 'success': 'True if requested path found (if specified) and no error codes',
                 'message': 'contains error string if any or empty string'}
        """
        result = {'object': None, 'success': False, 'message': ''}
        if not self.__initialized:
            self.log('Error: not initialized', True)
            result['message'] = 'Not initialized'
            return result
        self.log(f'\nStart to upload remote files to folder {folder}...', True)
        if not log_file_path:
            log_file_path = 'images_log.json'
        with open(log_file_path, 'w+') as log_file:
            log = []
            for file in files:
                response = self.__uploader.upload_remote_file(folder + '/' + str(file[0]) + file[1], file[2])
                if response['success']:
                    self.log(f'Uploading file accepted: {response["object"]["href"]}', True)
                    log.append({'filename': f'{file[0]}{file[1]}', 'size': f'{file[3]}'})
                else:
                    self.log(f'Uploading file failed: {file[2]} ({response["object"]})', True)
                    result['success'] = False
                    result['message'] = f'Uploading file failed: {file[2]} ({response["object"]})'
                    break
                # prevent ban
                time.sleep(0.3)
            json.dump(log, log_file)
            self.log(f'\nLog file saved to {log_file_path}', True)
        self.log(f'Uploading log file to disk with overwrite...', True)
        response = self.__uploader.upload_local_file(file_path=log_file_path, folder=(folder + '/'))
        if response['success']:
            self.log(f'Log file uploaded to disk', True)
        else:
            self.log(f'Uploading log file error. {response["message"]}', True)
        return result

    def list_disk(self):
        """
        This method show files list at Yandex disk, where limit is for pagination purposes
        Description here: https://yandex.ru/dev/disk/api/reference/all-files.html
        :return: {'object': 'contains JSON object or None if response body empty',
                 'success': 'True if requested path found (if specified) and no error codes',
                 'message': 'contains error string if any or empty string'}
        """
        if not self.__initialized:
            self.log('\nError: not initialized.', True)
            return {'object': None, 'success': False, 'message': 'Error: not initialized'}
        self.log('\nPrinting files list on Yandex disk...', True)
        result = self.__uploader.list_files(50)['object']
        self.log(result, True, sep='\n')
        return result

    def get_user_vk_status(self, user_id=None):
        """
        Get VK user status and return as text or return message string
        :param user_id: ID of VK user, if None - class instance ID will be taken
        :return: string contained status or empty string if error
        """
        if not self.__initialized:
            self.log('\nError: not initialized.', True)
            return ''
        result = self.__client.get_user_status(user_id)
        if result['success']:
            self.log(f'\nVK user status: {result["object"]}', True)
            return result["object"]
        else:
            self.log(f'\nVK user status: {result["message"]}', True)
            return ''

    def delete_file(self, file_path: str):
        """
        Delete file from Yandex disk
        :param file_path: file or folder name
        :return: {'object': 'contains JSON object or None if response body empty',
                 'success': 'True if requested path found (if specified) and no error codes',
                 'message': 'contains error string if any or empty string'}
        """
        if not self.__initialized:
            self.log('\nError: not initialized.', True)
            return {'object': None, 'success': False, 'message': 'Error: not initialized'}
        self.log('\nTry to delete file or folder: ' + file_path, True)
        result = self.__uploader.delete_file(file_path)
        if result['success']:
            self.log(f'File/Folder deleted: {file_path}', True)
        else:
            self.log(f'File/Folder delete error: {result["message"]}', True)
        return result

    def get_file_info(self, file_path: str):
        """
        Get file info on Yandex disk, suitable for check file existence
        :param file_path: File of folder name on Yandex disk
        :return: {'object': 'contains JSON object or None if response body empty',
                 'success': 'True if requested path found (if specified) and no error codes',
                 'message': 'contains error string if any or empty string'}
        """
        if not self.__initialized:
            self.log('\nError: not initialized', True)
            return {'object': None, 'success': False, 'message': 'Error: not initialized'}
        self.log(f'\nChecking if file/folder "{file_path}" is exist...', True)
        result = self.__uploader.get_file_info(file_path)
        if result['success']:
            self.log(f'File/Folder present: {file_path}', True)
        else:
            self.log(f'File/Folder not found: {result["message"]}', True)
        return result
