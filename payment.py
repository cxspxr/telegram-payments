
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import requests
import math

from telegram import (LabeledPrice, ShippingOption)
from telegram.ext import (Updater, CommandHandler, MessageHandler,
                          Filters, PreCheckoutQueryHandler, ShippingQueryHandler)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


order_id = False

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def start_callback(update, context):
    msg = "Use /order <id> to get an invoice"
    update.message.reply_text(msg)

def order_callback(update, context):
    global order_id
    order_id = context.args[0]
    if not order_id:
        update.message.reply_text("You haven't entered any order id, please try again")
        return
    msg = f"Okay now let's use the /pay to proceed to checkout if your order number is really {order_id}";
    update.message.reply_text(msg)


def start_without_shipping_callback(update, context):
    global order_id
    chat_id = update.message.chat_id
    title = f"Order {order_id} payment"
    description = "Payment for the goods ordered incl. shipping costs"
    payload = "Custom-Payload"
    # In order to get a provider_token see https://core.telegram.org/bots/payments#getting-a-token
    provider_token = "TOKEN"
    start_parameter = "test-payment"
    r = requests.get(f"route/to/fullfill/order/{order_id}")
    print(r.text)
    j = r.json()
    if j['status'] == 'NO':
        update.message.reply_text('There is no such order. Please, enter the valid id.')
        return
    if j['status'] == 'MISSING':
        update.message.reply_text('You have not provided any id. Please, try again.')
        return
    if j['status'] == 'ALREADY':
        update.message.reply_text('This order has been already paid. Please, try again.')
        return
    print(j)
    currency = j['currency']
    # price in dollars
    price = j['amount']
    price = float(price)
    price = math.ceil(price)
    price = int(price)
    # price * 100 so as to include 2 d.p.
    prices = [LabeledPrice(f"Order #{order_id}", price * 100)]

    # optionally pass need_name=True, need_phone_number=True,
    # need_email=True, need_shipping_address=True, is_flexible=True
    context.bot.send_invoice(chat_id, title, description, payload,
                             provider_token, start_parameter, currency, prices)


# after (optional) shipping, it's the pre-checkout
def precheckout_callback(update, context):
    query = update.pre_checkout_query
    # check the payload, is this from your bot?
    if query.invoice_payload != 'Custom-Payload':
        # answer False pre_checkout_query
        query.answer(ok=False, error_message="Something went wrong...")
    else:
        query.answer(ok=True)


# finally, after contacting to the payment provider...
def successful_payment_callback(update, context):
    global order_id
    # do something after successful receive of payment?
    r = requests.get(f"path/to/fullfill/order/{order_id}/pay")
    j = r.json()

    if j['status'] == 'NO':
        update.message.reply_text('There is no such order. Please, enter the valid id.')
        return
    if j['status'] == 'MISSING':
        update.message.reply_text('You have not provided any id. Please, try again.')
        return
    if j['status'] == 'ALREADY':
        update.message.reply_text('This order has been already paid. Please, try again.')
        return
    
    update.message.reply_text("Thank you for your payment!")


def main():
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater("BOT_TOKEN", use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # simple start function
    dp.add_handler(CommandHandler("start", start_callback))

    dp.add_handler(CommandHandler("order", order_callback))

    # Add command handler to start the payment invoice
    dp.add_handler(CommandHandler("pay", start_without_shipping_callback))

    # Pre-checkout handler to final check
    dp.add_handler(PreCheckoutQueryHandler(precheckout_callback))

    # Success! Notify your user!
    dp.add_handler(MessageHandler(Filters.successful_payment, successful_payment_callback))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
