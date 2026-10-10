# VPN, red y conectividad — Soporte Técnico de Nimbus Desk

Guía de conectividad de la empresa ficticia Nimbus Desk. Contenido de práctica.

## Qué es NimbusConnect

NimbusConnect es el cliente de VPN de la empresa. Crea una conexión cifrada entre la notebook y la red interna, y es obligatorio para acceder desde fuera de la oficina a sistemas internos como el repositorio de código, las bases de datos de prueba y los paneles de monitoreo. El correo y el chat no requieren VPN.

## Instalar NimbusConnect

El cliente viene preinstalado en las notebooks de la empresa. Si hace falta reinstalarlo, se busca "NimbusConnect" en el catálogo de software del portal de soporte y se instala con un clic. No se debe descargar de sitios externos. En equipos personales no se permite instalarlo.

## Conectarse a la VPN

Se abre NimbusConnect, se elige el perfil "Nimbus-Corporativo" y se inicia sesión con Nimbus ID y el segundo factor. La conexión demora entre 5 y 15 segundos. Un ícono verde en la barra de tareas indica que la conexión está activa. La sesión dura 12 horas y luego pide volver a autenticarse.

## Error VPN-401: autenticación fallida

El error VPN-401 significa que Nimbus ID rechazó las credenciales. Primero hay que verificar que se puede iniciar sesión en el correo desde el navegador. Si falla, la contraseña venció o la cuenta está bloqueada, y se restablece desde Nimbus ID. Si el correo funciona pero la VPN no, hay que revisar la hora del equipo: un reloj desajustado invalida el segundo factor.

## Error VPN-502: puerta de enlace no disponible

El error VPN-502 indica que el servidor de acceso no responde. Suele ser un problema temporal de la puerta de enlace. Se recomienda cerrar y volver a abrir NimbusConnect, esperar 2 minutos y reintentar. Si persiste, hay que consultar la página de estado de servicios, porque puede haber una caída general, y abrir un ticket si no hay avisos.

## Error VPN-619: tiempo de espera agotado

El error VPN-619 se produce cuando la conexión no llega al servidor, a menudo por una red que bloquea el tráfico de la VPN, como el wifi de un hotel o de un aeropuerto. Se puede probar con el perfil "Nimbus-Corporativo-443", que usa el puerto 443, o con el hotspot del celular. Si funciona con otra red, el problema es de la red de origen.

## La VPN se conecta pero no abre los sistemas

Si NimbusConnect está activa pero un sistema interno no carga, hay que comprobar el DNS: se ejecuta un ping al nombre del sistema. Si no resuelve, se desconecta y se vuelve a conectar la VPN. También puede ser que no se tenga el permiso para ese sistema, en cuyo caso corresponde una solicitud de acceso, no un ticket de red.

## La VPN se desconecta sola

Las desconexiones frecuentes suelen deberse a una conexión inestable o a la suspensión del equipo. Se recomienda desactivar el ahorro de energía del adaptador de red, usar un cable o acercarse al router, y mantener NimbusConnect actualizado. Si las caídas ocurren cada pocos minutos en una red estable, se abre un ticket con la hora aproximada de cada corte.

## Redes wifi de la oficina

La oficina tiene dos redes. "Nimbus-Corp" es para dispositivos de la empresa y se conecta con Nimbus ID. "Nimbus-Guest" es para visitas y dispositivos personales, tiene una clave que cambia cada día y no da acceso a sistemas internos. Los celulares personales deben usar solo "Nimbus-Guest".

## Wifi lento o intermitente en la oficina

Si el wifi de la oficina anda lento, hay que acercarse al punto de acceso, comprobar si el problema ocurre también a otras personas del piso y probar con cable. Los problemas generales se informan en el canal de soporte para que el equipo de redes lo revise. Un problema que solo afecta a una persona suele estar en su equipo.

## Trabajar desde casa: requisitos mínimos

Para trabajar de forma remota se recomienda una conexión de al menos 30 Mbps de bajada y 10 Mbps de subida. La empresa paga un bono de home office para internet, que gestiona Recursos Humanos. Si la conexión de casa es insuficiente, se puede pedir un cupo de coworking al responsable.

## Videollamadas con mala calidad

Para mejorar una videollamada, se cierran las aplicaciones que usan la red, se apaga la cámara si hace falta y se prefiere el cable al wifi. La VPN no debe estar activa durante una videollamada si no es necesaria, porque agrega latencia. Se puede probar la calidad de la conexión desde la herramienta de diagnóstico del portal de soporte.

## Acceso desde el exterior del país

Para usar la VPN desde otro país, la persona debe tener una autorización previa de viaje, tramitada por Recursos Humanos, y el equipo de seguridad debe habilitar el país. Sin esa habilitación, la conexión es rechazada por motivos de seguridad. La autorización se procesa en 2 días hábiles.

## Puertos y firewall

El tráfico de la VPN usa el puerto UDP 1194 y, como alternativa, TCP 443. Las redes que bloquean ambos puertos no permiten la conexión. Los pedidos para abrir puertos en el firewall de la empresa son solicitudes de red y se tramitan con aprobación del equipo de seguridad.
