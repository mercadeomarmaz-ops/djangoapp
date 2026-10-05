# Perfil CWR para AGADU

Esta rama genera envios CWR 2.1 para AGADU sin reutilizar las reglas especiales
de SADAIC. La referencia funcional principal es el envio aceptado
`CW26004584_000.V21`, incluido en `CW26004584_000.zip` (SHA-256
`BEC2ECB21D93B4CA5B6B29DB596BB270307F947D1D0697D2A8EDD5E3375AB22F`).
El archivo de referencia no se copia al repositorio.

## Evidencia de aceptacion

El envio contiene 10 transacciones NWR. El ACK final de AGADU devuelve estado
`AS` (Registration Accepted) para las 10 y asigna los identificadores remotos
8190849 a 8190858. Cada transaccion aceptada tiene esta secuencia:

`NWR`, `SPU`, `SPT`, `SWR`, `SWT`, `PWR`, `PER`, `REC`.

Los largos observados son 260, 183, 58, 180, 52, 110, 118 y 266 caracteres,
respectivamente. El archivo tambien contiene `HDR` de 101, `GRH` de 28, `GRT`
de 37 y `TRL` de 24 caracteres.

## Valores del perfil AGADU

La rama usa `CWR_PROFILE=AGADU` de forma predeterminada y conserva los valores
como variables de entorno para que puedan cambiarse sin tocar codigo:

| Variable | Predeterminado | Evidencia |
| --- | --- | --- |
| `PUBLISHER_NAME` | `CORPORACION MARMAZ S.A.S.` | HDR, SPU y PWR aceptados |
| `PUBLISHER_CODE` | `84` | nombre `CW26004584_000.V21` |
| `PUBLISHER_IPI_NAME` | `01135451385` | HDR y SPU aceptados |
| `PUBLISHER_SOCIETY_PR/MR/SR` | `84` | SPU aceptado (se serializa como `084`) |
| `AGADU_RECEIVER_CODE` | `000` | nombre del archivo aceptado |
| `AGADU_TERRITORY_CODE` | `2136` | SPT y SWT: `I2136` |
| `AGADU_SHARES_CHANGE_FLAG` | `N` | SPT y SWT: `N001` |
| `AGADU_TAX_ID` | `000000000` | SPU y SWR aceptados |

Las participaciones editoriales continúan configuradas en 50% para PR, MR y
SR. El perfil genera un solo editor `E` con codigo interno `P000001`, conserva
los codigos internos `W...` para los escritores, incluye `REC` cuando hay datos
de grabacion y no aplica la estructura editor/subeditor de SADAIC.

## Separacion de SADAIC

Las opciones `SADAIC_*` permanecen en un bloque independiente. Solo se usan si
se selecciona expresamente `CWR_PROFILE=SADAIC` o se activa la compatibilidad
`SADAIC_CWR_MODE`. En el perfil AGADU no se ponen en cero las participaciones de
propiedad, no se omiten registros `REC` y no se genera el segundo `SPU` de
subeditor.

## Pruebas

`AGADUCWRTest` valida el nombre del archivo, el orden y largo de registros y las
posiciones de los campos aceptados de HDR, SPU, SPT, SWR, SWT, PWR y REC. Las
pruebas existentes de SADAIC se conservan para detectar contaminación entre
perfiles.

## Datos operativos pendientes

Antes de desplegar esta rama se debe revisar el entorno del servicio y retirar
o reemplazar valores heredados de `main`, especialmente `SADAIC_CWR_MODE`,
`CWR_RECEIVER_CODE`, `PUBLISHER_NAME` y las tres sociedades del editor. También
quedan fuera del generador y deben confirmarse con AGADU:

- credenciales, canal y convención de transporte del archivo;
- si `_000` seguirá siendo el receptor para todos los lotes futuros;
- afiliaciones e IPI de cada escritor, porque provienen de los datos de obra;
- secuencia anual inicial de producción, que se calcula desde la base de datos;
- comportamiento de obras con varios editores o escritores no controlados, no
  representadas en el lote aceptado recibido.

La estructura implementada está validada únicamente para `NWR` CWR 2.1. No se
debe asumir aceptación de CWR 2.2 o 3.x sin un archivo o especificación de AGADU.
