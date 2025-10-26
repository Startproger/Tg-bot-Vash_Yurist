import telebot
import time
import random
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import threading
from tinydb import TinyDB, Query
TOKEN = "7647362919:AAFnN_KNj8S5Du-cAVUzPM9XGT_SYLtxcxQ"# Сюда запишите свой токен
bot = telebot.TeleBot(TOKEN)
ADMIN_TELEGRAM_ID = 2027072686 #Сюда запишите свой ID
tasks = {}
db = TinyDB('review.json')
Consultations = db.table('Consultations')
Review = Query()

# --------------------- Функции для базы данных ---------------------
def save_consultation(user_id, name, history):
    Consultations.insert({
        'user_id': user_id,
        'name': name,
        'history': history,
    })
    return True  # Возвращаем True, если сохранение прошло успешно


def main_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    keyboard.add(KeyboardButton("Запись на консультацию"))
    keyboard.add(KeyboardButton("Оставить отзыв"), KeyboardButton("Просмотреть отзывы"))  # Добавлена кнопка
    return keyboard


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    tasks[user_id] = tasks.get(user_id, [])
    bot.send_message(user_id, "Приветствую, я помощник организации ВАШ ЮРИСТ(Теребенин и партнёры).",
                     reply_markup=main_menu())

#  Хранилище для временных данных о записи
user_data = {}


# --------------------- 1. Запись на консультацию ---------------------
@bot.message_handler(func=lambda message: message.text == "Запись на консультацию")
def start_consultation(message):
    user_id = message.chat.id
    user_data[user_id] = {}  # Инициализация данных пользователя
    bot.send_message(user_id, "Пожалуйста, введите ваше имя:")
    bot.register_next_step_handler(message, get_name)

def get_name(message):
    user_id = message.chat.id
    user_data[user_id]['name'] = message.text
    bot.send_message(user_id, "Теперь, пожалуйста, напишите краткую историю вашей ситуации:")
    bot.register_next_step_handler(message, get_history)

def get_history(message):
    user_id = message.chat.id
    user_data[user_id]['history'] = message.text
    name = user_data[user_id]['name']
    history = user_data[user_id]['history']

    try:
        chat = bot.get_chat(user_id)
        if chat.username:
            user_link = f"//t.me/{chat.username}"
        else:
            user_link = f"tg://user?id={user_id}"
    except Exception as e:
        print(f"Ошибка при получении информации о пользователе: {e}")
        user_link = f"tg://user?id={user_id}" # Fallback, если не удалось получить информацию


    Consultations = f"""
    Новая заявка на консультацию:
    \nИмя: {name}
    \nИстория: {history}
    \nПользователь: {user_link}
    """

    if save_consultation(user_id, name, history):
        bot.send_message(ADMIN_TELEGRAM_ID, Consultations)
        bot.send_message(user_id, "Спасибо! Ваша заявка на консультацию принята. Вам скоро ответят.",
                         reply_markup=main_menu())
    else:
        bot.send_message(user_id, "Произошла ошибка при сохранении вашей заявки. Пожалуйста, попробуйте позже.", reply_markup=main_menu())

    del user_data[user_id]  # Очищаем данные пользователя


#-----------------------функция удаления отзывов
@bot.message_handler(func=lambda message: message.text == "clean")
def ask_for_review(message):
  with open("review.json", "w") as file:
      file.truncate()
  bot.send_message(message.chat.id, "Clean success", reply_markup=main_menu())

@bot.message_handler(func=lambda message: message.text == "Оставить отзыв")
def ask_for_review(message):
    bot.send_message(message.chat.id, "В отзыве укажите ваше имя и сообщение:")
    bot.register_next_step_handler(message, save_review)


def save_review(message):
    review_text = message.text
    db.insert({'user_id': message.chat.id, 'review': review_text})
    bot.send_message(message.chat.id, "Спасибо за ваш отзыв!", reply_markup=main_menu())



# Добавлена функция просмотра отзывов
@bot.message_handler(func=lambda message: message.text == "Просмотреть отзывы")
def view_reviews(message):
    reviews = db.all()
    if reviews:
        # Используем Inline Keyboard для пагинации (пример)
        show_reviews_page(message, 0)  # Начинаем с первой страницы

    else:
        bot.send_message(message.chat.id, "Пока нет ни одного отзыва.", reply_markup=main_menu())

# Функция для отображения отзывов постранично
def show_reviews_page(message, page_num):
    reviews = db.all()
    reviews_per_page = 3  # Количество отзывов на странице
    start_index = page_num * reviews_per_page
    end_index = start_index + reviews_per_page
    page_reviews = reviews[start_index:end_index]

    if not page_reviews:
        bot.send_message(message.chat.id, "Это последняя страница отзывов.", reply_markup=main_menu())
        return

    text = "Отзывы:\n\n"
    for i, review in enumerate(page_reviews):
        text += f"{start_index + i + 1}. {review['review']}\n"

    # Создаем Inline кнопки для навигации
    keyboard = InlineKeyboardMarkup()
    if page_num > 0:
        keyboard.add(InlineKeyboardButton("⬅️ Предыдущая", callback_data=f'prev_{page_num - 1}'))
    if end_index < len(reviews):
        keyboard.add(InlineKeyboardButton("➡️ Следующая", callback_data=f'next_{page_num + 1}'))
    keyboard.add(InlineKeyboardButton("Закрыть", callback_data="close")) # Добавил кнопку "Закрыть"

    bot.send_message(message.chat.id, text, reply_markup=keyboard)

# Обработчик callback запросов от Inline кнопок
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data.startswith('next_'):
        page_num = int(call.data[5:])
        show_reviews_page(call.message, page_num)
    elif call.data.startswith('prev_'):
        page_num = int(call.data[5:])
        show_reviews_page(call.message, page_num)
    elif call.data == "close":
        bot.delete_message(call.message.chat.id, call.message.message_id) # Удаляем сообщение с отзывами

# --------------------- Обработчик для всего остального ---------------------
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.send_message(message.chat.id, "Я не понимаю вас. Пожалуйста, используйте кнопки меню.", reply_markup=main_menu())

while True:
    try:
        print("🟢 Бот запускается...")
        bot.polling(none_stop=True, timeout=60)
    except Exception as e:
        print(f"🔴 Ошибка соединения: {e}")
        print("🔄 Перезапуск через 15 секунд...")
        time.sleep(15)

#Устоновка библиотек в googl collab
#!pip install telebot
#!pip install tinydb
#!pip install Query
#!pip install TinyDB
