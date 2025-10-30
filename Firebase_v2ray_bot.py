# -*- coding: utf-8 -*-

"""
FreeV2ray Telegram Bot - Firebase Edition (Multi-Language + Support)

This bot manages V2ray subscriptions, referrals (coins), and provides support.
It uses Firebase Firestore as a persistent database.
It requires a 'serviceAccountKey.json' file in the same directory.
"""

import logging
import asyncio
import re
from datetime import datetime

# Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials, firestore

# Telegram Bot Library (python-telegram-bot v20+)
# --- (FIXED) 'Message' import එක මෙතැනට එකතු කරන ලදී ---
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot, Message
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
)
# --- (FIXED) ParseMode import එක මෙතැනට වෙනස් කරන ලදී ---
from telegram.constants import ParseMode
# --------------------------------------------------


# --- Bot Settings (කරුණාකර මෙය සකසන්න) ---
BOT_TOKEN = "7015662481:AAGYK7Buir3TIezH38jpeeQ4mvQydY7tI_g"
OWNER_ID = 6687619682
MAIN_CHANNEL_ID = -1003209750658
MAIN_CHANNEL_USERNAME = "@freev2rayx" # @ දාන්න (e.g., @mychannel)
CHANNEL_INVITE_LINK = "https://t.me/freev2rayx" # Invite link (public or private)

# Referral Settings
COINS_PER_REFERRAL = 20
MIN_REFERRALS_FOR_PREMIUM = 5 # (දැන් මෙය භාවිතා නොවේ, නමුත් අනාගතයට තไว้)

# Broadcast Settings
BROADCAST_BATCH_SIZE = 25  # එක සැරේකට යවන ගණන
BROADCAST_SLEEP_TIME = 1   # batch අතර තත්පර ගණන

# --- Firebase Setup ---
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    logging.info("Firebase Firestore සාර්ථකව සම්බන්ධ විය.")
except FileNotFoundError:
    logging.error("!!! 'serviceAccountKey.json' file එක හමු නොවීය! !!!")
    logging.error("කරුණාකර key file එක, bot script එක ඇති folder එකේම තබන්න.")
    exit()
except ValueError as e:
    if "Could not deserialize key data" in str(e):
        logging.error("!!! 'serviceAccountKey.json' file එකේ අන්තර්ගතය වැරදියි! (Invalid JSON) !!!")
        logging.error("කරුණාකර Firebase වලින් අලුත් key file එකක් download කර paste කරන්න.")
        exit()
    else:
        logging.error(f"Firebase සම්බන්ධ වීමේ දෝෂයක්: {e}")
        exit()
except Exception as e:
    logging.error(f"Firebase ආරම්භ කිරීමේදී නොදන්නා දෝෂයක්: {e}")
    exit()

# Firestore Collections References
users_ref = db.collection("users")
admin_ref = db.collection("admin_settings")

# Conversation States (Support Feature සඳහා)
TYPING_SUPPORT_MESSAGE = 1

