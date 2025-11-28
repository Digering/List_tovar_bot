import telebot
import sqlite3

with open("token.txt", "r") as file:
    token = file.readline()

bot = telebot.TeleBot(token)

id_message = 0

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
    cursor.execute('''
        SELECT username
        FROM users
        WHERE user_id = '%s' ''' % message.from_user.id)
    rows = cursor.fetchall()
    conn.commit()
    cursor.close()
    conn.close()

    if rows is None:
        bot.send_message(message.chat.id, "У меня нет ваших данных в моих базах\nВведите свое имя по которому вас будут"
                                          " определять другие пользователи для просмотра ваших пожеланий")
        bot.register_next_step_handler(message, user_name)
    else:
        bot.send_message(message.chat.id,
        f"Здравствуйте {rows[0][0]}\nРад вас снова приветствовать")

def user_name(message):
    name = message.text.split()

    conn = sqlite3.connect('telegram.db')
    cursor = conn.cursor()
    cursor.execute("insert into users (user_id, username) values('%s','%s')" % (message.from_user.id, name[0]))
    conn.commit()
    cursor.close()
    conn.close()
    bot.send_message(message.chat.id, "Пользователь успешно зарегистрирован")
    bot.send_message(message.chat.id, "Для получения возможных команд введите /help")

@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.chat.id, "Список команд:\n/my_list\n/friend_list")

@bot.message_handler(commands=['my_list'])
def my_list(message):
    conn = sqlite3.connect('telegram.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT gifts.url
    FROM gifts
    JOIN users ON gifts.user_id = users.user_id
    WHERE gifts.user_id = '%s'
    ''' % message.from_user.id)
    rows = cursor.fetchall()
    conn.commit()
    cursor.close()
    conn.close()

    if rows is None:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton('Добавить товар', callback_data='add'))
        markup.add(telebot.types.InlineKeyboardButton('Выйти', callback_data='close'))
        bot.send_message(message.chat.id, "На данный момент список подарков пуст", reply_markup=markup)
    else:
        global id_message
        for row in rows:
            bot.send_message(message.chat.id, row)
            id_message += 1
        markup = telebot.types.InlineKeyboardMarkup()
        btm1 = telebot.types.InlineKeyboardButton('Добавить товар', callback_data='add')
        btm2 = telebot.types.InlineKeyboardButton('Убрать товар', callback_data='delete')
        markup.row(btm1, btm2)
        markup.add(telebot.types.InlineKeyboardButton('Выйти', callback_data='close'))
        bot.send_message(message.chat.id, "Список подарков", reply_markup=markup)

@bot.message_handler(commands=['friend_list'])
def friend_list(message):
    conn = sqlite3.connect('telegram.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT username
        FROM users
        WHERE user_id != '%s'
        ''' % message.from_user.id)
    rows = cursor.fetchall()
    conn.commit()
    cursor.close()
    conn.close()
    if not rows:
        bot.send_message(message.chat.id, "У меня есть информация только о вас")
    else:
        markup = telebot.types.InlineKeyboardMarkup()
        for (username,) in rows:
            markup.add(telebot.types.InlineKeyboardButton(text=str(username), callback_data=f'friend_{username}'))
        bot.send_message(message.chat.id, "Выберете чей список вы хотите посмотреть", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    global id_message
    if call.data == 'add':
        for i in range(id_message):
            bot.delete_message(call.message.chat.id, call.message.id - 1 - i)
        id_message = 0
        bot.edit_message_text("Введите ссылку на товар\n Для отмены введите close", call.message.chat.id, call.message.id)
        bot.register_next_step_handler(call.message, add_url)
    elif call.data.startswith('friend_'):
        bot.send_message(call.message.chat.id, call.data)
        friend_name = call.data.split('friend_')[1]

        conn = sqlite3.connect('telegram.db')
        cursor = conn.cursor()
        cursor.execute("""
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
            bot.send_message(call.message.chat.id, f"На данный момент список предпочтений {friend_name} пуст")

        else:
            for row in rows:
                bot.send_message(call.message.chat.id, row)
                id_message += 1
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton('Выйти', callback_data='close'))
            bot.send_message(call.message.chat.id, f"Список предпочтений {friend_name}", reply_markup=markup)

    elif call.data == 'close':
        for i in range(id_message):
            bot.delete_message(call.message.chat.id, call.message.id - 1 - i)
        id_message = 0
        bot.edit_message_text("Хорошо", call.message.chat.id, call.message.id)
    elif call.data == 'delete':
        bot.edit_message_text("Введи номер товара начиная сверху вниз от 1", call.message.chat.id, call.message.id)
        bot.register_next_step_handler(call.message, delete)

def add_url(message):

    url = message.text.split()

    if url[0] == 'close':
        bot.send_message(message.chat.id, "Операция отменена")

    elif message.link_preview_options is None:
        bot.send_message(message.chat.id, "Введите ссылку на конкретный товар")
        bot.register_next_step_handler(message, add_url)

    else:
        conn = sqlite3.connect('telegram.db')
        cursor = conn.cursor()
        cursor.execute("Select gifts.url "
                       "From gifts "
                       "JOIN users ON gifts.user_id = users.user_id "
                       "WHERE gifts.user_id = '%s' AND  gifts.url = '%s'" % (message.from_user.id, url[0]))

        if cursor.fetchone() is None:
            cursor.execute("insert into gifts (user_id, url) values('%s','%s')" % (message.from_user.id, url[0]))
            conn.commit()
            cursor.close()
            conn.close()
            bot.send_message(message.chat.id, "Подарок добавлен")
            bot.send_message(message.chat.id, "Для получения возможных команд введие /help")
        else:
            bot.send_message(message.chat.id, "Операция автоматически прервана т.к. данный товар уже есть в вашем списке")

def delete(message):
    id = message.text.split()
    conn = sqlite3.connect('telegram.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT gifts.id
        FROM gifts
        JOIN users ON gifts.user_id = users.user_id
        WHERE gifts.user_id = '%s'
        ''' % message.from_user.id)
    rows = cursor.fetchall()
    cursor.execute('''
            DELETE FROM gifts
            WHERE id = '%s'
        ''' % rows[int(id[0])-1])
    conn.commit()
    cursor.close()
    conn.close()
    global id_message
    id_message -= 1
    bot.send_message(message.chat.id, "Ссылка на товар удалена")

@bot.message_handler(content_types=['text'])
def text(message):
    bot.send_message(message.chat.id, "Простите, но я не умею поддерживать диалог\n"
                                      "Если вы пишете какую-либо команду то такой команды нет")

bot.polling(none_stop=True)