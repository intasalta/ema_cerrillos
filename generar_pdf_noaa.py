#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generar_pdf_noaa.py - Versión Estación Meteorológica Automática INTA EEA Salta - Cerrillos
Convierte el reporte mensual NOAA de Davis Vantage Pro2 (NOAAPRMO.TXT)
en un informe PDF institucional encolumnado y estilizado.
También actualiza el archivo historial 'informes.json'.
"""

import os
import re
import sys
import json
from datetime import datetime

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm

MESES_EN_ES = {
    'JAN': ('01', 'Enero'),
    'FEB': ('02', 'Febrero'),
    'MAR': ('03', 'Marzo'),
    'APR': ('04', 'Abril'),
    'MAY': ('05', 'Mayo'),
    'JUN': ('06', 'Junio'),
    'JUL': ('07', 'Julio'),
    'AUG': ('08', 'Agosto'),
    'SEP': ('09', 'Septiembre'),
    'OCT': ('10', 'Octubre'),
    'NOV': ('11', 'Noviembre'),
    'DEC': ('12', 'Diciembre'),
    'ENE': ('01', 'Enero'),
    'ABR': ('04', 'Abril'),
    'AGO': ('08', 'Agosto'),
    'DIC': ('12', 'Diciembre'),
}


def parse_noaa_txt(file_path):
    """Parsea el archivo NOAAPRMO.TXT de Davis Vantage Pro2 en Cerrillos."""
    with open(file_path, 'r', encoding='latin-1', errors='replace') as f:
        lines = [line.rstrip('\r\n') for line in f]

    if not lines:
        raise ValueError("El archivo está vacío.")

    month_code = 'OCT'
    year_str = '2026'
    station_name = 'INTA EEA Salta — Cerrillos'
    location_desc = 'INTA EEA Salta - Cerrillos, Salta'
    elev_str = '1235 msnm'

    for line in lines[:10]:
        m = re.search(r'SUMMARY\s+for\s+([A-Za-z]+)\.?\s+(\d{4})', line, re.IGNORECASE)
        if m:
            month_code = m.group(1).upper()
            year_str = m.group(2)

    month_num, month_name_es = MESES_EN_ES.get(month_code, ('00', month_code))

    # Buscar separadores de tabla "----"
    sep_indices = [i for i, line in enumerate(lines) if set(line.strip()) == {'-'}]
    
    table_rows = []
    summary_row = None
    extra_stats = []

    if len(sep_indices) >= 2:
        start_data = sep_indices[0] + 1
        end_data = sep_indices[1]

        # Filas diarias
        for i in range(start_data, end_data):
            line = lines[i]
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 10:
                day = parts[0]
                mean_t = parts[1]
                hi_t = parts[2]
                hi_time = parts[3]
                lo_t = parts[4]
                lo_time = parts[5]
                heat_d = parts[6]
                cool_d = parts[7]
                rain = parts[8]
                wind_avg = parts[9]
                wind_hi = parts[10] if len(parts) > 10 else '-'
                wind_time = parts[11] if len(parts) > 11 else '-'
                wind_dir = parts[12] if len(parts) > 12 else '-'
                table_rows.append([
                    day, mean_t, hi_t, hi_time, lo_t, lo_time,
                    heat_d, cool_d, rain, wind_avg, wind_hi, wind_time, wind_dir
                ])

        # Fila resumen
        if len(lines) > end_data + 1:
            line_sum = lines[end_data + 1]
            parts_sum = line_sum.split()
            if len(parts_sum) >= 10:
                summary_row = parts_sum
            
            # Estadísticas complementarias
            for line in lines[end_data + 2:]:
                if line.strip():
                    extra_stats.append(line.strip())

    return {
        'year': year_str,
        'month_num': month_num,
        'month_name': month_name_es,
        'station_name': station_name,
        'location_desc': location_desc,
        'elev': elev_str,
        'rows': table_rows,
        'summary': summary_row,
        'extra_stats': extra_stats,
        'raw_lines': lines
    }


def generar_pdf(data, output_pdf_path):
    """Genera el informe PDF institucional de Cerrillos encolumnado y estilizado en 1 página A4 Landscape."""
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=landscape(A4),
        leftMargin=9 * mm,
        rightMargin=9 * mm,
        topMargin=5 * mm,
        bottomMargin=4 * mm
    )

    styles = getSampleStyleSheet()
    
    # Paleta de colores agroclimática institucional
    C_NAVY = colors.HexColor('#0f2d59')       # Azul marino institucional INTA
    C_BLUE = colors.HexColor('#0284c7')       # Celeste / Sky 600
    C_ZEBRA = colors.HexColor('#f8fafc')      # Fondo fila par
    C_BORDER = colors.HexColor('#cbd5e1')     # Bordes sutiles
    C_DARK = colors.HexColor('#1e293b')       # Texto oscuro

    story = []

    # 1. ENCABEZADO SUPERIOR INSTITUCIONAL
    header_data = [
        [
            Paragraph(
                f"<font size='13' color='#0f2d59'><b>INSTITUTO NACIONAL DE TECNOLOGÍA AGROPECUARIA</b></font><br/>"
                f"<font size='10' color='#0284c7'><b>Estación Davis Vantage Pro2 — {data['station_name']}</b></font><br/>"
                f"<font size='7.5' color='#64748b'>Red Meteorológica Agropecuaria • {data['location_desc']} • Altitud: {data['elev']}</font>",
                styles['Normal']
            ),
            Paragraph(
                f"<div align='right'>"
                f"<font size='12' color='#0f2d59'><b>INFORME CLIMATOLÓGICO MENSUAL</b></font><br/>"
                f"<font size='11' color='#d97706'><b>{data['month_name'].upper()} {data['year']}</b></font><br/>"
                f"<font size='7' color='#64748b'>Generado automáticamente desde registro oficial</font>"
                f"</div>",
                styles['Normal']
            )
        ]
    ]
    t_header = Table(header_data, colWidths=[165 * mm, 112 * mm])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(t_header)
    story.append(HRFlowable(width="100%", thickness=1, color=C_BLUE, spaceBefore=2, spaceAfter=3))

    # 2. TARJETAS KPI RESUMEN RÁPIDO
    s = data['summary'] or []
    mean_temp = f"{s[0]} °C" if len(s) > 0 else "--"
    max_temp = f"{s[1]} °C (Día {s[2]})" if len(s) > 2 else "--"
    min_temp = f"{s[3]} °C (Día {s[4]})" if len(s) > 4 else "--"
    rain_tot = f"{s[7]} mm" if len(s) > 7 else "--"
    wind_max = f"{s[9]} km/h ({s[11]})" if len(s) > 11 else "--"

    kpi_card_style = ParagraphStyle(
        'KPICard',
        parent=styles['Normal'],
        fontSize=7,
        leading=8.5,
        alignment=1,
        textColor=C_DARK
    )

    kpi_table_data = [[
        Paragraph(f"<font color='#64748b' size='6.5'><b>TEMP. MEDIA</b></font><br/><font size='9.5' color='#0f2d59'><b>{mean_temp}</b></font>", kpi_card_style),
        Paragraph(f"<font color='#dc2626' size='6.5'><b>MÁXIMA ABSOLUTA</b></font><br/><font size='9' color='#dc2626'><b>{max_temp}</b></font>", kpi_card_style),
        Paragraph(f"<font color='#2563eb' size='6.5'><b>MÍNIMA ABSOLUTA</b></font><br/><font size='9' color='#2563eb'><b>{min_temp}</b></font>", kpi_card_style),
        Paragraph(f"<font color='#0284c7' size='6.5'><b>LLUVIA TOTAL</b></font><br/><font size='9.5' color='#0284c7'><b>{rain_tot}</b></font>", kpi_card_style),
        Paragraph(f"<font color='#059669' size='6.5'><b>RÁFAGA MÁXIMA</b></font><br/><font size='9' color='#059669'><b>{wind_max}</b></font>", kpi_card_style),
    ]]
    t_kpi = Table(kpi_table_data, colWidths=[55.4 * mm] * 5)
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
        ('BOX', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 2 * mm))

    # 3. TABLA ENCOLUMNADA COMPLETA (NOAA DAILY TABLE)
    headers = [
        ['DÍA', 'TEMP MED\n(°C)', 'T. MÁX\n(°C)', 'HORA\nMÁX', 'T. MÍN\n(°C)', 'HORA\nMÍN',
         'GRADOS DÍA\nCALOR', 'GRADOS DÍA\nFRÍO', 'LLUVIA\n(mm)',
         'VIENTO MED\n(km/h)', 'RÁFAGA\n(km/h)', 'HORA\nRÁF.', 'DIR.\nDOM.']
    ]

    col_widths = [
        12 * mm, # DÍA
        22 * mm, # TEMP MED
        22 * mm, # T. MÁX
        17 * mm, # HORA MÁX
        22 * mm, # T. MÍN
        17 * mm, # HORA MÍN
        25 * mm, # GRADOS CALOR
        25 * mm, # GRADOS FRÍO
        21 * mm, # LLUVIA
        24 * mm, # VIENTO MED
        23 * mm, # RÁFAGA MÁX
        17 * mm, # HORA RÁF
        18 * mm  # DIR DOM
    ]

    table_data = []
    table_data.append(headers[0])

    for r in data['rows']:
        table_data.append(r)

    if data['summary']:
        sum_vals = data['summary']
        if len(sum_vals) >= 12:
            row_sum = [
                'RESUMEN',
                sum_vals[0],
                sum_vals[1],
                f"Día {sum_vals[2]}",
                sum_vals[3],
                f"Día {sum_vals[4]}",
                sum_vals[5],
                sum_vals[6],
                sum_vals[7],
                sum_vals[8],
                sum_vals[9],
                f"Día {sum_vals[10]}",
                sum_vals[11]
            ]
        else:
            row_sum = ['RESUMEN'] + sum_vals
            while len(row_sum) < 13:
                row_sum.append('-')
        table_data.append(row_sum)

    t_style = [
        ('BACKGROUND', (0, 0), (-1, 0), C_NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 6.5),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 1.5),
        ('TOPPADDING', (0, 0), (-1, 0), 1.5),
        
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 6.3),
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 0.6),
        ('TOPPADDING', (0, 1), (-1, -1), 0.6),
        ('GRID', (0, 0), (-1, -1), 0.3, C_BORDER),
    ]

    num_data_rows = len(data['rows'])
    for row_idx in range(1, num_data_rows + 1):
        if row_idx % 2 == 0:
            t_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), C_ZEBRA))
        try:
            rain_val = float(table_data[row_idx][8])
            if rain_val > 0:
                t_style.append(('BACKGROUND', (8, row_idx), (8, row_idx), colors.HexColor('#e0f2fe')))
                t_style.append(('FONTNAME', (8, row_idx), (8, row_idx), 'Helvetica-Bold'))
                t_style.append(('TEXTCOLOR', (8, row_idx), (8, row_idx), colors.HexColor('#0369a1')))
        except (ValueError, IndexError):
            pass

    if data['summary']:
        last_idx = len(table_data) - 1
        t_style.extend([
            ('BACKGROUND', (0, last_idx), (-1, last_idx), colors.HexColor('#0284c7')),
            ('TEXTCOLOR', (0, last_idx), (-1, last_idx), colors.white),
            ('FONTNAME', (0, last_idx), (-1, last_idx), 'Helvetica-Bold'),
            ('FONTSIZE', (0, last_idx), (-1, last_idx), 6.6),
            ('TOPPADDING', (0, last_idx), (-1, last_idx), 1.2),
            ('BOTTOMPADDING', (0, last_idx), (-1, last_idx), 1.2),
        ])

    table_clima = Table(table_data, colWidths=col_widths)
    table_clima.setStyle(TableStyle(t_style))
    story.append(table_clima)

    # 4. ESTADÍSTICAS COMPLEMENTARIAS AL PIE
    story.append(Spacer(1, 1.5 * mm))

    stats_text = " • ".join(data['extra_stats']) if data['extra_stats'] else ""
    stats_text = stats_text.replace("ON", "el día").replace("Days of Rain:", "Días con lluvia:").replace("Method: Integration", "")

    footer_data = [
        [
            Paragraph(
                f"<font size='6.2' color='#475569'><b>Estadísticas bioclimáticas:</b> {stats_text}</font>",
                styles['Normal']
            ),
            Paragraph(
                f"<div align='right'><font size='6.2' color='#64748b'>Estación Davis Vantage Pro2 • {data['location_desc']} • INTA</font></div>",
                styles['Normal']
            )
        ]
    ]
    t_footer = Table(footer_data, colWidths=[200 * mm, 68 * mm])
    t_footer.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(t_footer)

    doc.build(story)
    print(f"[OK] PDF generado con éxito en: {output_pdf_path}")


def actualizar_historial_json(json_path, data, pdf_filename):
    """Actualiza o crea el archivo historial 'informes.json'."""
    informes = []
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                informes = json.load(f)
        except Exception as e:
            print(f"[WARN] Error leyendo {json_path}: {e}. Se creará nuevo.")
            informes = []

    s = data['summary'] or []
    item_nuevo = {
        'anio': int(data['year']),
        'mes': int(data['month_num']),
        'mes_nombre': data['month_name'],
        'archivo': pdf_filename,
        'temp_media': float(s[0]) if len(s) > 0 and s[0].replace('.', '', 1).replace('-', '', 1).isdigit() else None,
        'temp_max': float(s[1]) if len(s) > 1 and s[1].replace('.', '', 1).replace('-', '', 1).isdigit() else None,
        'temp_min': float(s[3]) if len(s) > 3 and s[3].replace('.', '', 1).replace('-', '', 1).isdigit() else None,
        'lluvia_total': float(s[7]) if len(s) > 7 and s[7].replace('.', '', 1).isdigit() else None,
        'rafaga_max': float(s[9]) if len(s) > 9 and s[9].replace('.', '', 1).isdigit() else None,
        'fecha_generacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    existe = False
    for i, it in enumerate(informes):
        if it.get('anio') == item_nuevo['anio'] and it.get('mes') == item_nuevo['mes']:
            informes[i] = item_nuevo
            existe = True
            break
    if not existe:
        informes.append(item_nuevo)

    informes.sort(key=lambda x: (x.get('anio', 0), x.get('mes', 0)), reverse=True)

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(informes, f, indent=2, ensure_ascii=False)
    print(f"[OK] Historial actualizado en: {json_path} ({len(informes)} registros)")


def find_input_file(base_dir):
    candidates = ['NOAAPRMO.TXT', 'NOAAPRMO.txt', 'noaaprmo.txt', 'NOAAPRMO']
    for folder in [base_dir, os.getcwd()]:
        for c in candidates:
            p = os.path.join(folder, c)
            if os.path.exists(p):
                return p
    return None


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = sys.argv[1] if len(sys.argv) > 1 else find_input_file(base_dir)
    
    if not input_file or not os.path.exists(input_file):
        print(f"[ERROR] No se encontró el archivo NOAAPRMO.TXT en {base_dir}")
        sys.exit(1)

    print(f"Procesando {input_file}...")
    data = parse_noaa_txt(input_file)
    print(f"Detectado resumen: Mes {data['month_num']} ({data['month_name']}) - Año {data['year']} | Estación: {data['station_name']}")

    pdf_filename = f"{data['year']}_{data['month_num']}.pdf"
    output_pdf = os.path.join(base_dir, pdf_filename)

    generar_pdf(data, output_pdf)

    json_path = os.path.join(base_dir, 'informes.json')
    actualizar_historial_json(json_path, data, pdf_filename)


if __name__ == '__main__':
    main()
