# Accesos, cuentas y contraseñas — Soporte Técnico de Nimbus Desk

Documentación del equipo de Soporte Técnico (TI) de Nimbus Desk, una empresa ficticia que desarrolla una plataforma SaaS de help desk. Contenido de práctica.

## Nimbus ID: el acceso único

Nimbus ID es el sistema de inicio de sesión único (SSO) de la empresa. Con una sola cuenta se accede al correo, al chat corporativo, a los documentos, a Nimbus People, a Nimbus Expenses y a las herramientas de ingeniería. El usuario tiene el formato nombre.apellido@nimbusdesk.example y se crea el primer día de trabajo.

## Primer inicio de sesión

La primera vez, Nimbus ID pide cambiar la contraseña temporal y registrar un segundo factor de autenticación. La contraseña temporal llega por mensaje al teléfono personal informado durante el alta y vence a las 24 horas. Si venció, hay que pedir una nueva al equipo de soporte técnico.

## Autenticación en dos pasos (MFA)

El segundo factor es obligatorio para todas las cuentas. Se registra una aplicación de autenticación en el celular, que genera códigos de 6 dígitos cada 30 segundos. También se puede usar una llave de seguridad física. No se aceptan códigos por mensaje de texto, porque pueden ser interceptados.

## Cambio de celular y MFA

Si se cambia de celular, hay que transferir la aplicación de autenticación antes de borrar el dispositivo viejo. Si el celular anterior ya no está disponible, se abre un ticket en el portal de soporte y se verifica la identidad por videollamada con una persona del equipo. El nuevo registro de MFA demora hasta 4 horas hábiles.

## Requisitos de contraseña

Las contraseñas de Nimbus ID deben tener al menos 14 caracteres y no pueden repetir ninguna de las últimas 10. No se exigen cambios periódicos, pero se pide cambiarla si hay sospecha de que fue expuesta. Se recomienda usar frases largas y el gestor de contraseñas corporativo.

## Cómo restablecer una contraseña

El restablecimiento es de autoservicio en la pantalla de inicio de sesión de Nimbus ID, opción "Olvidé mi contraseña". Se necesita acceso al correo personal registrado y al segundo factor. Si no se tiene acceso al segundo factor, hay que abrir un ticket para una verificación de identidad.

## Bloqueo de cuenta

Después de 5 intentos fallidos consecutivos, la cuenta se bloquea durante 15 minutos de forma automática. Pasado ese tiempo se puede volver a intentar. Si la cuenta sigue bloqueada, o aparece como "deshabilitada", el equipo de soporte puede desbloquearla desde el portal de soporte tras verificar la identidad.

## No puedo entrar a un sistema pero sí a Nimbus ID

Si Nimbus ID funciona pero una aplicación en particular niega el acceso, el problema suele ser de permisos y no de contraseña. Hay que pedir el acceso en el portal de soporte, en la categoría "Solicitud de acceso", indicando el sistema y el motivo. Un usuario puede tener sesión iniciada pero no estar autorizado para una aplicación.

## Solicitud de nuevos accesos

Los accesos a aplicaciones se solicitan en el portal de soporte con la aprobación de la persona responsable. Los accesos estándar, como correo y chat, se otorgan de forma automática. Los accesos con datos sensibles, como bases de datos de clientes o sistemas financieros, requieren además la aprobación del dueño del sistema y demoran hasta 2 días hábiles.

## Acceso a Nimbus People y a Nimbus Expenses

Estos portales usan Nimbus ID. Si no se puede iniciar sesión, es un problema técnico y se resuelve con soporte técnico. Las preguntas sobre el contenido de los portales, por ejemplo cuántos días de vacaciones quedan o el estado de un reembolso, las responden Recursos Humanos y Finanzas respectivamente.

## Cuentas compartidas y de servicio

No están permitidas las cuentas compartidas entre personas. Las cuentas de servicio, usadas por aplicaciones y automatizaciones, solo las crea el equipo de seguridad con un dueño asignado y una fecha de revisión anual. Las credenciales de servicio se guardan en el administrador de secretos y nunca en el código.

## Gestor de contraseñas corporativo

La empresa ofrece una licencia de un gestor de contraseñas a cada persona. Se solicita en el catálogo de software del portal de soporte. Permite generar y guardar contraseñas únicas y compartir credenciales de forma segura con equipos autorizados. Las contraseñas guardadas ahí no deben repetirse en el navegador.

## Baja de accesos al dejar la empresa

Los accesos de una persona que se va se revocan el último día de trabajo, a las 18:00. Recursos Humanos avisa a soporte técnico con al menos 5 días hábiles de anticipación cuando es posible. Los datos del buzón de correo se conservan 90 días y luego se eliminan, salvo retención legal.

## Cambios de rol y de equipo

Cuando una persona cambia de equipo, sus accesos anteriores se revisan y se quitan los que ya no corresponden. La persona responsable del nuevo equipo debe pedir los accesos necesarios. Soporte técnico recibe la notificación automática desde Nimbus People cuando se registra el cambio.