# --- Bot පණිවිඩ (සිංහල සහ English) ---
STRINGS = {
    'welcome': {
        'en': "👋 Welcome! Please select your language:",
        'si': "👋 ආයුබෝවන්! කරුණාකර ඔබගේ භාෂාව තෝරන්න:",
    },
    'force_join': {
        'en': (
            "You must join our main channel to use this bot.\n\n"
            f"Please join: {MAIN_CHANNEL_USERNAME}\n\n"
            "After joining, press the '✅ Joined' button."
        ),
        'si': (
            "මෙම bot භාවිතා කිරීමට, ඔබ අපගේ ප්‍රධාන නාලිකාවට (channel) සම්බන්ධ විය යුතුය.\n\n"
            f"කරුණාකර සම්බන්ධ වන්න: {MAIN_CHANNEL_USERNAME}\n\n"
            "සම්බන්ධ වූ පසු, '✅ සම්බන්ධ වුනා' බොත්තම ඔබන්න."
        ),
    },
    'joined_button': {
        'en': "✅ Joined",
        'si': "✅ සම්බන්ධ වුනා",
    },
    'checking_button': {
        'en': "Checking...",
        'si': "පරීක්ෂා කරමින්...",
    },
    'force_register': {
        'en': "Thanks for joining! 🙏\n\nNow, you need to register to get your referral link and access the bot.\n\nPlease use the command: `/register`",
        'si': "සම්බන්ධ වීම ගැන ස්තූතියි! 🙏\n\nදැන්, bot වෙත පිවිසීමට සහ ඔබගේ referral link එක ලබා ගැනීමට ඔබ ලියාපදිංචි විය යුතුය.\n\nකරුණාකර මෙම command එක භාවිතා කරන්න: `/register`",
    },
    'bot_menu_title': {
        'en': "✅ Welcome to the Bot Menu!\n\nHow can I help you?",
        'si': "✅ Bot Menu වෙත සාදරයෙන් පිළිගනිමු!\n\nමම ඔබට උදව් කළ හැක්කේ කෙසේද?",
    },
    'register_success': {
        'en': "✅ You are successfully registered!\n\nUse the buttons below to navigate.",
        'si': "✅ ඔබ සාර්ථකව ලියාපදිංචි විය!",
    },
    'already_registered': {
        'en': "You are already registered. Use the menu buttons to navigate.",
        'si': "ඔබ දැනටමත් ලියාපදිංචි වී ඇත. මෙනු බොත්තම් භාවිතා කරන්න.",
    },
    'my_account': {
        'en': "👤 **My Account**\n\n- **Your Coins:** `{coins}` 🪙\n- **Total Referrals:** `{refs}` 🙋‍♂️\n\n**Your Referral Link:**\n`{ref_link}`",
        'si': "👤 **මගේ ගිණුම**\n\n- **ඔබේ කාසි (Coins):** `{coins}` 🪙\n- **සම්පූර්ණ යොමු කිරීම් (Referrals):** `{refs}` 🙋‍♂️\n\n**ඔබගේ Referral Link එක:**\n`{ref_link}`",
    },
    'shop_title': {
        'en': "🛍️ **Premium V2Ray Shop**\n\nUse your coins to buy a package. Buying a package will alert the admin to create your service.\n\nYour Coins: `{coins}` 🪙",
        'si': "🛍️ **Premium V2Ray වෙළඳසැල**\n\nPackage එකක් මිලදී ගැනීමට ඔබගේ කාසි (coins) භාවිතා කරන්න. ඔබ මිලදී ගත් විට, admin හට service එක සෑදීමට දැනුම් දීමක් යයි.\n\nඔබේ කාසි: `{coins}` 🪙",
    },
    'not_enough_coins': {
        'en': "❌ **Purchase Failed**\n\nSorry, you don't have enough coins for this package.\n\n- Your Coins: `{coins}` 🪙\n- Package Cost: `{cost}` 🪙",
        'si': "❌ **මිලදී ගැනීම අසාර්ථකයි**\n\nකණගාටුයි, මෙම package එක සඳහා ඔබට ප්‍රමාණවත් කාසි නොමැත.\n\n- ඔබේ කාසි: `{coins}` 🪙\n- Package මිල: `{cost}` 🪙",
    },
    'purchase_success': {
        'en': "✅ **Purchase Successful!**\n\n`{cost}` coins have been deducted from your account.\n\nThe admin has been notified. Please wait patiently, your service will be created soon.",
        'si': "✅ **මිලදී ගැනීම සාර්ථකයි!**\n\nඔබගේ ගිණුමෙන් කාසි `{cost}` ක් අඩු කර ඇත.\n\nAdmin වෙත දැනුම් දී ඇත. කරුණාකර රැඳී සිටින්න, ඔබගේ service එක ඉක්මනින් සාදනු ඇත.",
    },
    'purchase_alert_to_admin': {
        'en': (
            "🔔 **New Purchase Alert!** 🔔\n\n"
            "**User:** {mention} (ID: `{user_id}`)\n"
            "**Package:** {package_name}\n"
            "**Cost:** {cost} Coins\n\n"
            "Please create the service for this user."
        ),
        'si': (
            "🔔 **නව මිලදී ගැනීමක්!** 🔔\n\n"
            "**User:** {mention} (ID: `{user_id}`)\n"
            "**Package:** {package_name}\n"
            "**මිල:** {cost} කාසි\n\n"
            "කරුණාකර මෙම user හට service එක සාදා දෙන්න."
        ),
    },
    'get_free_v2ray_no_post': {
        'en': "Sorry, the admin hasn't set up a free V2Ray post yet. Please check back later.",
        'si': "කණගාටුයි, admin තවමත් නොමිලේ V2Ray post එකක් සකසා නැත. කරුණාකර පසුව නැවත උත්සාහ කරන්න.",
    },
    'get_free_v2ray_follow_up': {
        'en': (
            "That was a free server!\n\n"
            "Tired of slow, crowded free servers? Get your own **Premium V2Ray** server!\n\n"
            "✅ High Speed\n"
            "✅ 99% Uptime\n"
            "✅ Low Ping\n\n"
            "Click /shop to see packages or /myaccount to check your coins!"
        ),
        'si': (
            "එය නොමිලේ දෙන ලද server එකකි!\n\n"
            "මන්දගාමී, සෙනඟ පිරුණු free server වලින් වෙහෙසට පත්ව සිටිනවාද? ඔබගේම **Premium V2Ray** server එකක් ලබා ගන්න!\n\n"
            "✅ අධික වේගය\n"
            "✅ 99% Uptime\n"
            "✅ අඩු Ping අගය\n\n"
            "Package බැලීමට /shop click කරන්න, නැතහොත් ඔබගේ කාසි (coins) බැලීමට /myaccount click කරන්න!"
        ),
    },
    'above_is_free': {
        'en': "⬆️ Here is your free server!",
        'si': "⬆️ ඔබගේ නොමිලේ server එක ඉහත ඇත!",
    },
    'support_start': {
        'en': "📨 **Support System**\n\nPlease type your question or problem now. The admin will receive your message and your User ID.\n\nType /cancel to abort.",
        'si': "📨 **සහාය පද්ධතිය (Support)**\n\nකරුණාකර ඔබගේ ප්‍රශ්නය හෝ ගැටලුව දැන් type කරන්න. Admin හට ඔබගේ පණිවිඩය සහ ඔබගේ User ID එක ලැබෙනු ඇත.\n\nඅවලංගු කිරීමට /cancel ලෙස type කරන්න.",
    },
    'support_message_sent': {
        'en': "✅ Your message has been sent to the admin. They will reply as soon as possible.",
        'si': "✅ ඔබගේ පණිවිඩය admin වෙත යවන ලදී. ඔවුන් හැකි ඉක්මනින් පිළිතුරු දෙනු ඇත.",
    },
    'support_forward_to_admin': {
        'en': "📨 Support ticket from {mention} (ID: `{user_id}`):\n\n--- MESSAGE ---",
        'si': "📨 {mention} (ID: `{user_id}`) ගෙන් support පණිවිඩයක්:\n\n--- MESSAGE ---",
    },
    'support_reply_admin_prompt': {
        'en': "To reply, use:\n`/reply {user_id} Your message here`",
        'si': "පිළිතුරු දීමට, මෙය භාවිතා කරන්න:\n`/reply {user_id} ඔබගේ පණිවිඩය`",
    },
    'support_reply_success_admin': {
        'en': "✅ Reply sent to User ID `{user_id}`.",
        'si': "✅ User ID `{user_id}` වෙත පිළිතුර යවන ලදී.",
    },
    'support_reply_fail_admin': {
        'en': "❌ Failed to send reply. The user might have blocked the bot. Error: {error}",
        'si': "❌ පිළිතුර යැවීමට නොහැකි විය. User සමහරවිට bot ව block කර ඇත. දෝෂය: {error}",
    },
    'support_reply_received_user': {
        'en': "📨 **Reply from Admin:**\n\n`{message}`",
        'si': "📨 **Admin ගෙන් පිළිතුරක්:**\n\n`{message}`",
    },
    'support_cancel': {
        'en': "Support request cancelled.",
        'si': "Support ඉල්ලීම අවලංගු කරන ලදී.",
    },
    'shop_button': {
        'en': "Shop",
        'si': "වෙළඳසැල",
    },
    'free_button': {
        'en': "Free V2Ray",
        'si': "නොමිලේ V2Ray",
    },
    'account_button': {
        'en': "My Account",
        'si': "මගේ ගිණුම",
    },
    'support_button': {
        'en': "Support",
        'si': "සහාය",
    },
    'back_button': {
        'en': "⬅️ Back",
        'si': "⬅️ ආපසු",
    },
}

