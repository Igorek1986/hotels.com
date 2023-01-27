import sqlite3 as sq
from sqlite3 import IntegrityError
from rapid_api import get_hotels
from loader import bot
from typing import Tuple, List
from datetime import datetime
from telebot.types import CallbackQuery


url = 'database/hotel.db'


def create_table():
    with sq.connect(url) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS search_city(
                    id INTEGER PRIMARY KEY,
                    user_input TEXT UNIQUE NOT NULL,
                    need_update INTEGER DEFAULT 0
                    )
                    """)

        cur.execute("""CREATE TABLE IF NOT EXISTS region_names(
                        id INTEGER NOT NULL PRIMARY KEY,
                        city TEXT NOT NULL,
                        country TEXT NOT NULL,
                        city_id TEXT UNIQUE NOT NULL,
                        search_city_id INTEGER NOT NULL,
                        FOREIGN KEY (search_city_id) REFERENCES search_city(id) 
                        ON DELETE NO ACTION ON UPDATE NO ACTION
                        )
                        """)

        cur.execute("""CREATE TABLE IF NOT EXISTS hotels(
                        id INTEGER NOT NULL PRIMARY KEY,
                        hotel_id TEXT UNIQUE NOT NULL,
                        name TEXT NOT NULL,
                        address TEXT,
                        amount INTEGER NOT NULL,
                        distance INTEGER NOT NULL,
                        hotel_link TEXT NOT NULL,
                        hotel_image_link TEXT NOT NULL,
                        region_names_id INTEGER NOT NULL,
                        date_update DATETIME,
                        FOREIGN KEY (region_names_id) REFERENCES region_names(id) 
                        ON DELETE NO ACTION ON UPDATE NO ACTION
                        )
                        """)

        cur.execute("""CREATE TABLE IF NOT EXISTS foto(
                        id INTEGER NOT NULL PRIMARY KEY, 
                        foto_url TEXT NOT NULL,
                        foto_hotel_id INTEGER NOT NULL,
                        FOREIGN KEY (foto_hotel_id) REFERENCES hotels(id) 
                        ON DELETE NO ACTION ON UPDATE NO ACTION
                        )
                        """)

        cur.execute("""CREATE TABLE IF NOT EXISTS history(
                        id INTEGER NOT NULL PRIMARY KEY,
                        user_id TEXT NOT NULL, 
                        command TEXT NOT NULL,
                        date_time TEXT NOT NULL,
                        find_hotel_id TEXT INTEGER NOT NULL,
                        amount_history INTEGER NOT NULL,
                        count_nights INTEGER NOT NULL,
                        count_foto INTEGER NOT NULL,
                        check_in TEXT NOT NULL,
                        check_out TEXT NOT NULL,
                        FOREIGN KEY (find_hotel_id) REFERENCES hotels(id) 
                        FOREIGN KEY (from_user_id) REFERENCES users(id) 
                        ON DELETE NO ACTION ON UPDATE NO ACTION
                        )
                        """)

        cur.execute("""CREATE TABLE IF NOT EXISTS users(
                        id INTEGER NOT NULL PRIMARY KEY,
                        from_user_id TEXT NOT NULL 
                        )
                        """)


def write_search_city(text: str) -> None:

    """Функция записывает город, который ищет пользователь."""

    with sq.connect(url) as conn:
        cur = conn.cursor()
        try:
            cur.execute("""INSERT INTO search_city(
                        user_input) VALUES (?)
                        """, (text, ))
        except IntegrityError:
            pass


def _get_id_table(table_name: str, column: str, text: str) -> str:

    """Функция получает id номер в таблице.
    :return id"""

    with sq.connect(url) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM " + table_name + " WHERE " + column + " = ?", (text, ))
        result = cur.fetchone()
        if result is not None:
            search_id_db = result[0]
        else:
            search_id_db = '0'
        return search_id_db


def get_address_hotel(hotel_id: str) -> [str, None]:

    """Функция получает адрес из базы данных."""

    with sq.connect(url) as conn:
        cur = conn.cursor()
        cur.execute("""SELECT address FROM hotels WHERE hotel_id = ?""", (hotel_id, ))
        address = str(cur.fetchone()[0])
        return address


def write_region_names(text, response_text) -> None:

    """Функция записывает найденный город, страну, уникальный номер."""

    search_city_id = _get_id_table('search_city', 'user_input', text)
    with sq.connect(url) as conn:
        cur = conn.cursor()
        for elem in response_text:
            try:
                cur.execute("""INSERT INTO region_names(city, country, city_id, search_city_id) 
                VALUES (?, ?, ?, ?)
                """, (elem[0], elem[1], elem[2], search_city_id))
            except IntegrityError:
                pass


def write_hotels(city_id: str, user_input: Tuple[str, str]) -> None:

    """Функция записывает найденную информацию об отелях."""

    region_names_id = _get_id_table('region_names', 'city_id', city_id)
    response_text = get_hotels(city_id, user_input)
    date_update = datetime.today().date()
    with sq.connect(url) as conn:
        cur = conn.cursor()
        for elem in response_text:
            cur.execute("""INSERT INTO hotels(hotel_id, name, amount, distance,
            hotel_link, hotel_image_link, region_names_id, date_update) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (hotel_id) DO UPDATE SET (amount, date_update) = (?, ?)""",
                        (elem[0], elem[1], elem[2], elem[3], elem[4], elem[5], region_names_id, date_update,
                         elem[2], date_update))


def write_user(call: CallbackQuery) -> None:

    """Функция записывает user_id в базу данных."""

    from_user_id = _get_id_table('users', 'from_user_id', str(call.from_user.id))
    if not from_user_id:
        with sq.connect(url) as conn:
            cur = conn.cursor()
            cur.execute("""INSERT INTO users(from_user_id) VALUES (?) """, (call.from_user.id, ))


def write_history(call: CallbackQuery, hotel_id: List[str]) -> None:

    """Функция записывает в базу данных найденные отели пользователем."""

    from_user_id = _get_id_table('users', 'from_user_id', str(call.from_user.id))

    with bot.retrieve_data(user_id=call.from_user.id, chat_id=call.message.chat.id) as data:

        command = data.get('command')
        date_command = data.get('date_command')
        count_nights = data.get('count_nights')
        check_in = data.get('check_in')
        check_out = data.get('check_out')
        count_foto = data.get('count_foto')

    with sq.connect(url) as conn:
        cur = conn.cursor()
        for elem in hotel_id:
            hotel_id = _get_id_table('hotels', 'hotel_id', elem)
            amount = cost_hotel_night(elem)
            cur.execute("""INSERT INTO history(user_id, command, date_time, find_hotel_id, amount_history, count_nights, 
            count_foto, check_in, check_out)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (from_user_id, command, date_command, hotel_id, amount, count_nights, count_foto, check_in, check_out))


