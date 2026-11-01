"""Textos de los contratos de prueba y su ground truth (empresas y datos ficticios).

Cada documento es una lista de bloques (tipo, texto). El mismo texto se dibuja en la imagen y se
guarda en `expected.json`, asi el "texto correcto" que se usa para medir la fidelidad del parsing
es exactamente lo que se renderizo.

Tipos de bloque: "title" (titulo centrado), "para" (parrafo), "heading" (encabezado de clausula),
"sub" (inciso con sangria), "sign" (linea de firmas).
"""

Block = tuple[str, str]

# ---------------------------------------------------------------------------
# Par 1 (y 3): cambios simples. Contrato de soporte tecnico; la adenda cambia solo
# el vencimiento (Segunda) y el monto mensual (Tercera).
# ---------------------------------------------------------------------------
SIMPLE_ORIGINAL: list[Block] = [
    ("title", "CONTRATO DE PRESTACIÓN DE SERVICIOS DE SOPORTE TÉCNICO"),
    (
        "para",
        "En la Ciudad de Buenos Aires, a 15 de enero de 2025, entre ANDINA LOGÍSTICA S.A., "
        'CUIT 30-71234567-8 (en adelante, "EL CLIENTE"), y TECHNOVA SERVICIOS S.R.L., '
        'CUIT 30-70987654-3 (en adelante, "EL PROVEEDOR"), se celebra el presente contrato, '
        "sujeto a las siguientes cláusulas:",
    ),
    ("heading", "CLÁUSULA PRIMERA – OBJETO."),
    (
        "para",
        "EL PROVEEDOR prestará a EL CLIENTE servicios de soporte técnico informático para su "
        "infraestructura de oficinas, en modalidad remota y presencial.",
    ),
    ("heading", "CLÁUSULA SEGUNDA – PLAZO Y VIGENCIA."),
    (
        "para",
        "El presente contrato tendrá vigencia desde el 1 de febrero de 2025 hasta el 31 de "
        "diciembre de 2025, pudiendo renovarse por acuerdo escrito de las partes.",
    ),
    ("heading", "CLÁUSULA TERCERA – PRECIO."),
    (
        "para",
        "EL CLIENTE abonará a EL PROVEEDOR un monto mensual de USD 2.500 (dólares "
        "estadounidenses dos mil quinientos), más IVA.",
    ),
    ("heading", "CLÁUSULA CUARTA – FORMA DE PAGO."),
    (
        "para",
        "El pago se efectuará por transferencia bancaria dentro de los diez (10) días corridos "
        "posteriores a la recepción de la factura.",
    ),
    ("heading", "CLÁUSULA QUINTA – CONFIDENCIALIDAD."),
    (
        "para",
        "Las partes se obligan a mantener en reserva toda la información a la que accedan con "
        "motivo de este contrato.",
    ),
    ("heading", "CLÁUSULA SEXTA – RESCISIÓN."),
    (
        "para",
        "Cualquiera de las partes podrá rescindir el contrato con un preaviso de treinta (30) "
        "días por escrito.",
    ),
    ("heading", "CLÁUSULA SÉPTIMA – LEY APLICABLE."),
    (
        "para",
        "El contrato se rige por las leyes de la República Argentina; serán competentes los "
        "tribunales ordinarios de la Ciudad de Buenos Aires.",
    ),
    (
        "sign",
        "p. EL CLIENTE ____________        p. EL PROVEEDOR ____________",
    ),
]

