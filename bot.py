import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
)
import aiohttp
import asyncio
from urllib.parse import urlparse
import sqlite3
import time
import pythonping
import socket

# Configuración inicial
TOKEN = "7725269349:AAGuTEMxnYYre1AA4BcO-_RL7N7Rz-cI3iU"
CHECK_INTERVAL = 60
ADMIN_CHAT_ID = None
DATABASE_NAME = "watchbot.db"

# Estados para la conversación de edición
EDITING, SET_PING_INTERVAL, SET_PORTS = range(3)

# Inicializar base de datos
def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INT PRIMARY KEY, settings TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS websites
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INT,
                  url TEXT,
                  check_interval INT DEFAULT 60,
                  last_status INT,
                  last_checked TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS metrics
                 (website_id INT,
                  timestamp TIMESTAMP,
                  response_time REAL,
                  status_code INT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS ct_certs
                 (website_id INT,
                  cert_hash TEXT,
                  first_seen TIMESTAMP)''')
    
    conn.commit()
    conn.close()

init_db()

# Helpers de base de datos
def get_db_connection():
    return sqlite3.connect(DATABASE_NAME)

# Inicializar aplicación
application = Application.builder().token(TOKEN).build()

# ========================= COMANDOS PRINCIPALES =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📚 Ayuda", callback_data='help'),
         InlineKeyboardButton("➕ Añadir Sitio", callback_data='add')],
        [InlineKeyboardButton("🔧 Editar", callback_data='edit'),
         InlineKeyboardButton("📈 Métricas", callback_data='metrics')]
    ]
    
    await update.message.reply_text(
        "👋 ¡Hola! Soy @watch_bot\n\n"
        "Puedo monitorizar tus sitios web y notificarte de cualquier problema.\n"
        "Usa los botones o comandos para interactuar:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def add_website(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Implementación similar a add_url pero con base de datos
    pass  # (Usar implementación anterior adaptada a SQL)

# ========================= FUNCIONALIDADES COMPLEJAS =========================

async def edit_website(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = get_db_connection()
    websites = conn.execute('SELECT id, url FROM websites WHERE user_id = ?', 
                           (query.from_user.id,)).fetchall()
    conn.close()
    
    keyboard = []
    for site in websites:
        keyboard.append([InlineKeyboardButton(site[1], callback_data=f'edit_{site[0]}')])
    
    await query.edit_message_text(
        "Selecciona un sitio para editar:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return EDITING

async def website_metrics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Implementar gráficos o estadísticas usando los datos de metrics
    pass

async def ping_host(update: Update, context: ContextTypes.DEFAULT_TYPE):
    host = " ".join(context.args)
    try:
        response = pythonping.ping(host, count=3)
        await update.message.reply_text(f"🏓 Resultados ping a {host}:\n{response.rtt_avg_ms}ms avg")
    except Exception as e:
        await update.message.reply_text(f"❌ Error al hacer ping: {str(e)}")

async def port_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    host = " ".join(context.args)
    open_ports = []
    
    # Escaneo básico de puertos comunes
    for port in [80, 443, 22, 21, 3389]:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        if result == 0:
            open_ports.append(str(port))
        sock.close()
    
    await update.message.reply_text(f"🔍 Puertos abiertos en {host}:\n{', '.join(open_ports) or 'Ninguno'}")

async def check_isup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Implementación de verificación manual
    pass

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Comando cancelado")
    return ConversationHandler.END

# ========================= MENSAJES Y CONFIGURACIÓN =========================

async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 **Menú de Ayuda**\n\n"
        "/add - Añadir sitio web\n"
        "/edit - Editar configuración\n"
        "/status - Estado de tus sitios\n"
        "/metrics - Métricas de rendimiento\n"
        "/ping [host] - Hacer ping\n"
        "/ports [host] - Escanear puertos\n"
        "/isup [url] - Verificación manual\n"
        "/cancel - Cancelar operación\n\n"
        "📢 Actualizaciones: @watch_bot_news\n"
        "💌 Soporte: @CaddisFly\n"
        "❤️ Considera donar para mantener el bot"
    )

# ========================= CONVERSATION HANDLERS =========================

edit_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('edit', edit_website)],
    states={
        EDITING: [CallbackQueryHandler(edit_website_settings)],
        SET_PING_INTERVAL: [MessageHandler(filters.TEXT, set_ping_interval)]
    },
    fallbacks=[CommandHandler('cancel', cancel_command)]
)

# ========================= TAREAS PERIÓDICAS =========================

async def check_ct_certificates(context: ContextTypes.DEFAULT_TYPE):
    # Implementar verificación de Certificate Transparency
    pass

async def scheduled_checks(context: ContextTypes.DEFAULT_TYPE):
    # Implementar verificaciones periódicas
    pass

# ========================= CONFIGURACIÓN FINAL =========================

def main():
    # Handlers principales
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_menu))
    application.add_handler(edit_conv_handler)
    
    # Handlers adicionales
    application.add_handler(CommandHandler("ping", ping_host))
    application.add_handler(CommandHandler("ports", port_scan))
    application.add_handler(CommandHandler("isup", check_isup))
    application.add_handler(CommandHandler("cancel", cancel_command))
    
    # Tareas programadas
    job_queue = application.job_queue
    job_queue.run_repeating(scheduled_checks, interval=CHECK_INTERVAL)
    job_queue.run_daily(check_ct_certificates, time=time(3, 0, 0))  # Verificar diario a las 3 AM

    application.run_polling()

if __name__ == "__main__":
    main()
