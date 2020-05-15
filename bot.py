import json
import logging
import os
import random
from threading import Lock

import jieba.posseg
from telegram import Chat
from telegram.ext import Updater, Filters, CommandHandler, MessageHandler
from telegram.messageentity import MessageEntity

logging.basicConfig(level=logging.INFO)
DEFAULT_P = 0.1
suffix_words = ['个屁', '个头', '个几把', '个鬼', '个卵']
bot_info = None
group_settings = dict()
settings_lock = Lock()
character_replacement_data = dict()
STICKER_FILE_ID = 'CAACAgUAAxkBAAMdXr2GlOY6nXjYR__c-f1yO9UcA48AAqYAA4XhawuRHo4uZmGeyBkE'


def test(update, context):
    update.message.reply_text(random.choice(['测个屁', '测个头']))


def generate_repeat_text(text):
    output = ''
    for char in text:
        replacement = character_replacement_data.get(char)
        output += replacement if replacement else char
    return output


def generate_insult_text(text):
    suffix_word = random.choice(suffix_words)
    keywords = list()
    input_words = jieba.posseg.cut(text)
    for w in input_words:
        if w.flag.startswith('v') or w.flag.startswith('a') or w.flag == 'i':
            keywords.append(w.word)
    if keywords:
        return random.choice(keywords) + suffix_word
    return None


def set(update, context):
    if len(context.args) != 1:
        update.message.reply_text('Usage: /setp <Reply Possibility> ([0.00~1.00])')
        return
    if update.message.chat.type not in [Chat.GROUP, Chat.SUPERGROUP]:
        update.message.reply_text('Only available in group chats')
        return
    try:
        new_p = round(float('0' + context.args[0]), 6)
        if new_p > 1:
            new_p = 1
        if new_p < 0:
            new_p = 0
    except ValueError:
        update.message.reply_text('Usage: /setp <Reply Possibility> ([0.00~1.00])')
        return
    group_settings[update.message.chat.id] = new_p
    save_settings()
    update.message.reply_text('Success! P = {0:.6f}'.format(new_p))


def get(update, context):
    if update.message.chat.type not in [Chat.GROUP, Chat.SUPERGROUP]:
        update.message.reply_text('Only available in group chats')
        return
    if update.message.chat.id not in group_settings:
        group_settings[update.message.chat.id] = DEFAULT_P
    save_settings()
    update.message.reply_text(
        'Reply Possibility in current group is: {0:.6f}'.format(group_settings[update.message.chat.id]))


def process_message(update, context):
    if update.message.chat.id not in group_settings:
        group_settings[update.message.chat.id] = DEFAULT_P
    if random.random() <= group_settings[update.message.chat.id]:
        if random.random() < 0.5:
            # insult
            reply_text = generate_insult_text(update.message.text)
            if reply_text:
                update.message.reply_text(reply_text)
        else:
            # repeat
            update.message.reply_text(generate_repeat_text(update.message.text), quote=False)
    print(update.message.chat.id, update.message.chat.title, update.message.from_user.id,
          update.message.from_user.full_name)


def reply_mention(update, context):
    mentions = update.message.parse_entities([MessageEntity.MENTION])
    for v in mentions.values():
        if '@' + bot_info.username in v:
            update.message.reply_sticker(STICKER_FILE_ID)
            return


def reply_reply(update, context):
    if update.message.reply_to_message.from_user.id != bot_info.id:
        return
    # reply to message replied to bot
    suffix_word = random.choice(suffix_words)
    keywords = list()
    input_words = jieba.posseg.cut(update.message.text)
    for w in input_words:
        if w.flag.startswith('v'):
            keywords.append(w.word)

    if keywords:
        update.message.reply_text(random.choice(keywords) + suffix_word)
    else:
        update.message.reply_text(update.message.text + suffix_word)


def reply_forward(update, context):
    if update.message.forward_from.id != bot_info.id:
        return
    # forward words of bot
    suffix_word = random.choice(suffix_words)
    update.message.reply_text('Forward' + suffix_word)


def reply_sticker(update, context):
    if update.message.reply_to_message.from_user.id != bot_info.id:
        return
    # reply to stickers replied to bot
    sticker_set = context.bot.get_sticker_set(update.message.sticker.set_name)
    sticker = random.choice(sticker_set.stickers)
    update.message.reply_sticker(sticker)


def load_settings():
    with settings_lock:
        global group_settings
        global character_replacement_data
        if os.path.isfile('char_replace_data.json'):
            with open('char_replace_data.json') as f:
                character_replacement_data = json.load(f)
        else:
            print('ERROR: char_replace_data.json does not exist')
        if os.path.isfile('settings.json'):
            with open('settings.json') as f:
                group_settings = json.load(f)
                group_settings = {int(k): v for k, v in group_settings.items()}
        else:
            print('ERROR: settings.json does not exist')


def save_settings():
    with settings_lock:
        with open('settings.json', 'w') as f:
            json.dump(group_settings, f)


def main():
    bot_token = os.environ.get('BOT_TOKEN')
    load_settings()
    updater = Updater(bot_token, use_context=True)
    updater.dispatcher.add_handler(CommandHandler('test', test))
    updater.dispatcher.add_handler(CommandHandler('setp', set, pass_args=True))
    updater.dispatcher.add_handler(CommandHandler('getp', get))
    updater.dispatcher.add_handler(MessageHandler(Filters.reply & Filters.sticker & Filters.group, reply_sticker))
    updater.dispatcher.add_handler(MessageHandler(Filters.reply & Filters.text & Filters.group, reply_reply))
    updater.dispatcher.add_handler(MessageHandler(Filters.forwarded & Filters.group, reply_forward))
    updater.dispatcher.add_handler(MessageHandler(Filters.entity(MessageEntity.MENTION) & Filters.group, reply_mention))
    updater.dispatcher.add_handler(MessageHandler(Filters.text & Filters.group, process_message))
    global bot_info
    bot_info = updater.bot.get_me()
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
