import os.path
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import glob
import pdfplumber
import csv

from unidecode import unidecode

import time

dir_db = "profesorado.db"
path_combined = "profesorado.csv"


def format_time(seconds):
    if seconds >= 60:
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{int(minutes)}\'" if seconds == 0 else f"{int(minutes)}\' {int(seconds)}\""
    else:
        return f"{int(seconds)}\""


def pdf_to_csv(pdf_path, csv_path):
    print("> Extrayendo información")

    time_tot = 0

    with pdfplumber.open(pdf_path) as pdf:
        with open(csv_path, mode='w', newline='', encoding='utf-8') as archivo:
            escritor_csv = None
            for i, page in enumerate(pdf.pages):

                time_ini = time.time()
                time_eta = format_time((time_tot / (i + 1)) * (len(pdf.pages) - (i + 1)))
                sys.stdout.write("\r  Leyendo PDF... %d/%d (ETA %s)" % (i + 1, len(pdf.pages), time_eta))

                texto = page.extract_text()
                lineas = texto.split("\n")

                # Identificar CUERPO y ESPECIALIDAD
                cuerpo, especialidad = None, None
                for linea in lineas:
                    if not cuerpo and linea.startswith(("PROFESSORS", "M. DE TALLER", "CATEDRÀTICS")):
                        cuerpo = linea.strip()
                    elif cuerpo and not especialidad:
                        especialidad = " ".join(linea.strip().split(" ")[:-1])
                        break

                # Procesar filas de la tabla
                for linea in lineas:
                    if linea and linea[0].isdigit():
                        partes = linea.split()
                        if len(partes) > 1:
                            numero = partes[0]
                            apellidos_nombre = " ".join(partes[1:-2])
                            apellidos, nombre = apellidos_nombre.split(",")[:2]
                            colectivo = " ".join(partes[-2:])

                            fila = {
                                "AÑO": os.path.basename(pdf_path).split(".")[0],
                                "CUERPO": cuerpo,
                                "ESPECIALIDAD": especialidad,
                                "NÚMERO": numero,
                                "APELLIDOS": apellidos.strip(),
                                "NOMBRE": nombre.strip(),
                                "COLECTIVO": colectivo
                            }

                            # Escribir en el CSV
                            if escritor_csv is None:
                                encabezados = fila.keys()
                                escritor_csv = csv.DictWriter(archivo, fieldnames=encabezados)
                                escritor_csv.writeheader()
                            escritor_csv.writerow(fila)

                time_tot += time.time() - time_ini


def csv_combination():
    # Ruta donde están los archivos CSV
    csv_files = glob.glob('./csv/*.csv')

    # Leer todos los archivos CSV
    df_list = [pd.read_csv(file) for file in csv_files]

    # Concatenar todos los DataFrames en uno solo
    df_combined = pd.concat(df_list)

    # Crear un DataFrame final con los datos agregados
    df_final = df_combined.pivot_table(
        index=['CUERPO', 'ESPECIALIDAD', 'APELLIDOS', 'NOMBRE'],
        columns='AÑO',
        values='NÚMERO',
        aggfunc='first'
    ).reset_index()

    # Ordenar las columnas para que la estructura sea más clara
    cols = ['CUERPO', 'ESPECIALIDAD', 'APELLIDOS', 'NOMBRE']
    years = sorted(set(df_combined['AÑO']))
    columns_order = cols + years
    df_final = df_final[columns_order]

    for col in ['APELLIDOS', 'NOMBRE']:
        df_final[col] = df_final[col].apply(unidecode)

    # Guardar el resultado en un nuevo archivo CSV
    df_final.to_csv(path_combined, index=False)

    print(f"Fusión completada y archivo guardado como {path_combined}")


