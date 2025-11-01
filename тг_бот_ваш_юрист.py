import telebot
import time
import requests
import os
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from tinydb import TinyDB, Query
from datetime import datetime, timedelta

TOKEN = ""

bot = telebot.TeleBot(TOKEN)
ADMIN_TELEGRAM_ID =

# Функция для получения московского времени (UTC+3)
def get_moscow_time():
    return datetime.now() + timedelta(hours=3)

def format_moscow_time():
    return get_moscow_time().strftime("%d.%m.%Y %H:%M")

try:
    db = TinyDB('review.json')
    Consultations = db.table('Consultations')
    Supports = db.table('Supports')
    Reviews = db.table('Reviews')
    Review = Query()
    print("✅ База данных загружена")
except Exception as e:
    print(f"❌ Ошибка базы данных: {e}")
    exit(1)

user_data = {}
user_review_messages = {}
user_files = {}
user_waiting_for_files = {}
admin_history_messages = {}
admin_current_page_files = {}

def save_consultation(user_id, name, history, files=None):
    try:
        return Consultations.insert({
            'user_id': user_id,
            'name': name,
            'history': history,
            'files': files or [],
            'status': 'new',
            'timestamp': time.time(),
            'date': format_moscow_time()
        })
    except Exception as e:
        print(f"❌ Ошибка сохранения консультации: {e}")
        return None

def save_supports(user_id, name, history, files=None):
    try:
        return Supports.insert({
            'user_id': user_id,
            'name': name,
            'history': history,
            'files': files or [],
            'status': 'new',
            'timestamp': time.time(),
            'date': format_moscow_time()
        })
    except Exception as e:
        print(f"❌ Ошибка сохранения сопровождения: {e}")
        return None

def save_review(user_id, review_text, rating, user_history=''):
    try:
        return Reviews.insert({
            'user_id': user_id,
            'review': review_text,
            'rating': rating,
            'has_history': bool(user_history),
            'type': 'after_completion' if user_history else 'voluntary',
            'timestamp': time.time(),
            'date': format_moscow_time()
        })
    except Exception as e:
        print(f"❌ Ошибка сохранения отзыва: {e}")
        return None

def get_user_history(user_id):
    try:
        consultations = Consultations.search((Review.user_id == user_id) & (Review.status == 'completed'))
        supports = Supports.search((Review.user_id == user_id) & (Review.status == 'completed'))

        history_text = ""

        if consultations:
            for consult in consultations:
                history_text += f"{consult['history']}\n"

        if supports:
            for support in supports:
                history_text += f"{support['history']}\n"

        return history_text.strip()
    except Exception as e:
        print(f"❌ Ошибка получения истории: {e}")
        return ""

def get_average_rating():
    try:
        reviews = Reviews.all()
        if not reviews:
            return 0, 0

        total_rating = sum(review.get('rating', 0) for review in reviews)
        average = total_rating / len(reviews)
        return round(average, 1), len(reviews)
    except Exception as e:
        print(f"❌ Ошибка расчета рейтинга: {e}")
        return 0, 0

def format_rating_stars(rating):
    try:
        stars = ""
        full_stars = int(rating)
        half_star = rating - full_stars >= 0.5

        for i in range(5):
            if i < full_stars:
                stars += "⭐"
            elif i == full_stars and half_star:
                stars += "✨"
            else:
                stars += "☆"
        return stars
    except:
        return "⭐☆☆☆☆"

def is_admin(user_id):
    return user_id == ADMIN_TELEGRAM_ID

def admin_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("📋 История"),
        KeyboardButton("⭐ Отзывы")
    )
    keyboard.add(
        KeyboardButton("🗑️ Очистка данных")
    )
    return keyboard

def user_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("👨‍💼 Запись на консультацию"),
        KeyboardButton("🏃 Сопровождение в суде")
    )
    keyboard.add(
        KeyboardButton("📝 Оставить отзыв"),
        KeyboardButton("⭐ Просмотреть отзывы")
    )
    return keyboard

@bot.message_handler(commands=['start'])
def start(message):
    try:
        user_id = message.from_user.id

        if is_admin(user_id):
            welcome_text = "👑 Добро пожаловать, Администратор!\n\nДоступные команды:"
            bot.send_message(message.chat.id, welcome_text, reply_markup=admin_menu())
        else:
            welcome_text = "👋 Приветствую вас!\n\nЯ помощник организации ВАШ ЮРИСТ (Теребенин и партнёры).\nЧем могу помочь?"
            bot.send_message(message.chat.id, welcome_text, reply_markup=user_menu())

    except Exception as e:
        print(f"❌ Ошибка команды /start: {e}")

