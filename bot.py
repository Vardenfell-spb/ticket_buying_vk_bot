# -*- coding: utf-8 -*-

import logging
import os
import random
from io import BytesIO

import cv2
import requests
from PIL import Image, ImageDraw, ImageFont, ImageColor
from pony.orm import db_session

import handlers
from models import UserState, Registration

try:
    from settings import *
except ImportError:
    exit('Скопируйте settings.py.deafault как settings.py, укажите в нем токен и ID группы')

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from speech_recognition_engine import vk_speech_recognition

log = logging.getLogger('bot')


def configure_logging():
    file_handler = logging.FileHandler('bot_exc.log', encoding='utf-8')
    stream_handler = logging.StreamHandler()

    stream_handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    file_handler.setFormatter(logging.Formatter(datefmt='%Y.%m.%d %H:%M:%S',
                                                fmt="%(asctime)s %(levelname)s %(message)s"))

    log.addHandler(stream_handler)
    log.addHandler(file_handler)
    log.setLevel(logging.DEBUG)
    stream_handler.setLevel(logging.DEBUG)
    file_handler.setLevel(logging.INFO)


class Bot:
    """
    Echo bot for vk.com
    группа: vk.com/club193211790
    Use python 3.7
    """

    def __init__(self, group_id, token):
        """
        :param group_id: ID группы vk
        :param token: токен группы
        """
        self.group_id = group_id
        self.token = token
        self.vk = vk_api.VkApi(token=token)
        self.long_poller = VkBotLongPoll(self.vk, self.group_id)
        self.api = self.vk.get_api()
        self.peer_id = None
        self.message = []
        self.send = []

    def run(self):
        """
        Запуск бота
        """
        for event in self.long_poller.listen():
            try:
                log.debug('обнаружен ивент: %s', event)
                self.on_event(event)
            except Exception as error:
                log.exception(f'Ошибка при получении ивента: {error}')

    @db_session
    def on_event(self, event):
        """
        Отправляет сообщение назад, если это текст
        Распознает аудиосообщение и возвращает текст

        :param event: VkBotMessageEvent object
        :return: None
        """
        if event.type != VkBotEventType.MESSAGE_NEW:
            log.info('Необрабатываемый тип сообщения %s', event.type)
            return
        self.peer_id = event.object.message['peer_id']
        self.message = []
        if UserState.exists(peer_id=self.peer_id):
            state = UserState.get(peer_id=self.peer_id)
        else:
            state = None
        if event.object['message']['text']:
            self.message.append(event.object['message']['text'])
            log.debug('обнаружено текстовое сообщение: %s', event.object['message']['text'])
        elif event.object.message['attachments']:
            mp3_urls = []
            for attachment in event.object.message['attachments']:
                if attachment['audio_message']:
                    log.debug('обнаружено аудиосообщение')
                    mp3_urls.append(attachment['audio_message']['link_mp3'])
            if mp3_urls:
                self.message = vk_speech_recognition(mp3_urls)
                self.send.append(f'Ваше сообщение: {self.message[0]}')
        self.processing(state)
        self.send_message()

    def processing(self, user_state):
        log.debug('обработка: %s', self.message)

        if user_state:
            # continue scenario
            steps = SCENARIOS[user_state.scenario]['steps']
            step = steps[user_state.step]
            handler = getattr(handlers, step['handler'])

            if self.message[0].lower() in COMMANDS:
                # выполнение обнаруженной команды из списка команд
                user_state.delete()
                if self.message[0].lower() == '/print':
                    self.print_ticket()
                else:
                    self.intents()

            elif handler(text=self.message[0], context=user_state.context):
                # next step
                next_step = steps[step['next_step']]
                if next_step['text']:
                    self.send.append(next_step['text'].format(**user_state.context))
                if step['next_step'] == 'save_ticket':
                    log.debug('сохранение билета в БД')
                    if Registration.exists(peer_id=self.peer_id):
                        old_ticket = Registration.get(peer_id=self.peer_id)
                        old_ticket.delete()
                    Registration(peer_id=self.peer_id,
                                 city_from=user_state.context['city_from'],
                                 city_to=user_state.context['city_to'],
                                 flight_date=user_state.context['flight_date'],
                                 seat_place=user_state.context['seat_place'],
                                 comment=user_state.context['comment'],
                                 phone_number=user_state.context['phone_number'],
                                 )
                if next_step['next_step']:
                    # switch to next step
                    user_state.step = step['next_step']
                    # save ticket

                else:
                    # finish scenario
                    user_state.delete()
            else:
                # retry current step
                if 'failure' in user_state.context:
                    self.send.append(user_state.context['failure'].format(**user_state.context))
                    user_state.delete()
                else:
                    self.send.append(step['failure_text'].format(**user_state.context))
        else:
            if self.message[0].lower() == '/print':
                self.print_ticket()
            else:
                self.intents()
                if not self.send:
                    self.send = [DEFAULT_ANSWER]

    def intents(self):
        for intent in INTENTS:
            if any(token in self.message[0].lower() for token in intent['tokens']):
                # run intent
                if intent['answer']:
                    log.debug('Ответ на вопрос: %s', intent['name'])
                    self.send.append(intent['answer'])
                else:
                    self.start_scenario(intent['scenario'])
                    break

    def start_scenario(self, scenario_name):
        log.debug('Старт сценария: %s', scenario_name)

        scenario = SCENARIOS[scenario_name]
        first_step = scenario['first_step']
        step = scenario['steps'][first_step]
        self.send.append(step['text'])
        UserState(scenario=scenario_name, step=first_step, context={}, peer_id=self.peer_id)

    def send_message(self, messages=None):
        """
        Отправка сообщений
        :param messages: list с сообщениями
        """
        if not messages:
            messages = self.send
        if messages:
            for message in messages:
                log.debug('попытка отправки: %s', message)
                self.api.messages.send(
                    message=message,
                    random_id=random.randint(0, 2 ** 20),
                    peer_id=self.peer_id
                )
        else:
            log.info('Сообщение пустое')
            return
        self.send = []

    def send_image(self, image):
        upload_url = self.api.photos.getMessagesUploadServer()['upload_url']
        upload_data = requests.post(url=upload_url, files={'photo': ('image.jpg', image, 'image/jpeg')}).json()
        image_data = self.api.photos.saveMessagesPhoto(**upload_data)
        owner_id = image_data[0]['owner_id']
        media_id = image_data[0]['id']
        attachment = f'photo{owner_id}_{media_id}'
        self.api.messages.send(
            attachment=attachment,
            random_id=random.randint(0, 2 ** 20),
            peer_id=self.peer_id
        )

    def print_ticket(self):
        if Registration.exists(peer_id=self.peer_id):
            ticket_info = Registration.get(peer_id=self.peer_id)
            user_pic_data = self.api.users.get(user_ids=self.peer_id, fields='photo_100,first_name,last_name')
            first_name = user_pic_data[0]['first_name']
            last_name = user_pic_data[0]['last_name']
            image_data = requests.get(url=user_pic_data[0]['photo_100'])
            image = BytesIO(image_data.content)
            avatar = Image.open(image)
            ticket = ImageMaker(ticket_info, avatar, first_name, last_name)
            ticket.run()
            if ticket.image:
                self.send_image(ticket.ticket())
        else:
            self.send.append('Вы не зарегистрировали билет')


