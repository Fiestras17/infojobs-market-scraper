import os
import re
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright
import json

def scrape_total_results():
    print("Iniciando extractor de métricas históricas de InfoJobs...")
    
    # DETECCIÓN DE ENTORNO: ¿Estamos en GitHub Actions o en tu ordenador?
    es_entorno_ci = os.getenv('CI') == 'true'
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            # En la nube será True (invisible), en tu PC será False (visible)
            headless=es_entorno_ci, 
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        
        # Camuflaje nativo
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        url = "https://www.infojobs.net/ofertas-trabajo/data-engineer"
        page.goto(url)
        
        print("Esperando carga de la página y gestionando cookies...")
        # Aumentamos ligeramente la espera para dejar que el desafío invisible pase solo
        page.wait_for_timeout(5000)
        
        # Gestionar banner de cookies para limpiar la pantalla
        try:
            cookie_btn = page.locator('button:has-text("Aceptar"), button:has-text("Consentir"), button:has-text("Aceptar y continuar")')
            if cookie_btn.count() > 0:
                cookie_btn.first.click()
                page.wait_for_timeout(1000)
        except Exception:
            pass
            
        # Quitamos la condición del 'iframe' y verificamos la URL una vez estabilizada la página
        url_actual = page.url.lower()
        if "captcha" in url_actual or "challenge" in url_actual:
            if es_entorno_ci:
                print("CAPTCHA BLOQUEANTE DETECTADO EN LA NUBE. Abortando extracción para no consumir recursos.")
                browser.close()
                return
            else:
                print("=========================================================")
                print("CAPTCHA DETECTADO: Tienes 25 segundos para resolverlo a mano.")
                print("=========================================================")
                page.wait_for_timeout(25000)

        # ... (AQUÍ SIGUE EL RESTO DE TU CÓDIGO EXACTAMENTE IGUAL) ...
            
        # 1. EXTRACTOR DEL TOTAL GLOBAL (h1#main-heading)
        total_ofertas = 0
        try:
            heading_element = page.locator('h1#main-heading')
            heading_element.wait_for(state="visible", timeout=5000)
            
            if heading_element.count() > 0:
                texto_encabezado = heading_element.first.inner_text()
                
                # Extraemos el primer bloque (ej: "1.450") y limpiamos los puntos
                primera_palabra = texto_encabezado.split()[0]
                num_limpio = ''.join(c for c in primera_palabra if c.isdigit())
                
                if num_limpio:
                    total_ofertas = int(num_limpio)
                    print(f"Total global extraído: {total_ofertas} ofertas.")
        except Exception as e:
            print(f"Error extrayendo el total global: {e}")

        # 2. EXTRACTOR DE LAS PROVINCIAS ESPECÍFICAS
        resultados_provincias = {}
        
        # Usamos una lista de tuplas con el ID y el Nombre de la provincia
        tipos_provincia = [
            ("33", "Madrid"),
            ("9", "Barcelona"),
            ("49", "Valencia"),
            ("34", "Málaga")
        ]
        
        for prv, nombre in tipos_provincia: 
            num_resultados = 0
            
            try:
                selector_provincia = f'label[for="check-province--{prv}"] span.ij-SidebarFilter-filter-label-count'
                elemento_provincia = page.locator(selector_provincia)
                
                try:
                    elemento_provincia.wait_for(state="visible", timeout=2000)
                    texto_completo = elemento_provincia.first.inner_text()
                    
                    numeros_limpios = re.findall(r'\d+', texto_completo)
                    if numeros_limpios:
                        num_resultados = int("".join(numeros_limpios))
                except Exception:
                    # Si da timeout, asume que no hay la etiqueta (0 ofertas)
                    pass 
                    
                # Guardamos usando el nombre de la ciudad en lugar del ID numérico
                resultados_provincias[nombre] = num_resultados
                
            except Exception as e:
                print(f"Error inesperado en provincia {nombre}: {e}")
                resultados_provincias[nombre] = 0

        # Matemáticas para sacar el resto de España
        suma_provincias = sum(resultados_provincias.values())
        
        if suma_provincias != total_ofertas:
            resultados_provincias["Otras provincias"] = total_ofertas - suma_provincias
        else:
            resultados_provincias["Otras provincias"] = 0


        # 3. EXTRACTOR DE PRESENCIALIDAD
        resultados_presencialidad = {}
        # 33 = Madrid, 9 = Barcelona, 49 = Valencia, 34 = Málaga
        for i in [3,2,1,4]: 
            num_resultados = 0
            pres = str(i)
            
            try:
                selector_presencialidad = f'label[for="check-teleworking--{pres}"] span.ij-SidebarFilter-filter-label-count'
                elemento_presencialidad = page.locator(selector_presencialidad)
                
                try:
                    elemento_presencialidad.wait_for(state="visible", timeout=2000)
                    texto_completo = elemento_presencialidad.first.inner_text()
                    
                    numeros_limpios = re.findall(r'\d+', texto_completo)
                    if numeros_limpios:
                        num_resultados = int("".join(numeros_limpios))
                except Exception:
                    # Si da timeout, asume que no hay la etiqueta (0 ofertas)
                    pass 
                    
                resultados_presencialidad[pres] = num_resultados
                
            except Exception as e:
                print(f"Error inesperado en provincia {pres}: {e}")
                resultados_presencialidad[pres] = 0


        resultados_jornada = {}
        
        # 1. Usamos una lista de tuplas para evitar los "if" anidados
        tipos_jornada = [
            ("1", "Completa"),
            ("10", "Indiferente"),
            ("3", "Parcial - Tarde"),
            ("5", "Parcial - Indiferente")
        ]
        
        for jor, tit in tipos_jornada: 
            num_resultados = 0
            
            try:
                selector_jornada = f'label[for="check-workday--{jor}"] span.ij-SidebarFilter-filter-label-count'
                elemento_jornada = page.locator(selector_jornada)
                
                try:
                    elemento_jornada.wait_for(state="visible", timeout=2000)
                    texto_completo = elemento_jornada.first.inner_text()
                    
                    numeros_limpios = re.findall(r'\d+', texto_completo)
                    if numeros_limpios:
                        num_resultados = int("".join(numeros_limpios))
                except Exception:
                    # Si da timeout, asume que no hay la etiqueta (0 ofertas)
                    pass 
                    
                resultados_jornada[tit] = num_resultados
                
            except Exception as e:
                print(f"Error inesperado en jornada {tit}: {e}")
                # 2. Corregido: Guardamos con el título (tit), no con el ID (jor)
                resultados_jornada[tit] = 0
                
        # 3. Matemáticas seguras y dinámicas usando sum()
        suma_jornadas = sum(resultados_jornada.values())
        
        if suma_jornadas != total_ofertas:
            resultados_jornada["Otra jornada"] = total_ofertas - suma_jornadas
        else:
            resultados_jornada["Otra jornada"] = 0


        resultados_indefinido = {}
        # 1. Inicializamos la variable a 0 por si el try falla (evita NameError)
        contratos_indefinidos = 0 
        
        try:
            selector_indefinido = 'label[for="check-contractType--1"] span.ij-SidebarFilter-filter-label-count'
            elemento_indefinido = page.locator(selector_indefinido)
            
            try:
                elemento_indefinido.wait_for(state="visible", timeout=2000)
                texto_completo = elemento_indefinido.first.inner_text()
                
                # 2. Extraemos los números (devuelve lista de strings)
                numeros_extraidos = re.findall(r'\d+', texto_completo)
                
                if numeros_extraidos:
                    # 3. Lo convertimos a entero real
                    contratos_indefinidos = int("".join(numeros_extraidos))
                    
            except Exception:
                # Si da timeout, asume que no hay la etiqueta (se queda en 0)
                pass 
                
            # 4. Hacemos las matemáticas de forma segura
            resultados_indefinido["indefinidos"] = contratos_indefinidos
            resultados_indefinido["no_indefinidos"] = total_ofertas - contratos_indefinidos
            
            print(f"Contratos indefinidos: {contratos_indefinidos} | Otros contratos: {resultados_indefinido['no_indefinidos']}")
            
        except Exception as e:
            # 5. Mensaje de error y variables actualizadas al contexto real
            print(f"Error inesperado extrayendo contratos indefinidos: {e}")
            resultados_indefinido["indefinidos"] = 0
            resultados_indefinido["no_indefinidos"] = total_ofertas



        # EL ARRAY FINAL ESTRUCTURADO

        array_final = [
            total_ofertas,
            resultados_provincias['Madrid'],
            resultados_provincias['Barcelona'],
            resultados_provincias['Valencia'],
            resultados_provincias['Málaga'],
            resultados_provincias["Otras provincias"],
            resultados_presencialidad['3'],
            resultados_presencialidad['2'],
            resultados_presencialidad['1'],
            resultados_presencialidad['4'],
            resultados_indefinido["indefinidos"],
            resultados_indefinido["no_indefinidos"],
            json.dumps(resultados_jornada, ensure_ascii=False) # <--- Aquí metes el diccionario
        ]
        
        print(f"Array listo para ingesta: {array_final}")
        
        browser.close()
        
    # PERSISTENCIA EN CSV (HISTÓRICO MLOps)
    if array_final[0] > 0 or any(val > 0 for val in array_final[1:]):
        archivo_salida = "infojobs_historico_ofertas.csv"
        ahora = datetime.now().strftime("%Y-%m-%d")
        
        nuevo_registro = {
            "Timestamp": ahora,
            "Total_Resultados": array_final[0],
            "Ofertas_Madrid": array_final[1],
            "Ofertas_Barcelona": array_final[2],
            "Ofertas_Valencia": array_final[3],
            "Ofertas_Malaga": array_final[4],
            "Otras_provincias": array_final[5],
            "Telework: Híbrido": array_final[6],
            "Telework: Solo Teletrabajo": array_final[7],
            "Telework: Presencial": array_final[8],
            "Telework: Sin especificar": array_final[9],
            "Contratos indefinidos": array_final[10],
            "Contratos no indefinidos": array_final[11],
            "Tipo_Jornada": array_final[12]
        }
        df_nuevo = pd.DataFrame([nuevo_registro])
        
        # Si el archivo ya existe, añadimos la fila abajo (append). Si no, lo creamos de cero.
        if os.path.exists(archivo_salida):
            df_existente = pd.read_csv(archivo_salida)
            df_final = pd.concat([df_existente, df_nuevo], ignore_index=True)
            print("Añadiendo nuevo registro al histórico existente.")
        else:
            df_final = df_nuevo
            print("Creando nuevo archivo de métricas históricas.")
            
        df_final.to_csv(archivo_salida, index=False, encoding='utf-8')
        print(f"\n¡Datos guardados! Registro actualizado en '{archivo_salida}'")
    else:
        print("\nNo se ha podido guardar nada porque la extracción falló o devolvió 0 en todas las métricas.")

if __name__ == "__main__":
    scrape_total_results()