def write_hotels_address_photo(response_lst: List[Tuple[str, str, List[str]]]) -> None:

    """Функция записывает адрес и фотографии в базу данных."""

    with sq.connect(url) as conn:
        cur = conn.cursor()

        for elem in response_lst:

            hotels_id = _get_id_table('hotels', 'hotel_id', elem[0])
            cur.execute("""UPDATE hotels SET address = ? WHERE hotel_id = ?""", (elem[1], elem[0], ))
            for photo in elem[2]:
                cur.execute("""INSERT INTO foto(foto_url, foto_hotel_id) 
                VALUES (?, ?) """, (photo, hotels_id))


def cost_hotel_night(hotel_id: str) -> [int, float]:

    """Функция возвращает стоимость проживания за сутки."""

    with sq.connect(url) as conn:
        cur = conn.cursor()
        cur.execute("""SELECT amount FROM hotels WHERE hotel_id = ?""", (hotel_id, ))
        cost = cur.fetchone()[0]
        return cost


def select_first_response(text: str) -> List[Tuple[str, str, str]]:

    """Функция возвращает найденный город, страну и id города."""

    with sq.connect(url) as conn:
        cur = conn.cursor()
        cur.execute("""SELECT city, country, city_id
                     FROM region_names
                     JOIN search_city ON region_names.search_city_id = search_city.id
                     WHERE user_input = ?""", (text, ))
        data = cur.fetchall()

    return data


def select_hotels_db(city_id: str, user_input: Tuple[str, str]) \
        -> List[Tuple[str, str, str, float | int, str, str, int]]:

    """Функция выбирает данные об отеле из базы данных, если дата записи в базе данных раньше текущей, то данные в базе
    обновляются."""

    region_names_id = _get_id_table('region_names', 'city_id', city_id)
    date_update = get_date_update(region_names_id)
    date_now = datetime.today().date()

    if date_now > date_update:
        with sq.connect(url) as conn:
            cur = conn.cursor()
            cur.execute("""UPDATE hotels SET amount = 0, date_update = ? WHERE region_names_id = ?""",
                        (date_now, region_names_id))
        write_hotels(city_id, user_input)

    with sq.connect(url) as conn:
        cur = conn.cursor()
        cur.execute("""SELECT hotel_id, name, address, amount, hotel_link, hotel_image_link, region_names_id
                    FROM hotels
                    JOIN region_names ON hotels.region_names_id = region_names.id
                    WHERE region_names_id = ?""", (region_names_id, ))
        data = cur.fetchall()

    return data


