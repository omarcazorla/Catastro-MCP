# Servidor MCP Catastro España

Servidor MCP (Model Context Protocol) para consultar datos catastrales de la Dirección General del Catastro de España directamente desde Claude Desktop.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## 🚀 Qué es esto

Un servidor MCP que permite a Claude consultar datos catastrales de inmuebles en España de forma natural. Solo tienes que preguntarle a Claude sobre cualquier inmueble y él buscará automáticamente la información en el Catastro.

**Ejemplo:** "Busca el inmueble con referencia catastral 7952405DF1875B" y Claude te devolverá todos los datos: dirección, superficie, antigüedad, uso, etc.

## 💻 Instalación

### Requisitos previos
- Python 3.8 o superior
- Claude Desktop
- macOS, Windows o Linux

### Paso 1: Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/Catastro-MCP.git
cd Catastro-MCP
```

### Paso 2: Crear entorno virtual (recomendado)

**En macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**En Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### Paso 3: Instalar dependencias

```bash
pip install -r requirements.txt
```

O manualmente:
```bash
pip install fastmcp httpx
```

### Paso 4: Configurar Claude Desktop

Edita el archivo de configuración de Claude Desktop:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

**Linux:** `~/.config/Claude/claude_desktop_config.json`

Añade esta configuración (ajusta la ruta a tu instalación):

```json
{
  "mcpServers": {
    "catastro": {
      "command": "/ruta/completa/al/venv/bin/python",
      "args": ["/ruta/completa/a/catastro_mcp.py"]
    }
  }
}
```

**Ejemplo en macOS:**
```json
{
  "mcpServers": {
    "catastro": {
      "command": "/Users/omar/Documents/GitHub/Catastro-MCP/venv/bin/python",
      "args": ["/Users/omar/Documents/GitHub/Catastro-MCP/catastro_mcp.py"]
    }
  }
}
```

### Paso 5: Reiniciar Claude Desktop

Cierra completamente Claude Desktop (Cmd+Q en macOS) y vuélvelo a abrir.

## 💁 Cómo usar

### 1. Búsqueda por referencia catastral (MÁS RECOMENDADO)

```
Busca el inmueble con referencia catastral 7952405DF1875B
```

Claude buscará automáticamente y te devolverá todos los datos del inmueble.

### 2. Búsqueda por dirección

```
Busca datos del inmueble en CL Mayor 76, Molins de Rei, Barcelona
```

**Nota:** Las búsquedas por dirección dependen de cómo el Catastro tiene registradas las direcciones. Si no encuentra resultados, es mejor usar la referencia catastral.

### 3. Búsqueda con localización interna

```
Busca el piso en CL Mayor 10, escalera A, planta 3, puerta B en Segovia
```

## 🔍 Mejores prácticas

1. **Usa referencias catastrales cuando sea posible** - Son más fiables y precisas
2. **Especifica provincia y municipio** - Mejora la precisión de las búsquedas
3. **Usa abreviaturas oficiales** para tipos de vía (CL, AV, PS, etc.)

## 📋 Ejemplos reales probados

```
# Funciona perfecto ✅
Busca el inmueble con referencia catastral 7952405DF1875B

# Devuelve múltiples inmuebles de la misma finca ✅
Busca inmuebles con referencia catastral 9134308DF2893C

