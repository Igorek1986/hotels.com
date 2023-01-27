from loader import bot
import handlers
from telebot.custom_filters import StateFilter
from utils.set_bot_commands import set_default_commands


def main():
    bot.add_custom_filter(StateFilter(bot))
    set_default_commands(bot)
    bot.infinity_polling()


if __name__ == '__main__':
    main()
