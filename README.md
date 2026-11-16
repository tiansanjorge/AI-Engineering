# AI-Engineering — Proyectos Integradores (Henry, AI Engineering)

Monorepo con las entregas de cada módulo de la carrera. Cada módulo vive en
su propia carpeta top-level, autocontenida (setup, dependencias y comandos
propios), documentada en su propio README.

## Módulos

| Módulo | Carpeta | Qué construye |
|---|---|---|
| 1 | [`modulo-1/`](modulo-1/README.md) | Asistente de soporte al cliente: pregunta → JSON con respuesta, confianza y acciones, con métricas de costo/latencia por ejecución. |
| 2 | [`modulo-2/`](modulo-2/README.md) | Chatbot de FAQs con RAG: chunking, embeddings, búsqueda vectorial y generación con contexto recuperado. Flujo obligatorio + bonus (agente evaluador) completos. |
| 3 | [`modulo-3/`](modulo-3/README.md) | Sistema multi-agente: orquestador (LangGraph) que clasifica la intención y deriva a agentes RAG de HR, Tech y Finance sobre Chroma, trazado en Langfuse. Bonus (agente evaluador con Score API) completo. |
| 4 | [`modulo-4/`](modulo-4/README.md) | Agente de comparación de contratos: 2 imágenes (contrato y adenda) → visión (GPT-4o) → 2 agentes (contextualización y extracción) → JSON validado con Pydantic, trazado en Langfuse. Proyecto final, con defensa en vivo. |

### Resultados medidos y qué hace falta para correrlos

| Módulo | Resultado medido (detalle en el README de cada uno) | Claves necesarias |
|---|---|---|
| 1 | Chain-of-thought elegido por experimento en 3 rondas (100 % de precisión en el set final); bloqueo de inyecciones antes de llamar al modelo. | `OPENAI_API_KEY` |
| 2 | RAG con trazabilidad por `chunks_related`; el evaluador bonus detectó un error de lectura de su propio juez, corregido exigiendo citas textuales. | `OPENAI_API_KEY` |
| 3 | Ruteo 100 % en los sets dev, validación y ciego; juez calibrado contra 30 puntajes humanos (Spearman 0,88). | `OPENAI_API_KEY` (Langfuse opcional) |
| 4 | 14 de 15 corridas perfectas en 5 pares de contratos, incluido uno con una inyección incrustada que el sistema señala sin obedecer. | `OPENAI_API_KEY` (Langfuse opcional) |

Todos los módulos incluyen tests que no llaman a ninguna API, así que se pueden correr sin claves.

## Entorno compartido

Un solo `.venv` en la raíz sirve para todos los módulos — cada uno declara
sus propias dependencias en `modulo-N/requirements.txt`, instalables sobre
ese mismo venv (`pip install -r modulo-1/requirements.txt`).

Las claves de API viven en un único `.env` en la raíz (gitignoreado): cada
script las carga con `load_dotenv()` sin ruta explícita, que busca el
archivo subiendo por los directorios padres — así no hace falta duplicar
secretos por módulo. Cada `modulo-N/.env.example` documenta qué variables
necesita ese módulo puntual.

## Cómo trabajar en un módulo

```bash
cd modulo-1   # o modulo-2, etc.
```

y seguir el README de esa carpeta.

## Material de referencia

`material/` (gitignoreado, fuera de este repo en el filesystem del
proyecto) contiene las lecturas, consignas y repositorios de ejemplo del
profesor para cada módulo. Es de solo lectura — nunca destino de escritura
ni de comandos git. El detalle de esta regla y el resto de las
convenciones del proyecto están en `CLAUDE.md`.
