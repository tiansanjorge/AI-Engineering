# Contratos de prueba

Pares de **contrato original + adenda** (empresas y datos ficticios) para probar el pipeline.
Se generan con `python scripts/generate_contracts.py` (determinista: misma salida cada vez).

| Par | Escenario | Cambios que debe detectar el sistema |
|---|---|---|
| `par1_simple/` | Contrato de soporte técnico. Cambios **simples**. | Cláusula Segunda (vencimiento 31/12/2025 → 31/12/2026) y Cláusula Tercera (monto USD 2.500 → USD 2.800). Las otras 5 cláusulas no cambian. |
| `par2_complejo/` | NDA. Cambios **complejos**: los 3 tipos. | **Modificación** de la Cláusula Tercera (suma Chile y Brasil), **eliminación** del inciso 4.3 de la Cláusula Cuarta (subcontratación), **adición** de la Cláusula Octava (datos personales). |
| `par3_escaneo_degradado/` | Mismo contenido que el par 1, pero como un escaneo malo (rotado, ruido, desenfoque, JPEG). | Los mismos que el par 1. Sirve para aislar el efecto de la calidad de imagen. |

## Qué hay en cada carpeta

- `original.(png|jpg)` y `adenda.(png|jpg)`: las imágenes que recibe el sistema.
- `expected.json`: el **ground truth** (lo correcto, escrito antes de correr el sistema):
  - `documents`: texto exacto de cada documento (para medir la fidelidad del parsing).
  - `changes`: lista de cambios con sección, tipo (`modificacion` / `eliminacion` / `adicion`) y tema.
  - `key_facts_in_summary`: datos que un resumen correcto debe mencionar.
  - `unchanged_sections`: cláusulas que **no** deben figurar como modificadas (falsos positivos).

La adenda no es una copia del contrato con cambios: nombra cláusulas ("se modifica la Cláusula
Tercera...") y hay que cruzarla con el original. Por eso sirve contar con un agente que primero
arme el mapa de correspondencias.
