# -*- coding: utf-8 -*-

"""
FreeV2ray Telegram Bot (Firebase + Multi-Language Edition)

මෙම bot ක්‍රියාත්මක වීමට පෙර:
1.  `pip install python-telegram-bot firebase-admin` install කරන්න.
2.  ඔබගේ Firebase `serviceAccountKey.json` file එක මෙම file එක ඇති තැනම තබන්න.
"""

import logging
import asyncio
from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler, 
    filters, CallbackQueryHandler
)
from telegram.error import Forbidden, BadRequest

# Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# --- CONFIGURATION (කරුණාකර මෙය නිවැරදිව පුරවන්න) ---
BOT_TOKEN = "7015662481:AAGYK7Buir3TIezH38jpeeQ4mvQydY7tI_g"
OWNER_ID = 6687619682
MAIN_CHANNEL_ID = -1003209750658
CHANNEL_INVITE_LINK = "https://t.me/freev2rayx"
REFERRAL_COIN_VALUE = 20
BROADCAST_BATCH_SIZE = 25

# --- (NEW) Multi-Language Strings (භාෂා ගබඩාව) ---
STRINGS = {
    'en': {
        'select_language': "👋 Welcome! Please select your language:",
        'please_join': "**🛑 Stop!**\n\nTo use this bot, you must first join our main channel.\n\nJoin the channel, then click /start again.",
        'welcome_not_registered': "Welcome {first_name}! 🇱🇰\n\nTo get your referral link and use all bot services (Shop, Free V2ray), please register first.\n\n👉 Type /register to register.",
        'welcome_registered': "Welcome back, {first_name}! 🇱🇰\n\n💰 **Your Coin Balance:** {coins} Coins\n\n**Available Commands:**\n🛒 /shop - Buy premium packages.\n🎁 /free - Get the daily free V2ray config.\n📊 /myaccount - View your account and referral link.",
        'err_not_registered': "🔒 **You are not registered!**\n\nTo use this feature, please type /register first.",
        'register_success': "✅ **Registration Successful!**\n\nYou can now use /shop and /free.\n\n🔗 **Your Referral Link:**\n`{link}`\n\nShare this link and earn **{value} Coins** for each referral!",
        'register_already': "✅ You are already registered!\n\nUse /myaccount to get your referral link.",
        'referral_notify': "🎉 Congratulations! {user_name} registered using your link.\nYou received **{value} Coins**!\n\n💰 **Your new Coin Balance:** {new_balance} Coins",
        'my_account': "**📊 My Account**\n\n📈 **Total Referrals:** {ref_count}\n💰 **Coin Balance:** {coins} Coins\n\n🔗 **Your Referral Link:**\n`{link}`\n\nType /shop to buy V2ray packages.",
        'shop_title': "🛒 **FreeV2ray Shop** 🛒\n\nYour Coin Balance: {coins} Coins\n\nChoose a package to buy using your coins:",
        'free_no_config': "😕 **Sorry!**\n\nThe owner has not set a free V2ray config for today yet.\nPlease check back later.",
        'free_success_followup': "🚀 **Enjoy your free V2ray!** 🚀\n\nThis is a free config, so speed and stability might be limited.\n\nFor an uninterrupted, high-speed premium server, check out our packages!\n👉 Type /shop **to see prices!**\n👉 Type /myaccount **to earn more coins!**",
        'err_admin_post_deleted': "⛔ **Error!**\nThe post set by the owner was deleted from the channel. Please inform the admin.",
        'err_generic': "⛔ An error occurred! Please try again later. (Error: {e})",
        'buy_success': "✅ **Purchase Successful!**\n\nYou bought '{package_name}'.\nYour new Coin Balance: {new_balance} Coins\n\nThe Owner (Admin) will contact you shortly. 🇱🇰",
        'buy_fail_coins': "⚠️ **Insufficient Coins!**\n\nTo buy '{package_name}', you need {price} Coins.\nYou only have {balance} Coins.\n\nShare your referral link to earn more!",
        'buy_err_tx': "⛔ Transaction error! Please try again.",
        'buy_err_no_package': "⛔ Error! This package is no longer available."
    },
    'si': {
        'select_language': "👋 ආයුබෝවන්! කරුණාකර ඔබගේ භාෂාව තෝරන්න:",
        'please_join': "**🛑 නවතින්න!**\n\nබොට් භාවිතා කිරීමට, කරුණාකර පළමුව අපගේ ප්‍රධාන නාලිකාවට (Main Channel) සම්බන්ධ වන්න.\n\nChannel එකට Join වූ පසු, නැවත /start ඔබන්න.",
        'welcome_not_registered': "ආයුබෝවන් {first_name}! 🇱🇰\n\nBot ගේ සියලුම සේවාවන් (Shop, Free V2ray) ලබා ගැනීමට සහ ඔබගේ referral link එක ලබා ගැනීමට, කරුණාකර පළමුව ලියාපදිංචි වන්න.\n\n👉 ලියාපදිංචි වීමට /register ලෙස type කරන්න.",
        'welcome_registered': "ආයුබෝවන් {first_name}, නැවතත් සාදරයෙන් පිළිගනිමු! 🇱🇰\n\n💰 **ඔබගේ Coin Balance:** {coins} Coins\n\n**ඔබට දැන් භාවිතා කළ හැක:**\n🛒 /shop - Premium packages මිලදී ගන්න.\n🎁 /free - දවසේ නොමිලේ V2ray config එක ලබා ගන්න.\n📊 /myaccount - ඔබගේ ගිණුම සහ referral link එක බලන්න.",
        'err_not_registered': "🔒 **ඔබ තවම ලියාපදිංචි වී නැත!**\n\nමෙම සේවාව භාවිතා කිරීමට, කරුණාකර පළමුව /register ලෙස type කර ලියාපදිංචි වන්න.",
        'register_success': "✅ **ලියාපදිංචිය සාර්ථකයි!**\n\nඔබට දැන් /shop සහ /free commands භාවිතා කළ හැක.\n\n🔗 **ඔබගේ Referral Link එක:**\n`{link}`\n\nමෙම link එක share කර එක් referral කෙනෙකු සඳහා **Coin {value}** ක් ලබා ගන්න!",
        'register_already': "✅ ඔබ දැනටමත් ලියාපදිංචි වී ඇත!\n\n/myaccount මගින් ඔබගේ referral link එක ලබා ගන්න.",
        'referral_notify': "🎉 සුභ පැතුම්! {user_name} ඔබගේ link එක හරහා ලියාපදිංචි විය.\nඔබට **Coin {value}** ක් ලැබුණි!\n\n💰 **ඔබගේ නව Coin Balance:** {new_balance} Coins",
        'my_account': "**📊 ඔබගේ ගිණුම (My Account)**\n\n📈 **මුළු Referral ගණන:** {ref_count}\n💰 **Coin Balance:** {coins} Coins\n\n🔗 **ඔබගේ Referral Link එක:**\n`{link}`\n\nV2ray packages මිලදී ගැනීමට /shop ලෙස type කරන්න.",
        'shop_title': "🛒 **FreeV2ray Shop** 🛒\n\nඔබගේ Coin Balance: {coins} Coins\n\nඔබගේ Coin භාවිතා කර කැමති package එකක් තෝරන්න:",
        'free_no_config': "😕 **සමාවන්න!**\n\nOwner විසින් තවමත් අද දින නොමිලේ V2ray config එකක් ඇතුලත් කර නැත.\nකරුණාකර මද වේලාවකින් නැවත උත්සාහ කරන්න.",
        'free_success_followup': "🚀 **Enjoy your free V2ray!** 🚀\n\nමෙය නොමිලේ දෙන config එකක් නිසා වේගය සහ ස්ථාවරත්වය අඩු විය හැක.\n\nතදබදයක් නැති, අධි වේගී Premium server එකක් සඳහා, අපගේ Premium packages බලන්න.\n👉 /shop **ටයිප් කර මිල ගණන් බලන්න!**\n👉 /myaccount **මගින් coin එකතු කරගන්න!**",
        'err_admin_post_deleted': "⛔ **දෝෂයක්!**\nOwner විසින් set කළ post එක channel එකෙන් delete කර ඇත. කරුණාකර Admin ට දන්වන්න.",
        'err_generic': "⛔ යම් දෝෂයක් සිදුවිය. කරුණාකර මද වේලාවකින් උත්සාහ කරන්න. (Error: {e})",
        'buy_success': "✅ **මිලදී ගැනීම සාර්ථකයි!**\n\nඔබ '{package_name}' මිලදී ගත්තා.\nඔබගේ නව Coin Balance: {new_balance} Coins\n\nOwner (Admin) විසින් ඔබව කෙටි වේලාවකින් සම්බන්ධ කරගනු ඇත. 🇱🇰",
        'buy_fail_coins': "⚠️ **Coin මදි! (Insufficient Coins)**\n\n'{package_name}' මිලදී ගැනීමට Coin {price} ක් අවශ්‍ය වේ.\nඔබ සතුව ඇත්තේ Coin {balance} ක් පමණි.\n\nReferral link එක share කර තවත් Coin එකතු කරගන්න!",
        'buy_err_tx': "⛔ ගනුදෙනුවේ දෝෂයක්! කරුණාකර නැවත උත්සාහ කරන්න.",
        'buy_err_no_package': "⛔ දෝෂයක්! මෙම Package එක තවදුරටත් වලංගු නැත."
    }
}

