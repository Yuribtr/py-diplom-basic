from ImageSaver import ImageSaver


class PrintColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def run_demo():
    token_vk = ''
    app_id_vk = ''
    token_ya = ''

    DEBUG_MODE = True
    vk_user_id = '22'
    folder_name = 'Test'
    max_images_qty = 5
    album = 'profile'  # can be wall, profile, saved
    log_file_path = 'images_log.json'
    padding = 40

    if token_vk == '':
        while app_id_vk == '':
            app_id_vk = input(
                f'{PrintColors.OKGREEN}VK token was not set. Pls input your APP ID to show auth URL: {PrintColors.ENDC}')
        print('Pls use below link in browser to get VK token: ' + ImageSaver.get_auth_link(app_id_vk, 'status,friends'))

    while token_vk == '':
        token_vk = input(f'{PrintColors.OKGREEN}Pls input VK token: {PrintColors.ENDC}')

    while token_ya == '':
        print('Yandex Disk token was not set. You can take it here: https://yandex.ru/dev/disk/poligon/')
        token_ya = input(f'{PrintColors.OKGREEN}Pls input Yandex Disk token: {PrintColors.ENDC}')

    print('Seems that everything is ready. Let\'s go!')
    print('\n' + f'{PrintColors.OKBLUE}Starting{PrintColors.ENDC}'.center(padding, '-'))

    saver = ImageSaver(token_vk=token_vk, token_ya=token_ya, uid_vk=vk_user_id, debug_mode=DEBUG_MODE)
    if not saver.is_initialized():
        print(f'{PrintColors.FAIL}Can\'t continue. I interrupt the demo!{PrintColors.ENDC}')
        return

    print('\n' + f'{PrintColors.OKBLUE}Heating{PrintColors.ENDC}'.center(padding, '-'))
    saver.get_user_vk_status()

    result = saver.get_file_info(folder_name)
    if result['success']:
        choice = ''
        while not (choice in ['y', 'n']):
            choice = input(f'{PrintColors.OKGREEN}\nTarget folder "{result["object"]["path"][6:]}" exists, would you '
                           f'like to delete it (otherwise files will be duplicated)? \nPress "y" to confirm or "n" '
                           f'to skip: {PrintColors.ENDC}')
            if choice == 'y':
                saver.delete_file(folder_name)
                break
            elif choice == 'n':
                break

    result = saver.create_folder(folder_name)
    # Let's continue even if 409 error received (folder exist)
    if result['success'] or result['message'].find('409') >= 0:
        print('\n' + f'{PrintColors.OKBLUE}Downloading{PrintColors.ENDC}'.center(padding, '-'))
        links = saver.get_images_links(album_id=album, max_qty=max_images_qty)
        print('\n' + f'{PrintColors.OKBLUE}Uploading{PrintColors.ENDC}'.center(padding, '-'))
        saver.upload_remote_files(folder_name, links, log_file_path)
        print('\n' + f'{PrintColors.OKBLUE}Checking{PrintColors.ENDC}'.center(padding, '-'))
        saver.list_disk()
    else:
        print(f'{PrintColors.FAIL}Something went wrong: {result["message"]}{PrintColors.ENDC}')

    print('\n' + f'{PrintColors.OKBLUE}Finishing{PrintColors.ENDC}'.center(padding, '-'))
    print('This is the end of demo!')


run_demo()
