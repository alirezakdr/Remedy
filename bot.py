#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram bot: Brands → Products → Usage instructions (text)
Mode: POLLING (for running on Render.com as a Worker) 
Library: python-telegram-bot v21+ (async)
"""
import asyncio
import logging
import json
import os
from typing import Dict, Any, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ---------- CONFIG ----------
BOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_YOUR_TELEGRAM_BOT_TOKEN_HERE")
DATA_FILE = "products.json"
MAX_BUTTONS_PER_ROW = 2

# ---------- DATA LOADING ----------
def load_data() -> Dict[str, Any]:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict) and "brands" in data and isinstance(data["brands"], dict)
    return data

def get_brands(data: Dict[str, Any]) -> List[str]:
    return list(data.get("brands", {}).keys())

def get_products_for_brand(data: Dict[str, Any], brand: str) -> List[str]:
    return list(data.get("brands", {}).get(brand, {}).keys())

def get_instruction(data: Dict[str, Any], brand: str, product: str) -> str:
    return data["brands"][brand][product]["instruction"]

# ---------- UI HELPERS ----------
def chunk_buttons(buttons, per_row=MAX_BUTTONS_PER_ROW):
    return [buttons[i:i+per_row] for i in range(0, len(buttons), per_row)]

def main_menu_keyboard(data: Dict[str, Any]) -> InlineKeyboardMarkup:
    brands = get_brands(data)
    buttons = [InlineKeyboardButton(text=brand, callback_data=f"B:{brand}") for brand in brands]
    rows = chunk_buttons(buttons)
    return InlineKeyboardMarkup(rows)

def brand_menu_keyboard(data: Dict[str, Any], brand: str) -> InlineKeyboardMarkup:
    products = get_products_for_brand(data, brand)
    buttons = [InlineKeyboardButton(text=p, callback_data=f"P:{brand}:{p}") for p in products]
    rows = chunk_buttons(buttons)
    rows.append([InlineKeyboardButton(text="⬅️ بازگشت به منوی برندها", callback_data="HOME")])
    return InlineKeyboardMarkup(rows)

def product_menu_keyboard(brand: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text="⬅️ بازگشت به محصولات", callback_data=f"B:{brand}")],
         [InlineKeyboardButton(text="🏠 بازگشت به منوی اصلی", callback_data="HOME")]]
    )

# ---------- HANDLERS ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = load_data()
    text = (
        "سلام! 👋\n"
        "از منوی زیر، برند مورد نظر را انتخاب کنید.\n"
        "سپس محصول را انتخاب کنید تا دستورالعمل استفاده برای شما ارسال شود."
    )
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(data))

async def home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = load_data()
    text = "برند مورد نظر را انتخاب کنید:"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=main_menu_keyboard(data))
    else:
        await update.message.reply_text(text, reply_markup=main_menu_keyboard(data))

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = load_data()

    if query.data == "HOME":
        await query.edit_message_text("برند مورد نظر را انتخاب کنید:", reply_markup=main_menu_keyboard(data))
        return

    try:
        if query.data.startswith("B:"):
            _, brand = query.data.split(":", 1)
            if brand not in data["brands"]:
                await query.edit_message_text("❗️این برند یافت نشد.", reply_markup=main_menu_keyboard(data))
                return
            text = f"محصولات برند «{brand}» را انتخاب کنید:"
            await query.edit_message_text(text, reply_markup=brand_menu_keyboard(data, brand))
            return

        if query.data.startswith("P:"):
            _, brand, product = query.data.split(":", 2)
            instruction = get_instruction(data, brand, product)
            title = f"📦 {brand} → {product}\n\n"
            await query.edit_message_text(
                title + instruction,
                reply_markup=product_menu_keyboard(brand),
                parse_mode=ParseMode.HTML
            )
            return
    except Exception as e:
        await query.edit_message_text(f"❌ خطا: {e}")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "راهنما:\n"
        "/start  شروع و نمایش منوی برندها\n"
        "/help   همین راهنما\n\n"
        "مدیریت محتوا: فایل products.json را ویرایش کنید."
    )

def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(CommandHandler("menu", home))
    return app

async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    app = build_app()
    print("Bot is running... (Polling mode)")
    await app.run_polling(close_loop=False)  # important for Render worker stability

if __name__ == "__main__":
    asyncio.run(main())
