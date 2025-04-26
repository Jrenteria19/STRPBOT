import os
import discord
from discord.ext import commands
from discord import app_commands
import pymysql
import logging
from dotenv import load_dotenv
import datetime
import random
import aiohttp
import io
from discord import Embed, Color, File
from datetime import datetime, timedelta
import uuid
import threading
import time


# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('bot')

# Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Configuración del bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)  # Mantenemos el prefijo pero no usaremos comandos de prefijo

# Conexión global a la base de datos MySQL de Railway
DB_HOST = os.getenv("MYSQLHOST", "mysql.railway.internal")
DB_USER = os.getenv("MYSQLUSER", "root")
DB_PASSWORD = os.getenv("MYSQLPASSWORD", "FPaHGLioxfZPXgtQcdmpJbLNbeBwSRTl")
DB_NAME = os.getenv("MYSQL_DATABASE", "railway")
DB_PORT = int(os.getenv("MYSQLPORT", "3306"))

db_lock = threading.Lock()
db_connection = None

def get_db_connection():
    """Obtiene la conexión global a la base de datos MySQL"""
    global db_connection
    if db_connection is None:
        db_connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False
        )
    return db_connection

def execute_with_retry(query, params=(), max_retries=3, retry_delay=1):
    """Ejecuta una consulta SQL con reintentos en caso de bloqueo"""
    for attempt in range(max_retries):
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                conn.commit()
                return cursor
            except pymysql.OperationalError as e:
                if "Lock wait timeout" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Database locked, retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    continue
                else:
                    raise
            except Exception:
                conn.rollback()
                raise
    raise pymysql.OperationalError("Database is locked after maximum retries")

def init_db():
    """Inicializa la base de datos si no existe"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Crear tabla de usuarios
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT NOT NULL,
            points INTEGER DEFAULT 0,
            last_daily TEXT
        )
        ''')
        
        # Crear tabla de configuración del servidor
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id BIGINT PRIMARY KEY,
            prefix VARCHAR(10) DEFAULT '!',
            welcome_channel_id BIGINT,
            welcome_message TEXT
        )
        ''')
        
        # Crear tabla de cédulas de identidad
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS cedulas (
            user_id BIGINT PRIMARY KEY,
            rut VARCHAR(20) NOT NULL UNIQUE,
            primer_nombre TEXT NOT NULL,
            segundo_nombre TEXT NOT NULL,
            apellido_paterno TEXT NOT NULL,
            apellido_materno TEXT NOT NULL,
            fecha_nacimiento TEXT NOT NULL,
            edad INTEGER NOT NULL,
            nacionalidad TEXT NOT NULL,
            genero TEXT NOT NULL,
            usuario_roblox TEXT NOT NULL,
            fecha_emision TEXT NOT NULL,
            fecha_vencimiento TEXT NOT NULL,
            avatar_url TEXT
        )
        ''')

        # Crear tabla de licencias
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS licencias (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id BIGINT NOT NULL,
            tipo_licencia TEXT NOT NULL,
            nombre_licencia TEXT NOT NULL,
            fecha_emision TEXT NOT NULL,
            fecha_vencimiento TEXT NOT NULL,
            emitida_por BIGINT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES cedulas(user_id)
        )
        ''')
        
        # Crear tabla de vehículos
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS vehiculos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id BIGINT NOT NULL,
            placa VARCHAR(20) NOT NULL UNIQUE,
            modelo TEXT NOT NULL,
            marca TEXT NOT NULL,
            gama TEXT NOT NULL,
            anio INTEGER NOT NULL,
            color TEXT NOT NULL,
            revision_tecnica TEXT NOT NULL,
            permiso_circulacion TEXT NOT NULL,
            codigo_pago TEXT NOT NULL,
            imagen_url TEXT NOT NULL,
            fecha_registro TEXT NOT NULL,
            registrado_por BIGINT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES cedulas(user_id)
        )
        ''')

        # Crear tabla de códigos de pago
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_codes (
            code TEXT PRIMARY KEY,
            amount INTEGER NOT NULL,
            description TEXT NOT NULL,
            user_id BIGINT NOT NULL,
            used BOOLEAN DEFAULT FALSE,
            created_at TEXT NOT NULL,
            used_at TEXT,
            created_by BIGINT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES cedulas(user_id)
        )
        ''')

        # Crear tabla de propiedades
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS propiedades (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id BIGINT NOT NULL,
            numero_domicilio TEXT NOT NULL UNIQUE,
            zona TEXT NOT NULL,
            color TEXT NOT NULL,
            numero_pisos INTEGER NOT NULL,
            codigo_pago TEXT NOT NULL,
            imagen_url TEXT NOT NULL,
            fecha_registro TEXT NOT NULL,
            registrado_por BIGINT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES cedulas(user_id)
        )
        ''')

        # Crear tabla de arrestos
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS arrestos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id TEXT NOT NULL,
            rut TEXT NOT NULL,
            razon TEXT NOT NULL,
            tiempo_prision TEXT NOT NULL,
            monto_multa INTEGER NOT NULL,
            foto_url TEXT NOT NULL,
            fecha_arresto TEXT NOT NULL,
            oficial_id TEXT NOT NULL,
            estado TEXT DEFAULT 'Activo'
        )
        ''')

        # Crear tabla de multas
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS multas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id TEXT NOT NULL,
            rut TEXT NOT NULL,
            razon TEXT NOT NULL,
            monto_multa INTEGER NOT NULL,
            foto_url TEXT NOT NULL,
            fecha_multa TEXT NOT NULL,
            oficial_id TEXT NOT NULL,
            estado TEXT DEFAULT 'Pendiente'
        )
        ''')

        # Crear tabla de emergencias
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS emergencias (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id BIGINT,
            razon TEXT,
            servicio TEXT,
            ubicacion TEXT,
            fecha TEXT,
            servicios_notificados TEXT
        )
        ''')

        conn.commit()
        logger.info("Base de datos inicializada correctamente")

# Definir los tipos de licencias disponibles
TIPOS_LICENCIAS = {
    "B": {"nombre": "Clase B - Vehículos particulares", "rol_id": 1339386615176630294},
    "C": {"nombre": "Clase C - Motocicletas", "rol_id": 1339386615176630293},
    "D": {"nombre": "Clase D - Transporte público", "rol_id": 1339386615159722124},
    "E": {"nombre": "Clase E - Vehículos de carga", "rol_id": 1347795270221434970},
    "F": {"nombre": "Clase F - Vehículos especiales", "rol_id": 1339386615159722123},
    "A1": {"nombre": "Clase A1 - Maquinaria agrícola", "rol_id": 1339386615176630296},
    "A2": {"nombre": "Clase A2 - Maquinaria industrial", "rol_id": 1339386615176630295},
    "A3": {"nombre": "Clase A3 - Vehículos de emergencia", "rol_id": 1347794731844898939},
    "A4": {"nombre": "Clase A4 - Vehículos militares", "rol_id": 1347794874484920320},
    "A5": {"nombre": "Clase A5 - Vehículos especiales pesados", "rol_id": 1347795085084987504},
    "A6": {"nombre": "Clase Armas - Portación de armas Bajo calibre Legalmente", "rol_id": 1339386615159722122}
}

# Definir opciones para autocompletado
GAMAS_VEHICULO = [
    "Baja", "Media", "Alta", "Premium", "Lujo", "Deportivo", "Superdeportivo", 
    "Clásico", "Colección", "Utilitario", "Trabajo", "Militar", "Policial", "Emergencia"
]

COLORES_VEHICULO = [
    "Negro", "Blanco", "Gris", "Plata", "Rojo", "Azul", "Verde", "Amarillo", 
    "Naranja", "Marrón", "Beige", "Dorado", "Morado", "Rosa", "Turquesa", "Burdeos"
]

ESTADOS_REVISION = [
    "Aprobada", "Rechazada", "Pendiente", "Vencida", "No Aplicable"
]

ESTADOS_PERMISO = [
    "Vigente", "Vencido", "En Trámite", "Suspendido", "Revocado"
]

# Lista de zonas para autocompletado
ZONAS_PROPIEDAD = ["Quilicura", "La Granja", "Las Condes", "Pudahuel"]

# Función para generar un RUT chileno único y válido
def generar_rut():
    while True:
        # Generar un número aleatorio entre 10.000.000 y 25.000.000
        num = random.randint(10000000, 25000000)
        
        # Calcular dígito verificador
        suma = 0
        multiplicador = 2
        
        # Algoritmo para calcular dígito verificador
        temp = num
        while temp > 0:
            suma += (temp % 10) * multiplicador
            multiplicador = multiplicador + 1 if multiplicador < 7 else 2
            temp //= 10
            
        dv = 11 - (suma % 11)
        
        if dv == 11:
            dv = '0'
        elif dv == 10:
            dv = 'K'
        else:
            dv = str(dv)
            
        rut = f"{num}-{dv}"
        
        # Verificar si el RUT ya existe en la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT rut FROM cedulas WHERE rut = %s', (rut,))
        result = cursor.fetchone()
        
        if not result:
            return rut

# Función para validar fecha de nacimiento
def validar_fecha_nacimiento(fecha_str):
    try:
        # Convertir string a objeto datetime
        fecha = datetime.strptime(fecha_str, "%d-%m-%Y")
        
        # Calcular edad
        hoy = datetime.now()
        edad = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))
        
        # Validar que la edad esté entre 18 y 80 años
        if 18 <= edad <= 80:
            return True, edad
        else:
            return False, None
    except ValueError:
        return False, None

# Función para obtener avatar de Roblox
async def obtener_avatar_roblox(username):
    try:
        # Verificar conexión a Roblox
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get("https://www.roblox.com", timeout=5.0) as resp:
                    if resp.status != 200:
                        logger.warning(f"No se puede conectar al sitio web de Roblox, estado: {resp.status}")
                        return "https://tr.rbxcdn.com/e5b3371b4efc7642a22c1b36265a9ba9/420/420/AvatarHeadshot/Png"
            except Exception as e:
                logger.warning(f"No se puede conectar al sitio web de Roblox: {e}")
                return "https://tr.rbxcdn.com/e5b3371b4efc7642a22c1b36265a9ba9/420/420/AvatarHeadshot/Png"
            
            # Intentar diferentes APIs para encontrar el ID de usuario
            apis_to_try = [
                f"https://api.roblox.com/users/get-by-username?username={username}",
                f"https://users.roblox.com/v1/users/search?keyword={username}&limit=10"
            ]
            
            user_id = None
            
            for api_url in apis_to_try:
                try:
                    async with session.get(api_url, timeout=10.0) as resp:
                        if resp.status != 200:
                            continue
                        
                        data = await resp.json()
                        
                        if "Id" in data:
                            user_id = data["Id"]
                            break
                        elif "data" in data and len(data["data"]) > 0:
                            for user in data["data"]:
                                if user.get("name", "").lower() == username.lower():
                                    user_id = user.get("id")
                                    break
                            if user_id:
                                break
                except Exception as e:
                    logger.warning(f"Error al intentar con API {api_url}: {e}")
                    continue
            
            if not user_id:
                logger.warning(f"No se pudo encontrar el ID de usuario para {username}, usando avatar predeterminado")
                return "https://tr.rbxcdn.com/e5b3371b4efc7642a22c1b36265a9ba9/420/420/AvatarHeadshot/Png"
            
            # Obtener URL del avatar
            try:
                avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=420x420&format=Png"
                async with session.get(avatar_url, timeout=10.0) as resp:
                    if resp.status == 200:
                        avatar_data = await resp.json()
                        if "data" in avatar_data and len(avatar_data["data"]) > 0:
                            avatar_url = avatar_data["data"][0].get("imageUrl")
                            if avatar_url:
                                return avatar_url
            except Exception as e:
                logger.error(f"Error al obtener avatar: {e}")
            
            # Si todo lo anterior falla, usar URL directa
            return f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png"
                
    except Exception as e:
        logger.error(f"Error al buscar usuario de Roblox: {e}")
        return "https://tr.rbxcdn.com/e5b3371b4efc7642a22c1b36265a9ba9/420/420/AvatarHeadshot/Png"

# Lista de nacionalidades comunes para autocompletar
NACIONALIDADES = [
    "Chile", "Argentina", "Perú", "Bolivia", "Colombia", "Ecuador", "Venezuela", 
    "Brasil", "Uruguay", "Paraguay", "México", "España", "Estados Unidos", 
    "Canadá", "Italia", "Francia", "Alemania", "Reino Unido", "Japón", "China"
]

# Lista de géneros para autocompletar
GENEROS = ["M", "F"]

# Función para autocompletar nacionalidad
async def autocompletar_nacionalidad(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocompleta la nacionalidad basado en lo que el usuario ha escrito"""
    return [
        app_commands.Choice(name=nacionalidad, value=nacionalidad)
        for nacionalidad in NACIONALIDADES if current.lower() in nacionalidad.lower()
    ][:25]  # Discord permite máximo 25 opciones

