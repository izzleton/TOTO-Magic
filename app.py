from flask import Flask, request, jsonify, render_template, redirect, url_for, session, Blueprint
import random
from datetime import datetime, timedelta, date
import hashlib
import hmac
import time
import mysql.connector
from mysql.connector import Error
import json
from functools import wraps
from dotenv import load_dotenv
import logging
import os
from flask_wtf.csrf import CSRFProtect
from flask_cors import CORS
import base64
from telegram import Bot, Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Dispatcher, Updater, CommandHandler, CallbackContext
import threading

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')

# Retrieve environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_ID = os.getenv('BOT_ID')
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
ADMIN_USER_ID = 1701738848
BOT_USERNAME = 'totomagicbot'
CHANNEL_CHAT_ID = -1002212825968

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
}

csrf = CSRFProtect()

# Create Flask app
app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

# Configure session cookies for cross-origin requests
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True

CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})

# Initialize the bot and dispatcher
bot = Bot(token=BOT_TOKEN)
toto_magic = Blueprint(
    'toto_magic',
    __name__,
    url_prefix='/games/toto_magic',
    template_folder='templates',
    static_folder='static',
    static_url_path='/games/toto_magic/static'
)

# Verify that environment variables are set
if not BOT_TOKEN:
    logging.error("BOT_TOKEN is not set. Please set the BOT_TOKEN environment variable.")
    raise Exception("BOT_TOKEN is not set.")
else:
    logging.info(f"BOT_TOKEN is set. Length: {len(BOT_TOKEN)} characters.")

if not BOT_ID:
    logging.error("BOT_ID is not set. Please set the BOT_ID environment variable.")
    raise Exception("BOT_ID is not set.")
else:
    logging.info(f"BOT_ID is set. Value: {BOT_ID}")

if not FLASK_SECRET_KEY:
    logging.error("FLASK_SECRET_KEY is not set.")
    raise Exception("FLASK_SECRET_KEY is not set.")
else:
    logging.info("FLASK_SECRET_KEY is set.")

def query_db(query, args=(), one=False):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, args)
        rv = cursor.fetchall()
        cursor.close()
        conn.close()
        return (rv[0] if rv else None) if one else rv
    except Error as e:
        logging.error(f"Database error: {e}")
        return None

def modify_db(query, args=()):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(query, args)
        conn.commit()
        cursor.close()
        conn.close()
    except Error as e:
        logging.error(f"Database error: {e}")
        raise e

