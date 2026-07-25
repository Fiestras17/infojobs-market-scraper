# 📊 ETL Pipeline: Mercado Laboral Data Engineering (InfoJobs)
[![Estado de Ingesta Diaria](https://github.com/Fiestras17/infojobs-market-scraper/actions/workflows/pipeline_diario.yml/badge.svg)](https://github.com/Fiestras17/infojobs-market-scraper/actions)

Este repositorio contiene un pipeline automatizado de extracción de datos diseñado para monitorizar diariamente el estado del mercado laboral para el rol de *Data Engineer* en España a través de InfoJobs. 

El proyecto representa la **Capa Bronce** dentro de una arquitectura Medallón, ingiriendo datos complejos y estructurándolos para su posterior análisis y limpieza en un entorno nube (PySpark/Spark SQL).

## 🚀 Arquitectura y Tecnologías
* **Lenguaje:** Python 3.10
* **Extracción (Scraping):** Playwright (Headless Browser)
* **Transformación y Estructurado:** Pandas, JSON, Regex
* **Orquestación (CI/CD):** GitHub Actions

## ⚙️ Características Técnicas Destacadas

1. **Evasión de Sistemas Anti-Bot:** Implementación de inyección de scripts nativos (`Object.defineProperty`) para enmascarar la bandera `webdriver` y gestión de *Invisible Challenges* para evitar bloqueos por parte de los sistemas de seguridad perimetral de la web.
2. **Resiliencia en la Nube:** Detección de entorno dinámico. Si el pipeline se topa con un CAPTCHA duro mientras se ejecuta en los servidores sin interfaz (headless) de GitHub Actions, aborta la ejecución de forma limpia para evitar baneos de IP o la ingesta de datos nulos.
3. **Manejo de Datos Anidados:** Extracción de múltiples variables categóricas (como el tipo de jornada o presencialidad) y su empaquetado en diccionarios JSON dentro de las celdas del CSV, preparándolas para un proceso de limpiado dinámico con PySpark/Spark SQL en la Capa Plata.
4. **Implementación de tipo de contrato:** Obtención del tipo de contrato con posibilidad de hacer un PIVOT en la capa de plata.

## 🔄 Orquestación
El script está automatizado mediante un *cron job* en GitHub Actions (`.github/workflows/pipeline_diario.yml`) que levanta un contenedor Ubuntu diariamente, instala las dependencias, ejecuta el navegador fantasma y realiza un *auto-commit* inyectando el nuevo archivo `infojobs_historico_ofertas.csv` directamente en la rama principal.

## 📂 Estructura de Datos (Esquema de Salida)
El archivo resultante genera métricas diarias con el siguiente esquema:
* `Timestamp`: Fecha de la ingesta (YYYY-MM-DD). Sin hora al ser una ejecución diaria.
* `Total_Resultados`: Volumen global de ofertas activas.
* `Ofertas_[Provincia]`: Desglose regional (Madrid, Barcelona, Valencia, Málaga, Otras).
* `Telework`: Distribución por modelo de trabajo (Híbrido, 100% Remoto, Presencial).
* `Contrato`: Número de contratos indefinidos y temporales.
* `Tipo_Jornada`: String anidado en formato JSON con la distribución de jornadas.
