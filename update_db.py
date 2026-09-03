import json
import os
import re
import sqlite3

TXT_FILE = "downld02.txt"
DB_FILE = "estacion.db"
JSON_FILE = "datos.json"

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
        print(f"ERROR: El archivo {TXT_FILE} no existe.")
        return

    with open(TXT_FILE, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    cursor = conn.cursor()
    records_inserted = 0

    for line in lines:
        line_str = line.strip()
        if (
            not line_str
            or line_str.startswith("---")
            or line_str.startswith("Date")
            or "Temp" in line_str
        ):
            continue

        parts = re.split(r"\s+", line_str)

        if len(parts) >= 2:
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
    print(f"Registros nuevos insertados en SQLite: {records_inserted}")


def export_json(conn):
    """Exporta las últimas 100 mediciones a un archivo JSON para la web."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT date, time, temp_out, out_hum, wind_speed, bar, rain FROM mediciones ORDER BY id DESC LIMIT 100"
    )
    rows = cursor.fetchall()

    # Revertir para mantener orden cronológico
    rows.reverse()

    data = [
        {
            "date": r[0],
            "time": r[1],
            "temp_out": float(r[2]) if r[2] else None,
            "out_hum": float(r[3]) if r[3] else None,
            "wind_speed": float(r[4]) if r[4] else None,
            "bar": float(r[5]) if r[5] else None,
            "rain": float(r[6]) if r[6] else None,
        }
        for r in rows
    ]

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Exportado correctamente a {JSON_FILE}")


if __name__ == "__main__":
    connection = sqlite3.connect(DB_FILE)
    create_table(connection)
    parse_and_insert(connection)
    export_json(connection)
    connection.close()