SIMPLE_AMENDMENT: list[Block] = [
    ("title", "ADENDA N.º 1 AL CONTRATO DE PRESTACIÓN DE SERVICIOS DE SOPORTE TÉCNICO"),
    (
        "para",
        "En la Ciudad de Buenos Aires, a 20 de octubre de 2025, ANDINA LOGÍSTICA S.A. y "
        "TECHNOVA SERVICIOS S.R.L., partes del contrato de fecha 15 de enero de 2025, acuerdan "
        "modificarlo del siguiente modo:",
    ),
    ("heading", "PRIMERO."),
    (
        "para",
        "Se modifica la CLÁUSULA SEGUNDA – PLAZO Y VIGENCIA, que queda redactada así: "
        '"El presente contrato tendrá vigencia desde el 1 de febrero de 2025 hasta el 31 de '
        'diciembre de 2026, pudiendo renovarse por acuerdo escrito de las partes."',
    ),
    ("heading", "SEGUNDO."),
    (
        "para",
        "Se modifica la CLÁUSULA TERCERA – PRECIO, que queda redactada así: "
        '"EL CLIENTE abonará a EL PROVEEDOR un monto mensual de USD 2.800 (dólares '
        'estadounidenses dos mil ochocientos), más IVA."',
    ),
    ("heading", "TERCERO."),
    (
        "para",
        "Las demás cláusulas del contrato permanecen vigentes sin modificaciones.",
    ),
    (
        "sign",
        "p. EL CLIENTE ____________        p. EL PROVEEDOR ____________",
    ),
]

SIMPLE_EXPECTED = {
    "case_id": "par1_simple",
    "description": "Cambios simples: la adenda modifica solo el vencimiento y el monto mensual.",
    "changes": [
        {
            "section": "Cláusula Segunda",
            "change_type": "modificacion",
            "topic": "Plazo y vigencia",
            "detail": "El vencimiento pasa del 31 de diciembre de 2025 al 31 de diciembre de 2026.",
        },
        {
            "section": "Cláusula Tercera",
            "change_type": "modificacion",
            "topic": "Precio",
            "detail": "El monto mensual pasa de USD 2.500 a USD 2.800.",
        },
    ],
    # Datos que un resumen correcto debe mencionar (se chequean mas adelante, con match flexible).
    "key_facts_in_summary": ["2026", "2.500", "2.800"],
    # Clausulas que NO deben aparecer como cambiadas (falsos positivos si aparecen).
    "unchanged_sections": [
        "Cláusula Primera",
        "Cláusula Cuarta",
        "Cláusula Quinta",
        "Cláusula Sexta",
        "Cláusula Séptima",
    ],
}

# ---------------------------------------------------------------------------
# Par 2: cambios complejos. NDA; la adenda modifica (Tercera), elimina (inciso 4.3) y agrega
# (Octava): los tres tipos de cambio.
# ---------------------------------------------------------------------------
COMPLEX_ORIGINAL: list[Block] = [
    ("title", "ACUERDO DE CONFIDENCIALIDAD"),
    (
        "para",
        "En la Ciudad de Buenos Aires, a 3 de marzo de 2025, entre HELIX BIOTECH S.A. "
        '(en adelante, "LA PARTE REVELADORA") y ORIÓN CONSULTORES S.A. (en adelante, '
        '"LA PARTE RECEPTORA"), se celebra el presente acuerdo de confidencialidad:',
    ),
    ("heading", "CLÁUSULA PRIMERA – INFORMACIÓN CONFIDENCIAL."),
    (
        "para",
        "Se considera Información Confidencial toda información técnica, científica, comercial "
        "o financiera revelada por LA PARTE REVELADORA, cualquiera sea su soporte.",
    ),
    ("heading", "CLÁUSULA SEGUNDA – OBLIGACIONES."),
    (
        "para",
        "LA PARTE RECEPTORA se obliga a custodiar la Información Confidencial con el mismo "
        "cuidado que aplica a la propia y a limitar el acceso a quienes necesiten conocerla.",
    ),
    ("heading", "CLÁUSULA TERCERA – ALCANCE TERRITORIAL."),
    (
        "para",
        "Las obligaciones de este acuerdo rigen en el territorio de la República Argentina y "
        "de la República Oriental del Uruguay.",
    ),
    ("heading", "CLÁUSULA CUARTA – RESTRICCIONES DE USO."),
    ("para", "LA PARTE RECEPTORA no podrá:"),
    (
        "sub",
        "4.1. utilizar la Información Confidencial para fines distintos de la evaluación de "
        "una posible colaboración;",
    ),
    (
        "sub",
        "4.2. realizar ingeniería inversa sobre las muestras o materiales recibidos;",
    ),
    (
        "sub",
        "4.3. subcontratar a terceros el tratamiento de la Información Confidencial.",
    ),
    ("heading", "CLÁUSULA QUINTA – PLAZO."),
    (
        "para",
        "Las obligaciones de confidencialidad durarán tres (3) años contados desde la fecha "
        "de firma.",
    ),
    ("heading", "CLÁUSULA SEXTA – DEVOLUCIÓN."),
    (
        "para",
        "A requerimiento de LA PARTE REVELADORA, la Información Confidencial deberá "
        "devolverse o destruirse dentro de los quince (15) días.",
    ),
    ("heading", "CLÁUSULA SÉPTIMA – LEY APLICABLE."),
    (
        "para",
        "El acuerdo se rige por las leyes de la República Argentina; serán competentes los "
        "tribunales ordinarios de la Ciudad de Buenos Aires.",
    ),
    (
        "sign",
        "p. LA PARTE REVELADORA ____________        p. LA PARTE RECEPTORA ____________",
    ),
]

