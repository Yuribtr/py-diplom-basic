# Домашнее задание к лекции 10.«Работа с классами на примере API VK»

Вам предстоит решить задачу поиска общих друзей у пользователей VK.

Ссылка на документацию [VK/dev](https://vk.com/dev/manuals).
Токен для запросов: 10b2e6b1a90a01875cfaa0d2dd307b7a73a15ceb1acf0c0f2a9e9c586f3b597815652e5c28ed8a1baf13c

## Задача №1
Пользователя нужно описать с помощью класса и реализовать метод поиска общих друзей, используя API VK.

## Задача №2
Поиск общих друзей должен происходить с помощью оператора `&`, т.е. `user1 & user2` должен выдать список
общих друзей пользователей user1 и user2, в этом списке должны быть экземпляры классов.

## Задача №3
Вывод `print(user)` должен выводить ссылку на профиль пользователя в сети VK

## Solution
VKClient can be initiated with token, received by URL formed with static method get_auth_link.
For calling get_auth_link you will need app id for standalone VK app (https://vk.com/apps?act=manage).
  
Initiated VKClient can show name and status of specified VK user, can compare friends lists of specified user with list of other VK users to find mutual friends.    
