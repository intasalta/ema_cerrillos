import os
import math
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

# 2. Diccionario Maestro de Mapeo (Cubre todas las estaciones Davis con o sin ET/Radiación)
COLUMN_MAP = {
    'Temp Ext (°C)': 'temp_ext',
    'Temp Máx': 'temp_max',
    'Temp Mín': 'temp_min',
    'Humedad Ext (%)': 'humedad_ext',
    'Punto Rocío': 'punto_rocio',
    'Vel Vent': 'vel_vent',
    'Dir Vent': 'dir_vent',
    'Wind Run': 'wind_run',
    'Ráfaga Vent': 'rafaga_vent',
    'Dir Ráfaga': 'dir_rafaga',
    'Vel Máx': 'vel_max',
    'Dir Máx': 'dir_max',
    'Sens Term Wind': 'sens_term_wind',
    'Índice Calor': 'indice_calor',
    'THW Index': 'thw',
    'THW': 'thw',
    'THSW': 'thsw',
    'Presión (hPa)': 'presion',
    'Lluvia (mm)': 'lluvia',
    'Int Lluvia': 'int_lluvia',
    'Rad Solar': 'rad_solar',
    'Energía Solar': 'energia_solar',
    'Rad Solar Máx': 'rad_solar_max',
    'UV': 'uv',
    'Dosis UV': 'dosis_uv',
    'UV Máx': 'uv_max',
    'Heat D-D': 'heat_dd',
    'Cool D-D': 'cool_dd',
    'Grados Día H': 'grados_dia_h',
    'Grados Día C': 'grados_dia_c',
    'Grados Día F': 'grados_dia_f',
    'Temp Int': 'temp_int',
    'Humedad Int': 'humedad_int',
    'Punto Rocío Int': 'punto_rocio_int',
    'Heat Int': 'heat_int',
    'EMC Int': 'emc_int',
    'Densidad Aire Int': 'densidad_aire_int',
    'ET': 'et',
    'Muestras Vent': 'muestras_vent',
    'Tx Vent': 'tx_vent',
    'Recepción ISS': 'recepcion_iss',
    'Intervalo Arc': 'intervalo_arc'
}

def clean_val(val):
    """Limpia textos sin datos ('---', '---.-') y convierte NaN a None para PostgreSQL."""
    if pd.isna(val):
        return None
    val_str = str(val).strip()
    if val_str in ['---', '---.-', '----', '']:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    return val

def sync():
    # Detecta downld08.csv o downld02.csv según el que exista en el repositorio
    csv_file = 'downld08.csv' if os.path.exists('downld08.csv') else 'downld02.csv'
    if not os.path.exists(csv_file):
        print(f"No se encontró ningún archivo CSV para procesar.")
        return

    print(f"Leyendo datos desde {csv_file}...")
    df = pd.read_csv(csv_file, encoding='latin1')

    # Parsear Fecha y Hora garantizando la zona horaria de Argentina (-03:00)
    df['fecha_hora'] = pd.to_datetime(
        df['Fecha'].astype(str) + ' ' + df['Hora'].astype(str), 
        format='%d/%m/%y %H:%M',
        errors='coerce'
    ).dt.strftime('%Y-%m-%dT%H:%M:%S-03:00')

    # Filtrar registros que no hayan podido parsear la fecha
    df = df.dropna(subset=['fecha_hora'])

    records = []
    for _, row in df.iterrows():
        record = {
            'estacion_id': ESTACION_ID,
            'fecha_hora': row['fecha_hora']
        }
        
        for csv_col, db_col in COLUMN_MAP.items():
            if csv_col in row:
                val = clean_val(row[csv_col])
                if val is not None:
                    record[db_col] = val

        records.append(record)

    if not records:
        print("No hay registros válidos para procesar.")
        return

    print(f"Procesando y volcando {len(records)} registros a Supabase...")

    # Realizar la carga en lotes de 100 registros con UPSERT
    chunk_size = 100
    for i in range(0, len(records), chunk_size):
        chunk = records[i:i + chunk_size]
        supabase.table("mediciones").upsert(
            chunk, 
            on_conflict="estacion_id,fecha_hora"
        ).execute()

    print("¡Sincronización completada con éxito sin campos vacíos!")

if __name__ == "__main__":
    sync()
