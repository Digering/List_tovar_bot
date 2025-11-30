import telebot
import sqlite3
from background import keep_alive
import os

with open("token.txt", "r") as file:
    token = file.readline()

bot = telebot.TeleBot(token)

id_message = 0
text = ''


@bot.message_handler(commands=['start'])
def start(message):
    conn = sqlite3.connect('telegram.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id varchar(100) UNIQUE,
        username varchar(50))''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id varchar(100),
        url varchar(300),
        FOREIGN KEY (user_id) REFERENCES users(user_id))''')
    cursor.execute(
        '''
        SELECT username
        FROM users
        WHERE user_id = ?''', (str(message.chat.id),))
    rows = cursor.fetchall()
    conn.commit()
    cursor.close()
    conn.close()

    bot.delete_message(message.chat.id, message.id)

    if rows == []:
        bot.send_message(
            message.chat.id,
            "У меня нет ваших данных в моих базах\nВведите свое имя по которому вас будут"
            " определять другие пользователи для просмотра ваших пожеланий")
        bot.register_next_step_handler(message, user_name)
    else:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(
            telebot.types.InlineKeyboardButton('Мои товары', callback_data='my_list'))
        markup.add(
            telebot.types.InlineKeyboardButton('Товары других пользователей', callback_data='friend_list'))
        bot.send_message(message.chat.id,f"Здравствуйте {rows[0][0]}\nРад вас снова приветствовать", reply_markup=markup)


def user_name(message):
    name = message.text.split()
    bot.delete_message(message.chat.id, message.id)

    conn = sqlite3.connect('telegram.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (user_id, username) VALUES (?, ?)",
                   (str(message.chat.id), name[0]))
    conn.commit()
    cursor.close()
    conn.close()
    global text
    text = 'Пользователь успешно зарегистрирован\n'
    master(message, text)


def master(message, text, otstup = 1):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton('Мои товары', callback_data='my_list'))
    markup.add(
        telebot.types.InlineKeyboardButton('Товары других пользователей', callback_data='friend_list'))
    try:
        bot.edit_message_text(f"{text}", message.chat.id, message.id - otstup, reply_markup=markup)
    except(telebot.apihelper.ApiTelegramException):
        bot.edit_message_text(f"{text}", message.chat.id, message.id, reply_markup=markup)

def friend_list(message):
    conn = sqlite3.connect('telegram.db')
    cursor = conn.cursor()

    cursor.execute(
        '''
        SELECT username
        FROM users
        WHERE user_id != ?''', (str(message.chat.id),))
    rows = cursor.fetchall()
    print(rows)
    conn.commit()
    cursor.close()
    conn.close()
    if rows == []:
        master(message, "У меня есть информация только о вас")
    else:
        markup = telebot.types.InlineKeyboardMarkup()
        for (username,) in rows:
            markup.add(
                telebot.types.InlineKeyboardButton(
                    text=str(username), callback_data=f'friend_{username}'))
        bot.edit_message_text("Выберете чей список вы хотите посмотреть", message.chat.id, message.id,
                                  reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    global id_message
    if call.data == 'add':
        for i in range(id_message):
            bot.delete_message(call.message.chat.id, call.message.id - 1 - i)
        id_message = 0
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(
            telebot.types.InlineKeyboardButton('Завершить', callback_data='my_list'))
        bot.edit_message_text(
            "Введите ссылку на товар",
            call.message.chat.id, call.message.id, reply_markup=markup)
        bot.register_next_step_handler(call.message, add_url)

    elif call.data == 'my_list':

        conn = sqlite3.connect('telegram.db')
        cursor = conn.cursor()
        cursor.execute(
            '''
        SELECT gifts.url
        FROM gifts
        JOIN users ON gifts.user_id = users.user_id
        WHERE gifts.user_id = ?''', (str(call.message.chat.id),))
        rows = cursor.fetchall()
        print(rows)
        conn.commit()
        cursor.close()
        conn.close()

        if rows == []:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton('Добавить товар',
                                                   callback_data='add'))
            markup.add(
                telebot.types.InlineKeyboardButton('Выйти', callback_data='exit'))

            bot.edit_message_text("На данный момент список подарков пуст", call.message.chat.id, call.message.id,
                                  reply_markup=markup)
        else:
            for row in rows:
                bot.send_message(call.message.chat.id, row)
                id_message += 1
            markup = telebot.types.InlineKeyboardMarkup()
            btm1 = telebot.types.InlineKeyboardButton('Добавить товар',
                                                      callback_data='add')
            btm2 = telebot.types.InlineKeyboardButton('Убрать товар',
                                                      callback_data='delete')
            markup.row(btm1, btm2)
            markup.add(
                telebot.types.InlineKeyboardButton('Выйти', callback_data='exit'))
            bot.delete_message(call.message.chat.id, call.message.id)
            bot.send_message(call.message.chat.id,
                             "Список подарков",
                             reply_markup=markup)

    elif call.data == 'friend_list':
        friend_list(call.message)

    elif call.data.startswith('friend_'):
        bot.delete_message(call.message.chat.id, call.message.id)

        friend_name = call.data.split('friend_')[1]

        conn = sqlite3.connect('telegram.db')
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT gifts.url
            FROM gifts
            JOIN users ON gifts.user_id = users.user_id
            WHERE users.username = ?
        """, (friend_name,))
        rows = cursor.fetchall()
        print(rows)
        conn.commit()
        cursor.close()
        conn.close()
        if rows is None:
            bot.send_message(
                call.message.chat.id,
                f"На данный момент список предпочтений {friend_name} пуст")

        else:
            for row in rows:
                bot.send_message(call.message.chat.id, row)
                id_message += 1
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton('Назад',
                                                   callback_data='close_f'), telebot.types.InlineKeyboardButton('Выйти',
                                                                                                                callback_data='exit'))
            bot.send_message(call.message.chat.id,
                             f"Список предпочтений {friend_name}",
                             reply_markup=markup)

    elif call.data == 'exit':
        for i in range(id_message):
            bot.delete_message(call.message.chat.id, call.message.id - 1 - i)
        id_message = 0
        master(call.message, "Вишлист", 0)
    elif call.data == 'close_f':
        for i in range(id_message):
            bot.delete_message(call.message.chat.id, call.message.id - 1 - i)
        id_message = 0
        friend_list(call.message, True)
    elif call.data == 'delete':
        bot.edit_message_text("Введи номер товара начиная сверху вниз от 1",
                              call.message.chat.id, call.message.id)
        bot.register_next_step_handler(call.message, delete)

def add_url(message):
    url = message.text.split()

    if message.json.get('link_preview_options') is None:

        bot.delete_message(message.chat.id, message.id)

        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(
            telebot.types.InlineKeyboardButton('Завершить', callback_data='my_list'))
        bot.edit_message_text("Введите ссылку на конкретный товар", message.chat.id, message.id - 1, reply_markup=markup)
        bot.register_next_step_handler(message, add_url)

    else:
        conn = sqlite3.connect('telegram.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT gifts.url "
            "FROM gifts "
            "JOIN users ON gifts.user_id = users.user_id "
            "WHERE gifts.user_id = ? AND gifts.url = ?",
            (str(message.chat.id), url[0]))

        bot.delete_message(message.chat.id, message.id)

        if cursor.fetchone() is None:
            cursor.execute("INSERT INTO gifts (user_id, url) VALUES (?, ?)",
                           (str(message.chat.id), url[0]))
            conn.commit()
            cursor.close()
            conn.close()
            master(message, 'Товар добавлен')
        else:

            master(message, 'Операция автоматически прервана т.к. данный товар уже есть в вашем списке')

def delete(message):

    global id_message

    for i in range(id_message):
        bot.delete_message(message.chat.id, message.id - 2 - i)
    id_message = 0

    bot.delete_message(message.chat.id, message.id)

    id = message.text.split()
    conn = sqlite3.connect('telegram.db')
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT gifts.id
        FROM gifts
        JOIN users ON gifts.user_id = users.user_id
        WHERE gifts.user_id = ?''', (str(message.chat.id),))
    rows = cursor.fetchall()
    cursor.execute(
        '''
            DELETE FROM gifts
            WHERE id = ?''', (rows[int(id[0]) - 1][0],))
    conn.commit()
    cursor.close()
    conn.close()
    master(message, 'Ссылка на товар удалена')

@bot.message_handler(content_types=['text'])
def text(message):
    global id_message
    for i in range(id_message):
        bot.delete_message(message.chat.id, message.id - 2 - i)
    id_message = 0
    bot.delete_message(message.chat.id, message.id)
    master(message, "Простите, но я не умею поддерживать диалог\n"
                         "Если вы пишете какую-либо команду то такой команды нет")

keep_alive()
bot.polling(none_stop=True)