def get_date_update(region_id: str) -> datetime.date:

    """Функция получает дату добавления данных в базу данных hotels."""

    with sq.connect(url) as conn:
        cur = conn.cursor()
        cur.execute("""SELECT date_update FROM hotels
                    WHERE region_names_id = ?""", (region_id, ))

        data = datetime.strptime(cur.fetchone()[0], '%Y-%m-%d').date()

    return data


def need_update(num_bool: str, text: str):

    """Функция устанавливает необходимость обновления списка городов."""

    city_id = _get_id_table('search_city', 'user_input', text)
    with sq.connect(url) as conn:
        cur = conn.cursor()
        cur.execute("""UPDATE search_city SET need_update = ? WHERE id = ?""", (num_bool, city_id))


def check_update(text) -> True | False:

    """Функция проверяет необходимость обновления списка городов."""

    city_id = _get_id_table('search_city', 'user_input', text)
    with sq.connect(url) as conn:
        cur = conn.cursor()
        cur.execute("""SELECT CASE WHEN EXISTS(SELECT need_update FROM search_city WHERE id = ?)
    THEN False ELSE True END""", (city_id,))
        data = bool((cur.fetchone())[0])
    return data


def check_hotel_in_database(region_names_id: str) -> True | False:

    """Функция проверяет есть ли отель в базе данных."""

    with sq.connect(url) as conn:
        cur = conn.cursor()

        cur.execute("""SELECT CASE WHEN EXISTS(SELECT hotel_id FROM hotels WHERE region_names_id = ?) 
        THEN True ELSE False END""", (region_names_id,))

        data = bool(cur.fetchone()[0])
        return data


def get_hotels_id(data: Tuple[str, int, int, int, str], user_input: Tuple[str, str]) -> List[str]:

    """Функция получает список hotel_id"""

    command, count_hotels, min_price, max_price, city_id = data

    region_names_id = _get_id_table('region_names', 'city_id', city_id)
    if check_hotel_in_database(region_names_id):
        select_hotels_db(city_id, user_input)
    else:
        write_hotels(city_id, user_input)

    with sq.connect(url) as conn:
        cur = conn.cursor()
        match command:
            case "/lowprice":
                cur.execute("""SELECT hotel_id FROM hotels WHERE amount != 0 AND region_names_id = ? 
                ORDER BY amount LIMIT ?""", (region_names_id, count_hotels))
            case "/highprice":
                cur.execute("""SELECT hotel_id FROM hotels WHERE amount != 0 AND region_names_id = ? 
                ORDER BY amount DESC LIMIT ?""", (region_names_id, count_hotels))
            case "/bestdeal":
                cur.execute("""SELECT hotel_id FROM hotels WHERE amount BETWEEN ? AND ? AND region_names_id = ?
                 ORDER BY distance LIMIT ?""", (min_price, max_price, region_names_id, count_hotels))

        data = cur.fetchall()
        data = [elem[0] for elem in data]
    return data


def result_hotels(hotels_id: List[str], count_photo: int, history: bool = False, history_id='')\
        -> List[list[Tuple[str, str, float | int, float | int, str, str], List[str]]]:
    data = []
    with sq.connect(url) as conn:
        cur = conn.cursor()
        for elem in hotels_id:

            if not history:
                cur.execute("""SELECT name, address, distance, ROUND(amount, 2), hotel_link, hotel_image_link 
                            FROM hotels 
                            WHERE hotel_id = ?""", (elem,))
            else:
                cur.execute("""SELECT name, address, distance, ROUND(amount_history, 2), hotel_link, hotel_image_link,
                                            command, date_time, count_nights, check_in, check_out 
                                            FROM history JOIN hotels ON find_hotel_id = hotels.id
                                            WHERE hotel_id = ? AND history.id = ?""", (elem, history_id))
            result_hotels_lst = [hotel_base_info for hotel_base_info in cur.fetchall()]
            cur.execute("""SELECT foto_url 
                        FROM hotels
                        JOIN foto ON hotels.id = foto_hotel_id 
                        WHERE hotel_id = ?
                        LIMIT ?""", (elem, count_photo))
            result_hotels_lst.append([url_image[0] for url_image in cur.fetchall()])
            data.append(result_hotels_lst)

    return data


def get_history(from_user_id: str):

    """Функция получает историю поиска отелей пользователя."""

    user_id = _get_id_table('users', 'from_user_id', from_user_id)
    with sq.connect(url) as conn:
        cur = conn.cursor()
        cur.execute("""SELECT hotel_id, count_foto, id FROM (SELECT * FROM history 
        JOIN hotels ON find_hotel_id = hotels.id WHERE user_id = ? 
        ORDER BY id DESC LIMIT 10) ORDER BY id""", (user_id, ))
        result_hotels_lst = [[[hotel_base_info[0]], hotel_base_info[1], hotel_base_info[2]]
                             for hotel_base_info in cur.fetchall()]
        return result_hotels_lst
