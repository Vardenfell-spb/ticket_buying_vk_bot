# -*- coding: utf-8 -*-

try:
    from settings import *
except ImportError:
    exit('Скопируйте settings.py.deafault как settings.py, укажите в нем токен и ID группы')
from datetime import *


def find_flight(context):
    if 'date' in context:
        flight_list = []
        flight_table = FLIGHT_TABLE[context['city_from'].lower()][context['city_to'].lower()]
        find_date = datetime.fromisoformat(context['date']).date()
        while len(flight_list) < 5:
            if str(find_date) in flight_table['one']:
                for flight_time in flight_table['one'][str(find_date)]:
                    flight_list.append(str(datetime.fromisoformat(f'{find_date}T{flight_time}')))
            if str(find_date.day) in flight_table['monthly']:
                for flight_time in flight_table['monthly'][str(find_date.day)]:
                    flight_list.append(str(datetime.fromisoformat(f'{find_date}T{flight_time}')))
            if str(find_date.isoweekday()) in flight_table['weekly']:
                for flight_time in flight_table['weekly'][str(find_date.isoweekday())]:
                    flight_list.append(str(datetime.fromisoformat(f'{find_date}T{flight_time}')))
            find_date += timedelta(days=1)
        context['flight_list'] = flight_list[:5]
        context['flight_list_text'] = ''

        for num, choice in enumerate(range(1, 6)):
            context['flight_list_text'] += f'{choice}. {flight_list[num]}\n'

        return True
    else:
        if context['city_from'].lower() in FLIGHT_TABLE:
            if context['city_to'].lower() in FLIGHT_TABLE[context['city_from'].lower()]:
                return True
            else:
                return False
        else:
            return False
