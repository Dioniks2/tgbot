import asyncio
import sqlite3
import math
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

BOT_TOKEN = "8703558017:AAElNjdskeY4p5blJxohAwb-KThZvMOtUQM"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# --- 🗄️ БАЗА ДАННЫХ (для игры) ---
def init_db():
    conn = sqlite3.connect("finance_game.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            current_week INTEGER DEFAULT 1,
            total_saved REAL DEFAULT 0.0
        )
    ''')
    conn.commit()
    conn.close()


# --- 🔢 СТЕЙТЫ (FSM) ---
class CreditStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_rate = State()
    waiting_for_term = State()
    waiting_for_early_payment = State()


class DepositStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_rate = State()
    waiting_for_term = State()


# --- ⌨️ КЛАВИАТУРЫ ---
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💳 Кредитный калькулятор")],
            [KeyboardButton(text="💰 Калькулятор вкладов")],
            [KeyboardButton(text="🎯 Игра: 52 недели богатства")],
            [KeyboardButton(text="ℹ️ О боте")]
        ],
        resize_keyboard=True
    )


def get_early_payment_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Без досрочного")],
            [KeyboardButton(text="Уменьшить срок")],
            [KeyboardButton(text="Уменьшить платеж")]
        ],
        resize_keyboard=True
    )


# --- 🚀 КОМАНДЫ И ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я твой персональный финансовый бот.\n"
        "Я помогу рассчитать кредит, депозит или накопить деньги!",
        reply_markup=get_main_keyboard()
    )


# --- 💳 МОДУЛЬ: КРЕДИТНЫЙ КАЛЬКУЛЯТОР ---
@dp.message(F.text == "💳 Кредитный калькулятор")
async def credit_start(message: Message, state: FSMContext):
    await message.answer("Введите сумму кредита (в рублях):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(CreditStates.waiting_for_amount)


@dp.message(CreditStates.waiting_for_amount)
async def credit_amount(message: Message, state: FSMContext):
    await state.update_data(amount=float(message.text))
    await message.answer("Введите годовую процентную ставку (в %):")
    await state.set_state(CreditStates.waiting_for_rate)


@dp.message(CreditStates.waiting_for_rate)
async def credit_rate(message: Message, state: FSMContext):
    await state.update_data(rate=float(message.text))
    await message.answer("Введите срок кредита (в месяцах):")
    await state.set_state(CreditStates.waiting_for_term)


@dp.message(CreditStates.waiting_for_term)
async def credit_term(message: Message, state: FSMContext):
    await state.update_data(term=int(message.text))
    await message.answer("Выберите вариант досрочного погашения (или 'Без досрочного'):",
                         reply_markup=get_early_payment_keyboard())
    await state.set_state(CreditStates.waiting_for_early_payment)


@dp.message(CreditStates.waiting_for_early_payment)
async def credit_calc(message: Message, state: FSMContext):
    data = await state.get_data()
    amount = data['amount']
    rate = data['rate'] / 100 / 12  # Месячная ставка
    term = data['term']
    option = message.text

    # Аннуитетный платеж
    payment = amount * (rate * (1 + rate) ** term) / (((1 + rate) ** term) - 1)
    total_payout = payment * term
    overpayment = total_payout - amount

    text = (
        f"📊 **Стандартный расчет:**\n"
        f"Ежемесячный платеж: {payment:.2f} руб.\n"
        f"Общая выплата: {total_payout:.2f} руб.\n"
        f"Переплата: {overpayment:.2f} руб.\n\n"
    )

    if option == "Уменьшить срок":
        # Пример: внесли единоразово досрочно 10% от суммы на 2-й месяц
        early_sum = amount * 0.1
        new_term = math.log(payment / (payment - (amount - early_sum) * rate)) / math.log(1 + rate)
        text += (
            f"⚡ **С досрочным (уменьшение срока):**\n"
            f"Если внести разово {early_sum:.2f} руб.,\n"
            f"Новый срок составит примерно: {math.ceil(new_term)} мес."
        )
    elif option == "Уменьшить платеж":
        early_sum = amount * 0.1
        new_amount = amount - early_sum
        new_payment = new_amount * (rate * (1 + rate) ** term) / (((1 + rate) ** term) - 1)
        text += (
            f"⚡ **С досрочным (уменьшение платежа):**\n"
            f"Если внести разово {early_sum:.2f} руб.,\n"
            f"Новый ежемесячный платеж: {new_payment:.2f} руб."
        )
    else:
        text += "Досрочное погашение не рассчитывалось."

    await message.answer(text, reply_markup=get_main_keyboard())
    await state.clear()


# --- 💰 МОДУЛЬ: КАЛЬКУЛЯТОР ВКЛАДОВ ---
@dp.message(F.text == "💰 Калькулятор вкладов")
async def deposit_start(message: Message, state: FSMContext):
    await message.answer("Введите сумму вклада (в рублях):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(DepositStates.waiting_for_amount)


@dp.message(DepositStates.waiting_for_amount)
async def deposit_amount(message: Message, state: FSMContext):
    await state.update_data(amount=float(message.text))
    await message.answer("Введите годовую ставку (в %):")
    await state.set_state(DepositStates.waiting_for_rate)


@dp.message(DepositStates.waiting_for_rate)
async def deposit_rate(message: Message, state: FSMContext):
    await state.update_data(rate=float(message.text))
    await message.answer("Введите срок вклада (в месяцах):")
    await state.set_state(DepositStates.waiting_for_term)


@dp.message(DepositStates.waiting_for_term)
async def deposit_calc(message: Message, state: FSMContext):
    # 🔧 ФИКС: сохраняем term в состояние
    await state.update_data(term=int(message.text))

    data = await state.get_data()
    amount = data['amount']
    rate = data['rate'] / 100
    term = data['term']  # Теперь работает

    # Простой расчет с капитализацией каждый месяц
    final_amount = amount * (1 + rate / 12) ** term
    profit = final_amount - amount

    await message.answer(
        f"📈 **Результат вклада (с капитализацией):**\n"
        f"Итоговая сумма: {final_amount:.2f} руб.\n"
        f"Чистая прибыль: {profit:.2f} руб.",
        reply_markup=get_main_keyboard()
    )
    await state.clear()


# --- 🎯 МОДУЛЬ: 52 НЕДЕЛИ БОГАТСТВА ---
@dp.message(F.text == "🎯 Игра: 52 недели богатства")
async def game_status(message: Message):
    conn = sqlite3.connect("finance_game.db")
    cursor = conn.cursor()
    cursor.execute("SELECT current_week, total_saved FROM users WHERE user_id = ?", (message.from_user.id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (message.from_user.id,))
        conn.commit()
        user = (1, 0.0)

    current_week, total_saved = user
    conn.close()

    # По классике каждую неделю откладывают на 100 руб больше (100, 200, 300...)
    money_to_save = current_week * 100

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📥 Я отложил деньги!")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        f"📅 **Неделя:** {current_week} из 52\n"
        f"💰 **На этой неделе нужно отложить:** {money_to_save} руб.\n"
        f"🏦 **Всего накоплено:** {total_saved:.2f} руб.\n\n"
        f"Суть игры: каждую неделю вы откладываете на 100 руб больше, чем в прошлую!",
        reply_markup=kb
    )


@dp.message(F.text == "📥 Я отложил деньги!")
async def game_save_money(message: Message):
    conn = sqlite3.connect("finance_game.db")
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT current_week, total_saved FROM users WHERE user_id = ?", (message.from_user.id,))
        user = cursor.fetchone()

        if user:
            current_week, total_saved = user

            # Проверка на завершение игры
            if current_week > 52:
                await message.answer(
                    "🏆 Вы уже завершили игру! Используйте /reset_game для перезапуска.",
                    reply_markup=get_main_keyboard()
                )
                return

            money_to_save = current_week * 100
            new_week = current_week + 1
            new_total = total_saved + money_to_save

            cursor.execute("UPDATE users SET current_week = ?, total_saved = ? WHERE user_id = ?",
                           (new_week, new_total, message.from_user.id))
            conn.commit()

            if new_week > 52:
                await message.answer(
                    f"🏆 **ПОЗДРАВЛЯЮ!** 🏆\n"
                    f"Вы прошли игру '52 недели богатства'!\n"
                    f"💰 Всего накоплено: {new_total:.2f} руб.",
                    reply_markup=get_main_keyboard()
                )
            else:
                await message.answer(
                    f"✅ Отлично! Вы отложили {money_to_save} руб.\n"
                    f"📊 Прогресс: {new_week - 1}/52 недель\n"
                    f"💰 Всего накоплено: {new_total:.2f} руб.\n\n"
                    f"🎯 На следующей неделе нужно отложить: {new_week * 100} руб.",
                    reply_markup=get_main_keyboard()
                )
        else:
            # Создаем нового пользователя
            cursor.execute("INSERT INTO users (user_id) VALUES (?)", (message.from_user.id,))
            conn.commit()
            await message.answer(
                "🔄 Игра начата! Нажмите '🎯 Игра: 52 недели богатства' чтобы начать.",
                reply_markup=get_main_keyboard()
            )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
    finally:
        conn.close()


# ➕ Добавьте команду для сброса игры
@dp.message(Command("reset_game"))
async def reset_game(message: Message):
    conn = sqlite3.connect("finance_game.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET current_week = 1, total_saved = 0 WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    conn.close()
    await message.answer("🔄 Игра сброшена! Начните накопления заново.", reply_markup=get_main_keyboard())


@dp.message(F.text == "🔙 Назад")
async def back_to_main(message: Message):
    await message.answer("Главное меню", reply_markup=get_main_keyboard())


# --- ℹ️ ДОПЫ: ИНФО ---
@dp.message(F.text == "ℹ️ О боте")
async def about_bot(message: Message):
    await message.answer(
        "🤖 Бот создан для учебного проекта.\n"
        "Выполнил студент группы: [ТВОЕ ИМЯ]\n"
        "Функционал включает кредиты, вклады и финансовый трекер.",
        reply_markup=get_main_keyboard()
    )


# --- 🏁 ЗАПУСК БОТА ---
async def main():
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