COMPLEX_AMENDMENT: list[Block] = [
    ("title", "ADENDA N.º 1 AL ACUERDO DE CONFIDENCIALIDAD"),
    (
        "para",
        "En la Ciudad de Buenos Aires, a 12 de septiembre de 2025, HELIX BIOTECH S.A. y "
        "ORIÓN CONSULTORES S.A., partes del acuerdo de fecha 3 de marzo de 2025, acuerdan "
        "modificarlo del siguiente modo:",
    ),
    ("heading", "PRIMERO."),
    (
        "para",
        "Se modifica la CLÁUSULA TERCERA – ALCANCE TERRITORIAL, que queda redactada así: "
        '"Las obligaciones de este acuerdo rigen en el territorio de la República Argentina, '
        "la República Oriental del Uruguay, la República de Chile y la República Federativa "
        'del Brasil."',
    ),
    ("heading", "SEGUNDO."),
    (
        "para",
        "Se elimina en su totalidad el inciso 4.3 de la CLÁUSULA CUARTA – RESTRICCIONES DE "
        "USO. Los incisos 4.1 y 4.2 se mantienen sin cambios.",
    ),
    ("heading", "TERCERO."),
    (
        "para",
        "Se incorpora la CLÁUSULA OCTAVA – PROTECCIÓN DE DATOS PERSONALES, con el siguiente "
        'texto: "Cuando la Información Confidencial incluya datos personales, LA PARTE '
        "RECEPTORA los tratará conforme a la Ley N.º 25.326 de Protección de los Datos "
        "Personales y adoptará las medidas de seguridad adecuadas para evitar su pérdida o "
        'acceso no autorizado."',
    ),
    ("heading", "CUARTO."),
    ("para", "Las demás cláusulas del acuerdo permanecen vigentes sin modificaciones."),
    (
        "sign",
        "p. LA PARTE REVELADORA ____________        p. LA PARTE RECEPTORA ____________",
    ),
]

COMPLEX_EXPECTED = {
    "case_id": "par2_complejo",
    "description": "Cambios complejos: una modificacion, una eliminacion y una adicion.",
    "changes": [
        {
            "section": "Cláusula Tercera",
            "change_type": "modificacion",
            "topic": "Alcance territorial",
            "detail": "Se suman Chile y Brasil a Argentina y Uruguay.",
        },
        {
            "section": "Cláusula Cuarta, inciso 4.3",
            "change_type": "eliminacion",
            "topic": "Restricciones de uso",
            "detail": "Se elimina la prohibición de subcontratar el tratamiento de la información.",
        },
        {
            "section": "Cláusula Octava",
            "change_type": "adicion",
            "topic": "Protección de datos personales",
            "detail": "Nueva cláusula: tratamiento de datos personales según la Ley 25.326.",
        },
    ],
    "key_facts_in_summary": ["Chile", "Brasil", "4.3", "25.326"],
    "unchanged_sections": [
        "Cláusula Primera",
        "Cláusula Segunda",
        "Cláusula Quinta",
        "Cláusula Sexta",
        "Cláusula Séptima",
    ],
}
