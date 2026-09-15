# Hoja de ruta

Este documento separa tres cosas: lo que se entrega en el curso, los extras que se intentarán si hay
tiempo y lo que queda para después del semestre como parte del proyecto doctoral. La pregunta, la
población y el método están en [`protocolo.md`](protocolo.md).

## 1. Núcleo: entrega del curso

Es el compromiso para la entrega final. Todo se reconstruye desde la descarga pública de SINAC; **el
repositorio no contiene datos**, solo el código que los carga y transforma.

| Componente | Contenido |
|---|---|
| Modelo de datos | Postgres con un subconjunto del OMOP CDM v5.4 y ETL reproducible desde la descarga (SINAC 2019–2023, versión estandarizada del INSP) |
| Cohortes | Definiciones en SQL documentadas, con tabla de atrición por definición |
| Exposiciones | (a) total de consultas; (b) índice APNCU aproximado; (c) inicio de la atención en el primer trimestre; (d) total de consultas en cohortes landmark (semanas 28, 32 y 34) |
| Simulación | Asociación que produce el truncamiento por sí solo, bajo la hipótesis nula (calendario NOM-007-SSA2-2016) |
| Sensibilidad | Corte de pretérmino (37/34/32), embarazos múltiples, nacimientos <22 semanas, años 2020–2021, mes asignado dentro del trimestre para el APNCU; gradiente por entidad y derechohabiencia |
| Ingeniería | `compose.yml`, pytest, CI en GitHub Actions, diccionario de datos |
| Documentación | README reproducible, limitaciones, declaración de uso de asistentes de IA |

### Decisiones de mapeo a OMOP previstas

Se documentan en detalle en el diccionario de datos; estas son las que condicionan el esquema.

| Dato de SINAC | Destino en OMOP | Nota |
|---|---|---|
| Madre y recién nacido | `PERSON` (dos registros) | Enlazados con `FACT_RELATIONSHIP` |
| Nacimiento | `VISIT_OCCURRENCE` | Unidad de atención en `CARE_SITE`, entidad en `LOCATION` |
| Semanas de gestación, peso al nacer | `MEASUREMENT` | Gestación sobre la madre, peso sobre el recién nacido |
| Total de consultas, trimestre de la primera consulta | `OBSERVATION` | Es un **conteo declarado**, no una fila por consulta; no se modela como visitas |
| Derechohabiencia | `PAYER_PLAN_PERIOD` | |
| Variables sin concepto estándar | `concept_id = 0` + `*_source_value` | Convención de OMOP; se listan en el diccionario |

## 2. Hitos del semestre

| Sesión | Hito |
|---|---|
| 18 | ETL a OMOP funcionando, cohorte base definida en SQL y tabla de atrición |
| 24 | Exposiciones a–d calculadas, primera versión de la simulación bajo la nula, CI en verde |
| 30 | Núcleo completo: tabla de sensibilidad, documentación y README reproducible |
| 31 | Presentación |

## 3. Extras condicionales

Se empiezan **solo cuando el núcleo esté cerrado**: CI en verde y tablas de atrición y sensibilidad
generadas. **Tienen riesgo real de no terminarse dentro del semestre** por la complejidad y el trabajo
adicional que implican. Si no se completan, se continúan terminado el semestre y su estado se actualiza
en este documento; el núcleo no depende de ellos.

### 3.1 Demostración del artefacto con ML + SHAP

- **Qué:** dos modelos de gradient boosting (LightGBM) que predicen parto pretérmino. El modelo
  *ingenuo* usa el total crudo de consultas; el modelo *libre de truncamiento* usa inicio en primer
  trimestre y variables sociodemográficas.
- **Variables excluidas de ambos:** semanas de gestación, peso al nacer y cualquier variable derivada de
  ellas (incluido el APNCU), porque contienen el desenlace.
- **Explicación:** SHAP sobre una submuestra estratificada, porque TreeSHAP sobre 10 millones de
  registros no es necesario ni práctico.
- **Qué se espera mostrar:** si el modelo ingenuo usa el truncamiento como su señal principal. Se
  contrasta con la simulación bajo la nula.