#---------------------команда История для администратора
@bot.message_handler(func=lambda message: message.text == "📋 История")
def show_admin_history(message):
    try:
        if not is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "⛔ Эта команда доступна только администратору.")
            return

        show_history_page(message, 0)

    except Exception as e:
        print(f"❌ Ошибка команды история: {e}")
        bot.send_message(message.chat.id, "⚠️ Произошла ошибка при загрузке истории заявок.")

def show_history_page(message, page_num):
    try:
        user_id = message.chat.id

        if user_id in admin_history_messages:
            try:
                bot.delete_message(user_id, admin_history_messages[user_id])
            except:
                pass

        consultations = Consultations.all()
        supports = Supports.all()

        all_applications = []

        for consult in consultations:
            consult['type'] = 'consultation'
            consult['type_emoji'] = '👨‍💼'
            consult['type_text'] = 'КОНСУЛЬТАЦИЯ'
            all_applications.append(consult)

        for support in supports:
            support['type'] = 'support'
            support['type_emoji'] = '🏃'
            support['type_text'] = 'СОПРОВОЖДЕНИЕ'
            all_applications.append(support)

        all_applications.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

        if not all_applications:
            bot.send_message(user_id, "История заявок пуста.", reply_markup=admin_menu())
            return

        applications_per_page = 3
        start_index = page_num * applications_per_page
        end_index = start_index + applications_per_page
        page_applications = all_applications[start_index:end_index]

        if not page_applications:
            bot.send_message(user_id, "📄 Это последняя страница истории.", reply_markup=admin_menu())
            return

        admin_current_page_files[user_id] = []

        text = f"📋 ИСТОРИЯ ЗАЯВОК\n\n"
        text += f"Всего заявок: {len(all_applications)}\n"
        text += f"Консультаций: {len(consultations)}\n"
        text += f"Сопровождений: {len(supports)}\n"
        text += "────────────────────\n"

        for i, app in enumerate(page_applications, start=start_index + 1):
            try:
                chat = bot.get_chat(app['user_id'])
                user_link = f"//t.me/{chat.username}" if chat.username else f"tg://user?id={app['user_id']}"
            except Exception as e:
                user_link = f"tg://user?id={app['user_id']}"

            status_emoji = "✅" if app.get('status') == 'completed' else "🆕"
            status_text = "ЗАВЕРШЕНО" if app.get('status') == 'completed' else "НОВАЯ"

            text += f"{app['type_emoji']} {app['type_text']} {status_emoji}\n"
            text += f"Статус: {status_text}\n"
            text += f"Дата: {app.get('date', 'Не указана')}\n"
            text += f"Имя: {app['name']}\n"
            text += f"История: {app['history'][:100]}{'...' if len(app['history']) > 100 else ''}\n"
            text += f"Файлов: {len(app.get('files', []))}\n"
            text += f"Клиент: {user_link}\n"
            text += "────────────────────\n"

            if app.get('files'):
                for file_data in app['files']:
                    file_data_with_meta = file_data.copy()
                    file_data_with_meta['application_type'] = app['type']
                    file_data_with_meta['application_id'] = app.doc_id
                    file_data_with_meta['user_name'] = app['name']
                    file_data_with_meta['date'] = app.get('date', 'Не указана')
                    admin_current_page_files[user_id].append(file_data_with_meta)

        keyboard = InlineKeyboardMarkup()
        row_buttons = []

        if page_num > 0:
            row_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f'admin_prev_{page_num - 1}'))

        if end_index < len(all_applications):
            row_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f'admin_next_{page_num + 1}'))

        if row_buttons:
            keyboard.add(*row_buttons)

        total_files_current_page = len(admin_current_page_files.get(user_id, []))
        if total_files_current_page > 0:
            keyboard.add(InlineKeyboardButton(f"📥 Скачать файлы ({total_files_current_page})", callback_data="admin_download_current_page_files"))

        keyboard.add(InlineKeyboardButton("❌ Закрыть", callback_data="admin_close_history"))

        sent_message = bot.send_message(
            user_id,
            text,
            reply_markup=keyboard
        )
        admin_history_messages[user_id] = sent_message.message_id

    except Exception as e:
        print(f"❌ Ошибка показа истории: {e}")
        bot.send_message(message.chat.id, "⚠️ Ошибка при загрузке истории заявок.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def handle_admin_callbacks(call):
    try:
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "⛔ Доступ запрещен")
            return

        if call.data.startswith('admin_next_'):
            page_num = int(call.data.split('_')[2])
            show_history_page(call.message, page_num)
            bot.answer_callback_query(call.id)

        elif call.data.startswith('admin_prev_'):
            page_num = int(call.data.split('_')[2])
            show_history_page(call.message, page_num)
            bot.answer_callback_query(call.id)

        elif call.data == "admin_download_current_page_files":
            download_current_page_files(call)

        elif call.data == "admin_close_history":
            user_id = call.message.chat.id
            try:
                bot.delete_message(user_id, call.message.message_id)
                if user_id in admin_history_messages:
                    del admin_history_messages[user_id]
                if user_id in admin_current_page_files:
                    del admin_current_page_files[user_id]
            except:
                pass
            bot.answer_callback_query(call.id, "История закрыта")

    except Exception as e:
        print(f"❌ Ошибка обработки админ callback: {e}")
        bot.answer_callback_query(call.id, "⚠️ Ошибка")

