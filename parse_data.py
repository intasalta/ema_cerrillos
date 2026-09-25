import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ARCHIVOS_A_CONVERTIR = ["downld02.txt", "downld08.txt"]

# Lista completa de las 37 columnas exactas del archivo Davis WeatherLink
COL_NAMES = [
    "Fecha", "Hora", "Temp Ext (°C)", "Temp Máx", "Temp Mín", "Humedad Ext (%)", "Punto Rocío",
    "Vel Vent", "Dir Vent", "Ráfaga Vent", "Vel Máx", "Dir Máx", "Sens Term Wind",
    "Índice Calor", "THW", "THSW", "Presión (hPa)", "Lluvia (mm)", "Int Lluvia",
    "Rad Solar", "Energía Solar", "Rad Solar Máx", "UV", "Dosis UV", "UV Máx",
    "Grados Día H", "Grados Día C", "Temp Int", "Humedad Int", "Punto Rocío Int", "Heat Int",
    "EMC Int", "Densidad Aire Int", "ET", "Muestras Vent", "Tx Vent", "Recepción ISS", "Intervalo Arc"
]

header_fill = PatternFill(start_color="1F4E78", fill_type="solid")
header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
data_font = Font(name="Calibri", size=10)
zebra_fill = PatternFill(start_color="F2F7FA", fill_type="solid")
thin_border = Border(
    left=Side(style='thin', color='D9D9D9'), right=Side(style='thin', color='D9D9D9'),
    top=Side(style='thin', color='D9D9D9'), bottom=Side(style='thin', color='D9D9D9')
)

for file_path in ARCHIVOS_A_CONVERTIR:
    try:
        # Leer el archivo con pandas ignorando las 3 primeras líneas de encabezado desalineadas
        # sep=r'\s+' maneja cualquier cantidad de espacios consecutivos entre columnas
        df = pd.read_csv(
            file_path,
            sep=r'\s+',
            skiprows=3,
            header=None,
            on_bad_lines='skip',
            encoding="utf-8",
            engine="python"
        )
        
        # Asignar nombres de columnas o ajustar si hay diferencia en la cantidad recuperada
        if df.shape[1] == len(COL_NAMES):
            df.columns = COL_NAMES
        elif df.shape[1] > len(COL_NAMES):
            df = df.iloc[:, :len(COL_NAMES)]
            df.columns = COL_NAMES
        else:
            df.columns = COL_NAMES[:df.shape[1]]

    except FileNotFoundError:
        print(f"Archivo no encontrado: {file_path}")
        continue
    except Exception as e:
        print(f"Error al procesar {file_path}: {e}")
        continue

    base_name = file_path.rsplit('.', 1)[0]
    
    # Exportar CSV ordenado
    df.to_csv(f"{base_name}.csv", index=False, na_rep="")

    # Exportar Excel formateado
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Datos Meteorológicos"

    # Título principal
    total_cols = len(df.columns)
    last_col_letter = get_column_letter(total_cols)
    ws.merge_cells(f"A1:{last_col_letter}1")
    ws["A1"] = f"Reporte Estación Meteorológica - {base_name}"
    ws["A1"].font = Font(name="Calibri", size=14, bold=True, color="1F4E78")

    # Encabezados en la Fila 3
    for col_idx, col_name in enumerate(df.columns, 1):
        cell = ws.cell(row=3, column=col_idx, value=col_name)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Filas de datos
    for r_idx, row in df.iterrows():
        row_num = r_idx + 4
        fill = zebra_fill if r_idx % 2 == 1 else PatternFill(fill_type=None)
        for c_idx, val in enumerate(row, 1):
            cell = ws.cell(row=row_num, column=c_idx)
            val_str = str(val).strip() if pd.notna(val) else ""
            
            if val_str == "---" or val_str == "":
                cell.value = ""
            else:
                try:
                    num_val = float(val_str)
                    cell.value = num_val
                    cell.number_format = "0.0" if "." in val_str else "0"
                except (ValueError, TypeError):
                    cell.value = val_str
            
            cell.font = data_font
            if fill.fill_type: 
                cell.fill = fill
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center", vertical="center")

    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = 13

    ws.freeze_panes = "A4"
    wb.save(f"{base_name}.xlsx")
    print(f"Procesado correctamente: {file_path} -> {base_name}.csv y {base_name}.xlsx")