def plot_evolution_by_specialty(csv_file, specialty):
    # Leer el archivo CSV
    df = pd.read_csv(csv_file)

    # Filtrar por la especialidad deseada
    df_specialty = df[df['ESPECIALIDAD'] == specialty]

    # Verificar si hay datos para la especialidad seleccionada
    if df_specialty.empty:
        print(f"No se encontraron datos para la especialidad {specialty}.")
        return

    # Transponer los datos para el gráfico
    df_plot = df_specialty.set_index(['CUERPO', 'APELLIDOS', 'NOMBRE']).T

    # Graficar
    plt.figure(figsize=(6, 3), dpi=60)
    for person in df_plot.columns:
        plt.plot(df_plot.index, df_plot[person], marker='o', label=f'{person}')

    plt.title(f'Evolución en la especialidad {specialty}')
    plt.xlabel('Año')
    plt.ylabel('Número')
    plt.legend(title='Personas', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def plot_evolution_by_person(df_row):
    # Extraer los datos para el gráfico
    years = list(df_row.columns.values)[4:]
    values = [df_row.iloc[0][year] for year in years]

    # Graficar
    plt.figure(figsize=(10, 6))
    plt.stem(years, values, label=f'{df_row.iloc[0]["APELLIDOS"]}, {df_row.iloc[0]["NOMBRE"]}')

    plt.title(f'Evolución de {df_row.iloc[0]["APELLIDOS"]}, {df_row.iloc[0]["NOMBRE"]} ({df_row.iloc[0]["ESPECIALIDAD"]})')
    plt.xlabel('Año')
    plt.ylabel('Número')
    plt.ylim(0, max(0, np.nanmax(values)) + 10)
    plt.grid(True)
    plt.show()


def update_list():
    pdf_files = glob.glob('./pdf/*.pdf')
    print(f"Se ha encontrado 1 archivo CSV" if len(pdf_files) == 1 else f"Se han encontrado {len(pdf_files)} archivos PDF")

    csv_files = glob.glob('./csv/*.csv')
    print(f"Se ha encontrado 1 archivo CSV" if len(csv_files) == 1 else f"Se han encontrado {len(csv_files)} archivos CSV")

    action = None
    while action not in range(1, 4):
        print("Operaciones:")
        print(" 1. Añadir archivos CSV ausentes")
        print(" 2. Recargar todos los CSV")
        print(" 3. Cancelar")
        action = input("Introduzca número (1... 3) > ")

        if action == "1":
            for pdf_file in pdf_files:
                if not os.path.splitext(os.path.basename(pdf_file))[0] in [os.path.splitext(os.path.basename(x))[0] for x in csv_files]:
                    print(f"\nAnalizando archivo {pdf_file}...")
                    csv_path = "./csv/" + os.path.splitext(os.path.basename(pdf_file))[0] + ".csv"
                    pdf_to_csv(pdf_file, csv_path)
            csv_combination()
            print("\nOperación finalizada")

        elif action == "2":
            for csv_file in csv_files:
                os.remove(csv_file)
            for pdf_file in pdf_files:
                print(f"\nAnalizando archivo {pdf_file}...")
                csv_path = "./csv/" + os.path.splitext(os.path.basename(pdf_file))[0] + ".csv"
                pdf_to_csv(pdf_file, csv_path)
            csv_combination()
            print("\nOperación finalizada")

        elif action == "3":
            print("\nOperación cancelada")
            return
        else:
            print("Comando no reconocido")


def find_people():
    if not os.path.isfile(path_combined):
        print("No existen registros. Actualice las listas antes de usar esta operación.")
        return

    fname = unidecode(input("Introduzca nombre > "))
    sname = unidecode(input("Introduzca apellidos > "))

    df = pd.read_csv(path_combined)

    df_person = df[(df['NOMBRE'].str.contains(fname, na=False)) & (df['APELLIDOS'].str.contains(sname, na=False))]

    if df_person.empty:
        print(f"No se encontraron datos para {fname} {sname}.")
        print("\nOperación finalizada")
        return

    for i, (_, row) in enumerate(df_person.iterrows()):
        print(f"{i}. {row["ESPECIALIDAD"]}: {row["APELLIDOS"]}, {row["NOMBRE"]}")

    if len(df_person) > 1:
        action = None

        while action is None:
            action = input(f"Escoja uno de los registros > ")

            if action not in [str(x) for x in range(0, len(df_person))]:
                print("Opción no disponible")
                action = None
            else:
                info_person(df_person.iloc[[int(action)]])
    else:
        info_person(df_person.iloc[[0]])


def info_person(p_df):
    print("Datos de la persona seleccionada:")
    print("> NOMBRE:", p_df.iloc[0]["APELLIDOS"], p_df.iloc[0]["NOMBRE"])
    print("> CUERPO:", p_df.iloc[0]["CUERPO"])
    print("> ESPECIALIDAD:", p_df.iloc[0]["ESPECIALIDAD"])

    plot_evolution_by_person(p_df)


def main():
    action = None

    while action != "3":
        print("\nMENÚ PRINCIPAL")
        print(" 1. Actualizar listados CSV")
        print(" 2. Buscar personas")
        print(" 3. Salir")

        action = input("Introduzca número (1... 3) > ")

        if action == "1":
            update_list()
        elif action == "2":
            find_people()
        elif action == "3":
            print("\nFIN DEL PROGRAMA")
        else:
            print("Comando no reconocido")


if __name__ == "__main__":
    main()