def download_current_page_files(call):
    try:
        user_id = call.message.chat.id

        if user_id not in admin_current_page_files or not admin_current_page_files[user_id]:
            bot.answer_callback_query(call.id, "На этой странице нет файлов")
            return

        files_to_download = admin_current_page_files[user_id]

        bot.answer_callback_query(call.id, f"📥 Начинаем загрузку {len(files_to_download)} файлов...")

        bot.send_message(user_id, f"📥 Загрузка файлов с текущей страницы\n\nВсего файлов: {len(files_to_download)}")

        successful_downloads = 0

        for i, file_data in enumerate(files_to_download, 1):
            try:
                app_type = "Консультация" if file_data['application_type'] == 'consultation' else "Сопровождение"
                caption = f"📄 Файл {i}/{len(files_to_download)}\n"
                caption += f"Тип: {app_type}\n"
                caption += f"Клиент: {file_data['user_name']}\n"
                caption += f"Дата: {file_data['date']}"

                if file_data['file_type'] == 'document':
                    bot.send_document(user_id, file_data['file_id'], caption=caption)
                elif file_data['file_type'] == 'photo':
                    bot.send_photo(user_id, file_data['file_id'], caption=caption)
                elif file_data['file_type'] == 'video':
                    bot.send_video(user_id, file_data['file_id'], caption=caption)

                successful_downloads += 1

                if i % 5 == 0:
                    time.sleep(1)

            except Exception as e:
                error_msg = f"❌ Ошибка при отправке файла {i}: {str(e)}"
                if len(error_msg) > 200:
                    error_msg = error_msg[:200] + "..."
                bot.send_message(user_id, error_msg)

        bot.send_message(user_id, f"✅ Загрузка завершена!\n\nУспешно отправлено: {successful_downloads}/{len(files_to_download)} файлов")

    except Exception as e:
        print(f"❌ Ошибка загрузки файлов текущей страницы: {e}")
        bot.answer_callback_query(call.id, "⚠️ Ошибка загрузки файлов")

#---------------------просмотр отзывов для администратора
@bot.message_handler(func=lambda message: message.text == "⭐ Отзывы")
def show_admin_reviews(message):
    try:
        if not is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "⛔ Эта команда доступна только администратору.")
            return

        show_reviews_page(message, 0)

    except Exception as e:
        print(f"❌ Ошибка команды отзывы: {e}")
        bot.send_message(message.chat.id, "⚠️ Произошла ошибка при загрузке отзывов.", reply_markup=admin_menu())

#---------------------просмотр отзывов для клиентов
@bot.message_handler(func=lambda message: message.text == "⭐ Просмотреть отзывы")
def show_user_reviews(message):
    try:
        if is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "⛔ Администратор не может просматривать отзывы через это меню.", reply_markup=admin_menu())
            return

        show_reviews_page(message, 0)

    except Exception as e:
        print(f"❌ Ошибка команды просмотра отзывов: {e}")
        bot.send_message(message.chat.id, "⚠️ Произошла ошибка при загрузке отзывов.", reply_markup=user_menu())