# --- Shop Packages (මෙය නොවෙනස්ව පවතී) ---
PRODUCTS = {
    "30d_50gb": {"name": "30 Day - 50GB", "price": 100},
    "30d_100gb": {"name": "30 Day - 100GB", "price": 200},
    "30d_unlimited": {"name": "30 Day - Unlimited", "price": 300},
    "50d_50gb": {"name": "50 Day - 50GB", "price": 200},
    "50d_100gb": {"name": "50 Day - 100GB", "price": 300},
    "50d_unlimited": {"name": "50 Day - Unlimited", "price": 400},
}

# --- Logging (දෝෂ පරීක්ෂාව සඳහා) ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Firebase Initialization (Firebase ආරම්භ කිරීම) ---
try:
    # Render වැනි platform වලදී, serviceAccountKey.json file එක
    # .gitignore කර ඇති නිසා, එය පරිසර විචල්‍යයකින් (Env Variable)
    # හෝ "Secret File" එකකින් පැමිණිය යුතුය.
    # මෙම කේතය file එකක් ලෙස එය බලාපොරොත්තු වේ.
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    logger.info("Firebase සාර්ථකව සම්බන්ධ කරන ලදී!")
except FileNotFoundError:
    logger.critical("FATAL ERROR: `serviceAccountKey.json` file එක හමු නොවීය!")
    logger.critical("කරුණාකර Render/VPS වෙත Secret File එකක් ලෙස මෙය upload කරන්න.")
    # Render/VPS මත deploy කරන විට, bot එක crash වීම වැලැක්වීමට
    # මෙතැනින් exit() කිරීම සමහරවිට අවශ්‍ය නොවනු ඇත, 
    # නමුත් file එක නොමැතිව bot ක්‍රියා නොකරයි.
    # Deployment පරිසරය අනුව මෙය සකස් කළ යුතුය.
    # දැනට, file එක නැත්නම් bot එක නතර වේ.
    exit(1) # නතර කිරීම
