# Pendientes, problemas conocidos y posibles mejoras

Registro de lo que se detecta mientras se construye el Módulo 4 y **no se resuelve en el momento**
(se revisa todo junto al terminar). Cada ítem lleva evidencia, impacto e ideas. Lo resuelto se
marca como tal, no se borra.

| ID | Área | Resumen | Prioridad | Estado |
|---|---|---|---|---|
| P-01 | Evaluación | El par 3 (escaneo degradado) se lee igual de bien que el limpio: no discrimina | Media | Abierto |
| P-02 | Modelo de datos | «Cero cambios» se trata como error: una adenda solo administrativa falla la validación | Baja | Abierto |
| P-03 | Corpus | Contratos sintéticos y digitales, de una sola página, un solo idioma | Media | Abierto |

---

## P-01 · El par 3 no estresa al parser

- **Qué pasa:** `scripts/eval_parsing.py` da WER 0,008-0,015 en las 6 imágenes, **idéntico** para
  limpias y degradadas. Las únicas diferencias son la cantidad de guiones bajos de la línea de
  firma (12 vs 13), irrelevantes: el contenido legal sale 100 % exacto en todas.
- **Evidencia:** `outputs/parsing_eval.json`.
- **Impacto:** el «escaneo malo» (rotación 2,2°, ruido, desenfoque 1,1, JPEG q62) es demasiado
  benigno para GPT-4o con `detail=high`: no sirve para mostrar cuándo falla el parser.
- **Ideas:** subir la degradación (rotación mayor, desenfoque 2-3, ruido alto, JPEG q30, recorte
  parcial, manchas) hasta encontrar el punto donde aparezcan errores, y documentar ese umbral.

## P-02 · «Cero cambios» es un error

- **Qué pasa:** `ExtractionResult` exige al menos un cambio. Una adenda legítima sin cambios
  sustantivos (p. ej. solo cambia el domicilio) no produciría un resultado válido.
- **Ideas:** distinguir «el modelo no encontró nada» de «la adenda no cambia nada» con un campo
  explícito, en vez de listas vacías.

## P-03 · Corpus acotado

- **Qué pasa:** 3 pares sintéticos, una página, español. No cubre tablas, firmas manuscritas,
  sellos, varias páginas ni otros idiomas.
