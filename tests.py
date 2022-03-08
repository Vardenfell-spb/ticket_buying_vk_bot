from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch, Mock, ANY

from pony.orm import db_session, rollback
from vk_api.bot_longpoll import VkBotEvent
from freezegun import freeze_time

import settings

from bot import Bot


def isolate_db(test_func):
    def wrapper(*args, **qwargs):
        with db_session:
            test_func(*args, **qwargs)
            rollback()

    return wrapper


@freeze_time('2021-02-01')
class Test1(TestCase):
    RAW_EVENT = {'type': 'message_new',
                 'object': {'message':
                                {'date': 1586706810, 'from_id': 150691, 'id': 66, 'out': 0, 'peer_id': 150691,
                                 'text': 'Test', 'conversation_message_id': 66, 'fwd_messages': [],
                                 'important': False, 'random_id': 0, 'attachments': [], 'is_hidden': False},
                            'client_info': {'button_actions':
                                                ['text', 'vkpay', 'open_app', 'location', 'open_link', 'open_photo'],
                                            'keyboard': True, 'inline_keyboard': True,
                                            'carousel': True, 'lang_id': 3}},
                 'group_id': 193211790,
                 'event_id': 'f647db999effc3508458f4c6f41fc30ef34bb069'}

    def test_run(self):
        count = 5
        events = [{}] * count
        long_poller_mock = Mock(return_value=events)
        long_poller_listen_mock = Mock()
        long_poller_listen_mock.listen = long_poller_mock

        with patch('bot.vk_api.VkApi'):
            with patch('bot.VkBotLongPoll', return_value=long_poller_listen_mock):
                bot = Bot('', '')
                bot.on_event = Mock()
                bot.run()

                bot.on_event.assert_called()
                bot.on_event.assert_any_call({})

                assert bot.on_event.call_count == count

    INPUTS = [
        'Билет',
        'Москва',
        'Владивосток',
        '2021-02-25',
        '6',
        '1',
        '5',
        'Нет',
        'Да',
        '89997775566',
    ]
    EXPECTED_OUTPUTS = [
        settings.SCENARIOS['ticket']['steps']['step1']['text'],
        settings.SCENARIOS['ticket']['steps']['step2']['text'],
        settings.SCENARIOS['ticket']['steps']['step3']['text'],
        settings.SCENARIOS['ticket']['steps']['step4']['text'].format(city_from='Москва', city_to='Владивосток',
                                                                      flight_list_text='1. 2021-02-25 10:00:00'
                                                                                       '\n2. 2021-02-27 12:25:00'
                                                                                       '\n3. 2021-03-01 11:25:00'
                                                                                       '\n4. 2021-03-06 12:25:00'
                                                                                       '\n5. 2021-03-08 11:25:00\n'),
        settings.SCENARIOS['ticket']['steps']['step5']['failure_text'],
        settings.SCENARIOS['ticket']['steps']['step5']['text'],
        settings.SCENARIOS['ticket']['steps']['step6']['text'],
        settings.SCENARIOS['ticket']['steps']['step7']['text'].format(city_from='Москва', city_to='Владивосток',
                                                                      flight_date='2021.02.25 10:00', seat_place='5',
                                                                      comment='—'),
        settings.SCENARIOS['ticket']['steps']['step8']['text'],
        settings.SCENARIOS['ticket']['steps']['save_ticket']['text'].format(phone_number='89997775566'),
    ]

    @isolate_db
    def test_run_ok(self):
        send_mock = Mock()
        api_mock = Mock()
        api_mock.messages.send = send_mock

        events = []
        for input_text in self.INPUTS:
            event = deepcopy(self.RAW_EVENT)
            event['object']['message']['text'] = input_text
            events.append(VkBotEvent(event))
        long_poller_mock = Mock()
        long_poller_mock.listen = Mock(return_value=events)
        with patch('bot.VkBotLongPoll', return_value=long_poller_mock):
            bot = Bot('', '')
            bot.api = api_mock
            bot.run()
        assert send_mock.call_count == len(self.INPUTS)

        real_outputs = []
        for call in send_mock.call_args_list:
            args, kwargs = call
            real_outputs.append(kwargs['message'])
        assert real_outputs == self.EXPECTED_OUTPUTS