# --- Premium Shop Packages ---
# 'callback_data': (Display Name, Price in Coins)
SHOP_PACKAGES = {
    "buy_30d_50g": ("30 Day - 50GB", 100),
    "buy_30d_100g": ("30 Day - 100GB", 200),
    "buy_30d_unlim": ("30 Day - Unlimited GB", 300),
    "buy_50d_50g": ("50 Day - 50GB", 200),
    "buy_50d_100g": ("50 Day - 100GB", 300),
    "buy_50d_unlim": ("50 Day - Unlimited GB", 400),
}


# --- Logging Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# PTB library එකෙන් එන අනවශ්‍ය log අඩු කරයි
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# === Utility Functions (උපකාරක Functions) ===

async def get_user_data(user_id):
    """Firestore එකෙන් user දත්ත ලබා ගනී."""
    doc_ref = users_ref.document(str(user_id))
    try:
        doc = await asyncio.to_thread(doc_ref.get)
        if doc.exists:
            return doc.to_dict()
    except Exception as e:
        logger.error(f"Firestore get_user_data (User: {user_id}) දෝෂයක්: {e}")
        # Firestore සම්බන්ධ වීමේ දෝෂයක් (e.g., key error)
        # මෙහිදී bot එක crash වීම වැළැක්වීමට හිස් data return කරයි
    
    # Default user data (අලුත් user or error)
    return {
        'id': user_id,
        'is_registered': False,
        'referral_count': 0,
        'coins': 0,
        'referred_by': None,
        'language': 'en' # Default භාෂාව English
    }

async def update_user_data(user_id, data):
    """Firestore එකේ user දත්ත යාවත්කාලීන කරයි."""
    try:
        doc_ref = users_ref.document(str(user_id))
        await asyncio.to_thread(doc_ref.set, data, merge=True)
    except Exception as e:
        logger.error(f"Firestore update_user_data (User: {user_id}) දෝෂයක්: {e}")

async def get_admin_settings():
    """Firestore එකෙන් admin settings ලබා ගනී."""
    try:
        doc_ref = admin_ref.document("settings")
        doc = await asyncio.to_thread(doc_ref.get)
        if doc.exists:
            return doc.to_dict()
    except Exception as e:
        logger.error(f"Firestore get_admin_settings දෝෂයක්: {e}")
        
    return {'free_v2ray_post_id': None}

async def update_admin_settings(data):
    """Firestore එකේ admin settings යාවත්කාලීන කරයි."""
    try:
        doc_ref = admin_ref.document("settings")
        await asyncio.to_thread(doc_ref.set, data, merge=True)
    except Exception as e:
        logger.error(f"Firestore update_admin_settings දෝෂයක්: {e}")

