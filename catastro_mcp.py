"""
Servidor MCP para consultar datos catastrales de España
Proporciona acceso a los servicios web de la Dirección General del Catastro
"""

from fastmcp import FastMCP
import httpx
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any, List
import logging

# Configurar logging
import os
log_file = os.path.join(os.path.dirname(__file__), 'catastro_mcp.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Inicializar servidor MCP
mcp = FastMCP("Catastro España")

# URLs de los servicios del Catastro
BASE_URL = "http://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero"
CALLEJERO_URL = f"{BASE_URL}/COVCCallejero.svc/rest"
CODIGOS_URL = f"{BASE_URL}/COVCCallejeroCodigos.svc/rest"


def buscar_numero_cercano(numero_buscado: int, numeros_disponibles: List[int]) -> Optional[int]:
    """
    Encuentra el número más cercano al buscado
    """
    if not numeros_disponibles:
        return None
    
    # Ordenar números
    numeros_ordenados = sorted(numeros_disponibles)
    
    # Buscar el más cercano
    mejor = numeros_ordenados[0]
    diferencia_minima = abs(numero_buscado - mejor)
    
    for num in numeros_ordenados:
        diferencia = abs(numero_buscado - num)
        if diferencia < diferencia_minima:
            diferencia_minima = diferencia
            mejor = num
    
    return mejor


def parse_xml_error(root: ET.Element) -> Optional[Dict[str, Any]]:
    """Extrae información de error del XML"""
    error = root.find(".//lerr/err")
    if error is not None:
        cod = error.find("cod")
        des = error.find("des")
        return {
            "error": True,
            "codigo": cod.text if cod is not None else "UNKNOWN",
            "descripcion": des.text if des is not None else "Error desconocido"
        }
    return None


def parse_inmueble_completo(bi: ET.Element) -> Dict[str, Any]:
    """Parsea un inmueble completo con todos sus datos"""
    inmueble = {}
    
    # Referencia catastral
    rc = bi.find(".//rc")
    if rc is not None:
        pc1 = rc.find("pc1")
        pc2 = rc.find("pc2")
        car = rc.find("car")
        cc1 = rc.find("cc1")
        cc2 = rc.find("cc2")
        
        ref_completa = ""
        if pc1 is not None and pc2 is not None:
            ref_completa = (pc1.text or "") + (pc2.text or "")
            if car is not None and car.text:
                ref_completa += car.text
            if cc1 is not None and cc1.text:
                ref_completa += cc1.text
            if cc2 is not None and cc2.text:
                ref_completa += cc2.text
        
        inmueble["referencia_catastral"] = ref_completa
    
    # Tipo de bien
    cn = bi.find(".//cn")
    if cn is not None:
        inmueble["tipo"] = cn.text
    
    # Domicilio tributario
    dt = bi.find(".//dt")
    if dt is not None:
        np = dt.find(".//np")
        nm = dt.find(".//nm")
        nv = dt.find(".//nv")
        tv = dt.find(".//tv")
        pnp = dt.find(".//pnp")
        
        direccion_partes = []
        if tv is not None and tv.text:
            direccion_partes.append(tv.text)
        if nv is not None and nv.text:
            direccion_partes.append(nv.text)
        if pnp is not None and pnp.text:
            direccion_partes.append(pnp.text)
        
        inmueble["direccion"] = " ".join(direccion_partes) if direccion_partes else None
        inmueble["provincia"] = np.text if np is not None else None
        inmueble["municipio"] = nm.text if nm is not None else None
        
        # Localización interna
        bq = dt.find(".//bq")
        es = dt.find(".//es")
        pt = dt.find(".//pt")
        pu = dt.find(".//pu")
        
        if any(x is not None and x.text for x in [bq, es, pt, pu]):
            inmueble["localizacion_interna"] = {
                "bloque": bq.text if bq is not None else None,
                "escalera": es.text if es is not None else None,
                "planta": pt.text if pt is not None else None,
                "puerta": pu.text if pu is not None else None
            }
    
    # Domicilio tributario no estructurado
    ldt = bi.find(".//ldt")
    if ldt is not None and ldt.text:
        inmueble["domicilio_completo"] = ldt.text
    
    # Datos económicos
    debi = bi.find(".//debi")
    if debi is not None:
        luso = debi.find("luso")
        sfc = debi.find("sfc")
        cpt = debi.find("cpt")
        ant = debi.find("ant")
        
        inmueble["uso"] = luso.text if luso is not None else None
        
        # Convertir superficie (puede tener coma como separador decimal)
        if sfc is not None and sfc.text:
            try:
                inmueble["superficie_m2"] = float(sfc.text.replace(',', '.'))
            except ValueError:
                inmueble["superficie_m2"] = None
        
        # Convertir coeficiente de participación (usa coma como separador decimal)
        if cpt is not None and cpt.text:
            try:
                inmueble["coef_participacion"] = float(cpt.text.replace(',', '.'))
            except ValueError:
                inmueble["coef_participacion"] = None
        
        inmueble["antiguedad"] = int(ant.text) if ant is not None and ant.text else None
    
    # Unidades constructivas
    lcons = bi.find(".//lcons")
    if lcons is not None:
        unidades = []
        for cons in lcons.findall(".//cons"):
            unidad = {}
            lcd = cons.find(".//lcd")
            stl = cons.find(".//stl")
            dtip = cons.find(".//dtip")
            
            if lcd is not None:
                unidad["uso"] = lcd.text
            if stl is not None and stl.text:
                try:
                    unidad["superficie_m2"] = float(stl.text.replace(',', '.'))
                except ValueError:
                    unidad["superficie_m2"] = None
            if dtip is not None:
                unidad["tipologia"] = dtip.text
            
            # Localización de la unidad
            loint = cons.find(".//loint")
            if loint is not None:
                bq = loint.find("bq")
                es = loint.find("es")
                pt = loint.find("pt")
                pu = loint.find("pu")
                
                unidad["localizacion"] = {
                    "bloque": bq.text if bq is not None else None,
                    "escalera": es.text if es is not None else None,
                    "planta": pt.text if pt is not None else None,
                    "puerta": pu.text if pu is not None else None
                }
            
            if unidad:
                unidades.append(unidad)
        
        if unidades:
            inmueble["unidades_constructivas"] = unidades
    
    # Subparcelas
    lspr = bi.find(".//lspr")
    if lspr is not None:
        subparcelas = []
        for spr in lspr.findall(".//spr"):
            subparcela = {}
            cspr = spr.find("cspr")
            ccc = spr.find(".//ccc")
            dcc = spr.find(".//dcc")
            ip = spr.find(".//ip")
            ssp = spr.find(".//ssp")
            
            if cspr is not None:
                subparcela["codigo"] = cspr.text
            if ccc is not None:
                subparcela["calificacion"] = ccc.text
            if dcc is not None:
                subparcela["cultivo"] = dcc.text
            if ip is not None:
                subparcela["intensidad_productiva"] = ip.text
            if ssp is not None and ssp.text:
                try:
                    subparcela["superficie_m2"] = float(ssp.text.replace(',', '.'))
                except ValueError:
                    subparcela["superficie_m2"] = None
            
            if subparcela:
                subparcelas.append(subparcela)
        
        if subparcelas:
            inmueble["subparcelas"] = subparcelas
    
    return inmueble


def parse_inmueble_listado(rcdnp: ET.Element) -> Dict[str, Any]:
    """Parsea un inmueble de un listado (versión simplificada)"""
    inmueble = {}
    
    # Referencia catastral
    rc = rcdnp.find(".//rc")
    if rc is not None:
        pc1 = rc.find("pc1")
        pc2 = rc.find("pc2")
        car = rc.find("car")
        
        ref_completa = ""
        if pc1 is not None and pc2 is not None:
            ref_completa = (pc1.text or "") + (pc2.text or "")
            if car is not None and car.text:
                ref_completa += car.text
        
        inmueble["referencia_catastral"] = ref_completa
    
    # Domicilio
    dt = rcdnp.find(".//dt")
    if dt is not None:
        np = dt.find(".//np")
        nm = dt.find(".//nm")
        nv = dt.find(".//nv")
        tv = dt.find(".//tv")
        pnp = dt.find(".//pnp")
        
        direccion_partes = []
        if tv is not None and tv.text:
            direccion_partes.append(tv.text)
        if nv is not None and nv.text:
            direccion_partes.append(nv.text)
        if pnp is not None and pnp.text:
            direccion_partes.append(pnp.text)
        
        inmueble["direccion"] = " ".join(direccion_partes) if direccion_partes else None
        inmueble["provincia"] = np.text if np is not None else None
        inmueble["municipio"] = nm.text if nm is not None else None
        
        # Localización interna
        bq = dt.find(".//bq")
        es = dt.find(".//es")
        pt = dt.find(".//pt")
        pu = dt.find(".//pu")
        
        if any(x is not None and x.text for x in [bq, es, pt, pu]):
            inmueble["localizacion_interna"] = {
                "bloque": bq.text if bq is not None else None,
                "escalera": es.text if es is not None else None,
                "planta": pt.text if pt is not None else None,
                "puerta": pu.text if pu is not None else None
            }
    
    return inmueble


def parse_candidatos(root: ET.Element, tipo: str) -> List[Dict[str, Any]]:
    """Parsea listas de candidatos (provincias, municipios, vías, números)"""
    candidatos = []
    
    if tipo == "provincias":
        for prov in root.findall(".//prov"):
            cpine = prov.find("cpine")
            np = prov.find("np")
            if cpine is not None and np is not None:
                candidatos.append({
                    "codigo_ine": cpine.text,
                    "nombre": np.text
                })
    
    elif tipo == "municipios":
        for muni in root.findall(".//muni"):
            nm = muni.find("nm")
            cmc = muni.find(".//cmc")
            cm = muni.find(".//cm")
            if nm is not None:
                candidato = {"nombre": nm.text}
                if cmc is not None:
                    candidato["codigo_catastro"] = cmc.text
                if cm is not None:
                    candidato["codigo_ine"] = cm.text
                candidatos.append(candidato)
    
    elif tipo == "vias":
        for calle in root.findall(".//calle"):
            tv = calle.find(".//tv")
            nv = calle.find(".//nv")
            cv = calle.find(".//cv")
            if nv is not None:
                candidato = {
                    "nombre": nv.text,
                    "tipo": tv.text if tv is not None else None
                }
                if cv is not None:
                    candidato["codigo"] = cv.text
                candidatos.append(candidato)
    
    elif tipo == "numeros":
        for nump in root.findall(".//nump"):
            pnp = nump.find(".//pnp")
            pc1 = nump.find(".//pc1")
            pc2 = nump.find(".//pc2")
            if pnp is not None:
                candidato = {"numero": pnp.text}
                if pc1 is not None and pc2 is not None:
                    candidato["referencia_catastral"] = (pc1.text or "") + (pc2.text or "")
                candidatos.append(candidato)
    
    return candidatos


@mcp.tool()
def buscar_inmueble_inteligente(
    provincia: str,
    municipio: str,
    nombre_via: str,
    numero: str,
    tipo_via: Optional[str] = None,
    escalera: Optional[str] = None,
    planta: Optional[str] = None,
    puerta: Optional[str] = None
) -> str:
    """
    Búsqueda inteligente de inmuebles. Si el número exacto no existe,
    busca automáticamente el número más cercano disponible.
    
    Esta es la función RECOMENDADA para buscar por dirección.
    
    Args:
        provincia: Nombre de la provincia
        municipio: Nombre del municipio
        nombre_via: Nombre de la vía
        numero: Número buscado
        tipo_via: Tipo de vía (CL, AV, etc.) - opcional pero recomendado
        escalera: Escalera (opcional)
        planta: Planta (opcional)
        puerta: Puerta (opcional)
    
    Returns:
        JSON con los datos del inmueble o el número más cercano encontrado
    """
    import json
    
    try:
        numero_buscado = int(numero)
    except ValueError:
        return json.dumps({
            "error": True,
            "mensaje": f"El número '{numero}' no es válido. Debe ser un número entero."
        }, ensure_ascii=False, indent=2)
    
    logger.info(f"Búsqueda inteligente: {tipo_via} {nombre_via} {numero}, {municipio}, {provincia}")
    
    try:
        # PASO 1: Intentar búsqueda directa
        params = {
            "Provincia": provincia,
            "Municipio": municipio,
            "NombreVia": nombre_via,
            "Numero": str(numero_buscado)
        }
        
        if tipo_via:
            params["TipoVia"] = tipo_via
        if escalera:
            params["Escalera"] = escalera
        if planta:
            params["Planta"] = planta
        if puerta:
            params["Puerta"] = puerta
        
        url = f"{CALLEJERO_URL}/Consulta_DNPLOC"
        logger.info(f"Intento 1: Búsqueda directa con número {numero_buscado}")
        
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
        
        xml_text = response.text
        xml_text = xml_text.replace(' xmlns="http://www.catastro.meh.es/"', '')
        xml_text = xml_text.replace(' xmlns:xsd="http://www.w3.org/2001/XMLSchema"', '')
        xml_text = xml_text.replace(' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"', '')
        
        root = ET.fromstring(xml_text)
        error_info = parse_xml_error(root)
        
        # Si no hay error, devolver resultado
        if not error_info:
            logger.info("Búsqueda directa exitosa")
            
            # Parsear respuesta exitosa
            bico = root.find(".//bico")
            if bico is not None:
                bi = bico.find(".//bi")
                if bi is not None:
                    return json.dumps({
                        "tipo_respuesta": "inmueble_completo",
                        "numero_buscado": numero_buscado,
                        "numero_encontrado": numero_buscado,
                        "coincidencia": "exacta",
                        "inmueble": parse_inmueble_completo(bi)
                    }, ensure_ascii=False, indent=2)
            
            lrcdnp = root.find(".//lrcdnp")
            if lrcdnp is not None:
                inmuebles = []
                for rcdnp in lrcdnp.findall(".//rcdnp"):
                    inmuebles.append(parse_inmueble_listado(rcdnp))
                
                return json.dumps({
                    "tipo_respuesta": "listado_inmuebles",
                    "numero_buscado": numero_buscado,
                    "numero_encontrado": numero_buscado,
                    "coincidencia": "exacta",
                    "total": len(inmuebles),
                    "inmuebles": inmuebles
                }, ensure_ascii=False, indent=2)
        
        # PASO 2: Si falla por número no existe, usar ConsultaNumero para obtener candidatos
        if "NUMERO NO EXISTE" in error_info.get("descripcion", "").upper() or "NÚMERO NO EXISTE" in error_info.get("descripcion", "").upper():
            logger.info(f"Número {numero_buscado} no existe. Usando ConsultaNumero para obtener candidatos...")
            
            # Usar el servicio ConsultaNumero que devuelve números cercanos automáticamente
            consulta_params = {
                "Provincia": provincia,
                "Municipio": municipio,
                "NombreVia": nombre_via,
                "Numero": str(numero_buscado)
            }
            if tipo_via:
                consulta_params["TipoVia"] = tipo_via
            
            consulta_url = f"{CALLEJERO_URL}/ConsultaNumero"
            
            with httpx.Client(timeout=30.0) as client:
                consulta_response = client.get(consulta_url, params=consulta_params)
                consulta_response.raise_for_status()
            
            consulta_xml = consulta_response.text
            consulta_xml = consulta_xml.replace(' xmlns="http://www.catastro.meh.es/"', '')
            consulta_xml = consulta_xml.replace(' xmlns:xsd="http://www.w3.org/2001/XMLSchema"', '')
            consulta_xml = consulta_xml.replace(' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"', '')
            
            consulta_root = ET.fromstring(consulta_xml)
            
            # Extraer números disponibles
            numeros_disponibles = []
            for nump in consulta_root.findall(".//nump"):
                pnp = nump.find(".//pnp")
                pc1 = nump.find(".//pc1")
                pc2 = nump.find(".//pc2")
                
                if pnp is not None and pc1 is not None and pc2 is not None:
                    try:
                        num_val = int(pnp.text) if pnp.text else None
                        if num_val:
                            numeros_disponibles.append({
                                "numero": num_val,
                                "referencia": (pc1.text or "") + (pc2.text or "")
                            })
                    except ValueError:
                        continue
            
            if numeros_disponibles:
                # Ordenar por diferencia con el número buscado
                numeros_disponibles.sort(key=lambda x: abs(x["numero"] - numero_buscado))
                numero_cercano = numeros_disponibles[0]
                
                logger.info(f"Número más cercano encontrado: {numero_cercano['numero']}")
                
                # Buscar datos completos del número más cercano
                params_cercano = {
                    "Provincia": provincia,
                    "Municipio": municipio,
                    "NombreVia": nombre_via,
                    "Numero": str(numero_cercano["numero"])
                }
                if tipo_via:
                    params_cercano["TipoVia"] = tipo_via
                
                with httpx.Client(timeout=30.0) as client:
                    response_cercano = client.get(url, params=params_cercano)
                    response_cercano.raise_for_status()
                
                xml_cercano = response_cercano.text
                xml_cercano = xml_cercano.replace(' xmlns="http://www.catastro.meh.es/"', '')
                xml_cercano = xml_cercano.replace(' xmlns:xsd="http://www.w3.org/2001/XMLSchema"', '')
                xml_cercano = xml_cercano.replace(' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"', '')
                
                root_cercano = ET.fromstring(xml_cercano)
                
                # Parsear resultado
                bico = root_cercano.find(".//bico")
                if bico is not None:
                    bi = bico.find(".//bi")
                    if bi is not None:
                        return json.dumps({
                            "tipo_respuesta": "inmueble_completo",
                            "numero_buscado": numero_buscado,
                            "numero_encontrado": numero_cercano["numero"],
                            "coincidencia": "cercano",
                            "diferencia": abs(numero_buscado - numero_cercano["numero"]),
                            "mensaje": f"El número {numero_buscado} no existe. Se encontró el número más cercano: {numero_cercano['numero']}",
                            "otros_numeros_disponibles": [n["numero"] for n in numeros_disponibles[:5]],
                            "inmueble": parse_inmueble_completo(bi)
                        }, ensure_ascii=False, indent=2)
                
                lrcdnp = root_cercano.find(".//lrcdnp")
                if lrcdnp is not None:
                    inmuebles = []
                    for rcdnp in lrcdnp.findall(".//rcdnp"):
                        inmuebles.append(parse_inmueble_listado(rcdnp))
                    
                    return json.dumps({
                        "tipo_respuesta": "listado_inmuebles",
                        "numero_buscado": numero_buscado,
                        "numero_encontrado": numero_cercano["numero"],
                        "coincidencia": "cercano",
                        "diferencia": abs(numero_buscado - numero_cercano["numero"]),
                        "mensaje": f"El número {numero_buscado} no existe. Se encontró el número más cercano: {numero_cercano['numero']}",
                        "otros_numeros_disponibles": [n["numero"] for n in numeros_disponibles[:5]],
                        "total": len(inmuebles),
                        "inmuebles": inmuebles
                    }, ensure_ascii=False, indent=2)
            
            # Si no se encontraron números cercanos
            return json.dumps({
                "error": True,
                "mensaje": f"No se encontró el número {numero_buscado} ni números cercanos en {tipo_via or 'CL'} {nombre_via}, {municipio}",
                "sugerencia": "Prueba con una búsqueda por referencia catastral o verifica la dirección"
            }, ensure_ascii=False, indent=2)
        
        # Si el error no es de número, devolverlo
        return json.dumps(error_info, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error en búsqueda inteligente: {e}", exc_info=True)
        return json.dumps({
            "error": True,
            "tipo": "error_inesperado",
            "mensaje": str(e)
        }, ensure_ascii=False, indent=2)


@mcp.tool()
def listar_numeros_via(
    provincia: str,
    municipio: str,
    tipo_via: Optional[str] = None,
    nombre_via: Optional[str] = None
) -> str:
    """
    Lista todos los números disponibles en una vía.
    Útil para encontrar qué números existen cuando una búsqueda directa falla.
    
    Args:
        provincia: Nombre de la provincia
        municipio: Nombre del municipio
        tipo_via: Abreviatura del tipo de vía (CL, AV, etc.)
        nombre_via: Nombre de la vía
    
    Returns:
        JSON con lista de números y sus referencias catastrales
    """
    try:
        # Primero buscar la vía
        url = f"{CALLEJERO_URL}/ConsultaVia"
        params = {
            "Provincia": provincia,
            "Municipio": municipio
        }
        
        if tipo_via:
            params["TipoVia"] = tipo_via
        if nombre_via:
            params["NombreVia"] = nombre_via
        
        logger.info(f"Listando vías en {url} con parámetros: {params}")
        
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
        
        # Limpiar namespace
        xml_text = response.text.replace(' xmlns="http://www.catastro.meh.es/"', '')
        xml_text = xml_text.replace(' xmlns:xsd="http://www.w3.org/2001/XMLSchema"', '')
        xml_text = xml_text.replace(' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"', '')
        
        root = ET.fromstring(xml_text)
        
        # Verificar errores
        error_info = parse_xml_error(root)
        if error_info:
            import json
            return json.dumps(error_info, ensure_ascii=False, indent=2)
        
        # Extraer información de vías
        vias = []
        for calle in root.findall(".//calle"):
            cv = calle.find(".//cv")
            tv = calle.find(".//tv")
            nv = calle.find(".//nv")
            
            if cv is not None and nv is not None:
                vias.append({
                    "codigo_via": cv.text,
                    "tipo": tv.text if tv is not None else None,
                    "nombre": nv.text
                })
        
        import json
        return json.dumps({
            "tipo_respuesta": "lista_vias",
            "total": len(vias),
            "vias": vias,
            "sugerencia": "Usa el codigo_via de la vía deseada para buscar inmuebles con más precisión"
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error listando vías: {e}", exc_info=True)
        import json
        return json.dumps({
            "error": True,
            "mensaje": str(e)
        }, ensure_ascii=False, indent=2)


@mcp.tool()
def consulta_datos_catastro(
    provincia: Optional[str] = None,
    municipio: Optional[str] = None,
    tipo_via: Optional[str] = None,
    nombre_via: Optional[str] = None,
    numero: Optional[str] = None,
    bloque: Optional[str] = None,
    escalera: Optional[str] = None,
    planta: Optional[str] = None,
    puerta: Optional[str] = None,
    codigo_provincia: Optional[str] = None,
    codigo_municipio: Optional[str] = None,
    codigo_via: Optional[str] = None,
    referencia_catastral: Optional[str] = None
) -> str:
    """
    Consulta datos catastrales no protegidos de inmuebles en España.
    
    Permite buscar inmuebles por:
    - Denominaciones: provincia, municipio, tipo_via, nombre_via, numero
    - Códigos: codigo_provincia, codigo_municipio, codigo_via, numero
    - Referencia catastral directa
    
    Args:
        provincia: Nombre de la provincia (ej: "Madrid", "Barcelona")
        municipio: Nombre del municipio
        tipo_via: Abreviatura del tipo de vía (CL=Calle, AV=Avenida, PS=Paseo, etc.)
        nombre_via: Nombre de la vía
        numero: Número del inmueble
        bloque: Bloque (opcional)
        escalera: Escalera (opcional)
        planta: Planta (opcional)
        puerta: Puerta (opcional)
        codigo_provincia: Código de provincia (alternativo a provincia)
        codigo_municipio: Código de municipio (alternativo a municipio)
        codigo_via: Código de vía (alternativo a tipo_via + nombre_via)
        referencia_catastral: Referencia catastral completa (14, 18 o 20 caracteres)
    
    Returns:
        JSON con los datos del inmueble o listado de candidatos
    """
    
    try:
        # Si se proporciona referencia catastral, usar ese servicio
        if referencia_catastral:
            params = {"RefCat": referencia_catastral}
            if provincia:
                params["Provincia"] = provincia
            if municipio:
                params["Municipio"] = municipio
            
            url = f"{CALLEJERO_URL}/Consulta_DNPRC"
            
        # Si se proporcionan códigos, usar servicio de códigos
        elif codigo_provincia:
            params = {
                "CodigoProvincia": codigo_provincia,
                "Numero": numero
            }
            if codigo_municipio:
                params["CodigoMunicipio"] = codigo_municipio
            if codigo_via:
                params["CodigoVia"] = codigo_via
            if bloque:
                params["Bloque"] = bloque
            if escalera:
                params["Escalera"] = escalera
            if planta:
                params["Planta"] = planta
            if puerta:
                params["Puerta"] = puerta
            
            url = f"{CODIGOS_URL}/Consulta_DNPLOC_Codigos"
            
        # Si se proporcionan denominaciones
        else:
            if not provincia or not municipio:
                return '{"error": true, "mensaje": "Debe proporcionar provincia y municipio, o usar referencia_catastral"}'
            
            params = {
                "Provincia": provincia,
                "Municipio": municipio
            }
            
            if numero:
                params["Numero"] = numero
            if tipo_via:
                params["TipoVia"] = tipo_via
            if nombre_via:
                params["NombreVia"] = nombre_via
            if bloque:
                params["Bloque"] = bloque
            if escalera:
                params["Escalera"] = escalera
            if planta:
                params["Planta"] = planta
            if puerta:
                params["Puerta"] = puerta
            
            url = f"{CALLEJERO_URL}/Consulta_DNPLOC"
        
        # Realizar petición
        logger.info(f"Consultando {url} con parámetros: {params}")
        
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
        
        # Log de la respuesta XML para depuración
        logger.info(f"Respuesta XML (primeros 1000 caracteres): {response.text[:1000]}")
        
        # Eliminar namespace del XML para facilitar el parsing
        xml_text = response.text
        # Remover el namespace xmlns="http://www.catastro.meh.es/"
        xml_text = xml_text.replace(' xmlns="http://www.catastro.meh.es/"', '')
        xml_text = xml_text.replace(' xmlns:xsd="http://www.w3.org/2001/XMLSchema"', '')
        xml_text = xml_text.replace(' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"', '')
        
        # Parsear XML
        root = ET.fromstring(xml_text)
        
        # Verificar errores
        error_info = parse_xml_error(root)
        if error_info:
            # Buscar candidatos según el tipo de error
            
            if "PROVINCIA NO EXISTE" in error_info["descripcion"].upper():
                candidatos = parse_candidatos(root, "provincias")
                if candidatos:
                    error_info["candidatos_provincias"] = candidatos
            
            elif "MUNICIPIO NO EXISTE" in error_info["descripcion"].upper():
                candidatos = parse_candidatos(root, "municipios")
                if candidatos:
                    error_info["candidatos_municipios"] = candidatos
            
            elif "VIA NO EXISTE" in error_info["descripcion"].upper() or "VÃA NO EXISTE" in error_info["descripcion"].upper():
                candidatos = parse_candidatos(root, "vias")
                if candidatos:
                    error_info["candidatos_vias"] = candidatos
            
            elif "NUMERO NO EXISTE" in error_info["descripcion"].upper() or "NÃšMERO NO EXISTE" in error_info["descripcion"].upper():
                candidatos = parse_candidatos(root, "numeros")
                if candidatos:
                    error_info["candidatos_numeros"] = candidatos
                else:
                    # Si no hay candidatos de números, sugerir buscar sin número
                    error_info["sugerencia"] = "El número especificado no existe. Intenta buscar sin especificar el número para ver qué números hay disponibles en esa vía."
            
            import json
            return json.dumps(error_info, ensure_ascii=False, indent=2)
        
        # Parsear respuesta exitosa
        resultado = {}
        
        # Verificar si es un inmueble completo (con datos económicos)
        bico = root.find(".//bico")
        if bico is not None:
            bi = bico.find(".//bi")
            if bi is not None:
                resultado["tipo_respuesta"] = "inmueble_completo"
                resultado["inmueble"] = parse_inmueble_completo(bi)
        
        # Verificar si es un listado de inmuebles
        else:
            lrcdnp = root.find(".//lrcdnp")
            if lrcdnp is not None:
                inmuebles = []
                for rcdnp in lrcdnp.findall(".//rcdnp"):
                    inmuebles.append(parse_inmueble_listado(rcdnp))
                
                resultado["tipo_respuesta"] = "listado_inmuebles"
                resultado["total"] = len(inmuebles)
                resultado["inmuebles"] = inmuebles
        
        # Si no hay datos
        if not resultado:
            resultado = {
                "error": False,
                "mensaje": "No se encontraron resultados para los parámetros proporcionados"
            }
        
        import json
        return json.dumps(resultado, ensure_ascii=False, indent=2)
        
    except httpx.HTTPError as e:
        logger.error(f"Error HTTP: {e}")
        import json
        return json.dumps({
            "error": True,
            "tipo": "http_error",
            "mensaje": str(e)
        }, ensure_ascii=False, indent=2)
    
    except ET.ParseError as e:
        logger.error(f"Error parseando XML: {e}")
        import json
        return json.dumps({
            "error": True,
            "tipo": "parse_error",
            "mensaje": f"Error parseando respuesta XML: {str(e)}"
        }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        logger.error(f"Error inesperado: {e}", exc_info=True)
        import json
        return json.dumps({
            "error": True,
            "tipo": "error_inesperado",
            "mensaje": str(e)
        }, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # Ejecutar servidor MCP
    mcp.run()
