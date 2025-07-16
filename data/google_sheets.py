# ===== LIBRARIES =====
import gspread
import asyncio
from google.oauth2.service_account import Credentials
from typing import Dict, List, Optional
from datetime import datetime

# ===== MODULES =====
from src.config.settings import SHEET_ID, SHEET_CREDENTIAL
from src.config.logs import logging

# ===== GOOGLE SHEETS SETUP =====
scopes = [
    'https://www.googleapis.com/auth/spreadsheets'
]

creds = Credentials.from_service_account_file(SHEET_CREDENTIAL, scopes=scopes)
client = gspread.authorize(creds)

try:
    sheet = client.open_by_key(SHEET_ID)
    worksheet = sheet.get_worksheet(0)  # Primera hoja
    logging.info("Google Sheets connected successfully")
except Exception as e:
    logging.error(f"Error connecting to Google Sheets: {str(e)}")
    worksheet = None

# ===== UTILITY FUNCTIONS =====
def get_next_row() -> int:
    """Obtiene la siguiente fila disponible en la hoja"""
    try:
        if not worksheet:
            return 2  # Default si no hay conexión
        
        # Buscar la primera fila vacía en la columna A (FECHA)
        values = worksheet.col_values(1)  # Columna A
        return len(values) + 1
    except Exception as e:
        logging.error(f"Error getting next row: {str(e)}")
        return 2

def find_operation_row(symbol: str) -> Optional[int]:
    """Encuentra la fila de una operación específica por símbolo"""
    try:
        if not worksheet:
            return None
        
        # Buscar en la columna B (MONEDA)
        values = worksheet.col_values(2)  # Columna B
        for i, value in enumerate(values):
            if value == symbol:
                return i + 1  # +1 porque gspread usa índices basados en 1
        return None
    except Exception as e:
        logging.error(f"Error finding operation row for {symbol}: {str(e)}")
        return None

# ===== MAIN FUNCTIONS =====
async def add_operation(operation: Dict):
    """Agrega una nueva operación al Google Sheets"""
    try:
        if not worksheet:
            logging.error("No worksheet connection available")
            return False
        
        # Obtener siguiente fila disponible
        row = get_next_row()
        
        # Preparar datos para insertar
        # Columnas: FECHA, MONEDA, DIRECCIÓN, ENTRADA, SL(-5%), TP1(+5%), TP2(10%), TP3(15%), TP4(+20%), RESULTADO, PROFIT
        data = [
            operation['date'],              # A - FECHA
            operation['symbol'],            # B - MONEDA
            operation['direction'],         # C - DIRECCIÓN
            operation['entry_price'],       # D - ENTRADA
            '',                            # E - SL (-5%) - Se actualizará cuando se cierre
            '',                            # F - TP1 (+5%) - Se actualizará si se alcanza
            '',                            # G - TP2 (10%) - Se actualizará si se alcanza
            '',                            # H - TP3 (15%) - Se actualizará si se alcanza
            '',                            # I - TP4 (+20%) - Se actualizará si se alcanza
            '',                            # J - RESULTADO - Se actualizará al cerrar
            ''                             # K - PROFIT - Se actualizará al cerrar
        ]
        
        # Insertar datos en la fila
        worksheet.insert_row(data, row)
        
        logging.info(f"Operation added to Google Sheets: {operation['symbol']} - Row {row}")
        return True
        
    except Exception as e:
        logging.error(f"Error adding operation to Google Sheets: {str(e)}")
        return False

async def update_operation_result(symbol: str, result: str, profit_percent: float):
    """Actualiza el resultado de una operación en Google Sheets"""
    try:
        if not worksheet:
            logging.error("No worksheet connection available")
            return False
        
        # Encontrar la fila de la operación
        row = find_operation_row(symbol)
        if not row:
            logging.error(f"Operation row not found for {symbol}")
            return False
        
        # Determinar qué columna actualizar basado en el resultado
        if result == 'SL':
            # Actualizar columna E (SL) y columnas J y K (RESULTADO y PROFIT)
            worksheet.update_cell(row, 5, 'HIT')  # Columna E - SL
            worksheet.update_cell(row, 10, result)  # Columna J - RESULTADO
            worksheet.update_cell(row, 11, f"{profit_percent:.2f}%")  # Columna K - PROFIT
            
        elif result == 'TP1':
            # Actualizar columna F (TP1)
            worksheet.update_cell(row, 6, 'HIT')  # Columna F - TP1
            
        elif result == 'TP2':
            # Actualizar columna G (TP2)
            worksheet.update_cell(row, 7, 'HIT')  # Columna G - TP2
            
        elif result == 'TP3':
            # Actualizar columna H (TP3)
            worksheet.update_cell(row, 8, 'HIT')  # Columna H - TP3
            
        elif result == 'TP4':
            # Actualizar columna I (TP4) y columnas J y K (RESULTADO y PROFIT)
            worksheet.update_cell(row, 9, 'HIT')  # Columna I - TP4
            worksheet.update_cell(row, 10, result)  # Columna J - RESULTADO
            worksheet.update_cell(row, 11, f"{profit_percent:.2f}%")  # Columna K - PROFIT
            
        elif result == 'MANUAL':
            # Actualizar columnas J y K (RESULTADO y PROFIT)
            worksheet.update_cell(row, 10, result)  # Columna J - RESULTADO
            worksheet.update_cell(row, 11, f"{profit_percent:.2f}%")  # Columna K - PROFIT
        
        logging.info(f"Operation updated in Google Sheets: {symbol} - {result} - Row {row}")
        return True
        
    except Exception as e:
        logging.error(f"Error updating operation result in Google Sheets: {str(e)}")
        return False

