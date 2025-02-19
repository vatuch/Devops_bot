import logging
import re
import paramiko
from dotenv import load_dotenv
from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
import os
import psycopg2
load_dotenv('D:/DevOps/bot/token.env')

logging.basicConfig(
    filename='logfile.txt', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

TOKEN = os.getenv('TOKEN')
RM_HOST = os.getenv('RM_HOST')
RM_PORT = os.getenv('RM_PORT')
RM_USER = os.getenv('RM_USER')
RM_PASSWORD = os.getenv('RM_PASSWORD')
DB_HOST = os.getenv('DB_HOST')  # добавить переменные окружения для базы данных
DB_PORT = os.getenv('DB_PORT')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_DATABASE = os.getenv('DB_DATABASE')
LOG_FILE_PATH = '/var/log/postgresql/postgresql-15-main.log'

def connect_db():
    """Функция для подключения к базе данных PostgreSQL."""
    try:
        conn = psycopg2.connect(
            dbname=DB_DATABASE,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        logger.info("Подключение к базе данных установлено.")
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        return None


def list_tables(update: Update, context: CallbackContext):
    """Команда для получения списка таблиц"""
    conn = connect_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
            tables = cursor.fetchall()
            response = "Таблицы в базе данных:\n" + "\n".join([table[0] for table in tables])
            update.message.reply_text(response)
        except Exception as e:
            logger.error(f"Ошибка при получении списка таблиц: {e}")
            update.message.reply_text("Не удалось получить таблицы.")
        finally:
            cursor.close()
            conn.close()
    else:
        update.message.reply_text("Не удалось подключиться к базе данных.")

def view_table(update: Update, context: CallbackContext):
    """Команда для просмотра содержимого конкретной таблицы"""
    table_name = context.args[0] if context.args else None
    if not table_name:
        update.message.reply_text("Пожалуйста, укажите имя таблицы. Пример: /view_table имя_таблицы")
        return

    conn = connect_db()
    if conn:
        try:
            cursor = conn.cursor()
            query = f"SELECT * FROM {table_name};"
            cursor.execute(query)
            records = cursor.fetchall()
            response = f"Содержимое таблицы {table_name}:\n"
            response += "\n".join([str(record) for record in records])
            update.message.reply_text(response)
        except Exception as e:
            logger.error(f"Ошибка при просмотре содержимого таблицы: {e}")
            update.message.reply_text("Не удалось получить содержимое таблицы.")
        finally:
            cursor.close()
            conn.close()
    else:
        update.message.reply_text("Не удалось подключиться к базе данных.")

def ssh_command(command):
    """ Выполняет команду на удаленном сервере по SSH. """
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(RM_HOST, username=RM_USER, password=RM_PASSWORD)
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        client.close()

        if error:
            return error.strip()
        return output.strip()
    except Exception as e:
        logger.error(f"Ошибка при выполнении команды: {str(e)}")
        return "Ошибка выполнения команды."

# Команды для мониторинга
def get_release(update: Update, context: CallbackContext):
    output = ssh_command('lsb_release -a')
    update.message.reply_text(f'Информация о релизе:\n{output}')

def get_postgresql_log(update: Update, context: CallbackContext):
    try:
        # Получаем последние 20 строк из файла лога PostgreSQL
        output = ssh_command('tail -20 /var/log/postgresql/postgresql-15-main.log')
        update.message.reply_text(f'Логи PostgreSQL:\n{output}')

    except Exception as e:
        update.message.reply_text(f'Ошибка при получении логов PostgreSQL: {e}')


def get_uname(update: Update, context: CallbackContext):
    output = ssh_command('uname -a')
    update.message.reply_text(f'Информация о системе:\n{output}')

def get_uptime(update: Update, context: CallbackContext):
    output = ssh_command('uptime')
    update.message.reply_text(f'Время работы системы:\n{output}')

def get_df(update: Update, context: CallbackContext):
    output = ssh_command('df -h')
    update.message.reply_text(f'Состояние файловой системы:\n{output}')

def get_free(update: Update, context: CallbackContext):
    output = ssh_command('free -h')
    update.message.reply_text(f'Состояние оперативной памяти:\n{output}')

def get_mpstat(update: Update, context: CallbackContext):
    output = ssh_command('mpstat')
    update.message.reply_text(f'Производительность системы:\n{output}')

def get_w(update: Update, context: CallbackContext):
    output = ssh_command('w')
    update.message.reply_text(f'Работающие пользователи:\n{output}')

def get_auths(update: Update, context: CallbackContext):
    output = ssh_command('last -n 10')
    update.message.reply_text(f'Последние 10 входов:\n{output}')

def get_critical(update: Update, context: CallbackContext):
    output = ssh_command('grep -i critical /var/log/syslog | tail -n 5')
    update.message.reply_text(f'Последние 5 критических событий:\n{output}')

def get_ps(update: Update, context: CallbackContext):
    output = ssh_command('ps -aux')
    update.message.reply_text(f'Запущенные процессы:\n{output}')


def get_ss(update: Update, context: CallbackContext):
    output = ssh_command('ss -tuln')
    update.message.reply_text(f'Используемые порты:\n{output}')


def get_apt_list(update: Update, context: CallbackContext):
    if context.args:
        package_name = " ".join(context.args)
        output = ssh_command(f'dpkg -l | grep {package_name}')
        if not output:
            output = "Пакет не найден."
    else:
        output = ssh_command('dpkg -l')

    update.message.reply_text(f'Информация об установленных пакетах:\n{output}')


def get_services(update: Update, context: CallbackContext):
    output = ssh_command('systemctl list-units --type=service')
    if not output:
        output = "Сервисы не найдены."
    update.message.reply_text(f'Запущенные сервисы:\n{output}')

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    update.message.reply_text(f'Привет {user.full_name}!')


FIND_PHONE, FIND_EMAIL, VERIFY_PASSWORD, SAVE_PHONE, SAVE_EMAIL = range(5)
def start(update: Update, context):
    user = update.effective_user
    update.message.reply_text(f'Привет {user.full_name} ! Выберите команду:\n/find_email - для поиска email-адресов\n/find_phone_number - для поиска телефонных номеров\n/verify_password - для проверки пароля'
                              'Доступные команды:\n'
                              '/get_release - Информация о релизе\n'
                              '/get_uname - Информация о системе\n'
                              '/get_uptime - Время работы\n'
                              '/get_df - Состояние файловой системы\n'
                              '/get_free - Состояние оперативной памяти\n'
                              '/get_mpstat - Производительность системы\n'
                              '/get_w - Рабочие пользователи\n'
                              '/get_auths - Последние 10 входов\n'
                              '/get_critical - Последние 5 критических событий\n'
                              '/get_ps - Запущенные процессы\n'
                              '/get_ss - Используемые порты\n'
                              '/get_apt_list [package_name] - Установленные пакеты\n'
                              '/get_services - Запущенные сервисы\n'
                              '/get_emails - Для работы с БД \n'
                              '/phone_numbers - Для работы с БД \n'
                              '/view_table (Название) - посмотрим на таблицы \n'
                              '/get_repl_logs - логи БД \n'
                              )


def helpCommand(update: Update, context: CallbackContext):
    update.message.reply_text('Выберите команду:\n/find_email - для поиска email-адресов\n/find_phone_number - для поиска телефонных номеров\n/verify_password - для проверки пароля')


def findPhoneNumbersCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска телефонных номеров: ')
    return FIND_PHONE

def findEmailCommand(update: Update, context: CallbackContext):
    update.message.reply_text('Введите текст для поиска email-адресов: ')
    return FIND_EMAIL

def verifyPasswordCommand(update: Update, context: CallbackContext):
    update.message.reply_text('Введите пароль для проверки: ')
    return VERIFY_PASSWORD

def findPhoneNumbers(update: Update, context: CallbackContext):
    user_input = update.message.text
    phoneNumRegex = re.compile(
        r'(\+7|8)[\s(]*(\d{3})[\s)]*(\d{3})[-\s]*(\d{2})[-\s]*(\d{2})|8[\s]*(\d{10})|8[- ]*(\d{3})[- ]*(\d{3})[- ]*(\d{2})[- ]*(\d{2})'
    )
    phoneNumberList = phoneNumRegex.findall(user_input)
    found_numbers = list(set([''.join(num) for num in phoneNumberList if num]))

    if not found_numbers:
        update.message.reply_text('Телефонные номера не найдены.')
        return ConversationHandler.END

    phoneNumbers = '\n'.join(f'{i + 1}. {num}' for i, num in enumerate(found_numbers))
    update.message.reply_text(f'Найденные номера телефонов:\n{phoneNumbers}')
    context.user_data['found_numbers'] = found_numbers  # Сохранить найденные номера
    update.message.reply_text('Хотите сохранить найденные номера в базе данных? (да/нет)')
    return SAVE_PHONE


def savePhoneNumbers(update: Update, context: CallbackContext):
    response = update.message.text.lower()
    if response == 'да':
        found_numbers = context.user_data.get('found_numbers', [])
        if not found_numbers:
            update.message.reply_text('Нет данных для сохранения.')
            return ConversationHandler.END

        conn = connect_db()
        if conn:
            try:
                cursor = conn.cursor()
                for number in found_numbers:
                    cursor.execute("INSERT INTO phone_numbers (phone_number) VALUES (%s)", (number,))
                conn.commit()
                update.message.reply_text('Телефонные номера успешно сохранены в базе данных.')
            except Exception as e:
                logger.error(f"Ошибка при сохранении номеров телефонов: {e}")
                update.message.reply_text('Ошибка при сохранении номеров телефонов.')
            finally:
                cursor.close()
                conn.close()
        else:
            update.message.reply_text("Не удалось подключиться к базе данных.")
    else:
        update.message.reply_text('Запись номеров отменена.')

    return ConversationHandler.END

def findEmails(update: Update, context: CallbackContext):
    user_input = update.message.text
    emailRegex = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    emailList = emailRegex.findall(user_input)

    if not emailList:
        update.message.reply_text('Email-адреса не найдены.')
        return ConversationHandler.END

    emails = '\n'.join(f'{i + 1}. {email}' for i, email in enumerate(emailList))
    update.message.reply_text(f'Найденные email-адреса:\n{emails}')
    context.user_data['found_emails'] = emailList  # Сохранить найденные email
    update.message.reply_text('Хотите сохранить найденные email-адреса в базе данных? (да/нет)')
    return SAVE_EMAIL


def saveEmails(update: Update, context: CallbackContext):
    response = update.message.text.lower()
    if response == 'да':
        found_emails = context.user_data.get('found_emails', [])
        if not found_emails:
            update.message.reply_text('Нет данных для сохранения.')
            return ConversationHandler.END

        conn = connect_db()
        if conn:
            try:
                cursor = conn.cursor()
                for email in found_emails:
                    cursor.execute("INSERT INTO emails (email) VALUES (%s)", (email,))
                conn.commit()
                update.message.reply_text('Email-адреса успешно сохранены в базе данных.')
            except Exception as e:
                logger.error(f"Ошибка при сохранении email-адресов: {e}")
                update.message.reply_text('Ошибка при сохранении email-адресов.')
            finally:
                cursor.close()
                conn.close()
        else:
            update.message.reply_text("Не удалось подключиться к базе данных.")
    else:
        update.message.reply_text('Запись email-адресов отменена.')

    return ConversationHandler.END

def verifyPassword(update: Update, context: CallbackContext):
    password = update.message.text

    # Регулярное выражение для проверки сложности пароля
    passwordRegex = re.compile(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])(?=.*[!@#$%^&*()]).{8,}$')

    # Проверяем соответствие регулярному выражению
    if (
        passwordRegex.match(password) and
        len(password) >= 8 and
        any(char.isupper() for char in password) and
        any(char.islower() for char in password) and
        any(char.isdigit() for char in password) and
        any(char in "!@#$%^&*()" for char in password)
    ):
        update.message.reply_text('Пароль сложный.')
    else:
        update.message.reply_text('Пароль простой.')

    return ConversationHandler.END



def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    convHandlerFindPhoneNumbers = ConversationHandler(
        entry_points=[CommandHandler('get_phone_numbers', findPhoneNumbersCommand)],
        states={
            FIND_PHONE: [MessageHandler(Filters.text & ~Filters.command, findPhoneNumbers)],
            SAVE_PHONE: [MessageHandler(Filters.text & ~Filters.command, savePhoneNumbers)],
        },
        fallbacks=[]
    )

    convHandlerFindEmails = ConversationHandler(
        entry_points=[CommandHandler('get_emails', findEmailCommand)],
        states={
            FIND_EMAIL: [MessageHandler(Filters.text & ~Filters.command, findEmails)],
            SAVE_EMAIL: [MessageHandler(Filters.text & ~Filters.command, saveEmails)],
        },
        fallbacks=[]
    )

    convHandlerVerifyPassword = ConversationHandler(
        entry_points=[CommandHandler('verify_password', verifyPasswordCommand)],
        states={
            VERIFY_PASSWORD: [MessageHandler(Filters.text & ~Filters.command, verifyPassword)],
        },
        fallbacks=[]
    )

    # Регистрируем обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", helpCommand))
    dp.add_handler(convHandlerFindPhoneNumbers)
    dp.add_handler(convHandlerFindEmails)
    dp.add_handler(convHandlerVerifyPassword)
    dp.add_handler(CommandHandler("get_release", get_release))
    dp.add_handler(CommandHandler("get_uname", get_uname))
    dp.add_handler(CommandHandler("get_uptime", get_uptime))
    dp.add_handler(CommandHandler("get_df", get_df))
    dp.add_handler(CommandHandler("get_free", get_free))
    dp.add_handler(CommandHandler("get_mpstat", get_mpstat))
    dp.add_handler(CommandHandler("get_w", get_w))
    dp.add_handler(CommandHandler("get_auths", get_auths))
    dp.add_handler(CommandHandler("get_critical", get_critical))
    dp.add_handler(CommandHandler("get_ps", get_ps))
    dp.add_handler(CommandHandler("get_ss", get_ss))
    dp.add_handler(CommandHandler("get_apt_list", get_apt_list))
    dp.add_handler(CommandHandler("get_services", get_services))
    dp.add_handler(CommandHandler("list_tables", list_tables))
    dp.add_handler(CommandHandler("view_table", view_table))
    dp.add_handler(CommandHandler("get_repl_logs", get_postgresql_log))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()