# Función para autocompletar género
async def autocompletar_genero(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocompleta el género basado en lo que el usuario ha escrito"""
    opciones = []
    if current.upper() == "M" or "mas" in current.lower():
        opciones.append(app_commands.Choice(name="Masculino", value="M"))
    if current.upper() == "F" or "fem" in current.lower():
        opciones.append(app_commands.Choice(name="Femenino", value="F"))
    return opciones

@bot.event
async def on_ready():
    """Evento que se ejecuta cuando el bot está listo"""
    logger.info(f'🚀 Bot conectado como {bot.user.name}')

    # Inicializar la base de datos
    init_db()
    
    # Sincronizar los comandos de aplicación con Discord
    try:
        synced = await bot.tree.sync()
        logger.info(f'✅ Sincronizados {len(synced)} comandos de aplicación')
    except Exception as e:
        logger.error(f'❌ Error al sincronizar comandos: {e}')

    # Contar miembros humanos (sin bots) en el servidor
    human_members = 0
    for guild in bot.guilds:
        if "Santiago RP" in guild.name:
            human_members = sum(1 for member in guild.members if not member.bot)
            break
        human_members = "Desconocido"

    # Establecer actividad simple
    activity = discord.Activity(
        type=discord.ActivityType.playing,
        name=f"SantiagoRP | Creado por Smile | {human_members} miembros"
    )
    await bot.change_presence(activity=activity)
    
    # Mensaje de log simple
    logger.info(
        f'🌆 Santiago RP listo | Creado por Smile | {human_members} miembros'
    )

# Comando de barra diagonal para crear cédula
@bot.tree.command(name="crear-cedula", description="Crea una cédula de identidad para un usuario")
@app_commands.describe(
    primer_nombre="Primer nombre del usuario",
    segundo_nombre="Segundo nombre del usuario",
    apellido_paterno="Apellido paterno del usuario",
    apellido_materno="Apellido materno del usuario",
    fecha_nacimiento="Fecha de nacimiento (formato DD-MM-YYYY)",
    nacionalidad="Nacionalidad del usuario",
    genero="Género (M o F)",
    usuario_roblox="Nombre de usuario en Roblox"
)
@app_commands.autocomplete(nacionalidad=autocompletar_nacionalidad, genero=autocompletar_genero)
async def slash_crear_cedula(
    interaction: discord.Interaction,
    primer_nombre: str,
    segundo_nombre: str,
    apellido_paterno: str,
    apellido_materno: str,
    fecha_nacimiento: str,
    nacionalidad: str,
    genero: str,
    usuario_roblox: str
):
    """Crea una cédula de identidad para un usuario usando comandos de barra diagonal"""
    
    # Verificar que el comando se use en el canal correcto
    if interaction.channel_id != 1339386616803885088:
        embed = discord.Embed(
            title="❌ Canal incorrecto",
            description="Este comando solo puede ser utilizado en el canal designado para cédulas.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Verificar si el usuario ya tiene una cédula
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT rut FROM cedulas WHERE user_id = %s', (interaction.user.id,))
    cedula_existente = cursor.fetchone()
    
    if cedula_existente:
        embed = discord.Embed(
            title="❌ Ya tienes una cédula",
            description=f"Ya tienes una cédula de identidad registrada con el RUT: **{cedula_existente['rut']}**",
            color=discord.Color.red()
        )
        embed.add_field(
            name="📋 Ver tu Cédula",
            value=f"Puedes ver tu cédula en cualquier momento usando el comando `/ver-cedula` en el canal <#{1339386616803885089}>",
            inline=False
        )
        embed.set_footer(text="Santiago RP - Sistema de Registro Civil")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Validar fecha de nacimiento
    fecha_valida, edad = validar_fecha_nacimiento(fecha_nacimiento)
    if not fecha_valida:
        embed = discord.Embed(
            title="❌ Fecha inválida",
            description="La fecha de nacimiento debe tener el formato DD-MM-YYYY y la edad debe estar entre 18 y 80 años.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Validar género
    if genero.upper() not in ['M', 'F']:
        embed = discord.Embed(
            title="❌ Género inválido",
            description="El género debe ser 'M' o 'F'.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Obtener avatar de Roblox
    avatar_url = await obtener_avatar_roblox(usuario_roblox)
    
    # Generar RUT único
    rut = generar_rut()
    
    # Generar fechas de emisión y vencimiento
    fecha_emision = datetime.now().strftime("%d-%m-%Y")
    fecha_vencimiento = (datetime.now() + timedelta(days=365*5)).strftime("%d-%m-%Y")  # 5 años de validez
    
    # Guardar en la base de datos
    try:
        cursor.execute('''
        INSERT INTO cedulas (
            user_id, rut, primer_nombre, segundo_nombre, apellido_paterno, 
            apellido_materno, fecha_nacimiento, edad, nacionalidad, genero, 
            usuario_roblox, fecha_emision, fecha_vencimiento, avatar_url
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            interaction.user.id, rut, primer_nombre, segundo_nombre, apellido_paterno,
            apellido_materno, fecha_nacimiento, edad, nacionalidad, genero,
            usuario_roblox, fecha_emision, fecha_vencimiento, avatar_url
        ))
        conn.commit()
        
        # Crear embed con la información de la cédula
        embed = discord.Embed(
            title="✅ Cédula de Identidad Creada",
            description=f"Se ha creado exitosamente tu cédula de identidad con el RUT: **{rut}**",
            color=discord.Color.green()
        )
        
        embed.add_field(name="Nombre Completo", value=f"{primer_nombre} {segundo_nombre} {apellido_paterno} {apellido_materno}", inline=False)
        embed.add_field(name="Fecha de Nacimiento", value=fecha_nacimiento, inline=True)
        embed.add_field(name="Edad", value=str(edad), inline=True)
        embed.add_field(name="Nacionalidad", value=nacionalidad, inline=True)
        embed.add_field(name="Género", value="Masculino" if genero == "M" else "Femenino", inline=True)
        embed.add_field(name="Usuario Roblox", value=usuario_roblox, inline=True)
        embed.add_field(name="Fecha de Emisión", value=fecha_emision, inline=True)
        embed.add_field(name="Fecha de Vencimiento", value=fecha_vencimiento, inline=True)
        
        embed.set_thumbnail(url=avatar_url)
        embed.set_footer(text="Santiago RP - Sistema de Registro Civil")
        
        await interaction.response.send_message(embed=embed)
        
        # Enviar mensaje en el canal de registros
        canal_registros = bot.get_channel(1339386616803885090)  # ID del canal de registros
        if canal_registros:
            embed_registro = discord.Embed(
                title="📋 Nueva Cédula Registrada",
                description=f"El usuario {interaction.user.mention} ha registrado una nueva cédula de identidad.",
                color=discord.Color.blue()
            )
            embed_registro.add_field(name="RUT", value=rut, inline=True)
            embed_registro.add_field(name="Nombre", value=f"{primer_nombre} {apellido_paterno}", inline=True)
            embed_registro.add_field(name="Usuario Roblox", value=usuario_roblox, inline=True)
            embed_registro.set_thumbnail(url=avatar_url)
            embed_registro.set_footer(text=f"ID: {interaction.user.id} • {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
            
            await canal_registros.send(embed=embed_registro)
        
    except Exception as e:
        logger.error(f"Error al crear cédula: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description="Ocurrió un error al crear tu cédula. Por favor, intenta nuevamente más tarde.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ver-cedula", description="Muestra tu cédula de identidad o la de otro usuario")
@app_commands.describe(ciudadano="Usuario del que quieres ver la cédula (opcional)")
async def slash_ver_cedula(interaction: discord.Interaction, ciudadano: discord.Member = None):
    """Muestra la cédula de identidad del usuario o de otro miembro"""
    
    # Verificar que el comando se use en el canal correcto
    if interaction.channel_id != 1339386616803885089:
        embed = discord.Embed(
            title="❌ Canal incorrecto",
            description="Este comando solo puede ser utilizado en el canal designado para ver cédulas.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Si no se especifica un ciudadano, mostrar la cédula del usuario que ejecuta el comando
    if ciudadano is None:
        ciudadano = interaction.user
    
    # Obtener la cédula de la base de datos
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT * FROM cedulas WHERE user_id = %s
    ''', (ciudadano.id,))
    
    cedula = cursor.fetchone()
    
    if not cedula:
        embed = discord.Embed(
            title="❌ Cédula no encontrada",
            description=f"No se encontró una cédula registrada para {ciudadano.mention}.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Crear embed con la información de la cédula
    embed = discord.Embed(
        title="🪪 Cédula de Identidad",
        description=f"**RUT:** {cedula['rut']}",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="Nombre Completo", 
        value=f"{cedula['primer_nombre']} {cedula['segundo_nombre']} {cedula['apellido_paterno']} {cedula['apellido_materno']}", 
        inline=False
    )
    embed.add_field(name="Fecha de Nacimiento", value=cedula['fecha_nacimiento'], inline=True)
    embed.add_field(name="Edad", value=str(cedula['edad']), inline=True)
    embed.add_field(name="Nacionalidad", value=cedula['nacionalidad'], inline=True)
    embed.add_field(name="Género", value="Masculino" if cedula['genero'] == "M" else "Femenino", inline=True)
    embed.add_field(name="Usuario Roblox", value=cedula['usuario_roblox'], inline=True)
    embed.add_field(name="Fecha de Emisión", value=cedula['fecha_emision'], inline=True)
    embed.add_field(name="Fecha de Vencimiento", value=cedula['fecha_vencimiento'], inline=True)
    
    embed.set_thumbnail(url=cedula['avatar_url'])
    embed.set_footer(text=f"Santiago RP - Sistema de Registro Civil • ID: {ciudadano.id}")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="eliminar-cedula", description="Elimina la cédula de identidad de un ciudadano")
@app_commands.describe(ciudadano="Ciudadano cuya cédula deseas eliminar")
async def slash_eliminar_cedula(interaction: discord.Interaction, ciudadano: discord.Member):
    """Elimina la cédula de identidad de un ciudadano (solo roles autorizados)"""
    
    # Lista de roles autorizados
    roles_autorizados = [
        1339386615235346439, 
        1347803116741066834, 
        1339386615222767662, 
        1346545514492985486, 
        1339386615247798362
    ]
    
    # Canal de logs
    canal_logs_id = 1363767555411542077
    
    # Verificar si el usuario tiene alguno de los roles autorizados
    tiene_permiso = False
    for role in interaction.user.roles:
        if role.id in roles_autorizados:
            tiene_permiso = True
            break
    
    if not tiene_permiso:
        embed = discord.Embed(
            title="❌ Sin permisos",
            description="No tienes permiso para eliminar cédulas de identidad.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Verificar si el ciudadano tiene una cédula
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT rut, primer_nombre, segundo_nombre, apellido_paterno, apellido_materno
    FROM cedulas WHERE user_id = ?
    ''', (ciudadano.id,))
    
    result = cursor.fetchone()
    
    if not result:
        embed = discord.Embed(
            title="❌ Cédula no encontrada",
            description=f"{ciudadano.display_name} no tiene una cédula de identidad registrada.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        conn.close()
        return
    
    # Guardar información para el log
    rut, primer_nombre, segundo_nombre, apellido_paterno, apellido_materno = result
    nombre_completo = f"{primer_nombre} {segundo_nombre} {apellido_paterno} {apellido_materno}"
    
    # Eliminar la cédula
    try:
        cursor.execute('DELETE FROM cedulas WHERE user_id = ?', (ciudadano.id,))
        conn.commit()
        
        # Mensaje de éxito para el usuario
        embed = discord.Embed(
            title="✅ Cédula Eliminada",
            description=f"La cédula de identidad de {ciudadano.mention} ha sido eliminada correctamente.",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Información eliminada",
            value=f"RUT: {rut}\nNombre: {nombre_completo}",
            inline=False
        )
        embed.set_footer(text="Santiago RP - Sistema de Registro Civil")
        
        await interaction.response.send_message(embed=embed)
        
        # Enviar log al canal de logs
        canal_logs = interaction.guild.get_channel(canal_logs_id)
        if canal_logs:
            log_embed = discord.Embed(
                title="🗑️ Cédula Eliminada",
                description=f"Se ha eliminado una cédula de identidad del sistema.",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            log_embed.add_field(
                name="Administrador",
                value=f"{interaction.user.mention} ({interaction.user.name})",
                inline=True
            )
            log_embed.add_field(
                name="Ciudadano",
                value=f"{ciudadano.mention} ({ciudadano.name})",
                inline=True
            )
            log_embed.add_field(
                name="RUT eliminado",
                value=rut,
                inline=True
            )
            log_embed.add_field(
                name="Nombre completo",
                value=nombre_completo,
                inline=False
            )
            log_embed.set_footer(text=f"ID del usuario: {ciudadano.id}")
            
            await canal_logs.send(embed=log_embed)
        else:
            logger.error(f"No se pudo encontrar el canal de logs con ID {canal_logs_id}")
            
    except Exception as e:
        logger.error(f"Error al eliminar cédula: {e}")
        embed = discord.Embed(
            title="❌ Error al eliminar cédula",
            description=f"Ocurrió un error al eliminar la cédula: {e}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.event
async def on_command_error(ctx, error):
    """Manejo global de errores para comandos de prefijo (por si alguien intenta usarlos)"""
    if isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(
            title="❌ Comando no encontrado",
            description="Los comandos con prefijo '!' ya no están disponibles. Por favor, usa los comandos de barra diagonal (/) en su lugar.",
            color=discord.Color.red()
        )
        embed.add_field(
            name="Comandos disponibles",
            value="Usa `/ayuda` para ver la lista de comandos disponibles.",
            inline=False
        )
        await ctx.send(embed=embed, delete_after=10)
    else:
        logger.error(f"Error no manejado: {error}")

# Definir los tipos de licencias disponibles
TIPOS_LICENCIAS = {
    "B": {"nombre": "Clase B - Vehículos particulares", "rol_id": 1339386615176630294},
    "C": {"nombre": "Clase C - Motocicletas", "rol_id": 1339386615176630293},
    "D": {"nombre": "Clase D - Transporte público", "rol_id": 1339386615159722124},
    "E": {"nombre": "Clase E - Vehículos de carga", "rol_id": 1347795270221434970},
    "F": {"nombre": "Clase F - Vehículos especiales", "rol_id": 1339386615159722123},
    "A1": {"nombre": "Clase A1 - Maquinaria agrícola", "rol_id": 1339386615176630296},
    "A2": {"nombre": "Clase A2 - Maquinaria industrial", "rol_id": 1339386615176630295},
    "A3": {"nombre": "Clase A3 - Vehículos de emergencia", "rol_id": 1347794731844898939},
    "A4": {"nombre": "Clase A4 - Vehículos militares", "rol_id": 1347794874484920320},
    "A5": {"nombre": "Clase A5 - Vehículos especiales pesados", "rol_id": 1347795085084987504},
    "A6": {"nombre": "Clase Armas - Portación de armas Bajo calibre Legalmente", "rol_id": 1339386615159722122}
}

# Función para autocompletar tipo de licencia
async def autocompletar_tipo_licencia(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocompleta el tipo de licencia basado en lo que el usuario ha escrito"""
    return [
        app_commands.Choice(name=f"{clase} - {info['nombre']}", value=clase)
        for clase, info in TIPOS_LICENCIAS.items() 
        if current.upper() in clase or current.lower() in info['nombre'].lower()
    ][:25]  # Discord permite máximo 25 opciones

@bot.tree.command(name="tramitar-licencia", description="Tramita una licencia para un ciudadano")
@app_commands.describe(
    ciudadano="Ciudadano que tramita la licencia",
    tipo_licencia="Tipo de licencia a tramitar"
)
@app_commands.autocomplete(tipo_licencia=autocompletar_tipo_licencia)
async def slash_tramitar_licencia(
    interaction: discord.Interaction,
    ciudadano: discord.Member,
    tipo_licencia: str
):
    """Tramita una licencia para un ciudadano (solo roles autorizados)"""
    
    # Lista de roles autorizados para tramitar licencias
    roles_autorizados = [
        1339386615235346439, 
        1347803116741066834, 
        1339386615222767662, 
        1346545514492985486, 
        1339386615247798362
    ]
    
    # Verificar si el usuario tiene alguno de los roles autorizados
    tiene_permiso = False
    for role in interaction.user.roles:
        if role.id in roles_autorizados:
            tiene_permiso = True
            break
    
    if not tiene_permiso:
        embed = discord.Embed(
            title="❌ Sin permisos",
            description="No tienes permiso para tramitar licencias.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Verificar si el tipo de licencia es válido
    if tipo_licencia not in TIPOS_LICENCIAS:
        embed = discord.Embed(
            title="❌ Tipo de licencia inválido",
            description="El tipo de licencia especificado no es válido.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Verificar si el ciudadano tiene cédula
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT rut FROM cedulas WHERE user_id = ?', (ciudadano.id,))
    cedula = cursor.fetchone()
    
    if not cedula:
        embed = discord.Embed(
            title="❌ Ciudadano sin cédula",
            description=f"{ciudadano.mention} no tiene una cédula de identidad registrada. Debe tramitar su cédula primero.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        conn.close()
        return
    
    # Verificar si el ciudadano ya tiene la licencia específica que está tramitando
    cursor.execute('SELECT id FROM licencias WHERE user_id = ? AND tipo_licencia = ?', 
                  (ciudadano.id, tipo_licencia))
    licencia_existente = cursor.fetchone()
    
    if licencia_existente:
        embed = discord.Embed(
            title="❌ Licencia ya tramitada",
            description=f"{ciudadano.mention} ya tiene tramitada la licencia {TIPOS_LICENCIAS[tipo_licencia]['nombre']}.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        conn.close()
        return
    
    # Verificar si el ciudadano tiene el rol requerido
    rol_id = TIPOS_LICENCIAS[tipo_licencia]['rol_id']
    rol = interaction.guild.get_role(rol_id)
    
    if not rol:
        embed = discord.Embed(
            title="❌ Error de configuración",
            description=f"No se pudo encontrar el rol con ID {rol_id}. Contacta a un administrador.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        conn.close()
        return
    
    if rol not in ciudadano.roles:
        embed = discord.Embed(
            title="❌ Requisitos no cumplidos",
            description=f"{ciudadano.mention} no tiene el rol requerido para tramitar esta licencia.\n\nSe requiere: {rol.mention}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        conn.close()
        return
    
    # Calcular fechas de emisión y vencimiento
    fecha_emision = datetime.now().strftime("%d/%m/%Y")
    fecha_vencimiento = (datetime.now() + timedelta(days=365*2)).strftime("%d/%m/%Y")  # 2 años de validez
    
    # Guardar la licencia en la base de datos
    try:
        cursor.execute('''
        INSERT INTO licencias 
        (user_id, tipo_licencia, nombre_licencia, fecha_emision, fecha_vencimiento, emitida_por) 
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (ciudadano.id, tipo_licencia, TIPOS_LICENCIAS[tipo_licencia]['nombre'], 
              fecha_emision, fecha_vencimiento, interaction.user.id))
        
        conn.commit()
        
        # Crear y enviar el mensaje embebido con la licencia
        embed = discord.Embed(
            title=f"🇨🇱 SANTIAGO RP 🇨🇱",
            description="DIRECCIÓN DE TRÁNSITO Y TRANSPORTE PÚBLICO",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="LICENCIA DE CONDUCIR", value=f"Tipo: {tipo_licencia}", inline=False)
        embed.add_field(name="Descripción", value=TIPOS_LICENCIAS[tipo_licencia]['nombre'], inline=False)
        embed.add_field(name="Titular", value=ciudadano.mention, inline=True)
        embed.add_field(name="RUT", value=cedula[0], inline=True)
        embed.add_field(name="Fecha Emisión", value=fecha_emision, inline=True)
        embed.add_field(name="Fecha Vencimiento", value=fecha_vencimiento, inline=True)
        embed.add_field(name="Emitida por", value=interaction.user.mention, inline=True)
        
        # Establecer la imagen del avatar del ciudadano
        embed.set_thumbnail(url=ciudadano.display_avatar.url)
        
        # Enviar la licencia al canal
        await interaction.response.send_message(embed=embed)
        
        # Enviar mensaje efímero de confirmación al usuario
        confirmacion_embed = discord.Embed(
            title="✅ ¡Licencia Tramitada con Éxito!",
            description=f"La licencia {tipo_licencia} ha sido tramitada correctamente para {ciudadano.mention}",
            color=discord.Color.green()
        )
        confirmacion_embed.add_field(
            name="📋 Detalles",
            value=f"Tipo: {tipo_licencia} - {TIPOS_LICENCIAS[tipo_licencia]['nombre']}\nVálida hasta: {fecha_vencimiento}",
            inline=False
        )
        confirmacion_embed.set_footer(text="Santiago RP - Dirección de Tránsito")
        
        # Enviar mensaje efímero al usuario
        await interaction.followup.send(embed=confirmacion_embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error al tramitar licencia: {e}")
        embed = discord.Embed(
            title="❌ Error al tramitar licencia",
            description=f"Ocurrió un error al tramitar la licencia: {e}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="ver-licencia", description="Muestra una licencia específica de un ciudadano")
@app_commands.describe(
    ciudadano="Ciudadano del que quieres ver la licencia",
    tipo_licencia="Tipo de licencia que quieres ver"
)
@app_commands.autocomplete(tipo_licencia=autocompletar_tipo_licencia)
async def slash_ver_licencia(
    interaction: discord.Interaction,
    ciudadano: discord.Member,
    tipo_licencia: str
):
    """Muestra una licencia específica de un ciudadano"""
    
    # Verificar que el comando se use en el canal correcto
    if interaction.channel_id != 1344192338397757461:
        embed = discord.Embed(
            title="❌ Canal incorrecto",
            description="Este comando solo puede ser utilizado en el canal designado para ver licencias.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Verificar si el tipo de licencia es válido
    if tipo_licencia not in TIPOS_LICENCIAS:
        embed = discord.Embed(
            title="❌ Tipo de licencia inválido",
            description="El tipo de licencia especificado no es válido.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verificar si el ciudadano tiene cédula y obtener su información
    cursor.execute('''
    SELECT rut, avatar_url 
    FROM cedulas WHERE user_id = ?
    ''', (ciudadano.id,))
    
    cedula = cursor.fetchone()
    
    if not cedula:
        embed = discord.Embed(
            title="❌ Ciudadano sin cédula",
            description=f"{ciudadano.mention} no tiene una cédula de identidad registrada.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        conn.close()
        return
    
    rut, avatar_url = cedula
    
    # Obtener la licencia específica del ciudadano
    cursor.execute('''
    SELECT nombre_licencia, fecha_emision, fecha_vencimiento, emitida_por
    FROM licencias 
    WHERE user_id = ? AND tipo_licencia = ?
    ''', (ciudadano.id, tipo_licencia))
    
    licencia = cursor.fetchone()
    conn.close()
    
    if not licencia:
        embed = discord.Embed(
            title="❌ Licencia no encontrada",
            description=f"{ciudadano.mention} no tiene la licencia tipo {tipo_licencia} tramitada.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    nombre_licencia, fecha_emision, fecha_vencimiento, emitida_por = licencia
    
    # Obtener el nombre del emisor si está disponible
    emisor = interaction.guild.get_member(emitida_por)
    emisor_nombre = emisor.mention if emisor else "Desconocido"
    
    # Crear y enviar el mensaje embebido con la licencia
    embed = discord.Embed(
        title=f"🇨🇱 SANTIAGO RP 🇨🇱",
        description="DIRECCIÓN DE TRÁNSITO Y TRANSPORTE PÚBLICO",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="LICENCIA DE CONDUCIR", value=f"Tipo: {tipo_licencia}", inline=False)
    embed.add_field(name="Descripción", value=nombre_licencia, inline=False)
    embed.add_field(name="Titular", value=ciudadano.mention, inline=True)
    embed.add_field(name="RUT", value=rut, inline=True)
    embed.add_field(name="Fecha Emisión", value=fecha_emision, inline=True)
    embed.add_field(name="Fecha Vencimiento", value=fecha_vencimiento, inline=True)
    embed.add_field(name="Emitida por", value=emisor_nombre, inline=True)
    
    # Establecer la imagen del avatar de la cédula en lugar del avatar de Discord
    embed.set_thumbnail(url=avatar_url)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="revocar-licencia", description="Revoca una licencia específica de un ciudadano")
@app_commands.describe(
    ciudadano="Ciudadano cuya licencia deseas revocar",
    tipo_licencia="Tipo de licencia a revocar",
    motivo="Motivo de la revocación de la licencia"
)
@app_commands.autocomplete(tipo_licencia=autocompletar_tipo_licencia)
async def slash_revocar_licencia(
    interaction: discord.Interaction,
    ciudadano: discord.Member,
    tipo_licencia: str,
    motivo: str
):
    """Revoca una licencia específica de un ciudadano (solo roles autorizados)"""
    
    # Canal de logs para revocaciones
    canal_logs_id = 1363652008585723944
    
    # Lista de roles autorizados para revocar licencias
    roles_autorizados = [
        1339386615235346439, 
        1347803116741066834, 
        1339386615222767662, 
        1346545514492985486, 
        1339386615247798362
    ]
    
    # Verificar si el usuario tiene alguno de los roles autorizados
    tiene_permiso = False
    for role in interaction.user.roles:
        if role.id in roles_autorizados:
            tiene_permiso = True
            break
    
    if not tiene_permiso:
        embed = discord.Embed(
            title="❌ Sin permisos",
            description="No tienes permiso para revocar licencias.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Verificar si el tipo de licencia es válido
    if tipo_licencia not in TIPOS_LICENCIAS:
        embed = discord.Embed(
            title="❌ Tipo de licencia inválido",
            description="El tipo de licencia especificado no es válido.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verificar si el ciudadano tiene la licencia específica
    cursor.execute('''
    SELECT id, nombre_licencia, fecha_emision FROM licencias 
    WHERE user_id = ? AND tipo_licencia = ?
    ''', (ciudadano.id, tipo_licencia))
    
    licencia = cursor.fetchone()
    
    if not licencia:
        embed = discord.Embed(
            title="❌ Licencia no encontrada",
            description=f"{ciudadano.mention} no tiene la licencia {tipo_licencia} para revocar.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        conn.close()
        return
    
    # Guardar información de la licencia para el mensaje
    licencia_id, nombre_licencia, fecha_emision = licencia
    
    # Obtener información de la cédula para el log
    cursor.execute('SELECT rut FROM cedulas WHERE user_id = ?', (ciudadano.id,))
    cedula = cursor.fetchone()
    rut = cedula[0] if cedula else "No disponible"
    
    # Eliminar la licencia
    try:
        cursor.execute('DELETE FROM licencias WHERE id = ?', (licencia_id,))
        conn.commit()
        
        # Crear y enviar el mensaje de revocación
        embed = discord.Embed(
            title=f"🚫 LICENCIA REVOCADA",
            description=f"Se ha revocado la licencia de {ciudadano.mention}",
            color=discord.Color.red()
        )
        
        embed.add_field(name="Tipo de licencia", value=f"{tipo_licencia} - {nombre_licencia}", inline=False)
        embed.add_field(name="Motivo de revocación", value=motivo, inline=False)
        embed.add_field(name="Autoridad", value=interaction.user.mention, inline=True)
        embed.add_field(name="Fecha", value=datetime.now().strftime("%d/%m/%Y"), inline=True)
        
        # Establecer la imagen del avatar del ciudadano
        embed.set_thumbnail(url=ciudadano.display_avatar.url)
        
        await interaction.response.send_message(embed=embed)
        
        # Enviar log al canal de logs
        canal_logs = interaction.guild.get_channel(canal_logs_id)
        if canal_logs:
            log_embed = discord.Embed(
                title="🚫 Licencia Revocada",
                description=f"Se ha revocado una licencia del sistema.",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            log_embed.add_field(
                name="Administrador",
                value=f"{interaction.user.mention} ({interaction.user.name})",
                inline=True
            )
            log_embed.add_field(
                name="Ciudadano",
                value=f"{ciudadano.mention} ({ciudadano.name})",
                inline=True
            )
            log_embed.add_field(
                name="RUT",
                value=rut,
                inline=True
            )
            log_embed.add_field(
                name="Licencia revocada",
                value=f"{tipo_licencia} - {nombre_licencia}",
                inline=False
            )
            log_embed.add_field(
                name="Fecha de emisión",
                value=fecha_emision,
                inline=True
            )
            log_embed.add_field(
                name="Fecha de revocación",
                value=datetime.now().strftime("%d/%m/%Y"),
                inline=True
            )
            log_embed.add_field(
                name="Motivo",
                value=motivo,
                inline=False
            )
            log_embed.set_footer(text=f"ID del usuario: {ciudadano.id}")
            
            await canal_logs.send(embed=log_embed)
        else:
            logger.error(f"No se pudo encontrar el canal de logs con ID {canal_logs_id}")
            
    except Exception as e:
        logger.error(f"Error al revocar licencia: {e}")
        embed = discord.Embed(
            title="❌ Error al revocar licencia",
            description=f"Ocurrió un error al revocar la licencia: {e}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# Función para validar formato de placa
def validar_placa(placa):
    """Valida que la placa tenga el formato ABC-123"""
    import re
    patron = re.compile(r'^[A-Z]{3}-\d{3}$')
    return bool(patron.match(placa))

# Función para validar año del vehículo
def validar_anio(anio_str):
    """Valida que el año sea un número entre 1900 y el año actual + 1"""
    try:
        anio = int(anio_str)
        anio_actual = datetime.now().year
        return 1900 <= anio <= anio_actual + 1, anio
    except ValueError:
        return False, None

# Funciones para autocompletado
async def autocompletar_gama(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocompleta la gama del vehículo"""
    return [
        app_commands.Choice(name=gama, value=gama)
        for gama in GAMAS_VEHICULO if current.lower() in gama.lower()
    ][:25]

async def autocompletar_color(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocompleta el color del vehículo"""
    return [
        app_commands.Choice(name=color, value=color)
        for color in COLORES_VEHICULO if current.lower() in color.lower()
    ][:25]

async def autocompletar_revision(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocompleta el estado de revisión técnica"""
    return [
        app_commands.Choice(name=estado, value=estado)
        for estado in ESTADOS_REVISION if current.lower() in estado.lower()
    ][:25]

async def autocompletar_permiso(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocompleta el estado del permiso de circulación"""
    return [
        app_commands.Choice(name=estado, value=estado)
        for estado in ESTADOS_PERMISO if current.lower() in estado.lower()
    ][:25]

@bot.tree.command(name="registrar-vehiculo", description="Registra un vehículo para un ciudadano")
@app_commands.describe(
    ciudadano="Ciudadano propietario del vehículo",
    placa="Placa del vehículo (formato ABC-123)",
    modelo="Modelo del vehículo",
    marca="Marca del vehículo",
    gama="Gama/Categoría del vehículo",
    año="Año del vehículo",
    color="Color del vehículo",
    revision_tecnica="Estado de la revisión técnica",
    permiso_circulacion="Estado del permiso de circulación",
    codigo_pago="Código de pago del vehículo",
    imagen="Imagen del vehículo (subir archivo)"
)
@app_commands.autocomplete(
    gama=autocompletar_gama,
    color=autocompletar_color,
    revision_tecnica=autocompletar_revision,
    permiso_circulacion=autocompletar_permiso
)
async def slash_registrar_vehiculo(
    interaction: discord.Interaction,
    ciudadano: discord.Member,
    placa: str,
    modelo: str,
    marca: str,
    gama: str,
    año: str,
    color: str,
    revision_tecnica: str,
    permiso_circulacion: str,
    codigo_pago: str,
    imagen: discord.Attachment
):
    """Registra un vehículo para un ciudadano (solo roles autorizados)"""
    
    # Lista de roles autorizados para registrar vehículos
    roles_autorizados = [
        1339386615235346439, 
        1347803116741066834, 
        1339386615222767662, 
        1346545514492985486, 
        1339386615247798362
    ]
    
    # Verificar si el usuario tiene alguno de los roles autorizados
    tiene_permiso = False
    for role in interaction.user.roles:
        if role.id in roles_autorizados:
            tiene_permiso = True
            break
    
    if not tiene_permiso:
        embed = discord.Embed(
            title="❌ Sin permisos",
            description="No tienes permiso para registrar vehículos.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Verificar si el ciudadano tiene cédula y obtener el avatar_url
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT rut, avatar_url FROM cedulas WHERE user_id = ?', (ciudadano.id,))
    cedula = cursor.fetchone()
    
    if not cedula:
        embed = discord.Embed(
            title="❌ Ciudadano sin cédula",
            description=f"{ciudadano.mention} no tiene una cédula de identidad registrada. Debe tramitar su cédula primero.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        conn.close()
        return
    
    rut, avatar_url = cedula
    
    # Validar formato de placa
    if not validar_placa(placa):
        embed = discord.Embed(
            title="❌ Formato de placa inválido",
            description="La placa debe tener el formato ABC-123 (tres letras mayúsculas, guion, tres números).",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        conn.close()
        return
    
    # Verificar si la placa ya está registrada
    cursor.execute('SELECT id FROM vehiculos WHERE placa = ?', (placa,))
    placa_existente = cursor.fetchone()
    
    if placa_existente:
        embed = discord.Embed(
            title="❌ Placa ya registrada",
            description=f"La placa {placa} ya está registrada en el sistema.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        conn.close()
        return
    
    # Validar año del vehículo
    anio_valido, anio_int = validar_anio(año)
    if not anio_valido:
        embed = discord.Embed(
            title="❌ Año inválido",
            description=f"El año debe ser un número entre 1900 y {datetime.now().year + 1}.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        conn.close()
        return
    
    # Validar archivo de imagen
    if not imagen.content_type.startswith('image/'):
        embed = discord.Embed(
            title="❌ Archivo inválido",
            description="Debes subir una imagen válida (JPEG, PNG, etc.).",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        conn.close()
        return
    
    # Verificar si el código de pago existe y no está usado
    cursor.execute('''
    SELECT code, used FROM payment_codes 
    WHERE code = ? AND user_id = ?
    ''', (codigo_pago, ciudadano.id))
    
    codigo_pago_data = cursor.fetchone()
    
    if not codigo_pago_data:
        embed = discord.Embed(
            title="❌ Código de pago inválido",
            description=f"El código de pago {codigo_pago} no existe o no pertenece al ciudadano especificado.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        conn.close()
        return
    
    if codigo_pago_data[1]:  # Si used == True
        embed = discord.Embed(
            title="❌ Código de pago ya usado",
            description=f"El código de pago {codigo_pago} ya ha sido utilizado previamente.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        conn.close()
        return
    
    # Fecha de registro
    fecha_registro = datetime.now().strftime("%d/%m/%Y")
    
    # Obtener URL de la imagen
    imagen_url = imagen.url
    
    # Registrar el vehículo y marcar el código como usado
    try:
        # Iniciar transacción
        cursor.execute('BEGIN TRANSACTION')
        
        # Registrar el vehículo
        cursor.execute('''
        INSERT INTO vehiculos 
        (user_id, placa, modelo, marca, gama, anio, color, revision_tecnica, 
        permiso_circulacion, codigo_pago, imagen_url, fecha_registro, registrado_por) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (ciudadano.id, placa, modelo, marca, gama, anio_int, color, 
              revision_tecnica, permiso_circulacion, codigo_pago, imagen_url, 
              fecha_registro, interaction.user.id))
        
        # Marcar el código de pago como usado
        cursor.execute('''
        UPDATE payment_codes 
        SET used = ?, used_at = ? 
        WHERE code = ?
        ''', (True, datetime.now().strftime("%d/%m/%Y %H:%M:%S"), codigo_pago))
        
        # Confirmar transacción
        conn.commit()
        
        # Crear y enviar el mensaje embebido con el vehículo registrado
        embed = discord.Embed(
            title=f"🇨🇱 SANTIAGO RP 🇨🇱",
            description="REGISTRO CIVIL Y DE VEHÍCULOS",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="CERTIFICADO DE REGISTRO VEHICULAR", value=f"Placa: {placa}", inline=False)
        
        # Información del vehículo
        embed.add_field(name="Propietario", value=ciudadano.mention, inline=True)
        embed.add_field(name="RUT", value=rut, inline=True)
        embed.add_field(name="Fecha Registro", value=fecha_registro, inline=True)
        
        embed.add_field(name="Marca", value=marca, inline=True)
        embed.add_field(name="Modelo", value=modelo, inline=True)
        embed.add_field(name="Año", value=str(anio_int), inline=True)
        
        embed.add_field(name="Color", value=color, inline=True)
        embed.add_field(name="Gama", value=gama, inline=True)
        embed.add_field(name="Código de Pago", value=codigo_pago, inline=True)
        
        embed.add_field(name="Revisión Técnica", value=revision_tecnica, inline=True)
        embed.add_field(name="Permiso de Circulación", value=permiso_circulacion, inline=True)
        embed.add_field(name="Registrado por", value=interaction.user.mention, inline=True)
        
        # Establecer la imagen del vehículo
        embed.set_image(url=imagen_url)
        
        # Establecer la imagen miniatura como el avatar_url de la cédula
        embed.set_thumbnail(url=avatar_url)
        
        # Enviar el registro al canal
        await interaction.response.send_message(embed=embed)
        
        # Enviar mensaje efímero de confirmación al usuario
        confirmacion_embed = discord.Embed(
            title="✅ ¡Vehículo Registrado con Éxito!",
            description=f"El vehículo con placa {placa} ha sido registrado correctamente para {ciudadano.mention}",
            color=discord.Color.green()
        )
        confirmacion_embed.add_field(
            name="📋 Detalles",
            value=f"Marca: {marca}\nModelo: {modelo}\nAño: {anio_int}\nColor: {color}\nCódigo de Pago: {codigo_pago}",
            inline=False
        )
        confirmacion_embed.set_footer(text="Santiago RP - Registro de Vehículos")
        
        # Enviar mensaje efímero al usuario
        await interaction.followup.send(embed=confirmacion_embed, ephemeral=True)
        
    except Exception as e:
        # Revertir transacción en caso de error
        conn.rollback()
        logger.error(f"Error al registrar vehículo: {e}")
        embed = discord.Embed(
            title="❌ Error al registrar vehículo",
            description=f"Ocurrió un error al registrar el vehículo: {e}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="ver-vehiculo", description="Muestra la información de un vehículo por su placa")
@app_commands.describe(placa="Placa del vehículo (formato ABC-123)")
async def slash_ver_vehiculo(interaction: discord.Interaction, placa: str):
    """Muestra la información de un vehículo por su placa"""
    
    # Verificar que el comando se use en el canal correcto
    ALLOWED_CHANNEL_ID = 1361178515898110212
    if interaction.channel_id != ALLOWED_CHANNEL_ID:
        embed = discord.Embed(
            title="❌ Canal incorrecto",
            description=f"Este comando solo puede ser utilizado en el canal <#{ALLOWED_CHANNEL_ID}>.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Validar formato de placa
    if not validar_placa(placa):
        embed = discord.Embed(
            title="❌ Formato de placa inválido",
            description="La placa debe tener el formato ABC-123 (tres letras mayúsculas, guion, tres números).",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Obtener información del vehículo y el avatar_url de la cédula
    cursor.execute('''
    SELECT v.user_id, v.modelo, v.marca, v.gama, v.anio, v.color, 
           v.revision_tecnica, v.permiso_circulacion, v.codigo_pago, 
           v.imagen_url, v.fecha_registro, v.registrado_por,
           c.rut, c.avatar_url
    FROM vehiculos v
    JOIN cedulas c ON v.user_id = c.user_id
    WHERE v.placa = ?
    ''', (placa,))
    
    vehiculo = cursor.fetchone()
    conn.close()
    
    if not vehiculo:
        embed = discord.Embed(
            title="❌ Vehículo no encontrado",
            description=f"No se encontró ningún vehículo con la placa {placa}.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    user_id, modelo, marca, gama, anio, color, revision_tecnica, permiso_circulacion, codigo_pago, imagen_url, fecha_registro, registrado_por, rut, avatar_url = vehiculo
    
    # Obtener información del propietario y registrador
    propietario = interaction.guild.get_member(user_id)
    registrador = interaction.guild.get_member(registrado_por)
    
    propietario_nombre = propietario.mention if propietario else "Desconocido"
    registrador_nombre = registrador.mention if registrador else "Desconocido"
    
    # Crear y enviar el mensaje embebido con el vehículo
    embed = discord.Embed(
        title=f"🇨🇱 SANTIAGO RP 🇨🇱",
        description="REGISTRO CIVIL Y DE VEHÍCULOS",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="CERTIFICADO DE REGISTRO VEHICULAR", value=f"Placa: {placa}", inline=False)
    
    # Información del vehículo
    embed.add_field(name="Propietario", value=propietario_nombre, inline=True)
    embed.add_field(name="RUT", value=rut, inline=True)
    embed.add_field(name="Fecha Registro", value=fecha_registro, inline=True)
    
    embed.add_field(name="Marca", value=marca, inline=True)
    embed.add_field(name="Modelo", value=modelo, inline=True)
    embed.add_field(name="Año", value=str(anio), inline=True)
    
    embed.add_field(name="Color", value=color, inline=True)
    embed.add_field(name="Gama", value=gama, inline=True)
    embed.add_field(name="Código de Pago", value=codigo_pago, inline=True)
    
    embed.add_field(name="Revisión Técnica", value=revision_tecnica, inline=True)
    embed.add_field(name="Permiso de Circulación", value=permiso_circulacion, inline=True)
    embed.add_field(name="Registrado por", value=registrador_nombre, inline=True)
    
    # Establecer la imagen del vehículo
    embed.set_image(url=imagen_url)
    
    # Establecer la imagen miniatura como el avatar_url de la cédula
    embed.set_thumbnail(url=avatar_url)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="eliminar-vehiculo", description="Elimina el registro de un vehículo")
@app_commands.describe(placa="Placa del vehículo a eliminar (formato ABC-123)")
async def slash_eliminar_vehiculo(interaction: discord.Interaction, placa: str):
    """Elimina el registro de un vehículo (solo roles autorizados)"""
    
    # Lista de roles autorizados
    roles_autorizados = [
        1339386615235346439, 
        1347803116741066834, 
        1339386615222767662, 
        1346545514492985486, 
        1339386615247798362
    ]
    
    # Canal de logs
    canal_logs_id = 1363652480130351214
    
    # Verificar si el usuario tiene alguno de los roles autorizados
    tiene_permiso = False
    for role in interaction.user.roles:
        if role.id in roles_autorizados:
            tiene_permiso = True
            break
    
    if not tiene_permiso:
        embed = discord.Embed(
            title="❌ Sin permisos",
            description="No tienes permiso para eliminar registros de vehículos.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Validar formato de placa
    if not validar_placa(placa):
        embed = discord.Embed(
            title="❌ Formato de placa inválido",
            description="La placa debe tener el formato ABC-123 (tres letras mayúsculas, guion, tres números).",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verificar si el vehículo existe y obtener información completa
    cursor.execute('''
    SELECT v.user_id, v.marca, v.modelo, v.gama, v.anio, v.color, 
           v.revision_tecnica, v.permiso_circulacion, v.codigo_pago, 
           v.imagen_url, v.fecha_registro, c.rut, c.avatar_url
    FROM vehiculos v
    JOIN cedulas c ON v.user_id = c.user_id
    WHERE v.placa = ?
    ''', (placa,))
    
    vehiculo = cursor.fetchone()
    
    if not vehiculo:
        embed = discord.Embed(
            title="❌ Vehículo no encontrado",
            description=f"No se encontró ningún vehículo con la placa {placa}.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        conn.close()
        return
    
    user_id, marca, modelo, gama, anio, color, revision_tecnica, permiso_circulacion, codigo_pago, imagen_url, fecha_registro, rut, avatar_url = vehiculo
    
    propietario = interaction.guild.get_member(user_id)
    propietario_nombre = propietario.mention if propietario else "Desconocido"
    
    # Eliminar el vehículo
    try:
        cursor.execute('DELETE FROM vehiculos WHERE placa = ?', (placa,))
        conn.commit()
        
        # Mensaje de éxito para el usuario
        embed = discord.Embed(
            title="✅ Vehículo Eliminado",
            description=f"El registro del vehículo con placa {placa} ha sido eliminado correctamente.",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Información eliminada",
            value=f"Propietario: {propietario_nombre}\nRUT: {rut}\nVehículo: {marca} {modelo}",
            inline=False
        )
        embed.set_footer(text="Santiago RP - Registro de Vehículos")
        
        await interaction.response.send_message(embed=embed)
        
        # Enviar log al canal de logs
        canal_logs = interaction.guild.get_channel(canal_logs_id)
        if canal_logs:
            log_embed = discord.Embed(
                title="🗑️ Registro Vehicular Eliminado",
                description=f"Se ha eliminado un registro vehicular del sistema.",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            log_embed.add_field(
                name="Administrador",
                value=f"{interaction.user.mention} ({interaction.user.name})",
                inline=True
            )
            log_embed.add_field(
                name="Propietario",
                value=f"{propietario_nombre} ({propietario.name if propietario else 'Desconocido'})",
                inline=True
            )
            log_embed.add_field(
                name="RUT",
                value=rut,
                inline=True
            )
            log_embed.add_field(
                name="Placa",
                value=placa,
                inline=True
            )
            log_embed.add_field(
                name="Vehículo",
                value=f"{marca} {modelo}",
                inline=True
            )
            log_embed.add_field(
                name="Año",
                value=str(anio),
                inline=True
            )
            log_embed.add_field(
                name="Color",
                value=color,
                inline=True
            )
            log_embed.add_field(
                name="Gama",
                value=gama,
                inline=True
            )
            log_embed.add_field(
                name="Código de Pago",
                value=codigo_pago,
                inline=True
            )
            log_embed.add_field(
                name="Revisión Técnica",
                value=revision_tecnica,
                inline=True
            )
            log_embed.add_field(
                name="Permiso de Circulación",
                value=permiso_circulacion,
                inline=True
            )
            log_embed.add_field(
                name="Fecha de Registro",
                value=fecha_registro,
                inline=True
            )
            log_embed.set_thumbnail(url=avatar_url if avatar_url else "https://tr.rbxcdn.com/e5b3371b4efc7642a22c1b36265a9ba9/420/420/AvatarHeadshot/Png")
            log_embed.set_footer(text=f"ID del usuario: {user_id}")
            
            await canal_logs.send(embed=log_embed)
        else:
            logger.error(f"No se pudo encontrar el canal de logs con ID {canal_logs_id}")
            
    except Exception as e:
        logger.error(f"Error al eliminar vehículo: {e}")
        embed = discord.Embed(
            title="❌ Error al eliminar vehículo",
            description=f"Ocurrió un error al eliminar el vehículo: {e}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# Función para generar un código único
def generar_codigo_pago():
    """Genera un código de pago único"""
    return str(uuid.uuid4())[:8].upper()  # Genera un código de 8 caracteres

@bot.tree.command(name="crear-codigo-pago", description="Crea un código de pago único para un ciudadano")
@app_commands.describe(
    ciudadano="Ciudadano que recibirá el código de pago",
    monto="Monto del pago en CLP",
    descripcion="Descripción del propósito del pago"
)
async def slash_crear_codigo_pago(
    interaction: discord.Interaction,
    ciudadano: discord.Member,
    monto: int,
    descripcion: str
):
    """Crea un código de pago único para un ciudadano (solo roles autorizados)"""
    
    # Lista de roles autorizados (mismos que para otros comandos administrativos)
    roles_autorizados = [
        1339386615235346439, 
        1347803116741066834, 
        1339386615222767662, 
        1346545514492985486, 
        1339386615247798362
    ]
    
    # Canal de logs para códigos de pago
    canal_logs_id = 1363652764613480560
    
    # Verificar si el usuario tiene alguno de los roles autorizados
    tiene_permiso = False
    for role in interaction.user.roles:
        if role.id in roles_autorizados:
            tiene_permiso = True
            break
    
    if not tiene_permiso:
        embed = discord.Embed(
            title="❌ Sin permisos",
            description="No tienes permiso para crear códigos de pago.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Verificar si el ciudadano tiene cédula
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT rut, avatar_url FROM cedulas WHERE user_id = ?', (ciudadano.id,))
    cedula = cursor.fetchone()
    
    if not cedula:
        embed = discord.Embed(
            title="❌ Ciudadano sin cédula",
            description=f"{ciudadano.mention} no tiene una cédula de identidad registrada. Debe tramitar su cédula primero.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        conn.close()
        return
    
    rut, avatar_url = cedula
    
    # Validar monto
    if monto <= 0:
        embed = discord.Embed(
            title="❌ Monto inválido",
            description="El monto debe ser un número positivo mayor que cero.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        conn.close()
        return
    
    # Generar código único
    while True:
        codigo = generar_codigo_pago()
        cursor.execute('SELECT code FROM payment_codes WHERE code = ?', (codigo,))
        if not cursor.fetchone():
            break
    
    # Fecha de creación
    fecha_creacion = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    # Guardar el código de pago en la base de datos
    try:
        cursor.execute('''
        INSERT INTO payment_codes 
        (code, amount, description, user_id, used, created_at, created_by) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (codigo, monto, descripcion, ciudadano.id, False, fecha_creacion, interaction.user.id))
        
        conn.commit()
        
        # Crear y enviar el mensaje embebido con el código de pago
        embed = discord.Embed(
            title=f"🇨🇱 SANTIAGO RP 🇨🇱",
            description="SISTEMA DE PAGOS",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="CÓDIGO DE PAGO", value=f"Código: {codigo}", inline=False)
        embed.add_field(name="Titular", value=ciudadano.mention, inline=True)
        embed.add_field(name="RUT", value=rut, inline=True)
        embed.add_field(name="Monto", value=f"${monto:,} CLP", inline=True)
        embed.add_field(name="Descripción", value=descripcion, inline=False)
        embed.add_field(name="Fecha Creación", value=fecha_creacion, inline=True)
        embed.add_field(name="Creado por", value=interaction.user.mention, inline=True)
        embed.add_field(name="Estado", value="Pendiente de uso", inline=True)
        
        # Establecer la imagen miniatura como el avatar de la cédula
        embed.set_thumbnail(url=avatar_url)
        
        # Enviar el código al canal
        await interaction.response.send_message(embed=embed)
        
        # Enviar mensaje efímero de confirmación al usuario
        confirmacion_embed = discord.Embed(
            title="✅ ¡Código de Pago Creado con Éxito!",
            description=f"El código de pago {codigo} ha sido creado correctamente para {ciudadano.mention}",
            color=discord.Color.green()
        )
        confirmacion_embed.add_field(
            name="📋 Detalles",
            value=f"Código: {codigo}\nMonto: ${monto:,} CLP\nDescripción: {descripcion}",
            inline=False
        )
        confirmacion_embed.add_field(
            name="ℹ️ Nota",
            value="Este código solo puede ser usado una vez. Se registrará su uso en el sistema.",
            inline=False
        )
        confirmacion_embed.set_footer(text="Santiago RP - Sistema de Pagos")
        
        # Enviar mensaje efímero al usuario
        await interaction.followup.send(embed=confirmacion_embed, ephemeral=True)
        
        # Enviar log al canal de logs
        canal_logs = interaction.guild.get_channel(canal_logs_id)
        if canal_logs:
            log_embed = discord.Embed(
                title="💸 Código de Pago Creado",
                description=f"Se ha creado un nuevo código de pago en el sistema.",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            log_embed.add_field(
                name="Administrador",
                value=f"{interaction.user.mention} ({interaction.user.name})",
                inline=True
            )
            log_embed.add_field(
                name="Ciudadano",
                value=f"{ciudadano.mention} ({ciudadano.name})",
                inline=True
            )
            log_embed.add_field(
                name="RUT",
                value=rut,
                inline=True
            )
            log_embed.add_field(
                name="Código",
                value=codigo,
                inline=True
            )
            log_embed.add_field(
                name="Monto",
                value=f"${monto:,} CLP",
                inline=True
            )
            log_embed.add_field(
                name="Descripción",
                value=descripcion,
                inline=False
            )
            log_embed.add_field(
                name="Fecha de Creación",
                value=fecha_creacion,
                inline=True
            )
            log_embed.set_thumbnail(url=avatar_url if avatar_url else "https://tr.rbxcdn.com/e5b3371b4efc7642a22c1b36265a9ba9/420/420/AvatarHeadshot/Png")
            log_embed.set_footer(text=f"ID del usuario: {ciudadano.id}")
            
            await canal_logs.send(embed=log_embed)
        else:
            logger.error(f"No se pudo encontrar el canal de logs con ID {canal_logs_id}")
            
    except Exception as e:
        logger.error(f"Error al crear código de pago: {e}")
        embed = discord.Embed(
            title="❌ Error al crear código de pago",
            description=f"Ocurrió un error al crear el código de pago: {e}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# Función para autocompletar zona
async def autocompletar_zona(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocompleta la zona de la propiedad"""
    return [
        app_commands.Choice(name=zona, value=zona)
        for zona in ZONAS_PROPIEDAD if current.lower() in zona.lower()
    ][:25]

# Función para validar número de pisos
def validar_numero_pisos(pisos_str):
    """Valida que el número de pisos sea un entero positivo"""
    try:
        pisos = int(pisos_str)
        return pisos > 0, pisos
    except ValueError:
        return False, None

@bot.tree.command(name="registrar-propiedad", description="Registra una propiedad para un ciudadano")
@app_commands.describe(
    ciudadano="Ciudadano propietario de la propiedad",
    numero_domicilio="Número de domicilio de la propiedad (ej. 1234)",
    zona="Zona donde se encuentra la propiedad",
    color="Color de la propiedad",
    numero_pisos="Número de pisos de la propiedad",
    codigo_pago="Código de pago de la propiedad",
    imagen="Imagen de la propiedad (subir archivo)"
)
@app_commands.autocomplete(
    zona=autocompletar_zona,
    color=autocompletar_color
)
async def slash_registrar_propiedad(
    interaction: discord.Interaction,
    ciudadano: discord.Member,
    numero_domicilio: str,
    zona: str,
    color: str,
    numero_pisos: str,
    codigo_pago: str,
    imagen: discord.Attachment
):
    """Registra una propiedad para un ciudadano (solo roles autorizados)"""
    
    # Lista de roles autorizados
    roles_autorizados = [
        1339386615235346439, 
        1347803116741066834, 
        1339386615222767662, 
        1346545514492985486, 
        1339386615247798362
    ]
    
    # Verificar si el usuario tiene alguno de los roles autorizados
    tiene_permiso = False
    for role in interaction.user.roles:
        if role.id in roles_autorizados:
            tiene_permiso = True
            break
    
    if not tiene_permiso:
        embed = discord.Embed(
            title="❌ Sin permisos",
            description="No tienes permiso para registrar propiedades.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Diferir la respuesta
    await interaction.response.defer()
    
    # Verificar si el ciudadano tiene cédula y obtener el avatar_url
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT rut, avatar_url FROM cedulas WHERE user_id = ?', (ciudadano.id,))
        cedula = cursor.fetchone()
    
    if not cedula:
        embed = discord.Embed(
            title="❌ Ciudadano sin cédula",
            description=f"{ciudadano.mention} no tiene una cédula de identidad registrada. Debe tramitar su cédula primero.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    rut, avatar_url = cedula
    
    # Validar número de domicilio
    if not numero_domicilio.strip():
        embed = discord.Embed(
            title="❌ Número de domicilio inválido",
            description="El número de domicilio no puede estar vacío.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    # Verificar si el número de domicilio ya está registrado
    cursor = execute_with_retry('SELECT id FROM propiedades WHERE numero_domicilio = ?', (numero_domicilio,))
    domicilio_existente = cursor.fetchone()
    
    if domicilio_existente:
        embed = discord.Embed(
            title="❌ Domicilio ya registrado",
            description=f"El número de domicilio {numero_domicilio} ya está registrado en el sistema.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    # Validar zona
    if zona not in ZONAS_PROPIEDAD:
        embed = discord.Embed(
            title="❌ Zona inválida",
            description=f"La zona debe ser una de las siguientes: {', '.join(ZONAS_PROPIEDAD)}.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    # Validar color
    if color not in COLORES_VEHICULO:
        embed = discord.Embed(
            title="❌ Color inválido",
            description=f"El color debe ser uno de los siguientes: {', '.join(COLORES_VEHICULO)}.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    # Validar número de pisos
    pisos_validos, pisos_int = validar_numero_pisos(numero_pisos)
    if not pisos_validos:
        embed = discord.Embed(
            title="❌ Número de pisos inválido",
            description="El número de pisos debe ser un número entero positivo.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    # Validar archivo de imagen
    if not imagen.content_type.startswith('image/'):
        embed = discord.Embed(
            title="❌ Archivo inválido",
            description="Debes subir una imagen válida (JPEG, PNG, etc.).",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    # Verificar si el código de pago existe y no está usado
    cursor = execute_with_retry('''
    SELECT code, used FROM payment_codes 
    WHERE code = ? AND user_id = ?
    ''', (codigo_pago, ciudadano.id))
    
    codigo_pago_data = cursor.fetchone()
    
    if not codigo_pago_data:
        embed = discord.Embed(
            title="❌ Código de pago inválido",
            description=f"El código de pago {codigo_pago} no existe o no pertenece al ciudadano especificado.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    if codigo_pago_data[1]:  # Si used == True
        embed = discord.Embed(
            title="❌ Código de pago ya usado",
            description=f"El código de pago {codigo_pago} ya ha sido utilizado previamente.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    # Fecha de registro
    fecha_registro = datetime.now().strftime("%d/%m/%Y")
    
    # Obtener URL de la imagen
    imagen_url = imagen.url
    
    # Registrar la propiedad y marcar el código como usado
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Iniciar transacción
            cursor.execute('BEGIN TRANSACTION')
            
            # Registrar la propiedad
            cursor.execute('''
            INSERT INTO propiedades 
            (user_id, numero_domicilio, zona, color, numero_pisos, codigo_pago, imagen_url, fecha_registro, registrado_por) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ciudadano.id, numero_domicilio, zona, color, pisos_int, codigo_pago, imagen_url, 
                  fecha_registro, interaction.user.id))
            
            # Marcar el código de pago como usado
            cursor.execute('''
            UPDATE payment_codes 
            SET used = ?, used_at = ? 
            WHERE code = ?
            ''', (True, datetime.now().strftime("%d/%m/%Y %H:%M:%S"), codigo_pago))
            
            # Confirmar transacción
            conn.commit()
        
        # Crear y enviar el mensaje embebido con la propiedad registrada
        embed = discord.Embed(
            title=f"🇨🇱 SANTIAGO RP 🇨🇱",
            description="REGISTRO CIVIL Y DE PROPIEDADES",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="CERTIFICADO DE REGISTRO DE PROPIEDAD", value=f"Domicilio: {numero_domicilio}", inline=False)
        
        embed.add_field(name="Propietario", value=ciudadano.mention, inline=True)
        embed.add_field(name="RUT", value=rut, inline=True)
        embed.add_field(name="Fecha Registro", value=fecha_registro, inline=True)
        
        embed.add_field(name="Zona", value=zona, inline=True)
        embed.add_field(name="Color", value=color, inline=True)
        embed.add_field(name="Número de Pisos", value=str(pisos_int), inline=True)
        
        embed.add_field(name="Código de Pago", value=codigo_pago, inline=True)
        embed.add_field(name="Registrado por", value=interaction.user.mention, inline=True)
        
        embed.set_image(url=imagen_url)
        embed.set_thumbnail(url=avatar_url)
        
        await interaction.followup.send(embed=embed)
        
        # Enviar mensaje efímero de confirmación al usuario
        confirmacion_embed = discord.Embed(
            title="✅ ¡Propiedad Registrada con Éxito!",
            description=f"La propiedad con domicilio {numero_domicilio} ha sido registrada correctamente para {ciudadano.mention}",
            color=discord.Color.green()
        )
        confirmacion_embed.add_field(
            name="📋 Detalles",
            value=f"Zona: {zona}\nColor: {color}\nNúmero de Pisos: {pisos_int}\nCódigo de Pago: {codigo_pago}",
            inline=False
        )
        confirmacion_embed.set_footer(text="Santiago RP - Registro de Propiedades")
        
        await interaction.followup.send(embed=confirmacion_embed, ephemeral=True)
        
        # Enviar log al canal de logs
        canal_logs = interaction.guild.get_channel(1363653392454520963)
        if canal_logs:
            log_embed = discord.Embed(
                title="🏠 Propiedad Registrada",
                description=f"Se ha registrado una nueva propiedad en el sistema.",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            log_embed.add_field(
                name="Administrador",
                value=f"{interaction.user.mention} ({interaction.user.name})",
                inline=True
            )
            log_embed.add_field(
                name="Propietario",
                value=f"{ciudadano.mention} ({ciudadano.name})",
                inline=True
            )
            log_embed.add_field(
                name="RUT",
                value=rut,
                inline=True
            )
            log_embed.add_field(
                name="Domicilio",
                value=numero_domicilio,
                inline=True
            )
            log_embed.add_field(
                name="Zona",
                value=zona,
                inline=True
            )
            log_embed.add_field(
                name="Color",
                value=color,
                inline=True
            )
            log_embed.add_field(
                name="Número de Pisos",
                value=str(pisos_int),
                inline=True
            )
            log_embed.add_field(
                name="Código de Pago",
                value=codigo_pago,
                inline=True
            )
            log_embed.add_field(
                name="Fecha de Registro",
                value=fecha_registro,
                inline=True
            )
            log_embed.set_image(url=imagen_url)
            log_embed.set_thumbnail(url=avatar_url if avatar_url else "https://tr.rbxcdn.com/e5b3371b4efc7642a22c1b36265a9ba9/420/420/AvatarHeadshot/Png")
            log_embed.set_footer(text=f"ID del usuario: {ciudadano.id}")
            
            await canal_logs.send(embed=log_embed)
        else:
            logger.error(f"No se pudo encontrar el canal de logs con ID 1363653392454520963")
            
    except Exception as e:
        logger.error(f"Error al registrar propiedad: {e}")
        embed = discord.Embed(
            title="❌ Error al registrar propiedad",
            description=f"Ocurrió un error al registrar la propiedad: {e}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="eliminar-propiedad", description="Elimina el registro de una propiedad")
@app_commands.describe(numero_domicilio="Número de domicilio de la propiedad a eliminar")
async def slash_eliminar_propiedad(interaction: discord.Interaction, numero_domicilio: str):
    """Elimina el registro de una propiedad (solo roles autorizados)"""
    
    # Lista de roles autorizados
    roles_autorizados = [
        1339386615235346439, 
        1347803116741066834, 
        1339386615222767662, 
        1346545514492985486, 
        1339386615247798362
    ]
    
    # Canal de logs
    canal_logs_id = 1363652764613480560
    
    # Verificar si el usuario tiene alguno de los roles autorizados
    tiene_permiso = False
    for role in interaction.user.roles:
        if role.id in roles_autorizados:
            tiene_permiso = True
            break
    
    if not tiene_permiso:
        embed = discord.Embed(
            title="❌ Sin permisos",
            description="No tienes permiso para eliminar registros de propiedades.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verificar si la propiedad existe y obtener información completa
    cursor.execute('''
    SELECT p.user_id, p.zona, p.color, p.numero_pisos, p.codigo_pago, 
           p.imagen_url, p.fecha_registro, c.rut, c.avatar_url
    FROM propiedades p
    JOIN cedulas c ON p.user_id = c.user_id
    WHERE p.numero_domicilio = ?
    ''', (numero_domicilio,))
    
    propiedad = cursor.fetchone()
    
    if not propiedad:
        embed = discord.Embed(
            title="❌ Propiedad no encontrada",
            description=f"No se encontró ninguna propiedad con el número de domicilio {numero_domicilio}.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        conn.close()
        return
    
    user_id, zona, color, numero_pisos, codigo_pago, imagen_url, fecha_registro, rut, avatar_url = propiedad
    
    propietario = interaction.guild.get_member(user_id)
    propietario_nombre = propietario.mention if propietario else "Desconocido"
    
    # Eliminar la propiedad
    try:
        cursor.execute('DELETE FROM propiedades WHERE numero_domicilio = ?', (numero_domicilio,))
        conn.commit()
        
        # Mensaje de éxito para el usuario
        embed = discord.Embed(
            title="✅ Propiedad Eliminada",
            description=f"El registro de la propiedad con número de domicilio {numero_domicilio} ha sido eliminado correctamente.",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Información eliminada",
            value=f"Propietario: {propietario_nombre}\nRUT: {rut}\nZona: {zona}",
            inline=False
        )
        embed.set_footer(text="Santiago RP - Registro de Propiedades")
        
        await interaction.response.send_message(embed=embed)
        
        # Enviar log al canal de logs
        canal_logs = interaction.guild.get_channel(canal_logs_id)
        if canal_logs:
            log_embed = discord.Embed(
                title="🗑️ Registro de Propiedad Eliminado",
                description=f"Se ha eliminado un registro de propiedad del sistema.",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            log_embed.add_field(
                name="Administrador",
                value=f"{interaction.user.mention} ({interaction.user.name})",
                inline=True
            )
            log_embed.add_field(
                name="Propietario",
                value=f"{propietario_nombre} ({propietario.name if propietario else 'Desconocido'})",
                inline=True
            )
            log_embed.add_field(
                name="RUT",
                value=rut,
                inline=True
            )
            log_embed.add_field(
                name="Número de Domicilio",
                value=numero_domicilio,
                inline=True
            )
            log_embed.add_field(
                name="Zona",
                value=zona,
                inline=True
            )
            log_embed.add_field(
                name="Color",
                value=color,
                inline=True
            )
            log_embed.add_field(
                name="Número de Pisos",
                value=str(numero_pisos),
                inline=True
            )
            log_embed.add_field(
                name="Código de Pago",
                value=codigo_pago,
                inline=True
            )
            log_embed.add_field(
                name="Fecha de Registro",
                value=fecha_registro,
                inline=True
            )
            log_embed.set_thumbnail(url=avatar_url if avatar_url else "https://tr.rbxcdn.com/e5b3371b4efc7642a22c1b36265a9ba9/420/420/AvatarHeadshot/Png")
            log_embed.set_footer(text=f"ID del usuario: {user_id}")
            
            await canal_logs.send(embed=log_embed)
        else:
            logger.error(f"No se pudo encontrar el canal de logs con ID {canal_logs_id}")
            
    except Exception as e:
        logger.error(f"Error al eliminar propiedad: {e}")
        embed = discord.Embed(
            title="❌ Error al eliminar propiedad",
            description=f"Ocurrió un error al eliminar la propiedad: {e}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="ver-propiedad", description="Muestra la información de una propiedad por su número de domicilio")
@app_commands.describe(numero_domicilio="Número de domicilio de la propiedad")
async def slash_ver_propiedad(interaction: discord.Interaction, numero_domicilio: str):
    """Muestra la información de una propiedad por su número de domicilio"""
    
    # Verificar que el comando se use en el canal correcto
    ALLOWED_CHANNEL_ID = 1363653559719170159
    if interaction.channel_id != ALLOWED_CHANNEL_ID:
        embed = discord.Embed(
            title="❌ Canal incorrecto",
            description=f"Este comando solo puede ser utilizado en el canal <#{ALLOWED_CHANNEL_ID}>.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Obtener información de la propiedad y el avatar_url de la cédula
    cursor.execute('''
    SELECT p.user_id, p.zona, p.color, p.numero_pisos, p.codigo_pago, 
           p.imagen_url, p.fecha_registro, p.registrado_por, c.rut, c.avatar_url
    FROM propiedades p
    JOIN cedulas c ON p.user_id = c.user_id
    WHERE p.numero_domicilio = ?
    ''', (numero_domicilio,))
    
    propiedad = cursor.fetchone()
    conn.close()
    
    if not propiedad:
        embed = discord.Embed(
            title="❌ Propiedad no encontrada",
            description=f"No se encontró ninguna propiedad con el número de domicilio {numero_domicilio}.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    user_id, zona, color, numero_pisos, codigo_pago, imagen_url, fecha_registro, registrado_por, rut, avatar_url = propiedad
    
    # Obtener información del propietario y registrador
    propietario = interaction.guild.get_member(user_id)
    registrador = interaction.guild.get_member(registrado_por)
    
    propietario_nombre = propietario.mention if propietario else "Desconocido"
    registrador_nombre = registrador.mention if registrador else "Desconocido"
    
    # Crear y enviar el mensaje embebido con la propiedad
    embed = discord.Embed(
        title=f"🇨🇱 SANTIAGO RP 🇨🇱",
        description="REGISTRO CIVIL Y DE PROPIEDADES",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="CERTIFICADO DE REGISTRO DE PROPIEDAD", value=f"Domicilio: {numero_domicilio}", inline=False)
    
    # Información de la propiedad
    embed.add_field(name="Propietario", value=propietario_nombre, inline=True)
    embed.add_field(name="RUT", value=rut, inline=True)
    embed.add_field(name="Fecha Registro", value=fecha_registro, inline=True)
    
    embed.add_field(name="Zona", value=zona, inline=True)
    embed.add_field(name="Color", value=color, inline=True)
    embed.add_field(name="Número de Pisos", value=str(numero_pisos), inline=True)
    
    embed.add_field(name="Código de Pago", value=codigo_pago, inline=True)
    embed.add_field(name="Registrado por", value=registrador_nombre, inline=True)
    
    # Establecer la imagen de la propiedad
    embed.set_image(url=imagen_url)
    
    # Establecer la imagen miniatura como el avatar_url de la cédula
    embed.set_thumbnail(url=avatar_url)
    
    await interaction.response.send_message(embed=embed)


# Function for autocompleting emergency services
async def autocompletar_servicio(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocompleta el servicio de emergencia basado en lo que el usuario ha escrito"""
    servicios_especificos = {
        "1339386615205859423": "CARABINEROS DE CHILE",
        "1339386615205859422": "Policía de Investigaciones",
        "1339386615205859421": "Bomberos de Chile",
        "1343691212946800651": "Costanera Norte",
        "1343691334766035007": "Seguridad Ciudadana",
        "1339386615205859420": "SAMU"
    }
    
    return [
        app_commands.Choice(name=nombre, value=rol_id)
        for rol_id, nombre in servicios_especificos.items()
        if current.lower() in nombre.lower()
    ][:25]

@bot.tree.command(
    name="entorno",
    description="Envía una alerta de emergencia a los servicios correspondientes"
)
@app_commands.describe(
    razon="Razón de la emergencia (obligatorio)",
    servicio="Servicio de emergencia que requieres (obligatorio)",
    ubicacion="Ubicación exacta de la emergencia (obligatorio)"
)
@app_commands.autocomplete(servicio=autocompletar_servicio)
async def slash_entorno(
    interaction: discord.Interaction,
    razon: str,
    servicio: str,
    ubicacion: str
):
    """Envía una alerta de emergencia a los servicios correspondientes"""
    # Verificar si el comando se está ejecutando en el canal correcto
    canal_permitido_id = 1344075561689026722
    if interaction.channel_id != canal_permitido_id:
        embed_error = discord.Embed(
            title="🚫 Canal Incorrecto",
            description="Este comando solo puede utilizarse en el canal designado para emergencias.",
            color=discord.Color.red()
        )
        embed_error.add_field(
            name="📋 Instrucciones",
            value=f"Dirígete al canal <#{canal_permitido_id}> para reportar emergencias.",
            inline=False
        )
        embed_error.set_footer(
            text="Sistema de Emergencias",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )
        await interaction.response.send_message(embed=embed_error, ephemeral=True)
        return

    # Mapeo de nombres de servicios a IDs de roles
    servicios_roles = {
        "1339386615205859423": "CARABINEROS DE CHILE",
        "1339386615205859422": "Policía de Investigaciones",
        "1339386615205859421": "Bomberos de Chile",
        "1343691212946800651": "Costanera Norte",
        "1343691334766035007": "Seguridad Ciudadana",
        "1339386615205859420": "SAMU"
    }

    # Verificar si el servicio seleccionado es válido
    try:
        rol_id = str(servicio)
        roles_a_mencionar = []
        servicios_notificados = []

        # Caso especial para Carabineros y PDI (mencionar ambos)
        if rol_id in ["1339386615205859423", "1339386615205859422"]:
            rol_carabineros = interaction.guild.get_role(1339386615205859423)
            if rol_carabineros:
                roles_a_mencionar.append(rol_carabineros)
                servicios_notificados.append("CARABINEROS DE CHILE")
            
            rol_pdi = interaction.guild.get_role(1339386615205859422)
            if rol_pdi:
                roles_a_mencionar.append(rol_pdi)
                servicios_notificados.append("Policía de Investigaciones")
        else:
            if rol_id in servicios_roles:
                rol = interaction.guild.get_role(int(rol_id))
                if rol:
                    roles_a_mencionar.append(rol)
                    servicios_notificados.append(servicios_roles[rol_id])

        if not roles_a_mencionar:
            embed_error = discord.Embed(
                title="❌ Servicio no válido",
                description="Por favor, selecciona un servicio de emergencia oficial.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed_error, ephemeral=True)
            return
    except Exception as e:
        logger.error(f"Error al procesar el servicio: {e}")
        embed_error = discord.Embed(
            title="❌ Error al procesar solicitud",
            description="Ocurrió un error al procesar tu solicitud. Inténtalo nuevamente.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed_error, ephemeral=True)
        return

    # Canal donde se enviará la alerta
    canal_emergencias_id = 1339386616803885094
    canal = interaction.guild.get_channel(canal_emergencias_id)

    if not canal:
        embed_error = discord.Embed(
            title="❌ Error",
            description="No se encontró el canal de emergencias.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed_error, ephemeral=True)
        return

    # Crear embed de emergencia
    embed = discord.Embed(
        title="🚨 ¡ALERTA DE EMERGENCIA! 🚨",
        description="**Se requiere asistencia inmediata**",
        color=discord.Color.red()
    )
    
    embed.add_field(
        name="📍 UBICACIÓN EXACTA",
        value=f"```ansi\n{ubicacion}\n```",
        inline=False
    )
    
    embed.add_field(
        name="🚔 SITUACIÓN DE EMERGENCIA",
        value=f"```yaml\n{razon}\n```",
        inline=False
    )
    
    embed.add_field(
        name="⏰ HORA DEL REPORTE",
        value=f"<t:{int(datetime.now().timestamp())}:F>",
        inline=True
    )

    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
    embed.set_footer(
        text=f"Sistema de Emergencias • ID: {interaction.id}",
        icon_url=interaction.guild.icon.url if interaction.guild.icon else None
    )
    
    # Enviar mensaje con mención a los roles y embed
    menciones = " ".join([rol.mention for rol in roles_a_mencionar])
    mensaje = f"**¡ATENCIÓN {menciones}!** Se requiere su presencia inmediata."
    await canal.send(content=mensaje, embed=embed)

    # Crear embed de confirmación
    embed_confirmacion = discord.Embed(
        title="✅ EMERGENCIA REPORTADA CON ÉXITO",
        description="Tu solicitud de emergencia ha sido enviada correctamente.",
        color=discord.Color.green()
    )
    
    embed_confirmacion.add_field(
        name="🚑 Servicios Notificados",
        value=f"**{', '.join(servicios_notificados)}**",
        inline=True
    )
    
    embed_confirmacion.add_field(
        name="📍 Ubicación Reportada",
        value=f"{ubicacion}",
        inline=True
    )
    
    embed_confirmacion.add_field(
        name="⏱️ Tiempo Estimado",
        value="Las unidades están siendo despachadas",
        inline=True
    )
    
    embed_confirmacion.add_field(
        name="📋 Instrucciones",
        value="Por favor, mantente en el lugar y espera la llegada del servicio solicitado.",
        inline=False
    )
    
    embed_confirmacion.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
    embed_confirmacion.set_footer(
        text="Gracias por utilizar el Sistema de Emergencias",
        icon_url=interaction.guild.icon.url if interaction.guild.icon else None
    )
    
    await interaction.response.send_message(embed=embed_confirmacion, ephemeral=True)

    # Registrar la alerta en la base de datos (opcional, para auditoría)
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS emergencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                razon TEXT,
                servicio TEXT,
                ubicacion TEXT,
                fecha TEXT,
                servicios_notificados TEXT
            )
            ''')
            cursor.execute('''
            INSERT INTO emergencias 
            (user_id, razon, servicio, ubicacion, fecha, servicios_notificados) 
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                interaction.user.id,
                razon,
                servicio,
                ubicacion,
                datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                ", ".join(servicios_notificados)
            ))
            conn.commit()
        logger.info(f"Emergencia registrada para el usuario {interaction.user.id}")
    except Exception as e:
        logger.error(f"Error al registrar emergencia en la base de datos: {e}")

    # Enviar log al canal de logs
    canal_logs_id = 1363652764613480560  # Usar el mismo canal de logs que otros comandos
    canal_logs = interaction.guild.get_channel(canal_logs_id)
    if canal_logs:
        log_embed = discord.Embed(
            title="🚨 Alerta de Emergencia Reportada",
            description="Se ha reportado una nueva emergencia.",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        log_embed.add_field(
            name="Usuario",
            value=f"{interaction.user.mention} ({interaction.user.name})",
            inline=True
        )
        log_embed.add_field(
            name="Razón",
            value=razon,
            inline=True
        )
        log_embed.add_field(
            name="Ubicación",
            value=ubicacion,
            inline=True
        )
        log_embed.add_field(
            name="Servicios Notificados",
            value=", ".join(servicios_notificados),
            inline=False
        )
        log_embed.set_footer(text=f"ID del usuario: {interaction.user.id}")
        await canal_logs.send(embed=log_embed)
    else:
        logger.error(f"No se pudo encontrar el canal de logs con ID {canal_logs_id}")

@bot.tree.command(
    name="arrestar-a",
    description="Registra el arresto de un ciudadano (Solo Carabineros y PDI)"
)
@app_commands.describe(
    ciudadano="Ciudadano a arrestar (obligatorio)",
    razon="Código penal infringido (obligatorio)",
    tiempo_prision="Tiempo de prisión (ej: 3 meses, 2 años, cadena perpetua) (obligatorio)",
    monto_multa="Monto de la multa en pesos chilenos (obligatorio)",
    foto="Foto del detenido (obligatorio)"
)
async def slash_arrestar_ciudadano(
    interaction: discord.Interaction,
    ciudadano: discord.Member,  # Cambiado de str a discord.Member
    razon: str,
    tiempo_prision: str,
    monto_multa: int,
    foto: discord.Attachment
):
    """Registra el arresto de un ciudadano en el sistema (Solo Carabineros y PDI)"""
    # Verificar que el comando se use en el canal correcto
    CANAL_PERMITIDO = 1344075561689026722
    if interaction.channel_id != CANAL_PERMITIDO:
        embed = discord.Embed(
            title="⚠️ CANAL INCORRECTO ⚠️",
            description="Este comando solo puede ser utilizado en el canal designado para procedimientos policiales.",
            color=discord.Color.orange()
        )
        embed.set_footer(text="Sistema de Justicia - SantiagoRP")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Verificar que el usuario tenga uno de los roles permitidos
    ROLES_AUTORIZADOS = [1339386615205859423, 1339386615205859422]  # Carabineros y PDI
    if not any(role.id in ROLES_AUTORIZADOS for role in interaction.user.roles):
        embed = discord.Embed(
            title="🚨 ACCESO DENEGADO 🚨",
            description="Solo personal de Carabineros y PDI puede realizar arrestos.",
            color=discord.Color.red()
        )
        embed.set_footer(text="Sistema de Justicia - SantiagoRP")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Verificar que el archivo adjunto sea una imagen
    if not foto.content_type.startswith('image/'):
        embed = discord.Embed(
            title="⚠️ ARCHIVO NO VÁLIDO ⚠️",
            description="El archivo adjunto debe ser una imagen (jpg, png, etc.).",
            color=discord.Color.orange()
        )
        embed.set_footer(text="Sistema de Justicia - SantiagoRP")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Verificar que el tiempo de prisión no esté vacío
    if not tiempo_prision.strip():
        embed = discord.Embed(
            title="⚠️ TIEMPO DE PRISIÓN INVÁLIDO ⚠️",
            description="Debes especificar un tiempo de prisión.",
            color=discord.Color.orange()
        )
        embed.set_footer(text="Sistema de Justicia - SantiagoRP")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Validar monto de multa
    if monto_multa < 0:
        embed = discord.Embed(
            title="⚠️ MONTO DE MULTA INVÁLIDO ⚠️",
            description="El monto de la multa no puede ser negativo.",
            color=discord.Color.orange()
        )
        embed.set_footer(text="Sistema de Justicia - SantiagoRP")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # El ciudadano ya es un objeto discord.Member, no necesitamos fetch_member
    detenido = ciudadano
    
    # Informar al usuario que estamos procesando
    await interaction.response.defer(ephemeral=True, thinking=True)
    
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verificar cédula del ciudadano
            cursor.execute('''
            SELECT primer_nombre, apellido_paterno, rut, avatar_url
            FROM cedulas WHERE user_id = ?
            ''', (str(detenido.id),))
            
            cedula = cursor.fetchone()
            
            if not cedula:
                embed = discord.Embed(
                    title="📄 CÉDULA NO ENCONTRADA 📄",
                    description=f"{detenido.mention} no tiene cédula registrada en el sistema.",
                    color=discord.Color.orange()
                )
                embed.set_footer(text="Sistema de Justicia - SantiagoRP")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            nombre, apellido, rut, roblox_avatar = cedula
            
            # Crear tabla de arrestos si no existe
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS arrestos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                rut TEXT NOT NULL,
                razon TEXT NOT NULL,
                tiempo_prision TEXT NOT NULL,
                monto_multa INTEGER NOT NULL,
                foto_url TEXT NOT NULL,
                fecha_arresto TEXT NOT NULL,
                oficial_id TEXT NOT NULL,
                estado TEXT DEFAULT 'Activo'
            )
            ''')
            
            # Registrar el arresto
            fecha_arresto = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            foto_url = foto.url
            
            cursor.execute('''
            INSERT INTO arrestos (
                user_id, rut, razon, tiempo_prision, monto_multa, 
                foto_url, fecha_arresto, oficial_id, estado
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(detenido.id), rut, razon, tiempo_prision, monto_multa, 
                foto_url, fecha_arresto, str(interaction.user.id), 'Activo'
            ))
            
            arresto_id = cursor.lastrowid
            conn.commit()
            
            # Obtener información del oficial
            cursor.execute('''
            SELECT primer_nombre, apellido_paterno
            FROM cedulas WHERE user_id = ?
            ''', (str(interaction.user.id),))
            
            oficial_info = cursor.fetchone()
            nombre_oficial = "Oficial Desconocido"
            if oficial_info:
                nombre_oficial = f"{oficial_info[0]} {oficial_info[1]}"
            
            # Determinar la institución del oficial
            institucion = "Funcionario Público"
            for role in interaction.user.roles:
                if role.id == 1339386615205859423:
                    institucion = "Carabineros de Chile"
                    break
                elif role.id == 1339386615205859422:
                    institucion = "Policía de Investigaciones"
                    break
            
            # Crear ficha de antecedentes
            embed_antecedentes = discord.Embed(
                title="🚨 REGISTRO DE DETENCIÓN 🚨",
                description=f"**FICHA DE ANTECEDENTES PENALES**\nN° {arresto_id:06d}",
                color=discord.Color.dark_red(),
                timestamp=datetime.now()
            )
            
            embed_antecedentes.add_field(
                name="👤 DATOS DEL DETENIDO",
                value=f"**Nombre:** {nombre} {apellido}\n**RUT:** {rut}\n**ID:** {detenido.id}",
                inline=False
            )
            
            embed_antecedentes.add_field(
                name="⚖️ INFRACCIÓN COMETIDA",
                value=f"```yaml\n{razon}\n```",
                inline=False
            )
            
            embed_antecedentes.add_field(
                name="🔒 SENTENCIA",
                value=f"**Tiempo de prisión:** {tiempo_prision}\n**Multa:** ${monto_multa:,} CLP",
                inline=True
            )
            
            embed_antecedentes.add_field(
                name="📅 FECHAS",
                value=f"**Detención:** <t:{int(datetime.now().timestamp())}:F>",
                inline=True
            )
            
            embed_antecedentes.add_field(
                name="👮 OFICIAL A CARGO",
                value=f"**Nombre:** {nombre_oficial}\n**Institución:** {institucion}\n**ID:** {interaction.user.id}",
                inline=False
            )
            
            embed_antecedentes.set_image(url=foto_url)
            embed_antecedentes.set_thumbnail(url=roblox_avatar if roblox_avatar else detenido.display_avatar.url)
            embed_antecedentes.set_footer(
                text=f"Sistema Judicial de SantiagoRP • Expediente N° {arresto_id:06d}",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )
            
            # Enviar al canal de antecedentes
            canal_antecedentes_id = 1363655409797304400
            canal_antecedentes = interaction.guild.get_channel(canal_antecedentes_id)
            
            if canal_antecedentes:
                await canal_antecedentes.send(embed=embed_antecedentes)
                canal_nombre = canal_antecedentes.mention
            else:
                canal_nombre = "canal de antecedentes"
                logger.error(f"No se pudo encontrar el canal de antecedentes con ID {canal_antecedentes_id}")
            
            # Enviar confirmación al oficial
            embed_confirmacion = discord.Embed(
                title="✅ ARRESTO REGISTRADO CON ÉXITO",
                description=f"Se ha registrado el arresto de {nombre} {apellido} en el sistema y publicado en {canal_nombre}.",
                color=discord.Color.green()
            )
            
            embed_confirmacion.add_field(
                name="📋 Detalles",
                value=f"**Expediente N°:** {arresto_id:06d}\n**Delito:** {razon}\n**Sentencia:** {tiempo_prision}",
                inline=False
            )
            
            embed_confirmacion.set_footer(
                text="Sistema Judicial de SantiagoRP",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )
            
            await interaction.followup.send(embed=embed_confirmacion, ephemeral=True)
            
            # Enviar DM al detenido
            try:
                embed_dm = discord.Embed(
                    title="🚨 NOTIFICACIÓN DE ARRESTO 🚨",
                    description="**Has sido arrestado por las autoridades de SantiagoRP.**\nPor favor, revisa los detalles a continuación y sigue las instrucciones proporcionadas.",
                    color=discord.Color.red(),
                    timestamp=datetime.now()
                )
                
                embed_dm.add_field(
                    name="👤 Datos Personales",
                    value=f"**Nombre:** {nombre} {apellido}\n**RUT:** {rut}",
                    inline=True
                )
                
                embed_dm.add_field(
                    name="⚖️ Delito Cometido",
                    value=f"```yaml\n{razon}\n```",
                    inline=False
                )
                
                embed_dm.add_field(
                    name="🔒 Sentencia",
                    value=f"**Tiempo de prisión:** {tiempo_prision}\n**Multa:** ${monto_multa:,} CLP",
                    inline=True
                )
                
                embed_dm.add_field(
                    name="👮 Autoridad Responsable",
                    value=f"**Oficial:** {nombre_oficial}\n**Institución:** {institucion}",
                    inline=True
                )
                
                embed_dm.add_field(
                    name="📋 Instrucciones",
                    value="Dirígete al canal de antecedentes para más detalles y sigue las indicaciones de las autoridades. Si tienes dudas, contacta a un oficial en el servidor.",
                    inline=False
                )
                
                embed_dm.set_thumbnail(url=foto_url)
                embed_dm.set_footer(
                    text=f"Expediente N° {arresto_id:06d} • Sistema Judicial de SantiagoRP",
                    icon_url=interaction.guild.icon.url if interaction.guild.icon else None
                )
                
                await detenido.send(embed=embed_dm)
                logger.info(f"DM de arresto enviado a {detenido.id}")
            except discord.Forbidden:
                logger.warning(f"No se pudo enviar DM al detenido {detenido.id}: DMs deshabilitados")
                embed_confirmacion.add_field(
                    name="⚠️ Advertencia",
                    value="No se pudo enviar un DM al detenido (DMs deshabilitados).",
                    inline=False
                )
                await interaction.followup.send(embed=embed_confirmacion, ephemeral=True)
            except Exception as e:
                logger.error(f"Error al enviar DM al detenido {detenido.id}: {str(e)}")
            
            # Registrar en el canal de logs
            canal_logs_id = 1363655836265877674
            canal_logs = interaction.guild.get_channel(canal_logs_id)
            if canal_logs:
                log_embed = discord.Embed(
                    title="🚨 Arresto Registrado",
                    description="Se ha registrado un nuevo arresto en el sistema.",
                    color=discord.Color.red(),
                    timestamp=datetime.now()
                )
                log_embed.add_field(
                    name="Detenido",
                    value=f"{nombre} {apellido} ({rut})",
                    inline=True
                )
                log_embed.add_field(
                    name="Oficial",
                    value=f"{nombre_oficial} ({institucion})",
                    inline=True
                )
                log_embed.add_field(
                    name="Delito",
                    value=razon,
                    inline=False
                )
                log_embed.add_field(
                    name="Sentencia",
                    value=f"Tiempo: {tiempo_prision}\nMulta: ${monto_multa:,} CLP",
                    inline=True
                )
                log_embed.set_footer(text=f"Expediente N° {arresto_id:06d}")
                await canal_logs.send(embed=log_embed)
            else:
                logger.error(f"No se pudo encontrar el canal de logs con ID {canal_logs_id}")
            
    except Exception as e:
        logger.error(f"Error al registrar arresto: {str(e)}")
        embed = discord.Embed(
            title="⚠️ ERROR EN EL REGISTRO ⚠️",
            description=f"Ocurrió un error durante el registro del arresto: {str(e)}",
            color=discord.Color.red()
        )
        embed.set_footer(text="Sistema Judicial - SantiagoRP")
        await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(
    name="multar",
    description="Registra una multa a un ciudadano (Solo Carabineros y PDI)"
)
@app_commands.describe(
    ciudadano="Ciudadano a multar (obligatorio)",
    razon="Motivo de la multa (obligatorio)",
    monto_multa="Monto de la multa en pesos chilenos (obligatorio)",
    foto="Foto de la licencia del ciudadano (obligatorio)"
)
async def slash_multar_ciudadano(
    interaction: discord.Interaction,
    ciudadano: discord.Member,
    razon: str,
    monto_multa: int,
    foto: discord.Attachment
):
    """Registra una multa a un ciudadano en el sistema (Solo Carabineros y PDI)"""
    # Verificar que el comando se use en el canal correcto
    CANAL_PERMITIDO = 1344075561689026722
    if interaction.channel_id != CANAL_PERMITIDO:
        embed = discord.Embed(
            title="⚠️ CANAL INCORRECTO ⚠️",
            description="Este comando solo puede ser utilizado en el canal designado para procedimientos policiales.",
            color=discord.Color.orange()
        )
        embed.set_footer(text="Sistema de Justicia - SantiagoRP")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Verificar que el usuario tenga uno de los roles permitidos
    ROLES_AUTORIZADOS = [1339386615205859423, 1339386615205859422]  # Carabineros y PDI
    if not any(role.id in ROLES_AUTORIZADOS for role in interaction.user.roles):
        embed = discord.Embed(
            title="🚨 ACCESO DENEGADO 🚨",
            description="Solo personal de Carabineros y PDI puede registrar multas.",
            color=discord.Color.red()
        )
        embed.set_footer(text="Sistema de Justicia - SantiagoRP")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Verificar que el archivo adjunto sea una imagen
    if not foto.content_type.startswith('image/'):
        embed = discord.Embed(
            title="⚠️ ARCHIVO NO VÁLIDO ⚠️",
            description="El archivo adjunto debe ser una imagen (jpg, png, etc.).",
            color=discord.Color.orange()
        )
        embed.set_footer(text="Sistema de Justicia - SantiagoRP")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Validar monto de multa
    if monto_multa <= 0:
        embed = discord.Embed(
            title="⚠️ MONTO DE MULTA INVÁLIDO ⚠️",
            description="El monto de la multa debe ser mayor a 0.",
            color=discord.Color.orange()
        )
        embed.set_footer(text="Sistema de Justicia - SantiagoRP")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # El ciudadano ya es un objeto discord.Member
    multado = ciudadano
    
    # Informar al usuario que estamos procesando
    await interaction.response.defer(ephemeral=True, thinking=True)
    
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verificar cédula del ciudadano
            cursor.execute('''
            SELECT primer_nombre, apellido_paterno, rut, avatar_url
            FROM cedulas WHERE user_id = ?
            ''', (str(multado.id),))
            
            cedula = cursor.fetchone()
            
            if not cedula:
                embed = discord.Embed(
                    title="📄 CÉDULA NO ENCONTRADA 📄",
                    description=f"{multado.mention} no tiene cédula registrada en el sistema.",
                    color=discord.Color.orange()
                )
                embed.set_footer(text="Sistema de Justicia - SantiagoRP")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            nombre, apellido, rut, roblox_avatar = cedula
            
            # Crear tabla de multas si no existe
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS multas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                rut TEXT NOT NULL,
                razon TEXT NOT NULL,
                monto_multa INTEGER NOT NULL,
                foto_url TEXT NOT NULL,
                fecha_multa TEXT NOT NULL,
                oficial_id TEXT NOT NULL,
                estado TEXT DEFAULT 'Pendiente'
            )
            ''')
            
            # Registrar la multa
            fecha_multa = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            foto_url = foto.url
            
            cursor.execute('''
            INSERT INTO multas (
                user_id, rut, razon, monto_multa, foto_url, 
                fecha_multa, oficial_id, estado
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(multado.id), rut, razon, monto_multa, foto_url, 
                fecha_multa, str(interaction.user.id), 'Pendiente'
            ))
            
            multa_id = cursor.lastrowid
            conn.commit()
            
            # Obtener información del oficial
            cursor.execute('''
            SELECT primer_nombre, apellido_paterno
            FROM cedulas WHERE user_id = ?
            ''', (str(interaction.user.id),))
            
            oficial_info = cursor.fetchone()
            nombre_oficial = "Oficial Desconocido"
            if oficial_info:
                nombre_oficial = f"{oficial_info[0]} {oficial_info[1]}"
            
            # Determinar la institución del oficial
            institucion = "Funcionario Público"
            for role in interaction.user.roles:
                if role.id == 1339386615205859423:
                    institucion = "Carabineros de Chile"
                    break
                elif role.id == 1339386615205859422:
                    institucion = "Policía de Investigaciones"
                    break
            
            # Crear ficha de la multa
            embed_multa = discord.Embed(
                title="📝 REGISTRO DE MULTA 📝",
                description=f"**FICHA DE MULTA**\nN° {multa_id:06d}",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            embed_multa.add_field(
                name="👤 DATOS DEL CIUDADANO",
                value=f"**Nombre:** {nombre} {apellido}\n**RUT:** {rut}\n**ID:** {multado.id}",
                inline=False
            )
            
            embed_multa.add_field(
                name="⚖️ MOTIVO DE LA MULTA",
                value=f"```yaml\n{razon}\n```",
                inline=False
            )
            
            embed_multa.add_field(
                name="💸 MONTO",
                value=f"**Multa:** ${monto_multa:,} CLP",
                inline=True
            )
            
            embed_multa.add_field(
                name="📅 FECHA",
                value=f"**Multa emitida:** <t:{int(datetime.now().timestamp())}:F>",
                inline=True
            )
            
            embed_multa.add_field(
                name="👮 OFICIAL A CARGO",
                value=f"**Nombre:** {nombre_oficial}\n**Institución:** {institucion}\n**ID:** {interaction.user.id}",
                inline=False
            )
            
            embed_multa.set_image(url=foto_url)
            embed_multa.set_thumbnail(url=roblox_avatar if roblox_avatar else multado.display_avatar.url)
            embed_multa.set_footer(
                text=f"Sistema Judicial de SantiagoRP • Multa N° {multa_id:06d}",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )
            
            # Enviar al canal de multas
            canal_multas_id = 1356084986918342748
            canal_multas = interaction.guild.get_channel(canal_multas_id)
            
            if canal_multas:
                await canal_multas.send(embed=embed_multa)
                canal_nombre = canal_multas.mention
            else:
                canal_nombre = "canal de multas"
                logger.error(f"No se pudo encontrar el canal de multas con ID {canal_multas_id}")
            
            # Enviar confirmación al oficial
            embed_confirmacion = discord.Embed(
                title="✅ MULTA REGISTRADA CON ÉXITO",
                description=f"Se ha registrado la multa de {nombre} {apellido} en el sistema y publicada en {canal_nombre}.",
                color=discord.Color.green()
            )
            
            embed_confirmacion.add_field(
                name="📋 Detalles",
                value=f"**Multa N°:** {multa_id:06d}\n**Motivo:** {razon}\n**Monto:** ${monto_multa:,} CLP",
                inline=False
            )
            
            embed_confirmacion.set_footer(
                text="Sistema Judicial de SantiagoRP",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )
            
            await interaction.followup.send(embed=embed_confirmacion, ephemeral=True)
            
            # Enviar DM al ciudadano multado
            try:
                embed_dm = discord.Embed(
                    title="📝 NOTIFICACIÓN DE MULTA 📝",
                    description="**Has recibido una multa por parte de las autoridades de SantiagoRP.**\nPor favor, revisa los detalles a continuación y sigue las instrucciones proporcionadas.",
                    color=discord.Color.gold(),
                    timestamp=datetime.now()
                )
                
                embed_dm.add_field(
                    name="👤 Datos Personales",
                    value=f"**Nombre:** {nombre} {apellido}\n**RUT:** {rut}",
                    inline=True
                )
                
                embed_dm.add_field(
                    name="⚖️ Motivo de la Multa",
                    value=f"```yaml\n{razon}\n```",
                    inline=False
                )
                
                embed_dm.add_field(
                    name="💸 Monto",
                    value=f"**Multa:** ${monto_multa:,} CLP",
                    inline=True
                )
                
                embed_dm.add_field(
                    name="👮 Autoridad Responsable",
                    value=f"**Oficial:** {nombre_oficial}\n**Institución:** {institucion}",
                    inline=True
                )
                
                embed_dm.add_field(
                    name="📋 Instrucciones",
                    value="Dirígete al canal de multas para más detalles y sigue las indicaciones de las autoridades. Si tienes dudas, contacta a un oficial en el servidor.",
                    inline=False
                )
                
                embed_dm.set_thumbnail(url=foto_url)
                embed_dm.set_footer(
                    text=f"Multa N° {multa_id:06d} • Sistema Judicial de SantiagoRP",
                    icon_url=interaction.guild.icon.url if interaction.guild.icon else None
                )
                
                await multado.send(embed=embed_dm)
                logger.info(f"DM de multa enviado a {multado.id}")
            except discord.Forbidden:
                logger.warning(f"No se pudo enviar DM al ciudadano multado {multado.id}: DMs deshabilitados")
                embed_confirmacion.add_field(
                    name="⚠️ Advertencia",
                    value="No se pudo enviar un DM al ciudadano multado (DMs deshabilitados).",
                    inline=False
                )
                await interaction.followup.send(embed=embed_confirmacion, ephemeral=True)
            except Exception as e:
                logger.error(f"Error al enviar DM al ciudadano multado {multado.id}: {str(e)}")
            
            # Registrar en el canal de logs
            canal_logs_id = 1363655836265877674
            canal_logs = interaction.guild.get_channel(canal_logs_id)
            if canal_logs:
                log_embed = discord.Embed(
                    title="📝 Multa Registrada",
                    description="Se ha registrado una nueva multa en el sistema.",
                    color=discord.Color.gold(),
                    timestamp=datetime.now()
                )
                log_embed.add_field(
                    name="Ciudadano Multado",
                    value=f"{nombre} {apellido} ({rut})",
                    inline=True
                )
                log_embed.add_field(
                    name="Oficial",
                    value=f"{nombre_oficial} ({institucion})",
                    inline=True
                )
                log_embed.add_field(
                    name="Motivo",
                    value=razon,
                    inline=False
                )
                log_embed.add_field(
                    name="Monto",
                    value=f"${monto_multa:,} CLP",
                    inline=True
                )
                log_embed.set_footer(text=f"Multa N° {multa_id:06d}")
                await canal_logs.send(embed=log_embed)
            else:
                logger.error(f"No se pudo encontrar el canal de logs con ID {canal_logs_id}")
            
    except Exception as e:
        logger.error(f"Error al registrar multa: {str(e)}")
        embed = discord.Embed(
            title="⚠️ ERROR EN EL REGISTRO ⚠️",
            description=f"Ocurrió un error durante el registro de la multa: {str(e)}",
            color=discord.Color.red()
        )
        embed.set_footer(text="Sistema Judicial - SantiagoRP")
        await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(
    name="borrar-antecedentes",
    description="Borra todos los antecedentes penales (arrestos y multas) de un ciudadano (solo roles autorizados)"
)
@app_commands.describe(ciudadano="Ciudadano cuyos antecedentes deseas borrar")
async def slash_borrar_antecedentes(interaction: discord.Interaction, ciudadano: discord.Member):
    """Borra todos los antecedentes penales (arrestos y multas) de un ciudadano (solo roles autorizados)"""
    # Lista de roles autorizados
    ROLES_AUTORIZADOS = [
        1339386615235346439,
        1347803116741066834,
        1339386615222767662,
        1346545514492985486,
        1339386615247798362
    ]
    
    # Canal de logs
    CANAL_LOGS_ID = 1363655836265877674
    
    # Verificar si el usuario tiene alguno de los roles autorizados
    tiene_permiso = any(role.id in ROLES_AUTORIZADOS for role in interaction.user.roles)
    
    if not tiene_permiso:
        embed = discord.Embed(
            title="🚨 ACCESO DENEGADO 🚨",
            description="No tienes permiso para borrar antecedentes penales.",
            color=discord.Color.red()
        )
        embed.set_footer(text="Sistema de Justicia - SantiagoRP")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Informar al usuario que estamos procesando
    await interaction.response.defer(thinking=True)
    
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verificar cédula del ciudadano
            cursor.execute('''
            SELECT primer_nombre, apellido_paterno, rut, avatar_url
            FROM cedulas WHERE user_id = ?
            ''', (str(ciudadano.id),))
            
            cedula = cursor.fetchone()
            
            if not cedula:
                embed = discord.Embed(
                    title="📄 CÉDULA NO ENCONTRADA 📄",
                    description=f"{ciudadano.mention} no tiene cédula registrada en el sistema.",
                    color=discord.Color.orange()
                )
                embed.set_footer(text="Sistema de Justicia - SantiagoRP")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            nombre, apellido, rut, roblox_avatar = cedula
            
            # Obtener arrestos y multas antes de borrar (para el log)
            cursor.execute('''
            SELECT id, razon, tiempo_prision, monto_multa, fecha_arresto
            FROM arrestos WHERE user_id = ? AND estado = 'Activo'
            ''', (str(ciudadano.id),))
            
            arrestos = cursor.fetchall()
            
            cursor.execute('''
            SELECT id, razon, monto_multa, fecha_multa
            FROM multas WHERE user_id = ? AND estado = 'Pendiente'
            ''', (str(ciudadano.id),))
            
            multas = cursor.fetchall()
            
            # Si no hay antecedentes, mostrar mensaje
            if not arrestos and not multas:
                embed = discord.Embed(
                    title="🟢 SIN ANTECEDENTES 🟢",
                    description=f"{ciudadano.mention} no tiene antecedentes penales para borrar.",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="👤 Ciudadano",
                    value=f"**Nombre:** {nombre} {apellido}\n**RUT:** {rut}",
                    inline=False
                )
                embed.set_thumbnail(url=roblox_avatar if roblox_avatar else ciudadano.display_avatar.url)
                embed.set_footer(
                    text="Sistema de Justicia - SantiagoRP",
                    icon_url=interaction.guild.icon.url if interaction.guild.icon else None
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Borrar arrestos
            cursor.execute('''
            DELETE FROM arrestos WHERE user_id = ?
            ''', (str(ciudadano.id),))
            
            # Borrar multas
            cursor.execute('''
            DELETE FROM multas WHERE user_id = ?
            ''', (str(ciudadano.id),))
            
            conn.commit()
            
            # Crear mensaje de confirmación
            embed = discord.Embed(
                title="🗑️ ANTECEDENTES BORRADOS 🗑️",
                description=f"Se han eliminado todos los antecedentes penales de {ciudadano.mention}.",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="👤 Ciudadano",
                value=f"**Nombre:** {nombre} {apellido}\n**RUT:** {rut}\n**ID:** {ciudadano.id}",
                inline=False
            )
            
            embed.add_field(
                name="📊 Resumen",
                value=f"**Arrestos eliminados:** {len(arrestos)}\n**Multas eliminadas:** {len(multas)}",
                inline=True
            )
            
            embed.add_field(
                name="👮 Autoridad",
                value=f"**Usuario:** {interaction.user.mention}\n**ID:** {interaction.user.id}",
                inline=True
            )
            
            embed.set_thumbnail(url=roblox_avatar if roblox_avatar else ciudadano.display_avatar.url)
            embed.set_footer(
                text="Sistema de Justicia - SantiagoRP",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )
            
            await interaction.followup.send(embed=embed)
            
            # Enviar log al canal de logs
            canal_logs = interaction.guild.get_channel(CANAL_LOGS_ID)
            if canal_logs:
                log_embed = discord.Embed(
                    title="🗑️ Antecedentes Penales Borrados",
                    description="Se han eliminado los antecedentes penales de un ciudadano.",
                    color=discord.Color.orange(),
                    timestamp=datetime.now()
                )
                
                log_embed.add_field(
                    name="👤 Ciudadano",
                    value=f"**Nombre:** {nombre} {apellido}\n**RUT:** {rut}\n**ID:** {ciudadano.id}",
                    inline=True
                )
                
                log_embed.add_field(
                    name="👮 Autoridad",
                    value=f"**Usuario:** {interaction.user.mention}\n**ID:** {interaction.user.id}",
                    inline=True
                )
                
                # Detalles de arrestos eliminados
                if arrestos:
                    arrestos_texto = ""
                    for arresto in arrestos:
                        arresto_id, razon, tiempo_prision, monto_multa, fecha_arresto = arresto
                        arrestos_texto += (
                            f"**Expediente N° {arresto_id:06d}**\n"
                            f"📜 Delito: {razon}\n"
                            f"⛓️ Sentencia: {tiempo_prision}\n"
                            f"💸 Multa: ${monto_multa:,} CLP\n"
                            f"📅 Fecha: {fecha_arresto}\n\n"
                        )
                    log_embed.add_field(
                        name="🚨 Arrestos Eliminados",
                        value=arrestos_texto,
                        inline=False
                    )
                
                # Detalles de multas eliminadas
                if multas:
                    multas_texto = ""
                    for multa in multas:
                        multa_id, razon, monto_multa, fecha_multa = multa
                        multas_texto += (
                            f"**Multa N° {multa_id:06d}**\n"
                            f"📜 Motivo: {razon}\n"
                            f"💸 Monto: ${monto_multa:,} CLP\n"
                            f"📅 Fecha: {fecha_multa}\n\n"
                        )
                    log_embed.add_field(
                        name="📝 Multas Eliminadas",
                        value=multas_texto,
                        inline=False
                    )
                
                log_embed.set_thumbnail(url=roblox_avatar if roblox_avatar else ciudadano.display_avatar.url)
                log_embed.set_footer(
                    text=f"Sistema de Justicia - SantiagoRP",
                    icon_url=interaction.guild.icon.url if interaction.guild.icon else None
                )
                
                await canal_logs.send(embed=log_embed)
            else:
                logger.error(f"No se pudo encontrar el canal de logs con ID {CANAL_LOGS_ID}")
            
    except Exception as e:
        logger.error(f"Error al borrar antecedentes: {str(e)}")
        embed = discord.Embed(
            title="⚠️ ERROR AL BORRAR ANTECEDENTES ⚠️",
            description=f"Ocurrió un error al borrar los antecedentes: {str(e)}",
            color=discord.Color.red()
        )
        embed.set_footer(text="Sistema de Justicia - SantiagoRP")
        await interaction.followup.send(embed=embed, ephemeral=True)
        

@bot.tree.command(
    name="ver-antecedentes",
    description="Muestra todos los antecedentes penales (arrestos y multas) de un ciudadano"
)
@app_commands.describe(ciudadano="Ciudadano cuyos antecedentes deseas ver (por defecto, tú mismo)")
async def slash_ver_antecedentes(interaction: discord.Interaction, ciudadano: discord.Member = None):
    """Muestra todos los antecedentes penales (arrestos y multas) de un ciudadano"""
    # Verificar que el comando se use en el canal correcto
    CANAL_PERMITIDO = 1344075561689026722
    if interaction.channel_id != CANAL_PERMITIDO:
        embed = discord.Embed(
            title="⚠️ CANAL INCORRECTO ⚠️",
            description="Este comando solo puede ser utilizado en el canal designado para procedimientos policiales.",
            color=discord.Color.orange()
        )
        embed.set_footer(text="Sistema de Justicia - SantiagoRP")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Si no se especifica un ciudadano, se usa el usuario que ejecuta el comando
    ciudadano = ciudadano or interaction.user
    
    # Informar al usuario que estamos procesando
    await interaction.response.defer(thinking=True)
    
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verificar cédula del ciudadano
            cursor.execute('''
            SELECT primer_nombre, apellido_paterno, rut, avatar_url
            FROM cedulas WHERE user_id = ?
            ''', (str(ciudadano.id),))
            
            cedula = cursor.fetchone()
            
            if not cedula:
                embed = discord.Embed(
                    title="📄 CÉDULA NO ENCONTRADA 📄",
                    description=f"{ciudadano.mention} no tiene cédula registrada en el sistema.",
                    color=discord.Color.orange()
                )
                embed.set_footer(text="Sistema de Justicia - SantiagoRP")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            nombre, apellido, rut, roblox_avatar = cedula
            
            # Obtener arrestos del ciudadano
            cursor.execute('''
            SELECT id, razon, tiempo_prision, monto_multa, foto_url, fecha_arresto, oficial_id
            FROM arrestos WHERE user_id = ? AND estado = 'Activo'
            ''', (str(ciudadano.id),))
            
            arrestos = cursor.fetchall()
            
            # Obtener multas del ciudadano
            cursor.execute('''
            SELECT id, razon, monto_multa, foto_url, fecha_multa, oficial_id
            FROM multas WHERE user_id = ? AND estado = 'Pendiente'
            ''', (str(ciudadano.id),))
            
            multas = cursor.fetchall()
            
            # Si no hay antecedentes, mostrar mensaje
            if not arrestos and not multas:
                embed = discord.Embed(
                    title="🟢 SIN ANTECEDENTES 🟢",
                    description=f"{ciudadano.mention} no tiene antecedentes penales registrados.",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="👤 Ciudadano",
                    value=f"**Nombre:** {nombre} {apellido}\n**RUT:** {rut}",
                    inline=False
                )
                embed.set_thumbnail(url=roblox_avatar if roblox_avatar else ciudadano.display_avatar.url)
                embed.set_footer(
                    text="Sistema de Justicia - SantiagoRP",
                    icon_url=interaction.guild.icon.url if interaction.guild.icon else None
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Crear embed principal
            embed = discord.Embed(
                title="📜 ANTECEDENTES PENALES 📜",
                description=f"**Reporte completo de antecedentes para {ciudadano.mention}**",
                color=discord.Color.purple(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="👤 DATOS DEL CIUDADANO",
                value=f"**Nombre:** {nombre} {apellido}\n**RUT:** {rut}\n**ID:** {ciudadano.id}",
                inline=False
            )
            
            # Mostrar arrestos
            if arrestos:
                arrestos_texto = ""
                for arresto in arrestos:
                    arresto_id, razon, tiempo_prision, monto_multa, foto_url, fecha_arresto, oficial_id = arresto
                    oficial = interaction.guild.get_member(int(oficial_id))
                    oficial_nombre = oficial.display_name if oficial else "Oficial Desconocido"
                    arrestos_texto += (
                        f"**Expediente N° {arresto_id:06d}**\n"
                        f"📜 **Delito:** {razon}\n"
                        f"⛓️ **Sentencia:** {tiempo_prision}\n"
                        f"💸 **Multa:** ${monto_multa:,} CLP\n"
                        f"📅 **Fecha:** {fecha_arresto}\n"
                        f"👮 **Oficial:** {oficial_nombre}\n\n"
                    )
                embed.add_field(
                    name="🚨 ARRESTOS",
                    value=arrestos_texto or "No hay arrestos registrados.",
                    inline=False
                )
            else:
                embed.add_field(
                    name="🚨 ARRESTOS",
                    value="No hay arrestos registrados.",
                    inline=False
                )
            
            # Mostrar multas
            if multas:
                multas_texto = ""
                for multa in multas:
                    multa_id, razon, monto_multa, foto_url, fecha_multa, oficial_id = multa
                    oficial = interaction.guild.get_member(int(oficial_id))
                    oficial_nombre = oficial.display_name if oficial else "Oficial Desconocido"
                    multas_texto += (
                        f"**Multa N° {multa_id:06d}**\n"
                        f"📜 **Motivo:** {razon}\n"
                        f"💸 **Monto:** ${monto_multa:,} CLP\n"
                        f"📅 **Fecha:** {fecha_multa}\n"
                        f"👮 **Oficial:** {oficial_nombre}\n\n"
                    )
                embed.add_field(
                    name="📝 MULTAS",
                    value=multas_texto or "No hay multas registradas.",
                    inline=False
                )
            else:
                embed.add_field(
                    name="📝 MULTAS",
                    value="No hay multas registradas.",
                    inline=False
                )
            
            embed.set_thumbnail(url=roblox_avatar if roblox_avatar else ciudadano.display_avatar.url)
            embed.set_footer(
                text="Sistema de Justicia - SantiagoRP",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )
            
            await interaction.followup.send(embed=embed)
            
    except Exception as e:
        logger.error(f"Error al consultar antecedentes: {str(e)}")
        embed = discord.Embed(
            title="⚠️ ERROR AL CONSULTAR ANTECEDENTES ⚠️",
            description=f"Ocurrió un error al consultar los antecedentes: {str(e)}",
            color=discord.Color.red()
        )
        embed.set_footer(text="Sistema de Justicia - SantiagoRP")
        await interaction.followup.send(embed=embed, ephemeral=True)
        
@bot.tree.command(name="ayuda", description="Muestra una lista de todos los comandos disponibles y sus detalles")
async def slash_ayuda(interaction: discord.Interaction):
    """Muestra una lista detallada y atractiva de todos los comandos disponibles"""
    
    # Verificar que el comando se use en el canal correcto
    CANAL_PERMITIDO = 1344075561689026722
    if interaction.channel_id != CANAL_PERMITIDO:
        embed = discord.Embed(
            title="⚠️ CANAL INCORRECTO ⚠️",
            description="Este comando solo puede ser utilizado en el canal designado para procedimientos generales.",
            color=discord.Color.red()
        )
        embed.add_field(
            name="📋 Instrucciones",
            value=f"Dirígete al canal <#{CANAL_PERMITIDO}> para usar este comando.",
            inline=False
        )
        embed.set_footer(
            text="Santiago RP - Sistema de Ayuda",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🚨 ¡SISTEMA DE AYUDA - SANTIAGO RP! 🚨",
        description="Aquí tienes una lista completa de todos los comandos disponibles, su función y dónde usarlos. ¡Explora y gestiona tu experiencia en el servidor!",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
    embed.set_footer(text="Santiago RP - Sistema de Ayuda", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    
    # Categorías de comandos
    comandos = {
        "📋 Registro Civil": [
            {
                "nombre": "/crear-cedula",
                "descripcion": "Crea una cédula de identidad para un usuario.",
                "canal": "<#1339386616803885088>",
                "permisos": "Solo administradores"
            },
            {
                "nombre": "/ver-cedula",
                "descripcion": "Muestra la cédula de un usuario (tuya por defecto).",
                "canal": "<#1339386616803885089>",
                "permisos": "Todos"
            },
            {
                "nombre": "/eliminar-cedula",
                "descripcion": "Elimina la cédula de un usuario.",
                "canal": "Cualquier canal",
                "permisos": "Roles autorizados"
            }
        ],
        "🚗 Dirección de Tránsito": [
            {
                "nombre": "/tramitar-licencia",
                "descripcion": "Tramita una licencia de conducir para un usuario.",
                "canal": "Cualquier canal",
                "permisos": "Roles autorizados"
            },
            {
                "nombre": "/ver-licencia",
                "descripcion": "Muestra una licencia específica de un usuario.",
                "canal": "<#1344192338397757461>",
                "permisos": "Todos"
            },
            {
                "nombre": "/revocar-licencia",
                "descripcion": "Revoca una licencia específica de un usuario.",
                "canal": "Cualquier canal",
                "permisos": "Roles autorizados"
            },
            {
                "nombre": "/registrar-vehiculo",
                "descripcion": "Registra un vehículo para un usuario.",
                "canal": "Cualquier canal",
                "permisos": "Roles autorizados"
            },
            {
                "nombre": "/ver-vehiculo",
                "descripcion": "Muestra la información de un vehículo registrado.",
                "canal": "<#1344192338397757461>",
                "permisos": "Todos"
            },
            {
                "nombre": "/eliminar-vehiculo",
                "descripcion": "Elimina el registro de un vehículo.",
                "canal": "Cualquier canal",
                "permisos": "Roles autorizados"
            }
        ],
        "🏠 Registro de Propiedades": [
            {
                "nombre": "/registrar-propiedad",
                "descripcion": "Registra una propiedad para un usuario.",
                "canal": "Cualquier canal",
                "permisos": "Roles autorizados"
            },
            {
                "nombre": "/ver-propiedad",
                "descripcion": "Muestra la información de una propiedad registrada.",
                "canal": "<#1344192338397757461>",
                "permisos": "Todos"
            },
            {
                "nombre": "/eliminar-propiedad",
                "descripcion": "Elimina el registro de una propiedad.",
                "canal": "Cualquier canal",
                "permisos": "Roles autorizados"
            }
        ],
        "🚨 Sistema de Emergencias": [
            {
                "nombre": "/entorno",
                "descripcion": "Reporta una emergencia a los servicios correspondientes.",
                "canal": "<#1344075561689026722>",
                "permisos": "Todos"
            }
        ],
        "⚖️ Sistema Judicial": [
            {
                "nombre": "/arrestar-a",
                "descripcion": "Registra el arresto de un ciudadano.",
                "canal": "<#1344075561689026722>",
                "permisos": "Carabineros y PDI"
            },
            {
                "nombre": "/multar",
                "descripcion": "Registra una multa a un ciudadano.",
                "canal": "<#1344075561689026722>",
                "permisos": "Carabineros y PDI"
            },
            {
                "nombre": "/borrar-antecedentes",
                "descripcion": "Borra todos los antecedentes penales de un ciudadano.",
                "canal": "Cualquier canal",
                "permisos": "Roles autorizados"
            },
            {
                "nombre": "/ver-antecedentes",
                "descripcion": "Muestra los antecedentes penales de un ciudadano.",
                "canal": "<#1344075561689026722>",
                "permisos": "Todos"
            }
        ]
    }
    
    # Agregar comandos al embed por categoría
    for categoria, lista_comandos in comandos.items():
        comandos_texto = ""
        for cmd in lista_comandos:
            comandos_texto += (
                f"**{cmd['nombre']}**\n"
                f"📝 **Descripción:** {cmd['descripcion']}\n"
                f"📍 **Canal:** {cmd['canal']}\n"
                f"🔒 **Permisos:** {cmd['permisos']}\n\n"
            )
        embed.add_field(
            name=categoria,
            value=comandos_texto,
            inline=False
        )
    
    # Enviar mensaje
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Iniciar el bot
bot.run(TOKEN)
