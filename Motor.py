
import openpyxl
import numpy as np
import pandas as pd
from fpdf import FPDF
import os
import streamlit as st
import io
import zipfile







# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="AgroReport Pro", layout="centered", page_icon="🌾")

# --- FUNCIONES DE APOYO ---
def convertir_a_segundos(tiempo_str):
    try:
        minutos, segundos = map(int, str(tiempo_str).split(':'))
        return (minutos * 60) + segundos
    except: return 0

def formatear_tiempo(segundos_totales):
    horas = segundos_totales // 3600
    minutos = (segundos_totales % 3600) // 60
    segundos = segundos_totales % 60
    return f"{int(horas):02d}:{int(minutos):02d}:{int(segundos):02d}"

# --- CLASE PDF ---
class PDF_Decorado(FPDF):
    def dibujar_logo_drone(self, x, y):
        self.set_draw_color(0, 102, 204)
        self.set_line_width(0.5)
        self.line(x, y, x + 10, y + 10)
        self.line(x + 10, y, x, y + 10)
        self.set_fill_color(0, 102, 204)
        self.circle(x+3.5, y+3.5, 3, 'F')

    def header(self):
        self.set_fill_color(0, 51, 102)
        self.rect(0, 0, 210, 40, 'F')
        self.dibujar_logo_drone(170, 12)
        self.set_text_color(255, 255, 255)
        self.set_font('Arial', 'B', 20)
        self.cell(0, 15, 'AGROFLY', 0, 1, 'L')
        self.ln(20)

    def footer(self):
        self.set_y(-20)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

# --- GENERADOR DE ZIP CON PDFs ---
def generar_zip_reportes(df_subido):
    # Procesamiento de datos
    df = df_subido.copy()
    df.columns = df.columns.astype(str).str.strip()
    df['fecha_simple'] = df['Flight time'].astype(str).str[:10]
    df['area_num'] = pd.to_numeric(df['Sprayed area'], errors='coerce').fillna(0)
    df['segundos_vuelo'] = df['Flight duration(min:sec)'].apply(convertir_a_segundos)
    df['insumo_num'] = pd.to_numeric(df['Total Amount(L/Kg)'], errors='coerce').fillna(0)

    informe = df.groupby(['fecha_simple', 'Location']).agg({
        'area_num': 'sum', 'insumo_num': 'sum', 'segundos_vuelo': 'sum', 'Flight time': 'count'
    }).reset_index()

    def corregir(row):
        mins = row['segundos_vuelo'] / 60
        ha = row['area_num']
        return ha / 10 if (mins > 0 and 1 < (ha/mins) < 10) else ha
    
    informe['Area Final'] = informe.apply(corregir, axis=1)

    # Creamos un archivo ZIP en memoria (RAM)
    buffer_zip = io.BytesIO()
    with zipfile.ZipFile(buffer_zip, "w") as zf:
        for i, fila in informe.iterrows():
            pdf = PDF_Decorado()
            pdf.add_page()
            
            pdf.set_text_color(0, 51, 102)
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, f"ORDEN DE TRABAJO: {fila['fecha_simple']}", "B", 1, 'L')
            pdf.ln(10)

            def agregar_fila_dato(label, valor, unidad=""):
                pdf.set_fill_color(240, 245, 255)
                pdf.set_font('Arial', 'B', 11)
                pdf.cell(60, 12, f" {label}", 1, 0, 'L', fill=True)
                pdf.set_font('Arial', '', 11)
                pdf.cell(0, 12, f" {valor} {unidad}", 1, 1, 'L')

            agregar_fila_dato("UBICACIÓN", fila['Location'])
            agregar_fila_dato("SUPERFICIE TOTAL", f"{fila['Area Final']:.2f}", "Hectáreas")
            agregar_fila_dato("INSUMO APLICADO", f"{fila['insumo_num']:.2f}", "L/Kg")
            agregar_fila_dato("TIEMPO DE OPERACIÓN", formatear_tiempo(fila['segundos_vuelo']))
            agregar_fila_dato("CANTIDAD DE VUELOS", int(fila['Flight time']))

            # Generamos el PDF como bytes
            pdf_bytes = pdf.output(dest='S')
            
            # Lo metemos dentro del ZIP
            nombre_pdf = f"Reporte_{fila['fecha_simple']}_{i}.pdf"
            zf.writestr(nombre_pdf, pdf_bytes)

    buffer_zip.seek(0)
    return buffer_zip # Retornamos el ZIP completo

# --- APP PRINCIPAL ---  pdf_bytes = pdf.output(dest='S')
def main():
    st.title("🌾 AgroReport: Procesador de Operaciones")
    st.markdown("Subí el log de tu drone y generá los informes automáticos.")

    uploaded_file = st.file_uploader("Elegí el archivo del drone (.xlsx)", type=['xlsx'])

    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
        
        st.subheader("📊 Vista Previa de Datos")
        st.dataframe(df.head(), use_container_width=True)

        # Generamos el archivo ZIP en memoria
        zip_preparado = generar_zip_reportes(df)


        # --- LÓGICA DE CONTROL DE TAMAÑO ---
        # Calculamos el tamaño en Megabytes
        # len(zip_preparado) nos da los bytes totales
        tamano_mb = len(zip_preparado) / (1024 * 1024)
        limite_maximo = 10  # Límite de 10 MB

        st.markdown("---")


        if tamano_mb <= limite_maximo:
            st.success(f"✅ Reportes procesados ({tamano_mb:.2f} MB). Ya podés descargar el paquete de informes.")
            
            # BOTÓN DE DESCARGA (Solo aparece si es menor al límite)
            st.download_button(
                label="📥 Descargar todos los Reportes (ZIP)",
                data=zip_preparado,
                file_name="Reportes_AgroReport.zip",
                mime="application/zip"
            )
        else:
            # MENSAJE DE ERROR si es muy pesado
            st.error(f"⚠️ El archivo generado es demasiado grande ({tamano_mb:.2f} MB).")
            st.warning(f"El límite permitido es de {limite_maximo} MB. Intentá procesar un Excel con menos filas.")

        
        st.success("✅ Reportes procesados. Ya podés descargar el paquete de informes.")
        
        # BOTÓN DE DESCARGA
        st.download_button(
            label="📥 Descargar todos los Reportes (ZIP)",
            data=zip_preparado,
            file_name="Reportes_AgroReport.zip",
            mime="application/zip"
        )

if __name__ == "__main__":
    main()
