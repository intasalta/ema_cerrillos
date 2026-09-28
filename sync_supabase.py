import os
import pandas as pd
from supabase import create_client, Client

# 1. Configurar conexión a Supabase desde variables de entorno
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Faltan las credenciales SUPABASE_URL o SUPABASE_KEY en las variables de entorno.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ID de la estación configurado en la tabla 'estaciones'
ESTACION_ID = "ema_cerrillos"

# 2. Mapeo de columnas del CSV a los nombres de la base de datos
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
    'Sens Term Wind': 'sens_term_wind',
    'Índice Calor': 'indice_calor',
    'Presión (hPa)': 'presion',
    'Lluvia (mm)': 'lluvia',
    'Int Lluvia': 'int_lluvia',
    'Heat D-D': 'heat_dd',
    'Cool D-D': 'cool_dd',
    'Temp Int': 'temp_int',
    'Humedad Int': 'humedad_int',
    'Punto Rocío Int': 'punto_rocio_int',
    'Heat Int': 'heat_int',
    'EMC Int': 'emc_int',
    'Densidad Aire Int': 'densidad_aire_int',
    'Muestras Vent': 'muestras_vent',
    'Tx Vent': 'tx_vent',
    'Recepción ISS': 'recepcion_iss',
    'Intervalo Arc': 'intervalo_arc'
}

def sync():
    csv_file = 'downld08.csv'
    if not os.path.exists(csv_file):
        print(f"El archivo {csv_file} no existe.")
        return

    # Leer el CSV (usando latin1 para evitar fallos de codificación con tildes)
    df = pd.read_csv(csv_file, encoding='latin1')

    # Convertir Fecha (DD/MM/YY) y Hora (HH:MM) a formato ISO Timestamp
    # Asume zona horaria de Argentina (-03:00)
    df['fecha_hora'] = pd.to_datetime(
        df['Fecha'] + ' ' + df['Hora'], 
        format='%d/%m/%y %H:%M',
        errors='coerce'
    ).dt.strftime('%Y-%m-%dT%H:%M:%S-03:00')

    # Descartar filas con fechas inválidas
    df = df.dropna(subset=['fecha_hora'])

    records = []
    for _, row in df.iterrows():
        record = {
            'estacion_id': ESTACION_ID,
            'fecha_hora': row['fecha_hora']
        }
        
        for csv_col, db_col in COLUMN_MAP.items():
            if csv_col in row and pd.notna(row[csv_col]):
                val = row[csv_col]
                # Reemplazar representaciones de texto sin viento ("---") por None
                if str(val).strip() == '---':
                    val = None
                record[db_col] = val

        records.append(record)

    if not records:
        print("No hay registros para procesar.")
        return

    print(f"Enviando {len(records)} registros a Supabase...")

    # Cargar en bloques de 100 registros para optimizar la red
    chunk_size = 100
    for i in range(0, len(records), chunk_size):
        chunk = records[i:i + chunk_size]
        # execute upsert utilizando la restricción UNIQUE (estacion_id, fecha_hora)
        supabase.table("mediciones").upsert(
            chunk, 
            on_conflict="estacion_id,fecha_hora"
        ).execute()

    print("¡Sincronización completada con éxito!")

if __name__ == "__main__":
    sync()