- **Qué no es:** un estimador de la asociación. Con un conteo truncado, un modelo predictivo aprende
  precisamente el sesgo que el estudio quiere medir; por eso se usa para demostrarlo.

### 3.2 Dashboard interactivo

- **Qué:** una interfaz para cambiar la definición de la cohorte (corte de pretérmino, semana landmark,
  exclusiones) y ver cómo cambian las estimaciones de cada medida de atención prenatal, incluido el
  APNCU.
- **Cómo:** sobre la tabla de sensibilidad y conteos pre-agregados, de modo que las estimaciones se
  recalculan en tiempo real sin volver a consultar los 10 millones de registros.

## 4. Después del semestre: continuidad con el proyecto doctoral

### 4.1 Lo que no se traslada: un modelo entrenado en SINAC

Un modelo entrenado en SINAC no puede aplicarse a la cohorte del INPer. Las variables de ambas fuentes
coinciden muy poco:

| Variable | SINAC | Cohorte INPer (variables de análisis) |
|---|---|---|
| Edad materna | Sí | Sí |
| Escolaridad | Sí | Sí, con 4 niveles (requiere recodificación) |
| Estado civil | Sí | Sí |
| Total de consultas prenatales | Sí | No |
| Trimestre de la primera consulta | Sí | No |
| Derechohabiencia | Sí | No (y sería casi constante) |
| Entidad de residencia | Sí | No |
| Embarazo múltiple | Sí | No |
| Semanas de gestación al parto | Sí | Sí (define el desenlace; no es predictor) |
| Peso al nacer, sexo del recién nacido | Sí | Sí (posteriores al desenlace; no son predictores) |
| Semana de gestación de cada muestra | No | Sí |
| Microbioma vaginal | No | Sí |

Entre las variables previas al parto solo coinciden edad, escolaridad y estado civil. Además, la
cohorte proviene de un hospital de referencia para embarazos de alto riesgo, que no es representativo
del registro nacional. La tabla refleja las variables de análisis de la cohorte; queda pendiente
revisar si la metadata clínica completa contiene alguna de las que faltan.

Una posibilidad limitada, que se evaluará pero no se compromete, es un puntaje de riesgo
sociodemográfico derivado de SINAC usado como una sola covariable en la cohorte. Requiere recodificar
las variables igual en ambas fuentes y no garantiza calibración entre poblaciones.

### 4.2 Lo que sí se traslada

1. **El modelo de datos.** La cohorte del INPer entra como una segunda fuente sobre el mismo esquema:
   - `PERSON`, una por participante;
   - `OBSERVATION_PERIOD`, desde la primera visita hasta el parto;
   - `SPECIMEN`, las muestras vaginales con su semana de gestación de recolección;
   - `MEASUREMENT`, las variables clínicas por visita.

   La metadata clínica de-identificada se lee desde su repositorio de origen; no se copia a este.
2. **La lógica de semana índice y cohortes landmark.** Las mismas definiciones SQL se aplican a las
   muestras: usar solo muestras tomadas antes de la semana X, sobre participantes que llegaron a la
   semana X.
3. **La simulación bajo la nula**, adaptada al calendario de muestreo de la cohorte. Sirve para evaluar
   cuánta información sobre la duración del embarazo transportan la semana de gestación al muestreo y
   el número de muestras por participante.
4. **El dashboard**, como herramienta de exploración de la ventana de muestreo. La ventana principal se
   preespecifica antes de mirar resultados; con 43 participantes y 14 eventos, elegirla a posteriori
   invalidaría la estimación.

### 4.3 Fuera de alcance, también después del semestre

- Integrar las abundancias del microbioma en OMOP más allá del registro de la muestra en `SPECIMEN`.
- Enlazar registros de SINAC con participantes del INPer; no es posible ni se pretende.

## Repositorios relacionados

- Análisis del proyecto doctoral: <https://github.com/martinruhle/Mexican-PretermBirth-analysis>
- Procesamiento de secuencias 16S: <https://github.com/martinruhle/Mexican-PretermBirth-16S-processing>
