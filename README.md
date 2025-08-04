# 🚀 CryptoAlert Pro

Un bot inteligente de Telegram que monitorea el mercado de criptomonedas en tiempo real y envía alertas automáticas cuando detecta movimientos significativos de precios.

## 📊 Características

- **Monitoreo en Tiempo Real**: Rastrea precios de criptomonedas usando WebSockets de Binance
- **Alertas Inteligentes**: Notifica automáticamente cuando hay cambios de precio ≥20% en ventanas de 2 horas
- **Anti-Spam**: Sistema inteligente que evita alertas duplicadas
- **Procesamiento por Lotes**: Maneja múltiples símbolos eficientemente respetando los límites de Binance
- **Uptime 24/7**: Servidor web integrado para mantener el bot activo continuamente
- **Integración con Google Sheets**: Almacena y gestiona datos de trading

## 🛠️ Tecnologías Utilizadas

- **Python 3.8+**
- **Binance API**: Para datos de mercado en tiempo real
- **Telegram Bot API**: Para envío de alertas
- **Flask**: Servidor web para uptime
- **AsyncIO**: Programación asíncrona para mejor rendimiento
- **Google Sheets API**: Para almacenamiento de datos

## 📋 Requisitos Previos

1. **Cuenta de Binance** con API habilitada
2. **Bot de Telegram** creado con @BotFather
3. **Canal/Grupo de Telegram** para recibir alertas
4. **Cuenta de Google** para Google Sheets (opcional)

## ⚙️ Configuración

### 1. Clona el repositorio
```bash
git clone https://github.com/tu-usuario/cryptoalert-pro.git
cd cryptoalert-pro
```

### 2. Instala las dependencias
```bash
pip install -r requirements.txt
```

### 3. Configura las variables de entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
# Binance API
API_KEY=tu_binance_api_key
API_SECRET=tu_binance_api_secret

# Telegram Bot Principal
BOT_TOKEN=tu_bot_token
CHANNEL_ID=tu_channel_id

# Telegram Bot de Logs (opcional)
BOT_LOG_TOKEN=tu_log_bot_token
CHANNEL_LOG_ID=tu_log_channel_id

# Google Sheets (opcional)
SHEET_ID=tu_google_sheet_id
SHEET_CREDENTIAL=tu_google_credentials_json
```

### 4. Obtener las credenciales necesarias

#### Binance API:
1. Ve a [Binance API Management](https://www.binance.com/en/my/settings/api-management)
2. Crea una nueva API Key
3. Habilita "Enable Reading" (no necesitas trading permissions)
4. Guarda tu API Key y Secret Key

#### Telegram Bot:
1. Habla con [@BotFather](https://t.me/botfather) en Telegram
2. Usa `/newbot` para crear un nuevo bot
3. Guarda el token que te proporciona
4. Añade el bot a tu canal/grupo y hazlo administrador
5. Obtén el ID del canal usando [@userinfobot](https://t.me/userinfobot)

## 🚀 Uso

### Ejecutar localmente
```bash
python main.py
```

### Ejecutar en producción
El bot incluye un servidor Flask que responde en el puerto 8000 para mantener el uptime:

```bash
python main.py
```

El servidor estará disponible en `http://localhost:8000`

## 📊 Funcionamiento

1. **Conexión**: El bot se conecta a la API de Binance usando WebSockets
2. **Monitoreo**: Rastrea precios de múltiples criptomonedas en tiempo real
3. **Análisis**: Calcula cambios porcentuales en ventanas de 2 horas
4. **Alertas**: Envía notificaciones cuando detecta cambios ≥20%
5. **Filtrado**: Evita spam con sistema de buckets de tiempo

## 📱 Formato de Alertas

```
🟢 #BTCUSDT 📈 +25.67%
💵 $45,230.50 💰 $1,234.56M
```

- 🟢📈 = Subida de precio
- 🔴📉 = Bajada de precio
- Símbolo de la criptomoneda
- Porcentaje de cambio
- Precio actual
- Volumen en millones

## ⚡ Configuración Avanzada

### Modificar el umbral de alerta
En `price_handler.py`, cambia la constante:
```python
THRESHOLD = 20.0  # Cambiar a tu porcentaje deseado
```

### Modificar la ventana de tiempo
```python
TIME_WINDOW = 2 * 60 * 60  # 2 horas en segundos
```

### Añadir más símbolos
Modifica la función `coin_handler` en `models/coin_handler.py`

## 🔧 Estructura del Proyecto

```
cryptoalert-pro/
├── main.py                 # Punto de entrada principal
├── config/
│   └── settings.py         # Configuración y variables de entorno
├── models/
│   ├── alert_handler.py    # Manejo de alertas de Telegram
│   ├── price_handler.py    # Lógica de monitoreo de precios
│   └── coin_handler.py     # Gestión de símbolos de criptomonedas
├── requirements.txt        # Dependencias de Python
├── .env                   # Variables de entorno (no incluir en git)
└── README.md              # Este archivo
```

## 🐛 Solución de Problemas

### Error de conexión a Binance
- Verifica que tu API Key y Secret sean correctos
- Asegúrate de que la API Key tenga permisos de lectura habilitados
- Revisa que no hayas excedido los límites de rate de Binance

### Bot no envía mensajes
- Confirma que el bot sea administrador del canal
- Verifica que el CHANNEL_ID sea correcto (debe incluir el `-` para canales)
- Revisa que el BOT_TOKEN sea válido

### Problemas de rendimiento
- El bot maneja automáticamente múltiples símbolos en lotes
- Si experimentas lag, reduce el número de símbolos monitoreados

## 📈 Próximas Características

- [ ] Dashboard web para visualización de datos
- [ ] Alertas personalizables por usuario
- [ ] Soporte para más exchanges
- [ ] Análisis técnico avanzado
- [ ] Backtesting de estrategias
- [ ] Notificaciones por email

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## ⚠️ Disclaimer

Este bot es solo para fines educativos e informativos. No constituye asesoramiento financiero. Siempre haz tu propia investigación antes de tomar decisiones de inversión.

## 📞 Soporte

Si tienes problemas o preguntas:
- Abre un [Issue](https://github.com/tu-usuario/cryptoalert-pro/issues)
- Contacta al desarrollador: [tu-email@ejemplo.com]

---

⭐ Si este proyecto te resulta útil, ¡no olvides darle una estrella!
