# Evaluación del sistema (Fase 6)

Evidencia de cómo se midió el sistema, qué falló y cómo se corrigió. Todo es reproducible:

```bash
python scripts/run_golden.py --run-tag mi-corrida --set dev|holdout|blind   # llama a la API (centavos)
```

Cada corrida: traza cada consulta en Langfuse (tags `<run-tag>`, intención esperada y categoría;
score `case_passed` por trace), guarda el detalle en `golden_runs/<run-tag>.json` y agrega una fila a
`golden_summary.csv`. Las funciones de métricas están en `src/evaluation.py` (con tests).

## Los tres sets

| Set | Archivo | Casos | Para qué |
|---|---|---|---|
| dev | `../test_queries.json` | 39 | Diagnosticar y ajustar. Cubre las 4 intenciones y casos típicos, de frontera, ambiguos, multi-intención, con ruido/ortografía, otro idioma, fuera de alcance, sin respuesta en los documentos y adversariales. |
| holdout | `../test_queries_holdout.json` | 14 | Validación: verificar que un ajuste generaliza. **Contaminación parcial:** después de ver sus fallos agregué "mantenimientos programados" y "disputas" a la descripción de las áreas del router. |
| blind | `../test_queries_blind.json` | 14 | Ciego: temas nuevos, corrido sobre v3 una sola vez y sin ajustes de prompt posteriores. Sirvió para detectar un bug y un modo de falla. Después de verlo se diseñó v4, así que **a partir de v4 también es un set "visto"**. |

Métricas (sin juez LLM, todas determinísticas): ruteo `strict` (intención == esperada) y `lenient`
(dentro de las aceptables, para consultas genuinamente ambiguas), `status_ok`, `facts_ok` (datos clave
presentes), `sources_ok` (sección esperada citada), `forbidden_ok` (frases prohibidas ausentes),
abstenciones indebidas y respuestas indebidas, matriz de confusión, latencia p50/p95 y costo estimado.
Un caso pasa si cumple ruteo `lenient`, estado, hechos, fuentes y frases prohibidas.

## Historial de iteraciones

| Versión | Cambio (uno por iteración) | dev | holdout | blind |
|---|---|---|---|---|
| v1 | Baseline (sistema de la Fase 4) | 92 % (36/39) | 79 % (11/14) | – |
| v2 | Router: alcance explícito de cada área; `out_of_scope` solo si es ajeno a la empresa | 97 % | 100 % | – |
| v3 | Agente de Finanzas: glosario de «reembolso» | 100 % | 100 % | **86 %** (12/14) |
| v4 | Guarda de recuperación contra falsos `out_of_scope` (umbral 0,43) | 97 % | 100 % | 100 % |
| v5 | Abstención decidida por evidencia (fuentes válidas), no por un booleano autodeclarado | **100 %** | **100 %** | **100 %** |
| v5 (rep. 2) | Misma configuración, segunda corrida | 100 % | 100 % | 100 % |

Costo de una corrida completa de un set de dev: ~USD 0,013; latencia p50 ≈ 2,5 s (≈ 1 s para consultas
fuera de alcance, que no invocan agente).

## Qué se encontró (y cómo)

1. **Dos errores míos en los sets, no del sistema.** T-TE-01 y H-HR-03 exigían un dato que la pregunta no
   pedía; se corrigieron *antes* de ajustar el sistema y se regeneraron las líneas base.
2. **Falsos rechazos del router (v1 → v2).** 3 de los 4 fallos de dev y 3 de 4 de holdout eran consultas
   internas válidas (horarios de la mesa de ayuda, intereses a clientes, facturas) rechazadas como
   `out_of_scope` con confianza 0,5 y razones erróneas ("facturación no es parte de los servicios
   internos"). Cambio: describir con precisión qué cubre cada área y cuándo es válido rechazar, con
   guías generales y ejemplos de temas que no están en ningún set. Generalizó: holdout 79 % → 100 %.
3. **El set ciego encontró un bug de código (`KeyError`)**: el router podía listar `out_of_scope` en
   `also_involves` y `finalize` se rompía. Corregido y con test de regresión.
4. **Los falsos rechazos persistían (ciego 86 %)**: dos consultas "¿cuánto tiempo guardan…?" volvieron a
   caer en `out_of_scope`. El prompt solo no alcanza, así que se agregó una defensa estructural
   (`src/routing_guard.py`): si un `out_of_scope` del router contradice una recuperación muy cercana
   (distancia coseno < 0,43), se rutea al dominio más cercano. El umbral salió de la brecha medida en
   dev + holdout: falsos rechazos ≤ 0,377 vs. consultas realmente ajenas ≥ 0,492 (con un adversarial en
   0,386 que, ruteado a Finanzas, igual no se aprueba nada).
5. **Un "arreglo" que no lo era (v3).** T-FI-05 pasó en v3 por suerte: medido con 10 repeticiones se
   abstenía **6/10** veces, y las respuestas abstenidas *contenían el dato correcto*. Causa de diseño:
   dependíamos de un booleano `abstained` autodeclarado y el prompt acoplaba "abstenerse" con "dejar
   `source_ids` vacío". v5 decide por evidencia: con ≥ 1 fuente válida la respuesta cuenta; sin fuentes,
   abstención. Resultado: **0/10 abstenciones** y 10/10 con el dato "30"; las 18 consultas ajenas a un
   agente siguen abstiéndose (0 falsas respuestas).

## Limitaciones (honestas)

- Los sets son chicos (39 + 14 + 14): un 100 % no demuestra perfección, solo que no hay fallos conocidos
  en estos casos. Con tan pocos casos, un intervalo de confianza del 95 % para un 100 % observado en 14
  es amplio (el límite inferior ronda el 77 %).
- dev se usó para ajustar; holdout quedó parcialmente contaminado; blind es "visto" desde v4. No queda
  ningún set virgen: para una validación externa haría falta uno nuevo.
- El modelo no es determinista aunque `temperature=0`: se midió una repetición completa y el caso T-FI-05
  con 10 muestras, no todos los casos con muchas repeticiones.
- La corrección de las respuestas se mide con datos clave y fuentes citadas, no con un juez semántico;
  eso lo cubre el evaluador del bonus (Fase 7).
- `routing_strict` de dev es 90 %: los 4 casos restantes son ambiguos donde el ruteo alternativo es válido
  (`acceptable_intents`).