except Exception as e:
    logger.critical(f"Firebase සම්බන්ධ කිරීමේ දෝෂයක්: {e}")
    exit(1) # නතර කිරීම

# --- (NEW) Helper Function: Get String ---
def get_string(lang_code: str, key: str) -> str:
    """
    භාෂාවට අදාළව නියමිත string එක ලබා දෙයි.
    'si' (Sinhala) යනු default භාෂාවයි.
    """
    if lang_code not in STRINGS:
        lang_code = 'si' # Default to Sinhala
    
    return STRINGS.get(lang_code, {}).get(key, f"STR_ERR: {key}")

# --- Firestore Helper Functions ---

async def get_user_doc(user_id: int, first_name: str = "User", username: str = "") -> firestore.DocumentSnapshot:
    """
    User කෙනෙක් Firestore එකෙන් ලබා ගනී.
    ඔහු/ඇය නොමැති නම්, නව document එකක් සාදයි.
    (NEW) 'language' field එක එකතු කර ඇත.
    """
    user_id_str = str(user_id)
    doc_ref = db.collection('users').document(user_id_str)
    doc = await doc_ref.get()
    
    if not doc.exists:
        user_data = {
            "user_id": user_id,
            "first_name": first_name,
            "username": username,
            "is_registered": False,
            "referral_count": 0,
            "coins": 0,
            "referred_by": None,
            "language": "si", # Default language
            "joined_date": firestore.SERVER_TIMESTAMP
        }
        await doc_ref.set(user_data)
        doc = await doc_ref.get() # නව දත්ත නැවත ලබා ගනී
        logger.info(f"නව user {user_id} ({first_name}) Firestore වෙත එකතු කරන ලදී.")
    
    return doc

