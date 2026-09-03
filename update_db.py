import os
import re
import sqlite3

# Nombre exacto de tu archivo plano en la raíz del repositorio
TXT_FILE = "downld02.txt"
DB_FILE = "estacion.db"

# Lista de columnas esperadas
COLUMNS = [
    "date",
    "time",
    "temp_out",
    "hi_temp",
    "low_temp",
    "out_hum",
    "dew_pt",
    "wind_speed",
    "wind_dir",
    "wind_run",
    "hi_speed",
    "hi_dir",
    "wind_chill",
    "heat_index",
    "thw_index",
    "thsw_index",
    "bar",
    "rain",
    "rain_rate",
    "solar_rad",
    "solar_energy",
    "hi_solar_rad",
    "heat_dd",
    "cool_dd",
    "in_temp",
    "in_hum",
    "in_dew",
    "in_heat",
    "in_emc",
    "in_air_density",
    "wind_samp",
    "wind_tx",
    "iss_recept",
    "arc_int",
]


def create_table(conn):
    cursor = conn.cursor()
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS mediciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {", ".join([f"{col} TEXT" for col in COLUMNS])},
            UNIQUE(date, time)
        )
    """
    )
    conn.commit()


def clean_value(val):
    val = val.strip()
    return None if val == "---" or val == "" else val


def parse_and_insert(conn):
    if not os.path.exists(TXT_FILE):
        print(f"ERROR: El archivo {TXT_FILE} no existe en la ruta actual.")
        return

    with open(TXT_FILE, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    cursor = conn.cursor()
    records_inserted = 0

    for line in lines:
        line_str = line.strip()

        # Ignorar líneas vacías, divisores de guiones o encabezados
        if (
            not line_str
            or line_str.startswith("---")
            or line_str.startswith("Date")
            or "Temp" in line_str
        ):
            continue

        # Separa por cualquier cantidad de espacios o tabulaciones
        parts = re.split(r"\s+", line_str)

        # Si la línea tiene al menos fecha y hora
        if len(parts) >= 2:
            # Rellenar con None si la línea tiene menos columnas de las esperadas
            row_data = [clean_value(p) for p in parts[: len(COLUMNS)]]
            if len(row_data) < len(COLUMNS):
                row_data.extend([None] * (len(COLUMNS) - len(row_data)))

            placeholders = ", ".join(["?"] * len(COLUMNS))
            col_names = ", ".join(COLUMNS)
            query = f"INSERT OR IGNORE INTO mediciones ({col_names}) VALUES ({placeholders})"

            cursor.execute(query, row_data)
            if cursor.rowcount > 0:
                records_inserted += 1

    conn.commit()
    print(
        f"Proceso completado con éxito. Registros nuevos insertados: {records_inserted}"
    )


if __name__ == "__main__":
    connection = sqlite3.connect(DB_FILE)
    create_table(connection)
    parse_and_insert(connection)
    connection.close()