async def check_channel_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """User, channel එකේ සාමාජිකයෙක්දැයි පරීක්ෂා කරයි."""
    try:
        member = await context.bot.get_chat_member(chat_id=MAIN_CHANNEL_ID, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
        else:
            return False
    except Exception as e:
        logger.error(f"Channel membership පරීක්ෂා කිරීමේ දෝෂයක් (ID: {user_id}): {e}")
        # Bot එක channel එකේ admin නැත්නම් හෝ ID වැරදි නම්, error එකක් එයි.
        return False # ආරක්‍ෂිතම දේ False return කිරීමයි

def get_string(key: str, lang: str):
    """භාෂාවට අදාළව නියමිත පණිවිඩය ලබා දෙයි."""
    try:
        return STRINGS[key][lang]
    except KeyError:
        # භාෂාව නොමැති නම් default English පෙන්වයි
        try:
            return STRINGS[key]['en']
        except KeyError:
            logger.error(f"STRING එකක් හමු නොවීය! Key: {key}")
            return f"MISSING_STRING_FOR_{key}"

def user_mention(user):
    """Markdown වලදී user ව mention කිරීමට short-hand එකක්."""
    if user.username:
        return f"@{user.username}"
    else:
        # MarkdownV2 වලදී විශේෂ අක්ෂර escape කළ යුතුය
        name = re.sub(r'([\[\]\(\)~`>#\+\-=|{}\.!])', r'\\\1', user.first_name)
        return f"[{name}](tg://user?id={user.id})"

# === User Check Decorator ===
# (මෙය /shop, /free, /myaccount වැනි commands වලට පෙර run වේ)

from functools import wraps

def user_checks(func):
    """
    Decorator එකක්. User, channel එකේ සහ register වී ඇත්දැයි පරීක්ෂා කරයි.
    නැතහොත්, අදාළ "force" පණිවිඩය යවයි.
    """
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        # as_callback=True ලෙස ආවොත්, update එක query එකක්
        message = update.message or update.callback_query.message
        user = update.effective_user
        
        user_data = await get_user_data(user.id)
        lang = user_data.get('language', 'en') # User ගේ භාෂාව ලබා ගනී

        # 1. Channel Member Check
        is_member = await check_channel_membership(user.id, context)
        if not is_member:
            keyboard = [[InlineKeyboardButton(f"🔗 {MAIN_CHANNEL_USERNAME}", url=CHANNEL_INVITE_LINK)],
                        [InlineKeyboardButton(f"✅ {get_string('joined_button', lang)}", callback_data="check_join_menu")]]
            await message.reply_text(
                get_string('force_join', lang),
                reply_markup=InlineKeyboardMarkup(keyboard),
                disable_web_page_preview=True
            )
            if update.callback_query:
                await update.callback_query.answer() # Button එකට loading අයින් කරයි
            return

        # 2. Registration Check
        if not user_data.get('is_registered', False):
            await message.reply_text(get_string('force_register', lang))
            if update.callback_query:
                await update.callback_query.answer() # Button එකට loading අයින් කරයි
            return

        # Checks Pass
        # User, channel එකේ සහ register වී ඇත්නම්, අදාළ command එක (func) run කරයි
        
        # kwargs හරහා user_data සහ lang pass කරයි
        kwargs['user_data'] = user_data
        kwargs['lang'] = lang
        
        # update object එක callback query එකක්ද command එකක්ද යන්න අනුව func එක call කරයි
        if update.callback_query:
             # Callback query එකක් නම්, update object එක සම්පූර්ණයෙන්ම යවයි
            return await func(update, context, *args, **kwargs)
        else:
            # Command එකක් නම්, update object එක යවයි
            return await func(update, context, *args, **kwargs)

    return wrapped


# === Bot Command Handlers ===

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot ආරම්භක command එක. Referral logic සහ language select."""
    user = update.effective_user
    user_data = await get_user_data(user.id)
    args = context.args

    # --- Language Selection (භාෂාව තේරීම) ---
    # User register වී නැත්නම් හෝ language එකක් set කර නැත්නම්
    if not user_data.get('is_registered', False) or not user_data.get('language'):
        # Referral Logic (භාෂාව තේරීමට පෙරම referral save කර ගනී)
        # User අලුත් සහ referral link එකකින් පැමිණියේ නම්
        if not user_data.get('referred_by') and args and args[0].isdigit():
            referrer_id = int(args[0])
            if referrer_id != user.id:
                user_data['referred_by'] = referrer_id
                await update_user_data(user.id, user_data)
                logger.info(f"User {user.id} was referred by {referrer_id} (pending registration)")

        # Language selection buttons
        keyboard = [
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
            [InlineKeyboardButton("🇱🇰 සිංහල", callback_data="lang_si")],
        ]
        await update.message.reply_text(
            f"{get_string('welcome', 'en')}\n\n{get_string('welcome', 'si')}", # භාෂා දෙකෙන්ම පෙන්වයි
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # --- User දැනටමත් register වී, භාෂාවක් තෝරා ඇත්නම් ---
    lang = user_data['language']
    is_member = await check_channel_membership(user.id, context)

    if not is_member:
        keyboard = [[InlineKeyboardButton(f"🔗 {MAIN_CHANNEL_USERNAME}", url=CHANNEL_INVITE_LINK)],
                    [InlineKeyboardButton(f"✅ {get_string('joined_button', lang)}", callback_data="check_join_menu")]]
        await update.message.reply_text(
            get_string('force_join', lang),
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )
    else:
        # User is member and registered, show bot menu
        await show_bot_menu(update, context, lang)


async def language_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Language selection button එක handle කරයි."""
    query = update.callback_query
    # --- (FIXED) effective_user වෙනුවට from_user භාවිතා කිරීම ---
    user = query.from_user 
    # ----------------------------------------------------
    await query.answer()
    
    lang_code = query.data.split("_")[1] # "lang_en" -> "en"
    
    user_data = await get_user_data(user.id)
    user_data['language'] = lang_code
    await update_user_data(user.id, user_data)
    
    logger.info(f"User {user.id} selected language: {lang_code}")

    # භාෂාව තේරූ පසු, channel check එක run කරයි
    is_member = await check_channel_membership(user.id, context)
    
    if not is_member:
        keyboard = [[InlineKeyboardButton(f"🔗 {MAIN_CHANNEL_USERNAME}", url=CHANNEL_INVITE_LINK)],
                    [InlineKeyboardButton(f"✅ {get_string('joined_button', lang_code)}", callback_data="check_join_menu")]]
        await query.edit_message_text(
            get_string('force_join', lang_code),
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )
    else:
        # Channel එකේ සිටී නම්, register පණිවිඩය පෙන්වයි
        await query.edit_message_text(get_string('force_register', lang_code))


async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User ලියාපදිංචි කිරීමේ command එක."""
    user = update.effective_user
    user_data = await get_user_data(user.id)
    lang = user_data.get('language', 'en')

    # 1. Channel Member Check
    is_member = await check_channel_membership(user.id, context)
    if not is_member:
        keyboard = [[InlineKeyboardButton(f"🔗 {MAIN_CHANNEL_USERNAME}", url=CHANNEL_INVITE_LINK)],
                    [InlineKeyboardButton(f"✅ {get_string('joined_button', lang)}", callback_data="check_join_register")]]
        await update.message.reply_text(
            get_string('force_join', lang),
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )
        return
    
    # 2. Already Registered Check
    if user_data.get('is_registered', False):
        await update.message.reply_text(get_string('already_registered', lang))
        await show_bot_menu(update, context, lang)
        return

    # --- New Registration Process ---
    user_data['is_registered'] = True
    user_data['username'] = user.username or user.first_name
    
    # Referral Coin Logic
    referrer_id = user_data.get('referred_by')
    if referrer_id:
        # Referrer (හඳුන්වා දුන් user) ගේ දත්ත update කරයි
        referrer_data = await get_user_data(referrer_id)
        # Referrer ද register වී ඇත්නම් පමණක් coins දෙයි
        if referrer_data.get('is_registered', False):
            referrer_data['referral_count'] = referrer_data.get('referral_count', 0) + 1
            referrer_data['coins'] = referrer_data.get('coins', 0) + COINS_PER_REFERRAL
            await update_user_data(referrer_id, referrer_data)
            
            logger.info(f"User {referrer_id} received {COINS_PER_REFERRAL} coins for referring {user.id}")
            
            # Referrer ට දන්වයි (Optional)
            try:
                ref_lang = referrer_data.get('language', 'en')
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=f"Congrats! A user you referred ({user_mention(user)}) has joined. You received {COINS_PER_REFERRAL} coins! 🪙"
                         if ref_lang == 'en' else
                         f"සුබ පැතුම්! ඔබ හඳුන්වා දුන් user ({user_mention(user)}) සම්බන්ධ විය. ඔබට කාසි {COINS_PER_REFERRAL} ක් ලැබුණා! 🪙",
                    parse_mode=ParseMode.MARKDOWN_V2
                )
            except Exception as e:
                logger.warning(f"Referrer {referrer_id} ට පණිවිඩය යැවීමට නොහැකි විය: {e}")
        else:
            logger.info(f"Referrer {referrer_id} is not registered. Holding referral for {user.id}.")
            # (Note: Referrer register වූ විට මෙම coin දෙන්නට logic එකක් අවශ්‍ය නම්, එය සංකීර්ණයි)

    await update_user_data(user.id, user_data)
    logger.info(f"New user registered: {user.id} ({user_data['username']})")

    await update.message.reply_text(get_string('register_success', lang))
    await show_bot_menu(update, context, lang)


async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """'✅ Joined' button එක handle කරයි."""
    query = update.callback_query
    # --- (FIXED) effective_user වෙනුවට from_user භාවිතා කිරීම ---
    user = query.from_user
    # ----------------------------------------------------
    
    user_data = await get_user_data(user.id)
    lang = user_data.get('language', 'en')

    await query.answer(f"{get_string('checking_button', lang)}", show_alert=False)
    is_member = await check_channel_membership(user.id, context)

    if is_member:
        await query.answer("✅ Thank you for joining!")
        callback_action = query.data # "check_join_menu" or "check_join_register"
        
        if callback_action == "check_join_register" or not user_data.get('is_registered', False):
            # Register command එක run කිරීමට user ව යොමු කරයි
            await query.edit_message_text(get_string('force_register', lang))
        else:
            # Bot menu එක පෙන්වයි
            await show_bot_menu(update, context, lang, query.message.message_id) # message edit කරයි
    else:
        await query.answer("❌ You haven't joined the channel yet.", show_alert=True)


async def show_bot_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, edit_message_id: int = None):
    """ප්‍රධාන bot menu (buttons) පෙන්වයි."""
    keyboard = [
        [
            InlineKeyboardButton(f"🛍️ {get_string('shop_button', lang)}", callback_data="menu_shop"),
            InlineKeyboardButton(f"🎁 {get_string('free_button', lang)}", callback_data="menu_free"),
        ],
        [
            InlineKeyboardButton(f"👤 {get_string('account_button', lang)}", callback_data="menu_account"),
            InlineKeyboardButton(f"📨 {get_string('support_button', lang)}", callback_data="menu_support"),
        ]
    ]
    
    text = get_string('bot_menu_title', lang)
    
    message = update.message or (update.callback_query and update.callback_query.message)
    if not message:
         logger.warning("show_bot_menu: 'message' object එකක් සොයාගත නොහැක.")
         return

    if edit_message_id:
        # පවතින message එක edit කරයි (e.g., check_join පසු)
        try:
            await context.bot.edit_message_text(
                chat_id=message.chat_id,
                message_id=edit_message_id,
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return # Edit කළ පසු, exit
        except Exception as e:
            logger.warning(f"Bot menu edit කිරීමේ දෝෂයක්: {e}")
            # Edit fail වුනොත්, අලුත් message එකක් යවයි (පහළ code එක run වේ)
    
    # අලුත් message එකක් යවයි
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))



async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ප්‍රධාන menu බොත්තම් handle කරයි."""
    query = update.callback_query
    await query.answer()
    
    # --- (FIXED) effective_user වෙනුවට from_user භාවිතා කිරීම ---
    user = query.from_user
    # ----------------------------------------------------
    user_data = await get_user_data(user.id)
    lang = user_data.get('language', 'en')
    
    # User checks (නැවතත් පරීක්ෂා කිරීම)
    is_member = await check_channel_membership(user.id, context)
    if not is_member or not user_data.get('is_registered', False):
        # User තවදුරටත් member කෙනෙක් නොවේ නම්, /start එකට යොමු කරයි
        await query.message.reply_text("Please /start the bot again.")
        return

    # Menu actions
    action = query.data.split("_")[-1] # "menu_shop" -> "shop"

    # user_checks decorator එකට අවශ්‍ය kwargs
    kwargs = {'user_data': user_data, 'lang': lang}

    if action == "shop":
        await shop_command(update, context, **kwargs)
    elif action == "free":
        await free_command(update, context, **kwargs)
    elif action == "account":
        await myaccount_command(update, context, **kwargs)
    elif action == "support":
        # Support command එක ConversationHandler එකක් නිසා,
        # අපි command එකක් call කරනවා වගේ පටන් ගන්න ඕනේ.
        await support_start(update, context, **kwargs)


@user_checks
async def myaccount_command(update: Update, context: ContextTypes.DEFAULT_TYPE, **kwargs):
    """User ගේ coin balance සහ referral link එක පෙන්වයි."""
    user_data = kwargs['user_data']
    lang = kwargs['lang']
    user_id = user_data['id']
    
    bot_username = (await context.bot.get_me()).username
    ref_link = f"https{':'}//t.me/{bot_username}?start={user_id}"
    
    text = get_string('my_account', lang).format(
        coins=user_data.get('coins', 0),
        refs=user_data.get('referral_count', 0),
        ref_link=ref_link
    )
    
    message = update.message or update.callback_query.message
    keyboard = [[InlineKeyboardButton(f"⬅️ {get_string('back_button', lang)}", callback_data="back_to_menu")]]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)
    else:
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)