def show_reviews_page(message, page_num):
    try:
        user_id = message.chat.id
        is_admin_user = is_admin(user_id)

        if user_id in user_review_messages:
            try:
                bot.delete_message(user_id, user_review_messages[user_id])
            except:
                pass

        reviews = Reviews.all()
        if not reviews:
            if is_admin_user:
                bot.send_message(user_id, "Пока нет ни одного отзыва.", reply_markup=admin_menu())
            else:
                bot.send_message(user_id, "Пока нет ни одного отзыва.", reply_markup=user_menu())
            return

        reviews_per_page = 2
        start_index = page_num * reviews_per_page
        end_index = start_index + reviews_per_page
        page_reviews = reviews[start_index:end_index]

        if not page_reviews:
            if is_admin_user:
                bot.send_message(user_id, "📄 Это последняя страница отзывов.", reply_markup=admin_menu())
            else:
                bot.send_message(user_id, "📄 Это последняя страница отзывов.", reply_markup=user_menu())
            return

        avg_rating, total_reviews = get_average_rating()

        text = f"📊 Рейтинг компании: {format_rating_stars(avg_rating)} ({avg_rating}/5)\n"
        text += f"👥 Всего отзывов: {total_reviews}\n\n"
        text += "⭐ Отзывы клиентов:\n"

        for i, review in enumerate(page_reviews, start=start_index + 1):
            review_text = review['review']
            if len(review_text) > 500:
                review_text = review_text[:500] + "..."

            text += f"────────────────────\n"
            text += f"{format_rating_stars(review.get('rating', 5))}\n"
            text += f"{review_text}\n\n"

        if len(text) > 4000:
            text = text[:4000] + "\n\n⚠️ Сообщение было сокращено из-за ограничений Telegram"

        keyboard = InlineKeyboardMarkup()
        row_buttons = []

        if page_num > 0:
            row_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f'review_prev_{page_num - 1}'))

        if end_index < len(reviews):
            row_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f'review_next_{page_num + 1}'))

        if row_buttons:
            keyboard.add(*row_buttons)

        keyboard.add(InlineKeyboardButton("❌ Закрыть", callback_data="review_close"))

        sent_message = bot.send_message(user_id, text, reply_markup=keyboard)
        user_review_messages[user_id] = sent_message.message_id

    except Exception as e:
        print(f"❌ Ошибка при отправке отзывов: {e}")
        if is_admin_user:
            bot.send_message(user_id, "⚠️ Не удалось загрузить отзывы. Попробуйте позже.", reply_markup=admin_menu())
        else:
            bot.send_message(user_id, "⚠️ Не удалось загрузить отзывы. Попробуйте позже.", reply_markup=user_menu())

@bot.callback_query_handler(func=lambda call: call.data.startswith('review_'))
def handle_review_pagination(call):
    try:
        if call.data.startswith('review_next_'):
            page_num = int(call.data.split('_')[2])
            show_reviews_page(call.message, page_num)
        elif call.data.startswith('review_prev_'):
            page_num = int(call.data.split('_')[2])
            show_reviews_page(call.message, page_num)
        elif call.data == "review_close":
            user_id = call.message.chat.id
            bot.delete_message(user_id, call.message.message_id)
            if user_id in user_review_messages:
                del user_review_messages[user_id]
            bot.answer_callback_query(call.id, "Отзывы закрыты")
        else:
            bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"❌ Ошибка пагинации отзывов: {e}")
        bot.answer_callback_query(call.id, "⚠️ Ошибка при загрузке страницы")

#---------------------очистка всех баз данных только с админ акка
@bot.message_handler(func=lambda message: message.text == "🗑️ Очистка данных")
def clean_all_databases(message):
    try:
        if not is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "⛔ Эта команда доступна только администратору.")
            return

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("✅ Да, очистить все", callback_data="confirm_clean_all"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_clean")
        )

        bot.send_message(
            message.chat.id,
            "⚠️ ВНИМАНИЕ!\n\n"
            "Вы собираетесь очистить ВСЕ базы данных:\n"
            "• 👨‍💼 Все заявки на консультации\n"
            "• 🏃 Все заявки на сопровождение\n"
            "• ⭐ Все отзывы и рейтинги\n\n"
            "Это действие невозможно отменить!\n"
            "Вы уверены, что хотите продолжить?",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"❌ Ошибка команды очистка: {e}")

@bot.callback_query_handler(func=lambda call: call.data in ["confirm_clean_all", "cancel_clean"])
def handle_clean_confirmation(call):
    try:
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "⛔ Доступ запрещен")
            return

        if call.data == "confirm_clean_all":
            Consultations.truncate()
            Supports.truncate()
            Reviews.truncate()

            user_data.clear()
            user_files.clear()
            user_waiting_for_files.clear()
            user_review_messages.clear()
            admin_history_messages.clear()
            admin_current_page_files.clear()

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="✅ ВСЕ базы данных полностью очищены!\n\n"
                     "• 👨‍💼 Заявки на консультации: 0\n"
                     "• 🏃 Заявки на сопровождение: 0\n"
                     "• ⭐ Отзывы: 0\n\n"
                     "Все временные данные также удалены.",
                reply_markup=None
            )
            bot.answer_callback_query(call.id, "✅ Все базы данных очищены")

        elif call.data == "cancel_clean":
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="❌ Очистка баз данных отменена.",
                reply_markup=None
            )
            bot.answer_callback_query(call.id, "Очистка отменена")
    except Exception as e:
        print(f"❌ Ошибка подтверждения очистки: {e}")

