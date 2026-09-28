import os
import math
import unicodedata
import pandas as pd
from supabase import create_client, Client

# 1. Configurar conexión a Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Faltan las credenciales SUPABASE_URL o SUPABASE_KEY en las variables de entorno.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ID de la estación (Asegúrate de que coincida con el ID registrado en la tabla 'estaciones')
ESTACION_ID = "ema_cerrillos"

# 2. Diccionario de mapeo en minúsculas y sin acentos/símbolos para evitar problemas de encoding
NORMALIZED_COLUMN_MAP = {
    'temp ext (c)': 'temp_ext',
    'temp ext (c)': 'temp_ext',
    'temp ext': 'temp_ext',
    'temp max': 'temp_max',
    'temp min': 'temp_min',
    'humedad ext (%)': 'humedad_ext',
    'humedad ext': 'humedad_ext',
    'punto rocio': 'punto_rocio',
    'vel vent': 'vel_vent',
    'dir vent': 'dir_vent',
    'wind run': 'wind_run',
    'rafaga vent': 'rafaga_vent',
    'dir rafaga': 'dir_rafaga',
    'vel max': 'vel_max',
    'dir max': 'dir_max',
    'sens term wind': 'sens_term_wind',
    'indice calor': 'indice_calor',
    'thw index': 'thw',
    'thw': 'thw',
    'thsw': 'thsw',
    'presion (hpa)': 'presion',
    'presion': 'presion',
    'lluvia (mm)': 'lluvia',
    'lluvia': 'lluvia',
    'int lluvia': 'int_lluvia',
    'rad solar': 'rad_solar',
    'energia solar': 'energia_solar',
    'rad solar max': 'rad_solar_max',
    'uv': 'uv',
    'dosis uv': 'dosis_uv',
    'uv max': 'uv_max',
    'heat d-d': 'heat_dd',
    'cool d-d': 'cool_dd',
    'grados dia h': 'grados_dia_h',
    'grados dia c': 'grados_dia_c',
    'grados dia f': 'grados_dia_f',
    'temp int': 'temp_int',
    'humedad int': 'humedad_int',
    'punto rocio int': 'punto_rocio_int',
    'heat int': 'heat_int',
    'emc int': 'emc_int',
    'densidad aire int': 'densidad_aire_int',
    'et': 'et',
    'muestras vent': 'muestras_vent',
    'tx vent': 'tx_vent',
    'recepcion iss': 'recepcion_iss',
    'intervalo arc': 'intervalo_arc'
}

def normalize_text(text):
    """Convierte texto a minúsculas, remueve tildes y arregla caracteres mal codificados."""
    if not isinstance(text, str):
        return ""
    # Corregir mojibake si ocurrió al leer en latin1
    try:
        text = text.encode('latin1').decode('utf-8')
    except Exception:
        pass
    
    # Quitar tildes y caracteres especiales como °
    text = text.replace('°', '').replace('Â', '')
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text.lower().strip()

def clean_val(val):
    """Limpia valores nulos y textos como '---'."""
    if pd.isna(val):
        return None
    val_str = str(val).strip()
    if val_str in ['---', '---.-', '----', '']:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    return val

def sync():
    csv_file = 'downld08.csv' if os.path.exists('downld08.csv') else 'downld02.csv'
    if not os.path.exists(csv_file):
        print(f"No se encontró ningún archivo CSV en el directorio.")
        return

    print(f"Leyendo archivo: {csv_file}")
    df = pd.read_csv(csv_file, encoding='latin1')

    # Mapear dinámicamente las columnas del CSV usando el texto normalizado
    col_mapping_real = {}
    for col in df.columns:
        norm_col = normalize_text(col)
        if norm_col in NORMALIZED_COLUMN_MAP:
            col_mapping_real[col] = NORMALIZED_COLUMN_MAP[norm_col]
        else:
            print(f"Columna no reconocida o sin mapeo: '{col}' (normalizada: '{norm_col}')")

    # Identificar nombres reales de Fecha y Hora
    fecha_col = next((c for c in df.columns if normalize_text(c) == 'fecha'), None)
    hora_col = next((c for c in df.columns if normalize_text(c) == 'hora'), None)

    if not fecha_col or not hora_col:
        print("Error: No se encontraron las columnas de Fecha u Hora.")
        return

    # Convertir Fecha y Hora a ISO Timestamptz de Argentina (-03:00)
    df['fecha_hora'] = pd.to_datetime(
        df[fecha_col].astype(str) + ' ' + df[hora_col].astype(str), 
        format='%d/%m/%y %H:%M',
        errors='coerce'
    ).dt.strftime('%Y-%m-%dT%H:%M:%S-03:00')

    df = df.dropna(subset=['fecha_hora'])

    records = []
    for _, row in df.iterrows():
        record = {
            'estacion_id': ESTACION_ID,
            'fecha_hora': row['fecha_hora']
        }
        
        for csv_col, db_col in col_mapping_real.items():
            val = clean_val(row[csv_col])
            if val is not None:
                record[db_col] = val

        records.append(record)

    if not records:
        print("No hay registros procesables.")
        return

    print(f"Subiendo {len(records)} registros corregidos a Supabase...")

    # Cargar en lotes de 100 con upsert
    chunk_size = 100
    for i in range(0, len(records), chunk_size):
        chunk = records[i:i + chunk_size]
        supabase.table("mediciones").upsert(
            chunk, 
            on_conflict="estacion_id,fecha_hora"
        ).execute()

    print("¡Sincronización finalizada exitosamente! Todos los campos han sido procesados.")

if __name__ == "__main__":
    sync()