@user_checks
async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE, **kwargs):
    """Premium shop එක (buttons) පෙන්වයි."""
    user_data = kwargs['user_data']
    lang = kwargs['lang']
    
    text = get_string('shop_title', lang).format(coins=user_data.get('coins', 0))
    
    keyboard = []
    # SHOP_PACKAGES dictionary එකෙන් බොත්තම් සාදයි
    for callback_data, (display_name, price) in SHOP_PACKAGES.items():
        button_text = f"{display_name} - {price} 🪙"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton(f"⬅️ {get_string('back_button', lang)}", callback_data="back_to_menu")])
    
    message = update.message or update.callback_query.message
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN_V2)
    else:
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN_V2)


@user_checks
async def free_command(update: Update, context: ContextTypes.DEFAULT_TYPE, **kwargs):
    """Admin විසින් set කළ free V2Ray post එක forward කරයි."""
    lang = kwargs['lang']
    
    admin_settings = await get_admin_settings()
    post_id = admin_settings.get('free_v2ray_post_id')
    
    message = update.message or update.callback_query.message

    if not post_id:
        await message.reply_text(get_string('get_free_v2ray_no_post', lang))
        return

    try:
        # Main Channel එකෙන් අදාළ post එක forward කරයි
        await context.bot.forward_message(
            chat_id=message.chat_id,
            from_chat_id=MAIN_CHANNEL_ID,
            message_id=post_id
        )
        # Follow-up message (Premium ගැන)
        await message.reply_text(get_string('get_free_v2ray_follow_up', lang), parse_mode=ParseMode.MARKDOWN_V2)
        
    except Exception as e:
        logger.error(f"Free post (ID: {post_id}) forward කිරීමේ දෝෂයක්: {e}")
        await message.reply_text("Error: Could not retrieve the free V2Ray post. The admin may need to update it.")
    
    if update.callback_query:
        # Callback query එකක් නම්, "Back" button එකක් යවයි
        keyboard = [[InlineKeyboardButton(f"⬅️ {get_string('back_button', lang)}", callback_data="back_to_menu")]]
        await message.reply_text(f"⬆️ {get_string('above_is_free', lang)}", reply_markup=InlineKeyboardMarkup(keyboard))