class ImageMaker:
    def __init__(self, ticket_info, avatar, first_name, last_name):
        self.ticket_info = ticket_info
        self.first_name = first_name
        self.last_name = last_name
        self.avatar = avatar
        self.image = None
        self.image_path = 'image/ticket_pattern.jpg'

    def run(self):
        try:
            self.make_image()
        except Exception as error:
            log.exception(f'Ошибка при создании изображения: {error}')

    def ticket(self):
        byte_file = BytesIO()
        self.image.save(byte_file, 'jpeg')
        byte_file.seek(0)
        return byte_file

    def make_image(self):
        self.image = Image.open(self.image_path)
        self.draw_text()
        self.insert_avatar()
        if not os.path.exists('image'):
            os.mkdir('image')

    def show_result(self):
        image = cv2.imread(f'image/{self.ticket_info.peer_id}.jpg')
        cv2.imshow("Ticket", image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def insert_avatar(self):
        pic_offset = (16, 16)
        self.image.paste(self.avatar, pic_offset)

    def draw_text(self):
        log.debug('Печать текста на картинке')
        draw = ImageDraw.Draw(self.image)
        font = ImageFont.truetype('arial.ttf', size=16)
        name = f'{self.first_name} {self.last_name}'
        step = 19
        draw.text((200, 66), name, font=font, fill=ImageColor.colormap['black'])
        draw.text((200, 66 + step), self.ticket_info.city_from, font=font, fill=ImageColor.colormap['black'])
        draw.text((200, 66 + step * 2), self.ticket_info.city_to, font=font, fill=ImageColor.colormap['black'])
        draw.text((200, 66 + step * 3), self.ticket_info.flight_date[:10], font=font, fill=ImageColor.colormap['black'])
        draw.text((200, 66 + step * 4), self.ticket_info.flight_date[11:], font=font, fill=ImageColor.colormap['black'])
        draw.text((200, 66 + step * 5), self.ticket_info.seat_place, font=font, fill=ImageColor.colormap['black'])


if __name__ == '__main__':
    configure_logging()
    bot = Bot(group_id=GROUP_ID, token=TOKEN)
    bot.run()