#---------------------заявка на консультацию
@bot.message_handler(func=lambda message: message.text == "👨‍💼 Запись на консультацию")
def start_consultation(message):
    try:
        if is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "⛔ Администратор не может создавать заявки.", reply_markup=admin_menu())
            return

        user_id = message.chat.id
        user_data[user_id] = {'type': 'consultation'}
        user_files[user_id] = []
        user_waiting_for_files[user_id] = True

        user_data[user_id]['step'] = 'waiting_name'

        bot.send_message(user_id, "Пожалуйста, введите ваше имя и номер телефона:")

    except Exception as e:
        print(f"❌ Ошибка начала консультации: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка. Пожалуйста, попробуйте снова.", reply_markup=user_menu())

def get_name_consultation(message):
    try:
        user_id = message.chat.id

        if user_id not in user_data or user_data[user_id].get('step') != 'waiting_name':
            bot.send_message(user_id, "❌ Пожалуйста, начните заново с меню.", reply_markup=user_menu())
            return

        user_data[user_id]['name'] = message.text
        user_data[user_id]['step'] = 'waiting_history'

        bot.send_message(user_id, "Теперь, пожалуйста, напишите краткую историю вашей ситуации:")

    except Exception as e:
        print(f"❌ Ошибка получения имени консультации: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка. Пожалуйста, начните заново.", reply_markup=user_menu())

def get_history_consultation(message):
    try:
        user_id = message.chat.id

        if user_id not in user_data or user_data[user_id].get('step') != 'waiting_history':
            bot.send_message(user_id, "❌ Пожалуйста, начните заново с меню.", reply_markup=user_menu())
            return

        user_data[user_id]['history'] = message.text
        user_waiting_for_files[user_id] = True
        user_data[user_id]['step'] = 'waiting_files'

        bot.send_message(
            user_id,
            "📎 Теперь вы можете прикрепить файлы, фото или видео к вашей заявке. Отправьте все необходимые материалы одним или несколькими сообщениями.\n\nКогда закончите, нажмите кнопку ниже:",
            reply_markup=create_files_keyboard()
        )

    except Exception as e:
        print(f"❌ Ошибка получения истории консультации: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка. Пожалуйста, начните заново.", reply_markup=user_menu())

#-------------------------заявка на сопровождение
@bot.message_handler(func=lambda message: message.text == "🏃 Сопровождение в суде")
def start_support(message):
    try:
        if is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "⛔ Администратор не может создавать заявки.", reply_markup=admin_menu())
            return

        user_id = message.chat.id
        user_data[user_id] = {'type': 'support'}
        user_files[user_id] = []
        user_waiting_for_files[user_id] = True

        user_data[user_id]['step'] = 'waiting_name'

        bot.send_message(user_id, "Пожалуйста, введите ваше имя и номер телефона:")

    except Exception as e:
        print(f"❌ Ошибка начала сопровождения: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка. Пожалуйста, попробуйте снова.", reply_markup=user_menu())

def get_name_support(message):
    try:
        user_id = message.chat.id

        if user_id not in user_data or user_data[user_id].get('step') != 'waiting_name':
            bot.send_message(user_id, "❌ Пожалуйста, начните заново с меню.", reply_markup=user_menu())
            return

        user_data[user_id]['name'] = message.text
        user_data[user_id]['step'] = 'waiting_history'

        bot.send_message(user_id, "Теперь, пожалуйста, напишите краткую историю вашей ситуации:")

    except Exception as e:
        print(f"❌ Ошибка получения имени сопровождения: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка. Пожалуйста, начните заново.", reply_markup=user_menu())

def get_history_support(message):
    try:
        user_id = message.chat.id

        if user_id not in user_data or user_data[user_id].get('step') != 'waiting_history':
            bot.send_message(user_id, "❌ Пожалуйста, начните заново с меню.", reply_markup=user_menu())
            return

        user_data[user_id]['history'] = message.text
        user_waiting_for_files[user_id] = True
        user_data[user_id]['step'] = 'waiting_files'

        bot.send_message(
            user_id,
            "📎 Теперь вы можете прикрепить файлы, фото или видео к вашей заявке. Отправьте все необходимые материалы одним или несколькими сообщениями.\n\nКогда закончите, нажмите кнопку ниже:",
            reply_markup=create_files_keyboard()
        )

    except Exception as e:
        print(f"❌ Ошибка получения истории сопровождения: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка. Пожалуйста, начните заново.", reply_markup=user_menu())