async def shop_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shop එකේ "Buy" බොත්තම් handle කරයි."""
    query = update.callback_query
    # --- (FIXED) effective_user වෙනුවට from_user භාවිතා කිරීම ---
    user = query.from_user
    # ----------------------------------------------------
    await query.answer()
    
    user_data = await get_user_data(user.id)
    lang = user_data.get('language', 'en')
    
    package_key = query.data # e.g., "buy_30d_50g"
    
    if package_key not in SHOP_PACKAGES:
        await query.message.reply_text("Error: Invalid package selected.")
        return

    package_name, package_cost = SHOP_PACKAGES[package_key]
    user_coins = user_data.get('coins', 0)

    # Check if user has enough coins
    if user_coins < package_cost:
        await query.message.reply_text(
            get_string('not_enough_coins', lang).format(
                coins=user_coins,
                cost=package_cost
            )
        )
        return

    # --- Purchase is successful ---
    # 1. Deduct coins
    user_data['coins'] = user_coins - package_cost
    await update_user_data(user.id, user_data)
    
    # 2. Notify user
    await query.message.reply_text(
        get_string('purchase_success', lang).format(cost=package_cost)
    )
    
    # 3. Notify admin
    try:
        admin_alert_text = get_string('purchase_alert_to_admin', 'en').format( # Admin ට English වලින්
            mention=user_mention(user),
            user_id=user.id,
            package_name=package_name,
            cost=package_cost
        )
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=admin_alert_text,
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f"Admin (ID: {OWNER_ID}) ට purchase alert එක යැවීමේ දෝෂයක්: {e}")

    # Go back to menu
    await show_bot_menu(update, context, lang, query.message.message_id)


async def back_to_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """'Back' button (Shop/Account වලින්) handle කරයි."""
    query = update.callback_query
    await query.answer()
    # --- (FIXED) effective_user වෙනුවට from_user භාවිතා කිරීම ---
    user = query.from_user
    # ----------------------------------------------------
    user_data = await get_user_data(user.id)
    lang = user_data.get('language', 'en')
    
    await show_bot_menu(update, context, lang, query.message.message_id)


# === Support Conversation Handler ===

@user_checks
async def support_start(update: Update, context: ContextTypes.DEFAULT_TYPE, **kwargs):
    """Support conversation එක පටන් ගනී."""
    lang = kwargs['lang']
    text = get_string('support_start', lang)
    
    message = update.message or update.callback_query.message
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2)
    else:
        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
        
    return TYPING_SUPPORT_MESSAGE # Conversation එකේ ඊළඟ state එකට යයි

async def get_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User ගේ support message එක ලබාගෙන Admin ට forward කරයි."""
    user = update.effective_user
    user_data = await get_user_data(user.id)
    lang = user_data.get('language', 'en')
    
    message = update.message
    
    # 1. Admin ට Forward කරයි
    try:
        admin_alert_text = get_string('support_forward_to_admin', 'en').format( # Admin ට English වලින්
            mention=user_mention(user),
            user_id=user.id
        )
        admin_reply_prompt = get_string('support_reply_admin_prompt', 'en').format(user_id=user.id)
        
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=admin_alert_text,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        # User ගේ message එක වෙනම forward කරයි (Stickers, Photos ආදියට)
        await message.forward(chat_id=OWNER_ID)
        # Admin ට reply කරන හැටි යවයි
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=admin_reply_prompt
        )
        
        # 2. User ට දන්වයි
        await message.reply_text(get_string('support_message_sent', lang))
        
    except Exception as e:
        logger.error(f"Support message (User: {user.id}) forward කිරීමේ දෝෂයක්: {e}")
        await message.reply_text("An error occurred while sending your message. Please try again.")

    return ConversationHandler.END # Conversation එක අවසන් කරයි

