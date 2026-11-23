# Web de la Asociación de Jóvenes Lingüistas

Código de la web de la AJL. La web se genera con Hugo a partir de textos en Markdown y fichas de datos en YAML. Cada cambio en la rama `main` publica la web de nuevo en GitHub Pages en uno o dos minutos.

## Editar con Pages CMS

1. Entrar en <https://app.pagescms.org> con la cuenta de GitHub que tenga acceso al repositorio.
2. Elegir el repositorio de la web y la rama `main`.
3. En el menú lateral aparecen los formularios: cada página, cada congreso, cada publicación, cada miembro de la Junta y cada curso de la Junta tiene el suyo.
4. Al pulsar «Save», Pages CMS guarda el cambio en el repositorio y la web se publica sola. El estado de la publicación se ve en la pestaña «Actions» del repositorio.

Los documentos (PDF, Word) se suben en «Documentos» y las imágenes en «Imágenes». Conviene nombrar los archivos sin espacios ni tildes.

## Dónde está cada cosa

| Contenido | Formulario en Pages CMS | Archivo |
| --- | --- | --- |
| Portada | Portada | `content/_index.md` |
| Páginas de texto (La Asociación, Sorteo AJL, Hazte socio, Convenio, Estudios Interlingüísticos, XLI Congreso Málaga 2027, páginas en otras lenguas) | Páginas | `content/*.md` |
| Seminarios AJL y sus ciclos | Seminarios AJL | `content/seminarios-ajl/` |
| Estatutos (texto y PDF del lector) | Estatutos | `content/estatutos.md` |
| Premios AJL y Ayudas económicas | Premios AJL, Ayudas económicas | `content/premios-ajl.md`, `content/ayudas-economicas.md` |
| Congreso anual: texto y documentos de candidatura | Congreso anual | `content/congresos-anteriores.md` |
| Congresos (las 41 ediciones, el mapa y las portadas) | Congresos | `data/congresos/` |
| Ciudades del mapa | Sedes del mapa | `data/sedes.yaml` |
| Miembros actuales de la Junta (cargo, contacto, retrato, biodata) | Junta Directiva (miembros actuales) | `content/junta-directiva/` |
| Composición de la Junta por cursos | Juntas por curso | `data/juntas/` |
| Antiguos miembros e histórico | Junta Directiva (página…) | `content/junta-directiva/_index.md` |
| Publicaciones | Publicaciones | `data/publicaciones/` |
| Socios fundadores | Socios fundadores | `data/socios/` |
| Dirección, correo y redes | Dirección y contacto | `data/sitio.yaml` |
| Menú y mapa del sitio | Menú y mapa del sitio | `data/menu.yaml` |
| Documentos | (Documentos) | `static/wp-content/uploads/` |
| Imágenes | (Imágenes) | `static/imagenes/` |

Los documentos de la web anterior conservan su dirección (`/wp-content/uploads/año/mes/archivo`), de modo que los enlaces antiguos siguen funcionando cuando el dominio apunte a esta web.

## Añadir un congreso

1. En «Congresos», crear una ficha nueva con el número romano, el número de edición, el nombre, el año, las fechas, la universidad, la web y el libro de resúmenes.
2. En «Sede», escribir el identificador de la ciudad tal como figura en «Sedes del mapa» (por ejemplo `salamanca`). Si la ciudad no está, añadirla en «Sedes del mapa» con su latitud y su longitud; la posición en el mapa se calcula sola.
3. Si es el próximo congreso, marcar «Es el próximo congreso» e indicar su página. Solo una ficha puede estar marcada; al celebrarse, se desmarca.
4. La portada del libro de resúmenes, si se sube, aparece en «Últimos congresos», que muestra las cinco ediciones más recientes ya celebradas. Las anteriores pasan a la cronología.

El mapa une con una línea las cinco ediciones más recientes. La curva de cada tramo se calcula sola; el campo «Curva del tramo» solo hace falta para corregir un tramo que tape un nombre.

## Añadir una publicación

En «Publicaciones», crear una ficha con los editores tal como aparecen en la cita, la función entre paréntesis («Eds.», «Coords.»), el año, el título, el enlace, el resto de la cita y la cubierta. La lista se ordena por año, de la más reciente a la más antigua; dentro del mismo año manda el campo «Orden».

## Añadir un curso de la Junta Directiva

1. En «Junta Directiva (miembros actuales)», crear o actualizar la ficha de cada miembro: nombre, dirección de la página, cargo, universidad, correo, ORCID, retrato, biodata en PDF y el texto de la biodata. Las fichas de quienes dejan la Junta se borran.
2. En «Juntas por curso», crear el curso nuevo (por ejemplo `2026-2027`) y añadir un cargo por miembro eligiendo su ficha. El curso más reciente se muestra como Junta actual, con los nombres enlazados a cada página; los demás pasan al histórico.
3. En el curso que termina, rellenar a mano el cargo, el nombre, la universidad y el ORCID de cada persona. Si existe el PDF de esa Junta, se adjunta en el mismo curso. Así el histórico no depende de las fichas de los miembros actuales.
4. Añadir a quienes salen a «Miembros de Juntas Directivas anteriores» en la página de la Junta.

## Trabajar en local

Hace falta Hugo 0.170.0 (extended no es necesario).

```
hugo server
```

La web queda en <http://localhost:1313/>. Tras construir con `hugo --minify`, los scripts de `scripts/` comprueban la web construida (necesitan Python con BeautifulSoup y, los dos últimos, Playwright con Chromium y un servidor local sobre `public/`):

```
python3 scripts/comprobar_enlaces.py public
python3 scripts/comprobar_contenido.py <copia de pages_v1.json> public
python3 scripts/comprobar_paginas.py public http://127.0.0.1:8765
python3 scripts/comprobar_diseno.py public http://127.0.0.1:8765
```

El primero comprueba los enlaces internos y los documentos; el segundo, que cada frase de las páginas de WordPress esté en la web nueva; el tercero, cada página en el navegador a cinco anchos; el cuarto, el contraste y las reglas de `design.md` que se pueden medir.

El lector de PDF de Estatutos usa pdf.js (`pdfjs-dist`), copiado en `static/vendor/pdfjs-dist/`. Para actualizarlo se cambia la versión en `package.json` y se ejecutan `npm install` y `npm run vendor`. Después se cambia `pdfjs` en `hugo.toml`.

## Publicación y dominio

El flujo `.github/workflows/publicar.yml` construye y publica la web. En el repositorio, «Settings > Pages > Source» debe estar en «GitHub Actions». La dirección base se toma de la configuración de Pages, así que no hay que cambiar `hugo.toml` al pasar al dominio propio.

Con este tipo de publicación, GitHub no lee el archivo `static/CNAME`: el dominio se activa en «Settings > Pages > Custom domain». Mientras dure la prueba, ese campo se deja vacío y la web se sirve en `asociacionjoveneslinguistas.github.io`.
