# AI-Engineering — Proyectos Integradores (Henry, AI Engineering)

Monorepo con las entregas de cada módulo de la carrera. Cada módulo vive en
su propia carpeta top-level, autocontenida (setup, dependencias y comandos
propios), documentada en su propio README.

## Módulos

| Módulo | Carpeta | Qué construye |
|---|---|---|
| 1 | [`modulo-1/`](modulo-1/README.md) | Asistente de soporte al cliente: pregunta → JSON con respuesta, confianza y acciones, con métricas de costo/latencia por ejecución. |
| 2 | [`modulo-2/`](modulo-2/README.md) | Chatbot de FAQs con RAG: chunking, embeddings, búsqueda vectorial y generación con contexto recuperado. Flujo obligatorio + bonus (agente evaluador) completos. |

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
