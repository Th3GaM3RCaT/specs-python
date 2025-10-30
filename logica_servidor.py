from glob import glob
from json import JSONDecodeError, dump, load, loads
from socket import AF_INET, SO_BROADCAST, SOCK_DGRAM, SOCK_STREAM, SOL_SOCKET, socket
from sys import argv
from threading import Thread

from PySide6.QtWidgets import QApplication
from logica_Hilo import Hilo
from sql_specs import consultas_sql as sql

import socket as sckt
HOST = sckt.gethostbyname(sckt.gethostname())
PORT = 5255

app = QApplication.instance()
if app is None:
    app = QApplication(argv)
    
    
    
# tengo un array de archivos json y tengo que migrarlo a la DB cambiando consultar_informacion y abrir_json para que usen la DB en vez de los archivos
archivos_json = glob("*.json")
clientes = []


def consultar_informacion(conn, addr):
    print(f"conectando por {addr}")
    while True:
        try:
            data = conn.recv(1024)
            if not data:
                print("cerrando consulta")
                break
            try:
                json_data = loads(data)
                if "Name" not in json_data and "MAC Address" not in json_data:
                    raise ValueError("JSON incompleto")
                print("guardando json en archivo")
                with open(
                    f"{json_data('Name')} {json_data('MAC Adress')}",
                    "w",
                    encoding="utf-8",
                ) as f:
                    dump(json_data, f, indent=4)
                    #sql.setDevice(json_data)
            except JSONDecodeError:
                print("JSON inválido")
        except ConnectionResetError:
            break
        except JSONDecodeError:
            print(f"datos inválidos de {addr}")
    print("cerrando conexion")
    conn.close()
    clientes.remove(conn)
    print(f"desconectado: {addr}")


def main():
    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"servidor escuchando en puerto {HOST}: {PORT}")
    while True:
        conn, addr = server_socket.accept()
        clientes.append(conn)
        hilo = Thread(target=consultar_informacion, args=(conn, addr))
        hilo.start()


def anunciar_ip():
    global clientes
    broadcast = socket(AF_INET, SOCK_DGRAM)
    broadcast.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    broadcast.sendto(b"servidor specs", ("255.255.255.255", 37020))


def abrir_json(position=0):
    if archivos_json:
        nombre_archivo = archivos_json[position]
        try:
            # Abre y lee el archivo JSON
            with open(nombre_archivo, "r", encoding="utf-8") as f:
                # Carga el contenido JSON en una estructura de Python
                datos = load(f)
                return datos
        except FileNotFoundError:
            print(f"Error: El archivo {nombre_archivo} no se encontró.")
        except JSONDecodeError:
            print(f"Error: El archivo {nombre_archivo} no es un JSON válido.")



def buscar_dispositivo():
    hilo = Hilo(anunciar_ip)
    hilo.start()
    hilo = Hilo(consultar_informacion)
    hilo.start()



# compilar usando:
# pyinstaller --onedir --noconsole servidor.py --add-data "sql_specs/statement*.sql;sql_specs/statement"