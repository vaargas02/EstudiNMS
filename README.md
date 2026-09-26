# Raíz y nervio

App de estudio offline (PWA) para la unidad neuromuscular: inervación muscular,
dermatomas, reflejos, miotomas, plexos, localización raíz/nervio y EMG.
437 preguntas con repetición espaciada y 19 secciones de consulta.

## Desplegar

1. Sube todos los archivos **a la raíz** del repositorio.
2. Settings › Pages › rama `main`, carpeta `/ (root)`.
3. Abre la URL en el móvil y añádela a la pantalla de inicio.

Si el repositorio no se llama `raiz-y-nervio`, cambia `app.rutaBase` en
`config.json` por `/nombre-del-repo/`.

## Venir de la versión anterior

Tu progreso de la versión 1.x no se pierde, pero hay que convertirlo una vez:

1. En la app antigua: Ajustes › Exportar progreso.
2. Abre `pasar-progreso.html` (en el móvil, añadiendo `pasar-progreso.html` al
   final de la URL de la app) y elige ese archivo.
3. En la app nueva: Ajustes › Importar progreso, con el archivo convertido.

## Imágenes de músculos (opcional)

```
pip3 install pillow
python3 imagenes-musculos.py
```

Descarga las láminas de Wikimedia a `img/musculos/` y las enlaza con sus
preguntas. Después sube `img/` y `contenido.json`, y sube en uno `versionCache`
y `VERSION`.

## Cambiar o añadir preguntas

Las preguntas viven en `parciales/`, un archivo por subtema. Para cambiar una,
edítala **manteniendo su `id`**: el progreso está guardado por `id`. Después:

```
python3 unir.py . 2026-10-01      # o la fecha del día
python3 validar.py .
```

Y sube en uno `app.versionCache` en `config.json` y `VERSION` en `sw.js`, o el
móvil seguirá sirviendo la versión anterior desde la caché.
