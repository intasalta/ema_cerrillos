import os
import math
import unicodedata
import pandas as pd
from supabase import create_client, Client

# ==============================================================================
# 1. Configuración de conexión a Supabase
# ==============================================================================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Faltan las credenciales SUPABASE_URL o SUPABASE_KEY en las variables de entorno.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ID de la estación registrada en la tabla 'estaciones'
ESTACION_ID = "ema_cerrillos"

# ==============================================================================
# 2. Diccionario de mapeo de columnas
# ==============================================================================
NORMALIZED_COLUMN_MAP = {
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

# ==============================================================================
# 3. Funciones auxiliares de limpieza
# ==============================================================================
def normalize_text(text):
    """Convierte texto a minúsculas, remueve tildes y arregla problemas de encoding."""
    if not isinstance(text, str):
        return ""
    try:
        text = text.encode('latin1').decode('utf-8')
    except Exception:
        pass
    
    text = text.replace('°', '').replace('Â', '')
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text.lower().strip()

def clean_val(val):
    """Limpia valores nulos y formatos de texto como '---' provenientes de la estación."""
    if pd.isna(val):
        return None
    val_str = str(val).strip()
    if val_str in ['---', '---.-', '----', '']:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    return val

# ==============================================================================
# 4. Función Principal de Sincronización
# ==============================================================================
def sync():
    csv_file = 'downld08.csv' if os.path.exists('downld08.csv') else 'downld02.csv'
    if not os.path.exists(csv_file):
        print(f"No se encontró ningún archivo CSV en el directorio.")
        return

    print(f"Leyendo archivo: {csv_file}")
    df = pd.read_csv(csv_file, encoding='latin1')

    # Mapear dinámicamente las columnas reales del CSV
    col_mapping_real = {}
    for col in df.columns:
        norm_col = normalize_text(col)
        if norm_col in NORMALIZED_COLUMN_MAP:
            col_mapping_real[col] = NORMALIZED_COLUMN_MAP[norm_col]

    # Identificar columnas de Fecha y Hora
    fecha_col = next((c for c in df.columns if normalize_text(c) == 'fecha'), None)
    hora_col = next((c for c in df.columns if normalize_text(c) == 'hora'), None)

    if not fecha_col or not hora_col:
        print("Error: No se encontraron las columnas de Fecha u Hora.")
        return

    # Convertir Fecha y Hora a Datetime nativo
    df['dt'] = pd.to_datetime(
        df[fecha_col].astype(str) + ' ' + df[hora_col].astype(str), 
        format='%d/%m/%y %H:%M',
        errors='coerce'
    )
    df = df.dropna(subset=['dt'])

    # --- ESTRATEGIA DE OPTIMIZACIÓN DINÁMICA ---
    # Consulta a Supabase para determinar cuál fue el último registro cargado
    try:
        response = supabase.table("mediciones") \
            .select("fecha_hora") \
            .eq("estacion_id", ESTACION_ID) \
            .order("fecha_hora", desc=True) \
            .limit(1) \
            .execute()
        
        if response.data and len(response.data) > 0:
            # Eliminar la información del offset (+00:00 / -03:00) para comparar directamente con el datetime local
            raw_fecha = response.data[0]['fecha_hora']
            ultima_fecha_db = pd.to_datetime(raw_fecha).tz_localize(None)
            print(f"Último registro detectado en Supabase: {ultima_fecha_db}")
            
            # Filtrar solo registros estrictamente más nuevos que el último existente
            df_filtrado = df[df['dt'] > ultima_fecha_db].copy()
        else:
            print("No se encontraron registros previos en la base. Sincronizando todo el CSV...")
            df_filtrado = df.copy()
            
    except Exception as e:
        print(f"Aviso: No se pudo verificar el último registro en Supabase ({e}). Se procesará todo el CSV.")
        df_filtrado = df.copy()

    if df_filtrado.empty:
        print("La base de datos ya está 100% al día. No hay nuevos registros para subir.")
        return

    df_filtrado['fecha_hora'] = df_filtrado['dt'].dt.strftime('%Y-%m-%d %H:%M:%S')

    records = []
    for _, row in df_filtrado.iterrows():
        record = {
            'estacion_id': ESTACION_ID,
            'fecha_hora': row['fecha_hora']
        }
        
        for csv_col, db_col in col_mapping_real.items():
            val = clean_val(row[csv_col])
            if val is not None:
                record[db_col] = val

        records.append(record)

    print(f"Subiendo {len(records)} registro(s) nuevo(s) a Supabase...")

    # Cargar en lotes de 100 mediante upsert
    chunk_size = 100
    for i in range(0, len(records), chunk_size):
        chunk = records[i:i + chunk_size]
        supabase.table("mediciones").upsert(
            chunk, 
            on_conflict="estacion_id,fecha_hora"
        ).execute()

    print("¡Sincronización finalizada exitosamente!")

if __name__ == "__main__":
    sync()