async def get_operation_history(symbol: str = None, limit: int = 100) -> List[Dict]:
    """Obtiene el historial de operaciones desde Google Sheets"""
    try:
        if not worksheet:
            logging.error("No worksheet connection available")
            return []
        
        # Obtener todos los datos
        all_data = worksheet.get_all_records()
        
        # Filtrar por símbolo si se proporciona
        if symbol:
            all_data = [row for row in all_data if row.get('MONEDA') == symbol]
        
        # Limitar resultados
        return all_data[:limit]
        
    except Exception as e:
        logging.error(f"Error getting operation history: {str(e)}")
        return []

async def get_statistics() -> Dict:
    """Obtiene estadísticas del historial de operaciones"""
    try:
        if not worksheet:
            logging.error("No worksheet connection available")
            return {}
        
        # Obtener todos los datos
        all_data = worksheet.get_all_records()
        
        # Inicializar estadísticas
        stats = {
            'total_operations': len(all_data),
            'sl_count': 0,
            'tp1_count': 0,
            'tp2_count': 0,
            'tp3_count': 0,
            'tp4_count': 0,
            'manual_count': 0,
            'total_profit': 0.0,
            'win_rate': 0.0,
            'avg_profit': 0.0
        }
        
        if not all_data:
            return stats
        
        # Calcular estadísticas
        wins = 0
        total_profit = 0.0
        
        for row in all_data:
            result = row.get('RESULTADO', '').strip()
            profit_str = row.get('PROFIT', '').strip()
            
            # Contar resultados
            if result == 'SL':
                stats['sl_count'] += 1
            elif result == 'TP1':
                stats['tp1_count'] += 1
                wins += 1
            elif result == 'TP2':
                stats['tp2_count'] += 1
                wins += 1
            elif result == 'TP3':
                stats['tp3_count'] += 1
                wins += 1
            elif result == 'TP4':
                stats['tp4_count'] += 1
                wins += 1
            elif result == 'MANUAL':
                stats['manual_count'] += 1
            
            # Calcular profit total
            if profit_str:
                try:
                    profit_value = float(profit_str.replace('%', ''))
                    total_profit += profit_value
                    if profit_value > 0:
                        wins += 1
                except ValueError:
                    pass
        
        # Calcular ratios
        if stats['total_operations'] > 0:
            stats['win_rate'] = (wins / stats['total_operations']) * 100
            stats['avg_profit'] = total_profit / stats['total_operations']
        
        stats['total_profit'] = total_profit
        
        return stats
        
    except Exception as e:
        logging.error(f"Error getting statistics: {str(e)}")
        return {}

async def clear_sheet():
    """Limpia toda la hoja (usar con precaución)"""
    try:
        if not worksheet:
            logging.error("No worksheet connection available")
            return False
        
        # Mantener solo los headers
        worksheet.clear()
        
        # Reagregar headers
        headers = [
            'FECHA', 'MONEDA', 'DIRECCIÓN', 'ENTRADA', 'SL (-5%)', 
            'TP1 (+5%)', 'TP2 (10%)', 'TP3 (15%)', 'TP4 (+20%)', 
            'RESULTADO', 'PROFIT'
        ]
        
        worksheet.insert_row(headers, 1)
        
        logging.info("Sheet cleared successfully")
        return True
        
    except Exception as e:
        logging.error(f"Error clearing sheet: {str(e)}")
        return False

# ===== ASYNC WRAPPER =====
async def google_sheets():
    """Función principal para inicializar Google Sheets"""
    try:
        # Verificar conexión
        if worksheet:
            logging.info("Google Sheets initialized successfully")
            return True
        else:
            logging.error("Failed to initialize Google Sheets")
            return False
    except Exception as e:
        logging.error(f"Error initializing Google Sheets: {str(e)}")
        return False

# ===== TESTING FUNCTIONS =====
async def test_add_operation():
    """Función de prueba para agregar una operación"""
    test_operation = {
        'symbol': 'BTCUSDT',
        'direction': 'LONG',
        'entry_price': 45000.0,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    result = await add_operation(test_operation)
    print(f"Test add operation result: {result}")

async def test_update_operation():
    """Función de prueba para actualizar una operación"""
    result = await update_operation_result('BTCUSDT', 'TP1', 5.0)
    print(f"Test update operation result: {result}")

async def test_get_statistics():
    """Función de prueba para obtener estadísticas"""
    stats = await get_statistics()
    print(f"Test statistics: {stats}")

# ===== EXECUTION EXAMPLE =====
if __name__ == "__main__":
    # Ejemplo de uso
    async def main():
        await google_sheets()
        await test_add_operation()
        await test_update_operation()
        stats = await test_get_statistics()
        print(stats)
    
    asyncio.run(main())