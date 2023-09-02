# -*- coding: utf-8 -*-
import logging
import re
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from aiogram.dispatcher.filters import Text
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from dotenv import dotenv_values

config = dotenv_values("config.env")
conf_str = dotenv_values("strings.env")
API_TOKEN = config['BOT_API_KEY']
# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

DEBUG = (config['DEBUG'] == 'True')

# Configure logging
logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S', level=logging.DEBUG if DEBUG else logging.INFO)

if config['BOT_ADMIN_SERVICE_GROUP']:
    service_chatid = int(config['BOT_ADMIN_SERVICE_GROUP'])
else:
    service_chatid = int(config['BOT_ADMIN_CHATID'])

class Event(StatesGroup):
    restoreAccess = State()  # Восстановление доступа
    provideMACID = State() #Предоставление ID и MAC
    question = State()  # Произвольный вопрос

##Markup
def AgreeToResetMarkup():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    yes = KeyboardButton(conf_str['YES'])
    no = KeyboardButton(conf_str['NO'])
    markup.add(yes, no)
    return markup

@dp.message_handler(commands=[])
async def any_other_private_message(message: types.Message):
    await bot.send_message(service_chatid,
                           f"🟢 Клиент ID{message.from_user.id} (@{message.from_user.username}) задал вопрос:\n\n{message.text}")
    await message.answer(conf_str['QUESTIONGOT'], parse_mode="HTML")

# Обработка начала общения
@dp.message_handler(state='*', commands=['start'])
async def send_welcome(message: types.Message):
    await bot.send_message(service_chatid,
                           f"🟢 Зашел ID {message.from_user.id} (@{message.from_user.username}) и начал пробовать бота.")
    await message.answer(
        conf_str['GREETING'].format(config['BOT_NAME'], message.from_user.first_name))

@dp.message_handler(commands=['help'])
async def send_help(message: types.Message):
    """
    This handler will be called when user sends `/help` command
    """
    await message.answer(conf_str['HELP'])

@dp.message_handler(commands=['yoursmarthome'])
async def send_yshdescripption(message: types.Message):
    await message.answer(conf_str['YOURSMARTHOMEDESCRIPTION1'], parse_mode="HTML")
    await message.answer(conf_str['YOURSMARTHOMEDESCRIPTION2'], parse_mode="HTML")
    await message.answer(conf_str['YOURSMARTHOMEDESCRIPTION3'], parse_mode="HTML")
    await message.answer(conf_str['YOURSMARTHOMEDESCRIPTION4'], parse_mode="HTML")

@dp.message_handler(commands=['more'], chat_type=types.ChatType.PRIVATE)
async def send_more(message: types.Message):
    await message.answer(conf_str['MOREDESCRIPTION'], parse_mode="HTML")


@dp.message_handler(commands=['restoreaccess'])
async def send_restoreaccess(message: types.Message):
    await message.answer(conf_str['RESTOREACCESSDESCRIPTION'], parse_mode="HTML", reply_markup=AgreeToResetMarkup())
    await Event.restoreAccess.set()

@dp.message_handler(state=Event.restoreAccess)
async def send_restoreaccess_warning(message: types.Message):
    if message.text.upper() == conf_str['YES'].upper():
        await bot.send_message(message.chat.id, conf_str["RESTOREACCESSMACID"], reply_markup=ReplyKeyboardRemove())
        with open(config["YUBIIBACK"], 'rb') as yubii, open(config["HCLBAK"], 'rb') as hcl:
            await bot.send_photo(chat_id=message.chat.id, photo=yubii)
            await bot.send_photo(chat_id=message.chat.id, photo=hcl)
        Event.next()
    elif message.text.upper() == conf_str['NO'].upper():
        await bot.send_message(message.chat.id, conf_str["RESTOREACCESSSUGGESTION"], reply_markup=ReplyKeyboardRemove())
    else:
        await bot.send_message(service_chatid,
                               f"🟢 Клиент ID{message.from_user.id} (@{message.from_user.username}) запрашивает помощь в восстановлении доступа:\n{message.text}")
        await message.answer(conf_str['RESTOREACCESSGOTSUGGGESTION'], parse_mode="HTML")
        await Event.last()
        await Event.next()

@dp.message_handler(state=Event.provideMACID)
async def send_restoreaccess_text(message: types.Message):
        await bot.send_message(service_chatid,
                               f"🟢 Клиент ID{message.from_user.id} (@{message.from_user.username}) прислал серийный номер контроллера для восстановления:\n{message.text}")
        await message.answer(conf_str['RESTOREACCESSGOTID'], parse_mode="HTML")
        await Event.last()
        await Event.next()

@dp.message_handler(commands=['question'])
async def send_question(message: types.Message):
    await message.answer(conf_str['QUESTIONDESCRIPTION'], parse_mode="HTML")
    await Event.question.set()

@dp.message_handler(state=Event.question)
async def send_question_text(message: types.Message):
    await bot.send_message(service_chatid,
                           f"🟢 Клиент ID{message.from_user.id} (@{message.from_user.username}) задал вопрос:\n{message.text}")
    await message.answer(conf_str['QUESTIONGOT'], parse_mode="HTML")
    await Event.last()
    await Event.next()

@dp.message_handler(
    lambda message: (message.reply_to_message is not None
                     and message.chat.id == service_chatid),
    state='*')
async def group_message(message: types.Message):
    try:
        msg = message.reply_to_message.text # if replied
        match = re.search(r"ID(.+?)\s", msg)
        if match:
            user_id = int(match.group(1))
            await bot.send_message(user_id, f"По вашему сообщению \n{msg} \n\nдаем ответ:\n{message.text}")
    except AttributeError:
        await bot.send_message(service_chatid, conf_str['GROUPUNKNOWNMESSAGE'])

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
