from pony.orm import Database, Required, Json

from settings import DB_CONFIG

db = Database()
db.bind(**DB_CONFIG)


class UserState(db.Entity):
    """
    Состояние пользователя в сценарии
    """
    peer_id = Required(int, unique=True)
    scenario = Required(str)
    step = Required(str)
    context = Required(Json)


class Registration(db.Entity):
    """
    Данные билета
    """
    peer_id = Required(int, unique=True)
    city_from = Required(str)
    city_to = Required(str)
    flight_date = Required(str)
    seat_place = Required(str)
    comment = Required(str)
    phone_number = Required(str)


db.generate_mapping(create_tables=True)
