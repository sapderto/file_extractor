import configparser
import json
import os
import time

import progress.bar
from telethon.errors.rpcerrorlist import FileReferenceExpiredError
from telethon.sync import TelegramClient
# классы для работы с каналами
# класс для работы с сообщениями
from telethon.tl.functions.messages import GetHistoryRequest


def print_names_of_chats():
    for dialog in client.iter_dialogs():
        print(dialog.title)


def filename_filter(string):
    unacceptable = ['\\', ',', ':', '/', '*', '?', '"', '<', '>', '|', '+', '%']
    return str(''.join((filter(lambda x: x not in unacceptable, string))))


# Считываем учетные данные
config = configparser.ConfigParser()
config.read("config.ini")

# Присваиваем значения внутренним переменным
api_id = config['Telegram']['api_id']
api_hash = config['Telegram']['api_hash']
username = config['Telegram']['username']
download_directory_name = config['Telegram']['directory']
# proxy = (proxy_server, proxy_port, proxy_key)
last_id = 0
client = TelegramClient('session_name', api_id, api_hash)

client.start()


async def dump_all_messages(channel, url, last_current_id):
    """Записывает json-файл с информацией о всех сообщениях канала/чата"""
    offset_msg = 0  # номер записи, с которой начинается считывание
    limit_msg = 30  # максимальное число записей, передаваемых за один раз

    all_messages = []  # список всех сообщений
    total_count_limit = 0  # поменяйте это значение, если вам нужны не все сообщения
    progress_bar_initiated = False
    prev_label = 0
    while True:  # Выгрузка сообщений из ТГ
        history = await client(GetHistoryRequest(
            peer=channel,
            offset_id=offset_msg,
            offset_date=None, add_offset=0,
            limit=limit_msg, max_id=0, min_id=last_current_id,
            hash=0))
        if not history.messages:
            break
        messages = history.messages
        for message in messages:  # Сохранение сообщений в список
            global last_id
            if not progress_bar_initiated:
                bar = progress.bar.Bar("Getting messages", max=int(message.id) - last_id)
                progress_bar_initiated = True
                bar.next()
            else:
                bar.next(n=(prev_label - message.id))
            prev_label = message.id
            all_messages.append(message)
            offset_msg = messages[len(messages) - 1].id
            total_messages = len(all_messages)
            if total_count_limit != 0 and total_messages >= total_count_limit:
                break
    if progress_bar_initiated:
        bar.finish()
    for message in all_messages[::-1]:  # Обход списка сообщений
        message_dict = message.to_dict()
        prev_id = last_id
        last_id = message_dict['id']
        if "media" in message_dict and message_dict["media"] and "document" in message_dict["media"] and \
                "application" in message_dict["media"]["document"]["mime_type"]:  # Фильтр сообщений
            # print(message_dict['id'], message_dict["media"]["document"]['mime_type'],
            #      message_dict["media"]["document"]["attributes"][0]["file_name"])
            filename_string = r"{}\{}\{}".format(download_directory_name, url, filename_filter(
                message_dict["media"]["document"]["attributes"][0]["file_name"]))
            file_size = int(message_dict["media"]["document"]['size'])
            if os.path.exists(filename_string):  # Проверка существования файла
                size_on_disk = os.path.getsize(filename_string)
                print("|--? {} {} already exists".format(message_dict["id"], filename_string), end='')
                if size_on_disk < file_size:  # Проверка размера скачанного файла
                    print(
                        " --X Size on disk = {}, Size from TG = {} ({} M) Redownload...".format(size_on_disk, file_size,
                                                                                                file_size / (
                                                                                                        1024 * 1024)))
                    try:
                        await client.download_media(message,
                                                    file=r"{}\{}\{}".format(download_directory_name, url,
                                                                            filename_filter(
                                                                                message_dict["media"]["document"][
                                                                                    "attributes"][0]["file_name"])))
                    except FileReferenceExpiredError:
                        # Возникает когда моргает интернет скачивание прерывается либо предыдущие файлы скачиваются
                        # слишком долго
                        print('|--E File reference has expired')
                        last_id = prev_id
                        break
                        # continue
                else:
                    print(" --> Sizes OK, Skipped.")
            else:
                print("|--+ {} Downloading new file {}, size {} ({} M)".format(message_dict["id"], filename_string,
                                                                               file_size, file_size / (1024 * 1024)))
                try:
                    await client.download_media(message,
                                                file=r"{}\{}\{}".format(download_directory_name, url, filename_filter(
                                                    message_dict["media"]["document"]["attributes"][0]["file_name"])))
                except FileReferenceExpiredError:
                    print('|--E File reference has expired')
                    last_id = prev_id
                    break
                    # continue


async def main():
    urls = ["BookJava", "BookPython"]  # Ссылки на группы
    for url in urls:
        print(url)
        global last_id
        last_id = 0
        if os.path.exists('channel_config.json') and os.path.getsize('channel_config.json') > 0:  # Конфиг файл групп
            with open('channel_config.json', 'r', encoding='utf8') as in_conf:
                min_id_config = json.load(in_conf)
        else:
            min_id_config = {url: 0}
        if url in min_id_config:
            current_min_id = min_id_config[url]
            last_id = current_min_id
        else:
            min_id_config[url] = 0
            current_min_id = 0
        channel = await client.get_entity(url)
        try:
            await dump_all_messages(channel, url, current_min_id)  # Скачивание файлов
        finally:  # В случае необрабатываемого исключения вылететь и сохранить то место, на котором остановился
            min_id_config[url] = last_id - 1
            print("last processed = {}".format(last_id))
            with open('channel_config.json', 'w', encoding='utf8') as outfile:
                json.dump(min_id_config, outfile, ensure_ascii=False)


while True:
    with client:
        client.loop.run_until_complete(main())
        time.sleep(30)