async def cancel_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Support conversation එක cancel කරයි."""
    user = update.effective_user
    user_data = await get_user_data(user.id)
    lang = user_data.get('language', 'en')
    
    await update.message.reply_text(get_string('support_cancel', lang))
    await show_bot_menu(update, context, lang) # Menu එක නැවත පෙන්වයි
    return ConversationHandler.END



# === Admin Command Handlers (Owner ට පමණි) ===

async def admin_only_filter(message: Message, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Command එක Owner ගෙන් දැයි පරීක්ෂා කරයි."""
    return message.from_user.id == OWNER_ID

admin_filter = filters.Chat(OWNER_ID) & filters.COMMAND

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin ට සියලුම user ලාට broadcast කිරීමට."""
    message = update.message
    
    if not message.reply_to_message:
        await message.reply_text("Please reply to a message to broadcast it.")
        return

    broadcast_message = message.reply_to_message
    
    # Firestore එකෙන් සියලුම registered user IDs ලබා ගනී
    try:
        all_users_docs = await asyncio.to_thread(users_ref.where("is_registered", "==", True).stream)
        user_ids = [doc.id for doc in all_users_docs]
    except Exception as e:
        await message.reply_text(f"Error fetching users from Firestore: {e}")
        return

    if not user_ids:
        await message.reply_text("No registered users found to broadcast to.")
        return

    await message.reply_text(f"Starting broadcast to {len(user_ids)} users...")
    
    success_count = 0
    failed_count = 0
    
    # Batch sending
    for i in range(0, len(user_ids), BROADCAST_BATCH_SIZE):
        batch = user_ids[i:i + BROADCAST_BATCH_SIZE]
        for user_id_str in batch:
            try:
                user_id = int(user_id_str)
                await broadcast_message.copy(chat_id=user_id)
                success_count += 1
            except Exception as e:
                failed_count += 1
                logger.warning(f"Broadcast to user {user_id} failed: {e}")
        
        # Telegram flood limits වළක්වා ගැනීමට sleep
        logger.info(f"Broadcast batch {i//BROADCAST_BATCH_SIZE + 1} sent. Sleeping for {BROADCAST_SLEEP_TIME}s...")
        await asyncio.sleep(BROADCAST_SLEEP_TIME) 
        
    await message.reply_text(
        f"Broadcast finished.\n"
        f"✅ Sent successfully: {success_count}\n"
        f"❌ Failed (bot blocked?): {failed_count}"
    )


async def send_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Alias for /broadcast (broadcast command එකම call කරයි)"""
    await broadcast_command(update, context)