async def get_bot_settings() -> dict:
    doc_ref = db.collection('config').document('bot_settings')
    doc = await doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    else:
        await doc_ref.set({'free_v2ray_post_id': None})
        return {'free_v2ray_post_id': None}

# --- General Helper Functions ---

async def is_user_in_channel(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=MAIN_CHANNEL_ID, user_id=user_id)
        if member.status in ['creator', 'administrator', 'member']:
            return True
    except (Forbidden, BadRequest) as e:
        logger.error(f"Channel check error (Bot channel එකේ admin ද?): {e}")
    except Exception as e:
        logger.error(f"Unknown channel check error: {e}")
    return False

async def send_join_channel_message(target, lang: str = 'si'):
    """
    (UPDATED) Channel එකට join වීමට පණිවිඩය (භාෂාවට අදාළව) යවයි.
    """
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Channel එකට Join වන්න / Join Channel", url=CHANNEL_INVITE_LINK)]
    ])
    text = get_string(lang, 'please_join')
    
    try:
        if isinstance(target, Update): # message එකක් නම්
            target_message = target.message or target.callback_query.message
            if target_message:
                await target_message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        else: # target එක message object එකක් නම් (fallback)
            await target.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Send Join Msg Error: {e}")


# --- (UPDATED) Pre-check Decorator ---

def user_checks(check_registered: bool = True):
    """
    Decorator: Channel join සහ registration (භාෂාවට අදාළව) පරීක්ෂා කරයි.
    """
    def decorator(func):
        @wraps(func)
        async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user = update.effective_user
            if not user:
                return # User හඳුනාගත නොහැකි නම් නතර කිරීම

            # User doc එක ලබා ගැනීම (මෙහිදී භාෂාවද ලැබේ)
            user_doc = await get_user_doc(user.id, user.first_name, user.username)
            user_data = user_doc.to_dict()
            lang = user_data.get('language', 'si') # User ගේ භාෂාව ලබා ගැනීම

            # 1. Channel Check (සැමවිටම)
            if not await is_user_in_channel(user.id, context):
                await send_join_channel_message(update, lang)
                return

            # 2. Register Check (අවශ්‍ය නම් පමණි)
            if check_registered and not user_data.get('is_registered', False):
                await update.message.reply_text(
                    get_string(lang, 'err_not_registered'),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Checks ok, user_data (භාෂාව සමග) command එකට pass කිරීම
            return await func(update, context, user_data=user_data, *args, **kwargs)
        return wrapped
    return decorator

# === Command Handlers (ප්‍රධාන අණ) ===

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    (NEW) /start command.
    වෙන කිසිවක් නොකර, භාෂා තේරීමේ බොත්තම් පමණක් පෙන්වයි.
    """
    if not update.message: return # Message එකක් නොමැතිනම් (e.g. channel post)

    keyboard = [
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇱🇰 සිංහල (Sinhala)", callback_data="lang_si")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        get_string('en', 'select_language') + "\n\n" + get_string('si', 'select_language'),
        reply_markup=reply_markup
    )

async def language_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    (NEW) භාෂා තේරීමේ බොත්තම් (lang_en / lang_si) handle කරයි.
    මෙය පැරණි /start logic එක ප්‍රතිස්ථාපනය කරයි.
    """
    query = update.callback_query
    if not query or not query.message: return
        
    await query.answer()
    
    user = query.effective_user
    if not user: return

    lang_code = query.data.split('_')[1] # 'en' or 'si'

    # 1. User doc එක ලබාගෙන භාෂාව Save කිරීම
    user_doc = await get_user_doc(user.id, user.first_name, user.username)
    await user_doc.reference.update({"language": lang_code})
    
    user_data = (await user_doc.reference.get()).to_dict() # යාවත්කාලීන දත්ත

    # 2. Channel Check
    if not await is_user_in_channel(user.id, context):
        await send_join_channel_message(query.message, lang_code)
        return

    # User channel එකේ සිටී.
    # 3. Register Check
    if not user_data.get('is_registered', False):
        # --- ලියාපදිංචි වී නැත්නම් ---
        text = get_string(lang_code, 'welcome_not_registered').format(first_name=user.first_name)
    else:
        # --- ලියාපදිංචි වී ඇත්නම් (Bot Menu) ---
        text = get_string(lang_code, 'welcome_registered').format(
            first_name=user.first_name,
            coins=user_data.get('coins', 0)
        )
    
    # User ට තේරූ භාෂාවෙන් පිළිතුරු දීම
    try:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
    except BadRequest as e:
        if "message is not modified" in str(e):
            pass # Message එක වෙනස් වී නැත්නම්, දෝෂයක් නොපෙන්වීම
        else:
            logger.warning(f"Language button edit error: {e}")
            await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN) # Fallback