@bot.message_handler(content_types=['document', 'photo', 'video'])
def handle_files(message):
    try:
        user_id = message.chat.id

        if not user_waiting_for_files.get(user_id, False):
            if is_admin(user_id):
                bot.send_message(user_id, "📎 Файлы можно прикрепить только при подаче заявки.", reply_markup=admin_menu())
            else:
                bot.send_message(user_id, "📎 Файлы можно прикрепить только при подаче заявки на консультацию или сопровождение.", reply_markup=user_menu())
            return

        if user_id not in user_files:
            user_files[user_id] = []

        file_info = None

        if message.document:
            file_info = bot.get_file(message.document.file_id)
            file_type = 'document'
        elif message.photo:
            file_info = bot.get_file(message.photo[-1].file_id)
            file_type = 'photo'
        elif message.video:
            file_info = bot.get_file(message.video.file_id)
            file_type = 'video'

        if file_info:
            user_files[user_id].append({
                'file_id': file_info.file_id,
                'file_type': file_type
            })
            bot.send_message(
                user_id,
                "✅ Файл добавлен к заявке. Вы можете отправить еще файлы или нажать '✅ Завершить отправку файлов'",
                reply_markup=create_files_keyboard()
            )
    except Exception as e:
        print(f"❌ Ошибка обработки файлов: {e}")

def create_files_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("✅ Завершить отправку файлов"))
    keyboard.add(KeyboardButton("🚫 Без файлов"))
    return keyboard

def create_rating_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=5)
    keyboard.add(
        InlineKeyboardButton("1⭐", callback_data="rating_1"),
        InlineKeyboardButton("2⭐", callback_data="rating_2"),
        InlineKeyboardButton("3⭐", callback_data="rating_3"),
        InlineKeyboardButton("4⭐", callback_data="rating_4"),
        InlineKeyboardButton("5⭐", callback_data="rating_5")
    )
    return keyboard

@bot.message_handler(func=lambda message: message.text == "✅ Завершить отправку файлов")
def finish_files_consultation(message):
    try:
        user_id = message.chat.id
        user_waiting_for_files[user_id] = False

        if user_id in user_data and user_data[user_id]['type'] == 'consultation':
            send_consultation_to_admin(user_id, message.from_user)
        elif user_id in user_data and user_data[user_id]['type'] == 'support':
            send_support_to_admin(user_id, message.from_user)
        else:
            if is_admin(user_id):
                bot.send_message(user_id, "❌ Произошла ошибка.", reply_markup=admin_menu())
            else:
                bot.send_message(user_id, "❌ Произошла ошибка. Пожалуйста, начните заявку заново.", reply_markup=user_menu())
    except Exception as e:
        print(f"❌ Ошибка завершения отправки файлов: {e}")

@bot.message_handler(func=lambda message: message.text == "🚫 Без файлов")
def no_files_consultation(message):
    try:
        user_id = message.chat.id
        user_waiting_for_files[user_id] = False
        user_files[user_id] = []

        if user_id in user_data and user_data[user_id]['type'] == 'consultation':
            send_consultation_to_admin(user_id, message.from_user)
        elif user_id in user_data and user_data[user_id]['type'] == 'support':
            send_support_to_admin(user_id, message.from_user)
        else:
            if is_admin(user_id):
                bot.send_message(user_id, "❌ Произошла ошибка.", reply_markup=admin_menu())
            else:
                bot.send_message(user_id, "❌ Произошла ошибка. Пожалуйста, начните заявку заново.", reply_markup=user_menu())
    except Exception as e:
        print(f"❌ Ошибка отправки без файлов: {e}")

def send_consultation_to_admin(user_id, user_info):
    try:
        name = user_data[user_id]['name']
        history = user_data[user_id]['history']
        files = user_files.get(user_id, [])

        try:
            chat = bot.get_chat(user_id)
            user_link = f"//t.me/{chat.username}" if chat.username else f"tg://user?id={user_id}"
        except Exception as e:
            user_link = f"tg://user?id={user_id}"

        consultation_doc_id = save_consultation(user_id, name, history, files)

        consultation_text = f"""
📋 Новая заявка на консультацию
Дата: {format_moscow_time()}

Контакты: {name}

История: {history}

Файлов прикреплено: {len(files)}

Клиент: {user_link}
        """

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("✅ Завершить работу", callback_data=f"complete_consultation_{consultation_doc_id}"))

        bot.send_message(ADMIN_TELEGRAM_ID, consultation_text, reply_markup=keyboard)

        if files:
            bot.send_message(ADMIN_TELEGRAM_ID, "📎 Прикрепленные файлы:")
            for file_data in files:
                try:
                    if file_data['file_type'] == 'document':
                        bot.send_document(ADMIN_TELEGRAM_ID, file_data['file_id'])
                    elif file_data['file_type'] == 'photo':
                        bot.send_photo(ADMIN_TELEGRAM_ID, file_data['file_id'])
                    elif file_data['file_type'] == 'video':
                        bot.send_video(ADMIN_TELEGRAM_ID, file_data['file_id'])
                except Exception as e:
                    bot.send_message(ADMIN_TELEGRAM_ID, f"❌ Ошибка при отправке файла: {str(e)}")

        bot.send_message(user_id, "✅ Спасибо! Ваша заявка на консультацию принята. Вам скоро ответят.", reply_markup=user_menu())

        if user_id in user_data:
            del user_data[user_id]
        if user_id in user_files:
            del user_files[user_id]
        if user_id in user_waiting_for_files:
            del user_waiting_for_files[user_id]

    except Exception as e:
        print(f"❌ Ошибка отправки консультации админу: {e}")
        bot.send_message(user_id, "❌ Произошла ошибка при отправке заявки. Пожалуйста, попробуйте снова.", reply_markup=user_menu())

