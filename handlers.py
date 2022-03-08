# -*- coding: utf-8 -*-
'''
Hadler - функция, которая принимает на вход text (текст входящего сообщения) и context (dict), а возвращает bool:
True - если шаг пройден, False - если данные введены неправильно
'''
import re

from pony.orm import db_session

from manager import *
from models import Registration

re_name = re.compile(r'^[\w\-\s]{2,40}$')
re_city = re.compile(r'^[a-zA-Zа-яА-ЯёЁ -]{2,40}$')
re_date = re.compile(r'\d{4}-\d{1,2}-\d{1,2}')
re_email = re.compile(r'\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b')
re_seat_place = re.compile(r'[1-5]')
re_phone = re.compile(r'\d{11}')


def handle_name(text, context):
    match = re.match(re_name, text)
    if match:
        context['name'] = text
        return True
    else:
        return False


def handle_email(text, context):
    matches = re.findall(re_email, text)
    if len(matches) > 0:
        context['email'] = matches[0]
        return True
    else:
        return False


def handle_city_from(text, context):
    matches = re.findall(re_city, text)
    if len(matches) > 0:
        context['city_from'] = matches[0]
        return True
    else:
        return False


def handle_city_to(text, context):
    matches = re.findall(re_city, text)
    if len(matches) > 0:
        context['city_to'] = matches[0]
        if not find_flight(context):
            context['failure'] = 'Между {city_from} и {city_to} нет рейсов'
            return False
        else:
            return True
    else:
        return False


def handle_date(text, context):
    matches = re.findall(re_date, text)
    if len(matches) > 0:
        date_str = matches[0]
        try:
            dt_date = datetime.fromisoformat(date_str).date()
        except Exception as exc:
            context['failure'] = f'Ошибка в дате: {exc}'
            return False
        else:
            today_date = datetime.today()
            context['date'] = date_str
            if dt_date >= today_date.date():
                find_flight(context)
                return True
            else:
                context['failure'] = 'Билеты нельзя купить в прошлом'
                return False
    else:
        return False


def handle_flight_num(text, context):
    matches = re.findall(re_seat_place, text)
    if len(matches) > 0:
        context['flight_num'] = matches[0]
        flight_date = datetime.fromisoformat(context['flight_list'][int(context['flight_num']) - 1])
        context['flight_date'] = flight_date.strftime(format='%Y.%m.%d %H:%M')

        return True
    else:
        return False


def handle_seat_place(text, context):
    matches = re.findall(re_seat_place, text)
    if len(matches) > 0:
        context['seat_place'] = matches[0]
        return True
    else:
        return False


def handle_comment(text, context):
    if text.lower() == 'нет':
        context['comment'] = '—'
    else:
        context['comment'] = str(text)
    return True


def handle_confirm(text, context):
    if text.lower() == 'нет':
        context['failure'] = 'Отмена заказа, попробуйте ещё раз'
    elif text.lower() == 'да':
        return True
    else:
        return False


def handle_phone(text, context):
    matches = re.findall(re_phone, text)
    if len(matches) > 0:
        context['phone_number'] = matches[0]
        return True
    else:
        return False