async def setfree_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/free command එක සඳහා post ID එක set කරයි."""
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Usage: `/setfree <message_id>`\n\n(Get the ID by forwarding a post from your channel to me.)")
        return
        
    post_id = int(args[0])
    await update_admin_settings({'free_v2ray_post_id': post_id})
    await update.message.reply_text(f"✅ Free V2Ray post ID has been set to: {post_id}")


async def post_id_finder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Channel එකෙන් forward කරන post වල ID එක ලබා දෙයි."""
    message = update.message
    if message.forward_from_chat and message.forward_from_chat.id == MAIN_CHANNEL_ID:
        post_id = message.forward_from_message_id
        await message.reply_text(
            f"Message ID from channel found: `{post_id}`\n\n"
            f"Use this command to set it:\n"
            f"`/setfree {post_id}`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    else:
        await message.reply_text("This is not a forwarded post from your Main Channel.")


async def addcoins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User කෙනෙකුට manually coins දීමට."""
    args = context.args
    if len(args) != 2 or not args[0].isdigit() or not args[1].isdigit():
        await update.message.reply_text("Usage: `/addcoins <user_id> <amount>`")
        return

    target_user_id = int(args[0])
    amount = int(args[1])
    
    try:
        user_data = await get_user_data(target_user_id)
        if not user_data.get('is_registered', False):
            await update.message.reply_text(f"Error: User ID {target_user_id} is not registered yet.")
            return
            
        user_data['coins'] = user_data.get('coins', 0) + amount
        await update_user_data(target_user_id, user_data)
        
        await update.message.reply_text(f"✅ Added {amount} coins to User ID {target_user_id}. New balance: {user_data['coins']} 🪙")
        
        # User ට දන්වයි
        try:
            lang = user_data.get('language', 'en')
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"🎁 Admin has added {amount} coins to your account! Your new balance is {user_data['coins']} 🪙."
                     if lang == 'en' else
                     f"🎁 Admin විසින් ඔබගේ ගිණුමට කාසි {amount} ක් එකතු කරන ලදී! ඔබගේ නව ශේෂය {user_data['coins']} 🪙."
            )
        except Exception as e:
            logger.warning(f"User {target_user_id} ට addcoins alert එක යැවීමට නොහැකි විය: {e}")
            
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")


async def reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Support ticket එකකට පිළිතුරු (reply) යවයි."""
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: `/reply <user_id> <message_text>`")
        return

    try:
        target_user_id = int(args[0])
    except ValueError:
        await update.message.reply_text("Invalid User ID. Usage: `/reply <user_id> <message_text>`")
        return
        
    reply_message = " ".join(args[1:])
    
    try:
        target_user_data = await get_user_data(target_user_id)
        lang = target_user_data.get('language', 'en')
        
        await context.bot.send_message(
            chat_id=target_user_id,
            text=get_string('support_reply_received_user', lang).format(message=reply_message),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        
        await update.message.reply_text(
            get_string('support_reply_success_admin', 'en').format(user_id=target_user_id)
        )
        
    except Exception as e:
        logger.error(f"Support reply to {target_user_id} failed: {e}")
        await update.message.reply_text(
            get_string('support_reply_fail_admin', 'en').format(user_id=target_user_id, error=e)
        )


# === Main Function (Bot එක පණ ගන්වයි) ===

def main():
    """Bot එක පණ ගන්වා run කරයි."""
    
    try:
        # Bot token එකෙන් Application එක සාදයි
        application = Application.builder().token(BOT_TOKEN).build()
    except Exception as e:
        logger.critical(f"Bot Token එකේ දෝෂයක්: {e}")
        logger.critical("Bot Token එක 'BOT_TOKEN' variable එකේ නිවැරදිව ඇතුළත් කර ඇත්දැයි පරීක්ෂා කරන්න.")
        return

    # --- Support Conversation Handler ---
    support_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("support", user_checks(support_start)),
            CallbackQueryHandler(main_menu_callback, pattern="^menu_support$")
        ],
        states={
            TYPING_SUPPORT_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_support_message)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_support)],
    )
    
    # --- User Handlers ---
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("register", register_command))
    application.add_handler(CallbackQueryHandler(language_button_handler, pattern="^lang_"))
    application.add_handler(CallbackQueryHandler(check_join_callback, pattern="^check_join_"))
    
    # Main Menu Commands & Callbacks
    # user_checks decorator එක command එකටම bind කරයි
    application.add_handler(CommandHandler("myaccount", myaccount_command))
    application.add_handler(CommandHandler("shop", shop_command))
    application.add_handler(CommandHandler("free", free_command))
    
    # Menu බොත්තම් (shop, free, account) main_menu_callback එකට යොමු කරයි
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^menu_(shop|free|account)$"))
    application.add_handler(CallbackQueryHandler(back_to_menu_callback, pattern="^back_to_menu$"))
    
    # Shop "Buy" buttons
    application.add_handler(CallbackQueryHandler(shop_button_handler, pattern="^buy_"))
    
    # Support Handler (ConversationHandler එක)
    application.add_handler(support_conv_handler)
    
    
    # --- Admin Handlers (Owner ට පමණි) ---
    application.add_handler(CommandHandler("broadcast", broadcast_command, filters=admin_filter))
    application.add_handler(CommandHandler("send", send_command, filters=admin_filter))
    application.add_handler(CommandHandler("setfree", setfree_command, filters=admin_filter))
    application.add_handler(CommandHandler("addcoins", addcoins_command, filters=admin_filter))
    application.add_handler(CommandHandler("reply", reply_command, filters=admin_filter))
    
    # Admin Post ID Finder (Owner ගෙන් එන forward වලට)
    application.add_handler(MessageHandler(
        filters.FORWARDED & filters.Chat(OWNER_ID),
        post_id_finder
    ))
    
    # --- Error Handler ---
    # application.add_error_handler(error_handler) # (අවශ්‍ය නම් පසුව එකතු කළ හැක)

    # Bot Run
    logger.info("Bot is starting to poll...")
    application.run_polling()


if __name__ == "__main__":
    main()