def send_support_to_admin(user_id, user_info):
    try:
        name = user_data[user_id]['name']
        history = user_data[user_id]['history']
        files = user_files.get(user_id, [])

        try:
            chat = bot.get_chat(user_id)
            user_link = f"//t.me/{chat.username}" if chat.username else f"tg://user?id={user_id}"
        except Exception as e:
            user_link = f"tg://user?id={user_id}"

        supports_doc_id = save_supports(user_id, name, history, files)

        supports_text = f"""
⚖️ Новая заявка на сопровождение в суд
Дата: {format_moscow_time()}

Контакты: {name}

История: {history}

Файлов прикреплено: {len(files)}

Клиент: {user_link}
        """

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("✅ Завершить работу", callback_data=f"complete_support_{supports_doc_id}"))

        bot.send_message(ADMIN_TELEGRAM_ID, supports_text, reply_markup=keyboard)

        if files:
            bot.send_message(ADMIN_TELEGRAM_ID, "📎 Прикрепленные файлы:")
            for file_data in files:
                try:
                    if file_data['file_type'] == 'document':
                        bot.send_document(ADMIN_TELEGRAM_ID, file_data['file_id'])
                    elif file_data['file_type'] == 'photo':
                        bot.send_photo(ADMIN_TELEGRAM_ID, file_data['file_id'])
                    elif file_data['file_type'] == 'video':
                        bot.send_video(ADMIN_TELEGRAM_ID, file_data['file_id'])
                except Exception as e:
                    bot.send_message(ADMIN_TELEGRAM_ID, f"❌ Ошибка при отправке файла: {str(e)}")

        bot.send_message(user_id, "✅ Спасибо! Ваша заявка на сопровождение в суде принята. С вами скоро свяжутся.", reply_markup=user_menu())

        if user_id in user_data:
            del user_data[user_id]
        if user_id in user_files:
            del user_files[user_id]
        if user_id in user_waiting_for_files:
            del user_waiting_for_files[user_id]

    except Exception as e:
        print(f"❌ Ошибка отправки сопровождения админу: {e}")
        bot.send_message(user_id, "❌ Произошла ошибка при отправке заявки. Пожалуйста, попробуйте снова.", reply_markup=user_menu())

#---------------------ПРОСТАЯ СИСТЕМА ОТЗЫВОВ
@bot.message_handler(func=lambda message: message.text == "📝 Оставить отзыв")
def ask_for_review(message):
    try:
        if is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "⛔ Администратор не может оставлять отзывы.", reply_markup=admin_menu())
            return

        user_id = message.chat.id
        # Просто сохраняем что пользователь хочет оставить отзыв
        user_data[user_id] = {'leaving_review': True}

        bot.send_message(message.chat.id, "⭐ Пожалуйста, оцените нашу работу по 5-балльной шкале:",
                         reply_markup=create_rating_keyboard())

    except Exception as e:
        print(f"❌ Ошибка запроса отзыва: {e}")

# Обработчик выбора рейтинга
@bot.callback_query_handler(func=lambda call: call.data.startswith('rating_'))
def handle_rating_callback(call):
    try:
        user_id = call.from_user.id

        if user_id not in user_data or not user_data[user_id].get('leaving_review'):
            bot.answer_callback_query(call.id, "❌ Пожалуйста, начните процесс отзыва заново")
            return

        rating = int(call.data.split('_')[1])
        user_data[user_id]['rating'] = rating

        # Удаляем сообщение с кнопками
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass

        bot.send_message(
            call.message.chat.id,
            f"✅ Вы поставили оценку: {format_rating_stars(rating)}\n\nТеперь напишите ваш отзыв:"
        )
        bot.answer_callback_query(call.id, f"✅ Оценка {rating} звезд принята")

    except Exception as e:
        print(f"❌ Ошибка обработки рейтинга: {e}")
        bot.answer_callback_query(call.id, "⚠️ Ошибка при выборе оценки")