# Búsqueda por dirección (puede fallar según el Catastro) ⚠️
Busca el inmueble en CL BALMES 203, Barcelona
```

## Tipos de vía más comunes

| Código | Descripción |
|--------|-------------|
| CL | Calle |
| AV | Avenida |
| PS | Paseo |
| PZ | Plaza |
| CM | Camino |
| CR | Carretera |
| TR | Travesía |
| UR | Urbanización |
| PJ | Pasaje |
| GL | Glorieta |

Ver lista completa en el documento oficial del Catastro (Anexo II).

## 📦 Respuestas del servidor

### Inmueble completo

Cuando se encuentra un único inmueble, devuelve:

```json
{
  "tipo_respuesta": "inmueble_completo",
  "inmueble": {
    "referencia_catastral": "2749704YJ0624N0001DI",
    "tipo": "UR",
    "direccion": "CL Alcalá 45",
    "provincia": "Madrid",
    "municipio": "Madrid",
    "uso": "Residencial",
    "superficie_m2": 85.5,
    "coef_participacion": 0.054,
    "antiguedad": 1975,
    "localizacion_interna": {
      "escalera": "A",
      "planta": "3",
      "puerta": "B"
    },
    "unidades_constructivas": [
      {
        "uso": "Vivienda",
        "superficie_m2": 85.5,
        "tipologia": "Piso"
      }
    ]
  }
}
```

### Listado de inmuebles

Cuando hay múltiples coincidencias:

```json
{
  "tipo_respuesta": "listado_inmuebles",
  "total": 3,
  "inmuebles": [
    {
      "referencia_catastral": "2749704YJ0624N0001DI",
      "direccion": "CL Alcalá 45",
      "provincia": "Madrid",
      "municipio": "Madrid",
      "localizacion_interna": {
        "escalera": "A",
        "planta": "1",
        "puerta": "A"
      }
    }
  ]
}
```

### Errores con candidatos

Cuando no se encuentra un parámetro, devuelve sugerencias:

```json
{
  "error": true,
  "codigo": "12",
  "descripcion": "LA PROVINCIA NO EXISTE",
  "candidatos_provincias": [
    {
      "codigo_ine": "28",
      "nombre": "Madrid"
    },
    {
      "codigo_ine": "08",
      "nombre": "Barcelona"
    }
  ]
}
```

## ✨ Características

- ✅ Búsqueda por **referencia catastral** (más fiable)
- ✅ Búsqueda por **denominaciones** (provincia, municipio, vía, número)
- ✅ Búsqueda por **códigos oficiales** (DGC e INE)
- ✅ Localización interna (bloque, escalera, planta, puerta)
- ✅ Datos completos del inmueble (uso, superficie, antigüedad, etc.)
- ✅ Unidades constructivas detalladas
- ✅ Subparcelas (para inmuebles rústicos)
- ✅ Manejo inteligente de errores con sugerencias
- ✅ Respuestas en JSON limpio y estructurado
- ✅ Parsing correcto de números decimales europeos (comas)
- ✅ Logging completo para depuración

## Datos disponibles

### Para inmuebles urbanos:
- Referencia catastral
- Dirección completa
- Uso (Residencial, Comercial, etc.)
- Superficie construida
- Coeficiente de participación
- Antigüedad
- Unidades constructivas (viviendas, locales, trasteros, etc.)

### Para inmuebles rústicos:
- Referencia catastral
- Localización (polígono, parcela)
- Subparcelas con cultivos
- Superficies
- Intensidad productiva

## ⚠️ Limitaciones

- Solo datos **no protegidos** (no incluye titularidad ni valor catastral)
- Las búsquedas por dirección dependen de cómo el Catastro tiene registradas las direcciones
  - **Recomendación:** Usa referencias catastrales siempre que sea posible
- Requiere conexión a Internet
- Depende de la disponibilidad del servicio del Catastro
- Los servicios del Catastro pueden tener límites de uso

## 🐛 Depuración

Si algo no funciona, revisa el archivo de log:

```bash
tail -f /ruta/a/Catastro-MCP/catastro_mcp.log
```

Este archivo contiene:
- Todas las peticiones realizadas al Catastro
- Respuestas XML completas (primeros 1000 caracteres)
- Errores detallados con stack traces

## 🔗 Enlaces útiles

- [Documentación oficial de los servicios web del Catastro](https://www.catastro.hacienda.gob.es/ws/esquemas.htm)
- [Sede electrónica del Catastro](https://www.sedecatastro.gob.es/)

## ⚖️ Licencia y uso de datos

Este proyecto está licenciado bajo la **Licencia MIT** - ver el archivo [LICENSE](LICENSE) para más detalles.

**Autor:** Omar Cazorla

### Importante sobre los datos del Catastro

Los datos proporcionados por este servidor provienen de los **servicios web públicos de la Dirección General del Catastro** y están sujetos a sus condiciones de uso. Este proyecto solo proporciona una interfaz MCP para facilitar el acceso a dichos servicios.

- Los datos del Catastro son de carácter público y gratuito
- Este servidor accede únicamente a datos **no protegidos** (sin titularidad ni valor catastral)
- El uso de los datos debe cumplir con la normativa del Catastro
- Más información: [Condiciones de uso del Catastro](https://www.catastro.hacienda.gob.es/)

**Nota:** Este es un proyecto independiente y no está oficialmente asociado ni respaldado por la Dirección General del Catastro.