# Function to send the play button to a specific chat (used by /announce command)
def send_play_button_to_chat():
    chat_id = CHANNEL_CHAT_ID

    # URL to the bot's deep link for starting the game
    bot_url = f'https://t.me/{BOT_USERNAME}?start=0'

    keyboard = [
        [InlineKeyboardButton(text='Play TOTO Magic 🪄' , url=bot_url)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the message to the chat
    sent_message = bot.send_message(chat_id=chat_id, text='Click the button below to play TOTO Magic! 🪄' , reply_markup=reply_markup)

    # Pin the message (ensure the bot has permission to pin messages)
    bot.pin_chat_message(chat_id=chat_id, message_id=sent_message.message_id)

# Command handler for /announce
def handle_announce_command(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    logging.info(f"Handling /announce command from user {user_id}")

    # Only allow the admin to use this command
    if user_id != ADMIN_USER_ID:
        bot.send_message(chat_id=chat_id, text='You are not authorized to use this command.')
        return
    # Send the play button to the channel and notify the admin
    send_play_button_to_chat()
    bot.send_message(chat_id=chat_id, text='Announcement sent and pinned.')

# Command handler for /play
def handle_play_command(message):
    logging.info(f"Handling /play command from user {message.from_user.id}")

    web_app_url = 'https://lilypad.croakey.io/games/toto_magic/'
    web_app = WebAppInfo(url=web_app_url)

    keyboard = [
        [InlineKeyboardButton(text='Play TOTO Magic 🪄' , web_app=web_app)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the play button in a private chat with the user
    bot.send_message(chat_id=message.chat.id, text='Click the button below to play TOTO Magic!', reply_markup=reply_markup)

def handle_start_command(message):
    user_id = message.from_user.id

    # 1) Get the username or set fallback if empty
    username = message.from_user.username or ''
    username = username.strip()
    if not username:
        username = f"user_{user_id}"

    text = message.text
    args = text.split()
    referrer_id = args[1] if len(args) > 1 else None

    # 2) Referral logic (unchanged)
    if referrer_id and str(user_id) != referrer_id:
        try:
            referrer_id = int(referrer_id)
            logging.info(f"User {user_id} was referred by {referrer_id}")
        except ValueError:
            logging.error(f"Invalid referrer_id: {referrer_id}")
            referrer_id = None
    else:
        referrer_id = None

    # 3) Create or update user info
    create_or_update_user(
        {
            'id': user_id,
            'username': username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name
        },
        referrer_id
    )

    # 4) Build the multiline welcome text for the caption
    welcome_text = (
        "Welcome to TOTO Magic 🪄\n\n"
        "Based off the popular arcade game, “Zoltar”, TOTO Magic aims to begin a new meta in the Play-to-Earn "
        "games — we like to call it “Wish to Earn”! 🔮\n\n"
        "Simply login, make your 3 daily wishes, and earn coins! Plus, invite friends for more rewards! "
        "Simple enough? Start wishing now! 🪄\n\n"
        "Use /play to begin"
    )

    # 5) Send the photo with the multiline caption
    #    Adjust the file path if needed; e.g. "static/TotoMagic.jpg" or the full path
    try:
        with open("static/TotoMagic.jpg", "rb") as photo_file:
            bot.send_photo(
                chat_id=message.chat.id,
                photo=photo_file,
                caption=welcome_text
            )
    except FileNotFoundError:
        logging.error("TotoMagic.jpg not found in 'static' folder. Falling back to a text-only message.")
        # In case the image is missing, fall back to sending text only
        bot.send_message(
            chat_id=message.chat.id,
            text=welcome_text
        )

def handle_update(update):
    try:
        if update.message:
            message = update.message
            chat_id = message.chat.id
            text = message.text or ""
            logging.info(f"Received message: '{text}' from chat_id: {chat_id}")
            if text.startswith('/start'):
                handle_start_command(message)
            elif text.startswith('/play'):
                handle_play_command(message)
            elif text.startswith('/announce'):
                handle_announce_command(message)
            else:
                logging.info("Received unrecognized command.")
        else:
            logging.info(f"Received update without message: {update.to_dict()}")
            # Handle other update types if necessary
    except Exception as e:
        logging.error(f"Error in handle_update: {e}")
        try:
            logging.error(f"Update causing error: {update.to_dict()}")
        except Exception as ex:
            logging.error(f"Could not convert update to dict: {ex}")

# List of fortunes
fortunes = [
    "Beware of the half truth, you may have the wrong half.",
    "Don't wait for people to be friendly. Show them how.",
    "From small beginnings come great things.",
    "Everyone smiles in the same language.",
    "Some pursue happiness and some create it.",
    "What you see depends on what you are looking for.",
    "When you lose, don't lose the lesson.",
    "The best place to find a helping hand is at the end of your arm!",
    "Put your future in good hands, your own!",
    "Do not miss out on something that is great just because it may be difficult.",
    "A goal without a plan is merely a wish.",
    "No matter how smart you are, you will never convince someone stupid that they are stupid.",
    "If Cinderella’s slipper fitted perfectly, why did it fall off?",
    "Be kind to unkind people, they need it most.",
    "If you hear the onion ring…don't answer it.",
    "Always borrow money from a pessimist, they will not expect it back.",
    "With great power comes an even greater electricity bill.",
    "There is nothing better than a friend, especially one with chocolate.",
    "You don't realize what you have until it's gone, toilet paper is the best example.",
    "Better late than never, but never late is better.",
    "Those that live in the past limit their future.",
    "If at first you don't succeed, I suggest you forget the parachute jump.",
    "If plan “A” fails, try the other 25 letters in the alphabet.",
    "I always cook with wine and sometimes I add it to the food.",
    "Growing old is mandatory, growing up is optional.",
    "The best way to appreciate your job is to imagine being without one.",
    "A diamond is just a lump of coal that did well under pressure.",
    "Doing nothing is hard; you never know when you've finished.",
    "The older you get, the better you get, unless you're a banana.",
    "The wizard sees great success in your future.",
    "A new adventure awaits you, guided by the wisdom of TOTO.",
    "You will find what you seek with the help of a kind wizard.",
    "Believe in your dreams, for they are the wishes of your heart.",
    "The magic within you will lead you to greatness.",
    "Unexpected wealth will soon find its way to you.",
    "A faithful friend is a strong defense; seek out those you trust.",
    "Your creative mind will bring you prosperity.",
    "A journey of a thousand miles begins with a single step.",
    "Your efforts will soon be rewarded in the most magical way."
]

def verify_telegram_auth(init_data, bot_token):
    from urllib.parse import parse_qsl, unquote

    # Parse the init_data into a dictionary
    data = dict(parse_qsl(init_data, keep_blank_values=True))

    received_hash = data.pop('hash', None)
    if not received_hash:
        return False
    # Do not modify or decode the values before hashing

    # Sort the parameters
    sorted_data = sorted(data.items())

    # Construct the data check string using raw values
    data_check_string = '\n'.join([f"{k}={v}" for k, v in sorted_data])

    # Compute the secret key using HMAC-SHA256 with 'WebAppData' as the key
    secret_key = hmac.new(
        key=b'WebAppData',
        msg=bot_token.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()

    # Compute the hash
    computed_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()

    # Compare hashes
    if not hmac.compare_digest(computed_hash, received_hash):
        logging.error("Hash mismatch")
        logging.error(f"Computed hash: {computed_hash}")
        logging.error(f"Received hash: {received_hash}")
        logging.error(f"Data check string: {data_check_string}")
        return False

    # After verification, you can safely decode and process the data
    # For 'user' field, you may now URL-decode and parse it
    if 'user' in data:
        data['user'] = unquote(data['user'])
        try:
            user_data = json.loads(data['user'])
            data.update(user_data)
            data.pop('user')  # Remove the 'user' field as it's now expanded
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding user JSON: {e}")
            return False

    return data

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'User not authenticated'}), 401
        return f(*args, **kwargs)
    return decorated_function

@toto_magic.route('/')
def index():
    return render_template('toto_magic.html', bot_id=BOT_ID)

@app.route('/games/toto_magic/webhook', methods=['POST'])
@csrf.exempt
def webhook():
    try:
        logging.info("Processing webhook request")
        # Get the JSON data from the request
        update_data = request.get_json()
        logging.info(f"Received update: {update_data}")

        # Convert the JSON data into a telegram.Update object
        update = Update.de_json(update_data, bot)

        # Handle the update
        handle_update(update)
        return 'OK', 200
    except Exception as e:
        logging.error(f"Error processing webhook request: {e}")
        # Return 200 OK to prevent Telegram from resending the update
        return 'OK', 200

@toto_magic.route('/is_authenticated')
def is_authenticated():
    return jsonify({'is_authenticated': bool('user_id' in session)})

@toto_magic.route('/get_user_data', methods=['GET'])
@login_required
def get_user_data():
    user_id = session.get('user_id')
    user = query_db('SELECT * FROM users WHERE id = %s', (user_id,), one=True)
    if user is None:
        return jsonify({'error': 'User not found'}), 404
    user = dict(user)
    return jsonify({'user': user})

@toto_magic.route('/auth/telegram', methods=['POST'])
@csrf.exempt
def auth_telegram():
    bot_token = BOT_TOKEN  # Ensure this is set correctly

    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data received'}), 400

    encoded_init_data = data.get('initData')
    if not encoded_init_data:
        return jsonify({'status': 'error', 'message': 'Missing initData'}), 400

    # Base64 decode initData
    try:
        init_data_bytes = base64.b64decode(encoded_init_data)
        init_data = init_data_bytes.decode('utf-8')
    except Exception as e:
        logging.error(f"Error decoding initData: {e}")
        return jsonify({'status': 'error', 'message': 'Invalid initData encoding'}), 400

    # Log the initData for debugging
    logging.info(f"Received initData: {repr(init_data)}")

    # Use the updated verification function
    auth_data = verify_telegram_auth(init_data, bot_token)
    if not auth_data:
        return jsonify({'status': 'error', 'message': 'Invalid hash in initData'}), 403

    # Proceed to create or update the user
    create_or_update_user(auth_data)

    user_id = int(auth_data['id'])
    user_in_db = query_db('SELECT * FROM users WHERE id = %s', (user_id,), one=True)
    if user_in_db:
        user_data = dict(user_in_db)
    else:
        user_data = {}

    # Return a JSON response
    return jsonify({'status': 'ok', 'user': user_data})

def create_or_update_user(user_data, referrer_id=None):
    user_id = int(user_data['id'])
    username = user_data.get('username', '').strip()
    if not username:
        username = f"user_{user_id}"  # fallback if empty username didn't get set earlier

    # Store user details in session
    session['user_id'] = user_id
    session['username'] = username
    session['first_name'] = user_data.get('first_name', '')
    session['last_name'] = user_data.get('last_name', '')

    # Check if user already exists
    user_in_db = query_db('SELECT * FROM users WHERE id = %s', (user_id,), one=True)
    if user_in_db is None:
        # Handle duplicate usernames (in case another user with empty username existed)
        if username:
            username_exists = query_db('SELECT id FROM users WHERE username = %s', (username,), one=True)
            if username_exists and username_exists['id'] != user_id:
                # Append user ID to make username unique
                username = f"{username}_{user_id}"

        # Start user with 3 wishes, no beta wizard bonus, 0 balance
        is_beta_wizard = False
        balance = 0
        modify_db(
            'INSERT INTO users (id, username, balance, is_beta_wizard, last_wish_time, wish_count) VALUES (%s, %s, %s, %s, %s, %s)',
            (
                user_id,
                username,
                balance,
                int(is_beta_wizard),
                datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                3
            )
        )

        # Referral logic
        if referrer_id and str(user_id) != str(referrer_id):
            existing_referrer = query_db('SELECT referrer_id FROM users WHERE id = %s', (user_id,), one=True)
            if not existing_referrer or not existing_referrer['referrer_id']:
                # give bonus to new user
                balance += 100
                modify_db('UPDATE users SET balance = %s, referrer_id = %s WHERE id = %s', (balance, referrer_id, user_id))
                # give bonus to referrer
                referrer_in_db = query_db('SELECT * FROM users WHERE id = %s', (referrer_id,), one=True)
                if referrer_in_db:
                    modify_db(
                        'UPDATE users SET balance = balance + 100, referral_count = COALESCE(referral_count, 0) + 1 WHERE id = %s',
                        (referrer_id,)
                    )
                else:
                    modify_db(
                        'INSERT INTO users (id, username, balance, referral_count, last_wish_time, wish_count) VALUES (%s, %s, %s, %s, %s, %s)',
                        (
                            referrer_id,
                            '',  # unknown username for referrer
                            100,
                            1,
                            datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                            3
                        )
                    )
    else:
        # Optional: update user info if needed
        modify_db('UPDATE users SET first_name = %s, last_name = %s WHERE id = %s',
                  (user_data.get('first_name', ''), user_data.get('last_name', ''), user_id))

def get_user_wish_count(user_id):
    user = query_db('SELECT wish_count, last_wish_time FROM users WHERE id = %s', (user_id,), one=True)
    if not user:
        return 3, None  # Default to 3 wishes

    wish_count = user['wish_count']
    last_wish_time_str = user['last_wish_time']

    if last_wish_time_str:
        last_wish_time = datetime.strptime(str(last_wish_time_str), '%Y-%m-%d %H:%M:%S')
    else:
        last_wish_time = None

    if wish_count < 3 and last_wish_time:
        # Calculate the number of wishes to refill
        time_since_last_wish = datetime.utcnow() - last_wish_time
        hours_passed = time_since_last_wish.total_seconds() // 3600  # Convert to hours
        wishes_to_refill = int(hours_passed // 8)

        if wishes_to_refill > 0:
            wish_count = min(wish_count + wishes_to_refill, 3)
            last_wish_time = datetime.utcnow()
            modify_db('UPDATE users SET wish_count = %s, last_wish_time = %s WHERE id = %s',
                      (wish_count, last_wish_time.strftime('%Y-%m-%d %H:%M:%S'), user_id))
    else:
        last_wish_time = datetime.utcnow()
        modify_db('UPDATE users SET last_wish_time = %s WHERE id = %s',
                  (last_wish_time.strftime('%Y-%m-%d %H:%M:%S'), user_id))

    return wish_count, last_wish_time

@toto_magic.route('/make_wish', methods=['POST'])
@csrf.exempt  # Exempt CSRF protection for this route
@login_required
def make_wish():
    user_id = session.get('user_id')
    # At the beginning of make_wish()
    logging.info(f"User ID: {user_id}")

    user = query_db('SELECT * FROM users WHERE id = %s', (user_id,), one=True)
    if user is None:
        return jsonify({'error': 'User not found'}), 404

    # Convert user to a dictionary to use .get() method
    user = dict(user)

    wish_count, last_wish_time = get_user_wish_count(user_id)
    # After fetching wish_count and last_wish_time
    logging.info(f"Wish Count: {wish_count}, Last Wish Time: {last_wish_time}")

    if wish_count <= 0:
        # Calculate time until next wish refill
        if last_wish_time:
            time_since_last_wish = datetime.utcnow() - last_wish_time
            time_until_next_refill = timedelta(hours=8) - time_since_last_wish
            if time_until_next_refill.total_seconds() < 0:
                time_until_next_refill = timedelta(0)
            hours, remainder = divmod(time_until_next_refill.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            time_until_next_refill_str = f'{int(hours)}h {int(minutes)}m'
        else:
            time_until_next_refill_str = '8h 0m'

        return jsonify({
            'error': 'No wishes left.',
            'time_until_next_refill': time_until_next_refill_str
        }), 403

    # Process the wish
    result = random.choices(['High Reward', 'Small Reward', 'No Reward'], [0.1, 0.3, 0.6])[0]
    fortune = random.choice(fortunes)

    amount = 0
    if result != 'No Reward':
        amount = 100 if result == 'High Reward' else 10
        user_balance = user['balance'] + amount
        reward = f"{result}. You received {amount} gasless tokens."
    else:
        user_balance = user['balance']
        reward = result

    # Decrease wish count and update last_wish_time
    wish_count -= 1
    last_wish_time = datetime.utcnow()
    modify_db('UPDATE users SET balance = %s, wish_count = %s, last_wish_time = %s WHERE id = %s',
              (user_balance, wish_count, last_wish_time.strftime('%Y-%m-%d %H:%M:%S'), user_id))

    # Check for achievements
    achievements = []
    if not user.get('has_first_wish', False):
        user_balance += 10
        achievements.append({'achievement': "Baby's First Wish", 'tokens': 10})
        modify_db('UPDATE users SET balance = %s, has_first_wish = %s WHERE id = %s',
                  (user_balance, 1, user_id))
    response = {
        'status': 'success',
        'reward': reward,
        'fortune': fortune,
        'balance': user_balance,
        'coins': amount,
        'wish_count': wish_count,
        'time_until_next_refill': '8h 0m'
    }

    if achievements:
        response['achievements'] = achievements

    # Before returning the response
    logging.info(f"Response: {response}")

    return jsonify(response)

@toto_magic.route('/grant_extra_wish', methods=['POST'])
@csrf.exempt
@login_required
def grant_extra_wish():
    user_id = session.get('user_id')
    current_time = datetime.utcnow()

    # Check if the user has engaged with the tweet in the last 24 hours
    user = query_db('SELECT last_tweet_time, wish_count FROM users WHERE id = %s', (user_id,), one=True)
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found.'})

    last_tweet_time_str = user['last_tweet_time']
    if last_tweet_time_str:
        last_tweet_time = datetime.strptime(str(last_tweet_time_str), '%Y-%m-%d %H:%M:%S')
        time_since_last_tweet = current_time - last_tweet_time
        if time_since_last_tweet < timedelta(hours=24):
            return jsonify({'status': 'error', 'message': 'You can only use this feature once every 24 hours.'})

    # Grant the extra wish
    new_wish_count = min(user['wish_count'] + 1, 3)  # Max 3 wishes
    modify_db('UPDATE users SET wish_count = %s, last_tweet_time = %s WHERE id = %s',
              (new_wish_count, current_time.strftime('%Y-%m-%d %H:%M:%S'), user_id))

    return jsonify({'status': 'success', 'wish_count': new_wish_count})

@toto_magic.route('/grant_extra_wish_from_ad', methods=['POST'])
@csrf.exempt
@login_required
def grant_extra_wish_from_ad():
    user_id = session.get('user_id')
    current_time = datetime.utcnow().date()  # We'll compare just the date, if `last_ads_reset` is date
    user = query_db('SELECT daily_ads_used, last_ads_reset, wish_count FROM users WHERE id = %s',
                    (user_id,), one=True)
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found.'}), 404

    daily_ads_used = user['daily_ads_used'] or 0
    last_ads_reset = user['last_ads_reset']  # expected to be a date or possibly NULL
    wish_count = user['wish_count'] or 0

    # 1) Reset daily_ads_used if last_ads_reset != today's date
    if not last_ads_reset or last_ads_reset != current_time:
        daily_ads_used = 0
        # Update the DB to reflect the reset
        modify_db('UPDATE users SET daily_ads_used = 0, last_ads_reset = %s WHERE id = %s',
                  (current_time, user_id))

    # 2) Check if user has reached the limit of 3 ads per day
    if daily_ads_used >= 3:
        return jsonify({'status': 'error', 'message': 'You have already watched 3 ads today.'}), 403

    # 3) If wish_count is already 3, no need to add a wish
    if wish_count >= 3:
        return jsonify({'status': 'error', 'message': 'You already have 3 wishes.'}), 403

    # 4) Otherwise, proceed: grant an extra wish
    new_wish_count = wish_count + 1
    if new_wish_count > 3:
        new_wish_count = 3

    # 5) Increment daily_ads_used by 1
    new_daily_ads_used = daily_ads_used + 1

    # 6) Update DB
    modify_db('''
        UPDATE users
        SET wish_count = %s,
            daily_ads_used = %s,
            last_ads_reset = %s
        WHERE id = %s
    ''', (
        new_wish_count,
        new_daily_ads_used,
        current_time,   # keep track that we used an ad on this date
        user_id
    ))

    return jsonify({
        'status': 'success',
        'wish_count': new_wish_count,
        'daily_ads_used': new_daily_ads_used
    })

@toto_magic.route('/claim_collab_quest', methods=['POST'])
@csrf.exempt
@login_required
def claim_collab_quest():
    user_id = session.get('user_id')
    # Fetch user, check if they've already claimed
    user = query_db('SELECT balance, has_battleground_quest FROM users WHERE id = %s', (user_id,), one=True)
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found.'}), 404

    if user['has_battleground_quest'] == 1:
        return jsonify({'status': 'error', 'message': 'You already claimed the Collab Quest bonus.'})

    # Award +1000 coins, mark quest as claimed
    new_balance = user['balance'] + 1000
    modify_db('UPDATE users SET balance = %s, has_battleground_quest = 1 WHERE id = %s',
              (new_balance, user_id))

    return jsonify({'status': 'success', 'new_balance': new_balance})

# Route to get the TOTO Twitter quest status
@toto_magic.route('/get_follow_toto_status', methods=['GET'])
@csrf.exempt
@login_required
def get_follow_toto_status():
    user_id = session.get('user_id')
    row = query_db(
        'SELECT has_follow_toto_quest FROM users WHERE id = %s',
        (user_id,),
        one=True
    )
    if not row:
        return jsonify({'error': 'User not found'}), 404

    # 1 => quest done
    # 0 => quest not done
    if row['has_follow_toto_quest'] == 1:
        return jsonify({
            'done': True,
            'message': 'You have already completed the TOTOtheToad follow quest.'
        })
    else:
        return jsonify({
            'done': False,
            'message': 'You can claim this quest.'
        })

# Route to claim TOTO Twitter quest
@toto_magic.route('/claim_follow_toto_quest', methods=['POST'])
@csrf.exempt
@login_required
def claim_follow_toto_quest():
    user_id = session.get('user_id')
    row = query_db(
        'SELECT balance, has_follow_toto_quest FROM users WHERE id = %s',
        (user_id,),
        one=True
    )
    if not row:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404

    if row['has_follow_toto_quest'] == 1:
        return jsonify({
            'status': 'error',
            'message': 'You have already claimed this quest.'
        }), 403

    # Grant +1000 coins
    new_balance = row['balance'] + 1000

    # Mark quest as done
    modify_db(
        'UPDATE users SET balance = %s, has_follow_toto_quest = 1 WHERE id = %s',
        (new_balance, user_id)
    )

    return jsonify({
        'status': 'success',
        'new_balance': new_balance,
        'message': 'Follow TOTO quest claimed! +1000 coins!'
    })

@toto_magic.route('/get_wish_status', methods=['GET'])
@csrf.exempt
@login_required
def get_wish_status():
    user_id = session.get('user_id')
    wish_count, last_wish_time = get_user_wish_count(user_id)

    if wish_count < 3 and last_wish_time:
        time_since_last_wish = datetime.utcnow() - last_wish_time
        time_until_next_refill = timedelta(hours=8) - time_since_last_wish
        if time_until_next_refill.total_seconds() < 0:
            time_until_next_refill = timedelta(0)
        hours, remainder = divmod(time_until_next_refill.total_seconds(), 3600)
        minutes, _ = divmod(remainder, 60)
        time_until_next_refill_str = f'{int(hours)}h {int(minutes)}m'
    else:
        time_until_next_refill_str = '8h 0m'

    return jsonify({
        'wish_count': wish_count,
        'time_until_next_refill': time_until_next_refill_str
    })

# Define a helper function to calculate the daily reward based on the current day
def daily_reward_for_day(day):
    # Day 1 = 10, Day 2 = 20, ... Day 7 = 70
    # If day > 7, cap at 70
    return min(day * 10, 70)

@app.route('/games/toto_magic/get_daily_status', methods=['GET'])
@csrf.exempt
@login_required
def get_daily_status():
    user_id = session.get('user_id')
    # Fetch the user's daily check-in info
    result = query_db('SELECT current_day, last_claim_time FROM daily_checks WHERE user_id = %s', (user_id,), one=True)

    if not result:
        # No record found, user hasn't claimed yet
        return jsonify({'current_day': 1, 'time_until_next_claim': "00:00:00"})

    current_day = result['current_day']
    last_claim_dt = result['last_claim_time']

    # If never claimed before
    if last_claim_dt is None:
        return jsonify({'current_day': 1, 'time_until_next_claim': "00:00:00"})
    else:
        # Check type just in case
        if not isinstance(last_claim_dt, datetime):
            # If it's somehow a string, convert it
            # This should not happen if using mysql.connector which returns datetime directly
            last_claim_dt = datetime.strptime(str(last_claim_dt), '%Y-%m-%d %H:%M:%S')

        now = datetime.utcnow()
        time_diff = now - last_claim_dt
        hours_since_claim = time_diff.total_seconds() / 3600.0
        if hours_since_claim >= 24:
            # Reset day
            current_day = 1
            time_until_next_claim = 0
        else:
            time_until_next_claim = int((24 - hours_since_claim) * 3600)

        # Convert time_until_next_claim to HH:MM:SS
        h = time_until_next_claim // 3600
        m = (time_until_next_claim % 3600) // 60
        s = time_until_next_claim % 60
        time_str = f"{int(h):02d}:{int(m):02d}:{int(s):02d}"

        return jsonify({
            'current_day': current_day,
            'time_until_next_claim': time_str
        })


@app.route('/games/toto_magic/claim_daily', methods=['POST'])
@csrf.exempt
def claim_daily():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'User not authenticated'}), 403

    user_id = session['user_id']

    # Fetch user's daily info
    daily_info = query_db('SELECT current_day, last_claim_time FROM daily_checks WHERE user_id = %s', (user_id,), one=True)

    if not daily_info:
        # If no daily record exists, create one now since user never claimed
        current_day = 1
        now = datetime.utcnow()
        modify_db('INSERT INTO daily_checks (user_id, current_day, last_claim_time) VALUES (%s, %s, %s)',
                  (user_id, current_day, now))
        reward = current_day * 10
        user_info = query_db('SELECT balance FROM users WHERE id = %s', (user_id,), one=True)
        if not user_info:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        new_balance = user_info['balance'] + reward
        modify_db('UPDATE users SET balance = %s WHERE id = %s', (new_balance, user_id))
        return jsonify({
            'status': 'ok',
            'coins': reward,
            'new_balance': new_balance,
            'next_day': current_day,
            'last_claim_time': now.strftime('%Y-%m-%d %H:%M:%S')
        })

    current_day = daily_info['current_day']
    last_claim_dt = daily_info['last_claim_time']

    now = datetime.utcnow()

    if last_claim_dt is not None:
        if not isinstance(last_claim_dt, datetime):
            last_claim_dt = datetime.strptime(str(last_claim_dt), '%Y-%m-%d %H:%M:%S')

        # Check if user can claim today
        if now < last_claim_dt + timedelta(hours=24):
            # Not yet 24 hours since last claim
            remaining_td = (last_claim_dt + timedelta(hours=24)) - now
            # Convert remaining_td to HH:MM:SS
            total_seconds = int(remaining_td.total_seconds())
            h = total_seconds // 3600
            m = (total_seconds % 3600) // 60
            s = total_seconds % 60
            time_str = f"{int(h):02d}:{int(m):02d}:{int(s):02d}"

            return jsonify({'status': 'error', 'message': f'You can only claim once every 24 hours. Time remaining: {time_str}'}), 403
    else:
        # If never claimed before, they can claim now
        last_claim_dt = None

    # User can claim now
    new_day = current_day + 1 if current_day < 7 else 1
    reward = new_day * 10

    # Update user balance
    user_info = query_db('SELECT balance FROM users WHERE id = %s', (user_id,), one=True)
    if not user_info:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404

    new_balance = user_info['balance'] + reward
    modify_db('UPDATE users SET balance = %s WHERE id = %s', (new_balance, user_id))

    # Update daily checks
    modify_db('UPDATE daily_checks SET current_day = %s, last_claim_time = %s WHERE user_id = %s',
              (new_day, now, user_id))

    return jsonify({
        'status': 'ok',
        'coins': reward,
        'new_balance': new_balance,
        'next_day': new_day,
        'last_claim_time': now.strftime('%Y-%m-%d %H:%M:%S')
    })

@toto_magic.route('/leaderboard_content', methods=['GET'])
def leaderboard_content():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page
    max_users = 1000

    users = query_db('''
        SELECT id, username, balance, COALESCE(referral_count, 0) as referral_count
        FROM users
        ORDER BY balance DESC
        LIMIT %s OFFSET %s
    ''', (per_page, offset))

    total_users_row = query_db('SELECT COUNT(*) as count FROM users', one=True)
    total_users = total_users_row['count'] if total_users_row else 0
    total_pages = (min(max_users, total_users) + per_page - 1) // per_page

    return render_template('leaderboard_content.html', users=users, page=page, total_pages=total_pages, per_page=per_page)

@toto_magic.route('/leaderboard', methods=['GET'])
def leaderboard():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page
    max_users = 1000

    users = query_db('''
        SELECT username, balance
        FROM users
        ORDER BY balance DESC
        LIMIT %s OFFSET %s
    ''', (per_page, offset))

    total_users_row = query_db('SELECT COUNT(*) as count FROM users', one=True)
    total_users = total_users_row['count'] if total_users_row else 0
    total_pages = (min(max_users, total_users) + per_page - 1) // per_page

    return render_template('leaderboard.html', users=users, page=page, total_pages=total_pages, per_page=per_page)

@toto_magic.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('toto_magic.index'))

# Allow embedding in iframe
@toto_magic.after_request
def add_header(response):
    response.headers['X-Frame-Options'] = 'ALLOWALL'
    return response

# Register the Blueprint
app.register_blueprint(toto_magic)

csrf.init_app(app)