# Обработчик текста отзыва
@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get('leaving_review') and user_data.get(message.from_user.id, {}).get('rating'))
def handle_review_text(message):
    try:
        user_id = message.from_user.id

        if user_id not in user_data:
            return

        review_text = message.text
        rating = user_data[user_id].get('rating', 5)

        # Сохраняем отзыв
        save_review(user_id, review_text, rating)

        bot.send_message(
            message.chat.id,
            f"✅ Благодарим за ваш отзыв и оценку {format_rating_stars(rating)}!",
            reply_markup=user_menu()
        )

        # Очищаем данные пользователя
        if user_id in user_data:
            del user_data[user_id]

    except Exception as e:
        print(f"❌ Ошибка сохранения отзыва: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка при сохранении отзыва. Пожалуйста, попробуйте снова.", reply_markup=user_menu())

#---------------------обработка завершения работы
@bot.callback_query_handler(func=lambda call: call.data.startswith('complete_'))
def complete_work(call):
    try:
        if call.data.startswith('complete_consultation_'):
            consultation_id = int(call.data.split('_')[2])
            consultation = Consultations.get(doc_id=consultation_id)
            if consultation:
                user_id = consultation['user_id']
                Consultations.update({'status': 'completed'}, doc_ids=[consultation_id])

        elif call.data.startswith('complete_support_'):
            support_id = int(call.data.split('_')[2])
            support = Supports.get(doc_id=support_id)
            if support:
                user_id = support['user_id']
                Supports.update({'status': 'completed'}, doc_ids=[support_id])

        if 'user_id' in locals():
            review_keyboard = InlineKeyboardMarkup()
            review_keyboard.add(InlineKeyboardButton("⭐ Оставить отзыв", callback_data="leave_review_after_completion"))

            bot.send_message(
                user_id,
                "✅ Работа по вашей заявке завершена! Спасибо, что выбрали нашу компанию.\n\n"
                "Пожалуйста, оставьте отзыв о нашей работе - это поможет нам становиться лучше!",
                reply_markup=review_keyboard
            )

            bot.answer_callback_query(call.id, "✅ Заявка отмечена как завершенная")
            bot.edit_message_text(
                chat_id=ADMIN_TELEGRAM_ID,
                message_id=call.message.message_id,
                text=call.message.text + "\n\n✅ ЗАВЕРШЕНО",
                reply_markup=None
            )
        else:
            bot.answer_callback_query(call.id, "❌ Заявка не найдена")
    except Exception as e:
        print(f"❌ Ошибка завершения работы: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "leave_review_after_completion")
def ask_for_review_after_completion(call):
    try:
        user_id = call.from_user.id

        # Удаляем предыдущее сообщение
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass

        user_data[user_id] = {'leaving_review': True}
        bot.send_message(call.message.chat.id, "⭐ Пожалуйста, оцените нашу работу по 5-балльной шкале:",
                         reply_markup=create_rating_keyboard())
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"❌ Ошибка запроса отзыва после завершения: {e}")

#---------------------общий обработчик сообщений
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    try:
        user_id = message.chat.id

        # Если пользователь в процессе заявки
        if user_id in user_data:
            current_step = user_data[user_id].get('step')

            if current_step == 'waiting_name':
                if user_data[user_id]['type'] == 'consultation':
                    get_name_consultation(message)
                else:
                    get_name_support(message)
                return

            elif current_step == 'waiting_history':
                if user_data[user_id]['type'] == 'consultation':
                    get_history_consultation(message)
                else:
                    get_history_support(message)
                return

        # Если это не отзыв и не заявка, показываем меню
        if not user_data.get(user_id, {}).get('leaving_review'):
            if is_admin(user_id):
                bot.send_message(message.chat.id, "❌ Используйте кнопки меню администратора.", reply_markup=admin_menu())
            else:
                bot.send_message(message.chat.id, "❌ Я не понимаю вас. Пожалуйста, используйте кнопки меню.", reply_markup=user_menu())

    except Exception as e:
        print(f"❌ Ошибка обработки сообщения: {e}")

def run_bot():
    while True:
        try:
            print("🟢 Бот запускается...")
            bot.polling(none_stop=True, timeout=60)
        except requests.exceptions.ConnectionError as e:
            print(f"🔴 Ошибка соединения: {e}")
            print("🔄 Перезапуск через 5 секунд...")
            time.sleep(5)
        except Exception as e:
            print(f"🔴 Критическая ошибка: {e}")
            print("🔄 Перезапуск через 5 секунд...")
            time.sleep(5)

if __name__ == "__main__":
    run_bot()

#Устоновка библиотек
#!pip install telebot
#!pip install tinydb
#!pip install Query
#!pip install TinyDB
