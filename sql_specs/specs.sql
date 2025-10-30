CREATE TABLE "Dispositivos"(
  serial VARCHAR NOT NULL,
  "DTI" INTEGER,
  user VARCHAR,
  "MAC" VARCHAR,
  model VARCHAR,
  processor VARCHAR,
  "GPU" VARCHAR,
  "RAM" INTEGER,
  disk VARCHAR,
  license_status BOOLEAN,
  ip VARCHAR,
  activo BOOLEAN,
  PRIMARY KEY(serial)
);


CREATE TABLE activo(
  "Dispositivos_serial" VARCHAR NOT NULL,
  "powerOn" BOOLEAN,
  date DATETIME,
  CONSTRAINT serial_activo
    FOREIGN KEY ("Dispositivos_serial") REFERENCES "Dispositivos" (serial)
);


CREATE TABLE almacenamiento(
  "Dispositivos_serial" VARCHAR NOT NULL,
  nombre VARCHAR,
  capacidad INTEGER,
  tipo VARCHAR,
  actual BOOLEAN,
  id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
  fecha_instalacion DATETIME,
  CONSTRAINT serial_almacenamiento
    FOREIGN KEY ("Dispositivos_serial") REFERENCES "Dispositivos" (serial)
);


CREATE TABLE aplicaciones(
  "Dispositivos_serial" VARCHAR NOT NULL,
  name VARCHAR,
  version VARCHAR,
  publisher VARCHAR,
  id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
  CONSTRAINT "serial_Dispositivos_serial"
    FOREIGN KEY ("Dispositivos_serial") REFERENCES "Dispositivos" (serial)
);


CREATE TABLE informacion_diagnostico(
  "Dispositivos_serial" VARCHAR NOT NULL,
  json_diagnostico TEXT,
  "reporteDirectX" TEXT,
  fecha DATETIME,
  id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
  CONSTRAINT serial_informacion_diagnostico
    FOREIGN KEY ("Dispositivos_serial") REFERENCES "Dispositivos" (serial)
);


CREATE TABLE memoria(
  "Dispositivos_serial" VARCHAR NOT NULL,
  modulo VARCHAR,
  fabricante VARCHAR,
  capacidad INTEGER,
  velocidad INTEGER,
  numero_serie VARCHAR,
  actual BOOLEAN,
  id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
  fecha_instalacion DATETIME,
  CONSTRAINT serial_memoria
    FOREIGN KEY ("Dispositivos_serial") REFERENCES "Dispositivos" (serial)
);


CREATE TABLE registro_cambios(
  "Dispositivos_serial" VARCHAR NOT NULL,
  user VARCHAR,
  processor VARCHAR,
  "GPU" VARCHAR,
  "RAM" INTEGER,
  disk VARCHAR,
  license_status BOOLEAN,
  ip VARCHAR,
  date DATETIME,
  id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
  CONSTRAINT "Dispositivos_registro_cambios"
    FOREIGN KEY ("Dispositivos_serial") REFERENCES "Dispositivos" (serial)
);