async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    (UPDATED) /register command (භාෂාවට අදාළව)
    """
    user = update.effective_user
    if not user or not update.message: return

    # (මෙහි decorator නැත. Manual checks)
    user_doc_ref = db.collection('users').document(str(user.id))
    user_doc = await user_doc_ref.get()
    
    if not user_doc.exists:
        user_doc = await get_user_doc(user.id, user.first_name, user.username)
        
    user_data = user_doc.to_dict()
    lang = user_data.get('language', 'si')

    # 1. Channel Check
    if not await is_user_in_channel(user.id, context):
        await send_join_channel_message(update.message, lang)
        return

    # 2. දැනටමත් register ද?
    if user_data.get('is_registered', False):
        await update.message.reply_text(get_string(lang, 'register_already'))
        return

    # --- නව ලියාපදිංචිය ---
    await user_doc_ref.update({"is_registered": True})
    
    bot_username = context.bot_data.get('username', 'YOUR_BOT_USERNAME')
    referral_link = f"https://t.me/{bot_username}?start={user.id}"
    
    text = get_string(lang, 'register_success').format(
        link=referral_link,
        value=REFERRAL_COIN_VALUE
    )
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

    # 3. Referral Logic
    referrer_id = None
    if context.args:
        try: referrer_id = int(context.args[0])
        except (IndexError, ValueError): pass

    if user_data.get('referred_by') is None and referrer_id and referrer_id != user.id:
        referrer_doc_ref = db.collection('users').document(str(referrer_id))
        referrer_doc = await referrer_doc_ref.get()

        if referrer_doc.exists:
            referrer_lang = referrer_doc.to_dict().get('language', 'si')
            
            await referrer_doc_ref.update({
                "coins": firestore.Increment(REFERRAL_COIN_VALUE),
                "referral_count": firestore.Increment(1)
            })
            await user_doc_ref.update({"referred_by": referrer_id})
            
            try:
                new_balance = (referrer_doc.to_dict().get('coins', 0)) + REFERRAL_COIN_VALUE
                notify_text = get_string(referrer_lang, 'referral_notify').format(
                    user_name=user.first_name,
                    value=REFERRAL_COIN_VALUE,
                    new_balance=new_balance
                )
                await context.bot.send_message(chat_id=referrer_id, text=notify_text)
            except Exception as e:
                logger.warning(f"Referrer {referrer_id} ට message යැවීමට නොහැකි විය: {e}")

@user_checks(check_registered=True)
async def myaccount_command(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict = None):
    """
    (UPDATED) /myaccount (භාෂාවට අදාළව)
    """
    user = update.effective_user
    lang = user_data.get('language', 'si')
    bot_username = context.bot_data.get('username', 'YOUR_BOT_USERNAME')
    referral_link = f"https://t.me/{bot_username}?start={user.id}"
    
    text = get_string(lang, 'my_account').format(
        ref_count=user_data.get('referral_count', 0),
        coins=user_data.get('coins', 0),
        link=referral_link
    )
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

@user_checks(check_registered=True)
async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict = None):
    """
    (UPDATED) /shop (භාෂාවට අදාළව)
    """
    lang = user_data.get('language', 'si')
    coin_balance = user_data.get('coins', 0)
    
    keyboard = []
    for key, product in PRODUCTS.items():
        text = f"{product['name']} - {product['price']} Coins"
        callback_data = f"buy_{key}"
        keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = get_string(lang, 'shop_title').format(coins=coin_balance)
    
    await update.message.reply_text(text, reply_markup=reply_markup)

@user_checks(check_registered=True)
async def free_command(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict = None):
    """
    (UPDATED) /free (භාෂාවට අදාළව)
    """
    user_id = update.effective_user.id
    lang = user_data.get('language', 'si')
    settings = await get_bot_settings()
    post_id = settings.get('free_v2ray_post_id')
    
    if not post_id or post_id == 0:
        await update.message.reply_text(get_string(lang, 'free_no_config'))
        return

    try:
        # 1. Free V2ray එක Forward කිරීම
        await context.bot.forward_message(
            chat_id=user_id,
            from_chat_id=MAIN_CHANNEL_ID,
            message_id=post_id
        )
        
        # 2. Follow-up Premium Message
        await asyncio.sleep(1)
        await context.bot.send_message(
            chat_id=user_id,
            text=get_string(lang, 'free_success_followup'),
            parse_mode=ParseMode.MARKDOWN
        )
        
    except BadRequest as e:
        if "message to forward not found" in str(e).lower():
            await update.message.reply_text(get_string(lang, 'err_admin_post_deleted'))
            await context.bot.send_message(OWNER_ID, f"⚠️ ERROR: /free command එක අසාර්ථකයි. Post ID {post_id} channel එකේ නැත! /setfree මගින් අලුත් ID එකක් යොදන්න.")
        else:
            await update.message.reply_text(get_string(lang, 'err_generic').format(e=e))
    except Exception as e:
        logger.error(f"/free command error: {e}")
        await update.message.reply_text(get_string(lang, 'err_generic').format(e=e))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    (UPDATED) Shop එකේ 'Buy' බොත්තම් (භාෂාවට අදාළව)
    """
    query = update.callback_query
    if not query or not query.message: return
        
    await query.answer()
    
    user = query.effective_user
    if not user: return
        
    data = query.data
    
    if not data.startswith("buy_"):
        return # මෙය 'lang_' button එකක් නොවේ

    # User checks (Manual)
    user_doc_ref = db.collection('users').document(str(user.id))
    user_doc = await user_doc_ref.get()
    
    if not user_doc.exists:
        # User කෙසේ හෝ /shop වෙත ගොස් ඇත, නමුත් db එකේ නැත.
        # (මෙය සිදුවිය නොහැක, නමුත් ආරක්ෂාව සඳහා)
        await get_user_doc(user.id, user.first_name, user.username)
        await query.message.reply_text("⛔ Error! Please type /start again.")
        return

    user_data = user_doc.to_dict()
    lang = user_data.get('language', 'si')

    if not await is_user_in_channel(user.id, context):
        await send_join_channel_message(query.message, lang)
        return

    if not user_data.get('is_registered', False):
        await query.message.reply_text(get_string(lang, 'err_not_registered'))
        return

    product_key = data[4:]
    if product_key not in PRODUCTS:
        await query.edit_message_text(get_string(lang, 'buy_err_no_package'))
        return
        
    product = PRODUCTS[product_key]
    price = product['price']
    
    # --- Firebase Transaction ---
    @firestore.async_transactional
    async def process_purchase(transaction, user_ref, price_to_deduct):
        doc = await user_ref.get(transaction=transaction)
        current_balance = doc.to_dict().get('coins', 0)
        if current_balance >= price_to_deduct:
            new_balance = current_balance - price_to_deduct
            transaction.update(user_ref, {"coins": new_balance})
            return True, new_balance # සාර්ථකයි
        else:
            return False, current_balance # අසාර්ථකයි

    try:
        is_success, balance = await process_purchase(db.transaction(), user_doc_ref, price)

        if is_success:
            # --- සාර්ථකයි (Success) ---
            text = get_string(lang, 'buy_success').format(
                package_name=product['name'],
                new_balance=balance
            )
            await query.edit_message_text(text)
            
            # Owner ට දැනුම් දීම (English)
            user_mention = f"@{user.username}" if user.username else f"ID: {user.id}"
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"🔔 **නව අලෙවියක්! (New Sale)** 🔔\n\n"
                     f"**User:** {user.first_name} ({user_mention})\n"
                     f"**Package:** {product['name']}\n"
                     f"**Price Paid:** {price} Coins\n\n"
                     f"කරුණාකර මොහුට V2ray config එක සාදා දෙන්න.",
                disable_web_page_preview=True
            )
        else:
            # --- අසාර්ථකයි (Failed) ---
            text = get_string(lang, 'buy_fail_coins').format(
                package_name=product['name'],
                price=price,
                balance=balance
            )
            await context.bot.send_message(chat_id=user.id, text=text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Transaction error: {e}")
        await query.message.reply_text(get_string(lang, 'buy_err_tx'))

# === Admin & Broadcast Commands (මෙම කොටස් නොවෙනස්ව පවතී) ===

async def owner_only_command(update: Update, context: ContextTypes.DEFAULT_TYPE, func):
    """Owner ID එක පරීක්ෂා කරන Helper function එකක්"""
    if not update.effective_user or update.effective_user.id != OWNER_ID:
        logger.warning(f"Unauthorized access denied for {update.effective_user.id}.")
        return
    await func(update, context)

async def send_command_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    replied_message = update.message.reply_to_message
    if not replied_message:
        await update.message.reply_text("භාවිතය: /send command එක ඔබ යැවීමට බලාපොරොත්තු වන V2ray පණිවිඩයට 'Reply' කරන්න.")
        return
    users_query = db.collection('users').select(["user_id"]).stream()
    target_users = [int(doc.id) async for doc in users_query if int(doc.id) != OWNER_ID]
    total_users = len(target_users)
    if total_users == 0:
        await update.message.reply_text("😕 Bot හට ලියාපදිංචි වූ කිසිදු පරිශීලකයෙකු (users) හමු නොවීය.")
        return
    await update.message.reply_text(f"⏳ V2ray (/send) Broadcast ආරම්භ වෙමින් පවතී...\nමුළු Users: {total_users}\nBatch Size: {BROADCAST_BATCH_SIZE}")
    sent_count, failed_count = 0, 0
    for i, user_id in enumerate(target_users):
        try:
            await replied_message.copy(chat_id=user_id)
            sent_count += 1
            if (i + 1) % BROADCAST_BATCH_SIZE == 0: await asyncio.sleep(1) 
            else: await asyncio.sleep(0.05)
        except (Forbidden, BadRequest): failed_count += 1
        except Exception as e:
            logger.error(f"Send (copy) failed for user {user_id}: {e}")
            failed_count += 1
    await update.message.reply_text(f"📣 Send සම්පූර්ණයි! (Sent: {sent_count}, Failed: {failed_count})")

async def broadcast_command_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_to_send = update.message.text.split(' ', 1)
    if len(message_to_send) < 2:
        await update.message.reply_text("භාවිතය: /broadcast <ඔබේ text message එක>")
        return
    message_content = message_to_send[1]
    users_query = db.collection('users').select(["user_id"]).stream()
    target_users = [int(doc.id) async for doc in users_query if int(doc.id) != OWNER_ID]
    total_users = len(target_users)
    if total_users == 0:
        await update.message.reply_text("😕 Bot හට ලියාපදිංචි වූ කිසිදු පරිශීලකයෙකු (users) හමු නොවීය.")
        return
    await update.message.reply_text(f"⏳ Text Broadcast ආරම්භ වෙමින් පවතී...\nමුළු Users: {total_users}\nBatch Size: {BROADCAST_BATCH_SIZE}")
    sent_count, failed_count = 0, 0
    for i, user_id in enumerate(target_users):
        try:
            await context.bot.send_message(chat_id=user_id, text=message_content, parse_mode=ParseMode.MARKDOWN)
            sent_count += 1
            if (i + 1) % BROADCAST_BATCH_SIZE == 0: await asyncio.sleep(1)
            else: await asyncio.sleep(0.05)
        except (Forbidden, BadRequest): failed_count += 1
        except Exception as e:
            logger.error(f"Broadcast (text) failed for user {user_id}: {e}")
            failed_count += 1
    await update.message.reply_text(f"📣 Broadcast සම්පූර්ණයි! (Sent: {sent_count}, Failed: {failed_count})")

async def setfree_command_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        post_id = int(context.args[0])
        settings_ref = db.collection('config').document('bot_settings')
        await settings_ref.set({'free_v2ray_post_id': post_id}, merge=True)
        await update.message.reply_text(f"✅ සාර්ථකයි!\n/free command එක සඳහා Post ID එක `{post_id}` ලෙස සකසන ලදී.")
    except (IndexError, ValueError):
        await update.message.reply_text("භාවිතය: /setfree <Post ID>\n\n(Post ID එක ලබා ගැනීමට, channel එකේ message එකක් මට forward කරන්න)")
    except Exception as e:
        logger.error(f"/setfree error: {e}")
        await update.message.reply_text(f"⛔ දෝෂයක්! {e}")

async def addcoins_command_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id_to_add = int(context.args[0])
        amount_to_add = int(context.args[1])
        user_ref = db.collection('users').document(str(user_id_to_add))
        user_doc = await user_ref.get()
        if not user_doc.exists:
            await update.message.reply_text(f"⛔ දෝෂයක්! User ID {user_id_to_add} දත්ත ගබඩාවේ (db) නැත.")
            return
        await user_ref.update({"coins": firestore.Increment(amount_to_add)})
        new_balance = user_doc.to_dict().get('coins', 0) + amount_to_add
        await update.message.reply_text(f"✅ සාර්ථකයි!\nUser {user_id_to_add} ට Coin {amount_to_add} ක් එකතු කරන ලදී.\nනව Balance: {new_balance}")
        
        try:
            user_lang = user_doc.to_dict().get('language', 'si')
            if user_lang == 'si':
                notify_text = f"🎉 සුභ පැතුම්!\nOwner විසින් ඔබට **Coin {amount_to_add}** ක් තෑගි දෙන ලදී!\nඔබගේ නව balance: {new_balance} Coins"
            else:
                notify_text = f"🎉 Congratulations!\nThe Owner sent you a gift of **{amount_to_add} Coins**!\nYour new balance: {new_balance} Coins"
            await context.bot.send_message(user_id_to_add, notify_text)
        except: pass
            
    except (IndexError, ValueError):
        await update.message.reply_text("භාවිතය: /addcoins <User ID> <Amount>")
    except Exception as e:
        logger.error(f"/addcoins error: {e}")
        await update.message.reply_text(f"⛔ දෝෂයක්! {e}")

async def get_forwarded_post_id_handler_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fwd_chat = update.message.forward_from_chat
    if fwd_chat and fwd_chat.id == MAIN_CHANNEL_ID:
        post_id = update.message.forward_from_message_id
        await update.message.reply_text(
            f"✅ **Post ID හමුවිය!**\n\nPost ID: `{post_id}`\n\nSet කිරීමට:\n`/setfree {post_id}`",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(f"⛔ කරුණාකර ඔබගේ **Main Channel** ({MAIN_CHANNEL_ID}) එකෙන් පමණක් message එකක් forward කරන්න.")

# Owner command wrappers
async def send_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await owner_only_command(update, context, send_command_logic)
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await owner_only_command(update, context, broadcast_command_logic)
async def setfree_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await owner_only_command(update, context, setfree_command_logic)
async def addcoins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await owner_only_command(update, context, addcoins_command_logic)
async def get_forwarded_post_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user and update.effective_user.id == OWNER_ID:
        await get_forwarded_post_id_handler_logic(update, context)

# === Bot Startup ===

async def post_init(application: Application):
    try:
        bot_info = await application.bot.get_me()
        application.bot_data['username'] = bot_info.username
        logger.info(f"Bot @{bot_info.username} ලෙස සාර්ථකව ලොග් විය.")
        await application.bot.send_message(chat_id=OWNER_ID, text="🤖 Bot සාර්ථකව ආරම්භ විය (Multi-Language Active)!")
    except Exception as e:
        logger.critical(f"Bot username ලබා ගැනීමට නොහැකි විය: {e}")
        application.bot_data['username'] = "YOUR_BOT_USERNAME"

def main():
    logger.info("Bot ආරම්භ වෙමින් පවතී...")

    application = Application.builder().token(BOT_TOKEN).build()

    # Handlers එකතු කිරීම
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("register", register_command))
    application.add_handler(CommandHandler("myaccount", myaccount_command))
    application.add_handler(CommandHandler("shop", shop_command))
    application.add_handler(CommandHandler("free", free_command))
    
    application.add_handler(CallbackQueryHandler(language_button_handler, pattern="^lang_"))
    application.add_handler(CallbackQueryHandler(button_handler, pattern="^buy_"))
    
    # Owner (Admin) Commands
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("send", send_command))
    application.add_handler(CommandHandler("setfree", setfree_command))
    application.add_handler(CommandHandler("addcoins", addcoins_command))
    
    application.add_handler(MessageHandler(
        filters.FORWARDED & filters.User(user_id=OWNER_ID), 
        get_forwarded_post_id_handler
    ))
    
    application.post_init = post_init

    logger.info("Bot polling ආරම්භ කරයි...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

