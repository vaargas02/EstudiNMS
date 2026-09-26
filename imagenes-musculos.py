#!/usr/bin/env python3
"""
Raíz y nervio: imágenes de músculos (opcional)
==============================================

Descarga de Wikimedia la lámina anatómica de cada músculo (casi siempre la de
Gray's Anatomy, con el músculo resaltado) y la enlaza con sus preguntas.

La app funciona perfectamente sin esto. Si lo ejecutas, las preguntas de
músculos pasan a mostrar su lámina.

Uso (desde la carpeta de la app, donde está index.html):
    python3 imagenes-musculos.py            # descarga lo que falte y enlaza
    python3 imagenes-musculos.py --force    # vuelve a descargar todo

Requisitos: Python 3.8+. Recomendado: pip install pillow (reduce el tamaño).

Después de ejecutarlo, sube al repositorio la carpeta img/ y contenido.json,
y sube en uno versionCache en config.json y VERSION en sw.js.

Para cambiar la lámina de un músculo, pon el nombre del archivo de Commons en
OVERRIDES (abajo) y ejecuta con --force.
"""
import json, os, re, sys, time, urllib.parse, urllib.request, urllib.error, html, io

# id de la app -> título del artículo en la Wikipedia inglesa
MUSCLES = {
    'trapecio': 'Trapezius', 'romboides': 'Rhomboid major muscle', 'serrato': 'Serratus anterior muscle',
    'pectclav': 'Pectoralis major muscle', 'pectest': 'Pectoralis major muscle',
    'supraesp': 'Supraspinatus muscle', 'infraesp': 'Infraspinatus muscle', 'subesc': 'Subscapularis muscle',
    'dorsalancho': 'Latissimus dorsi muscle', 'redmayor': 'Teres major muscle', 'deltoides': 'Deltoid muscle',
    'redmenor': 'Teres minor muscle', 'biceps': 'Biceps', 'braquial': 'Brachialis muscle', 'triceps': 'Triceps',
    'braquiorr': 'Brachioradialis', 'erlc': 'Extensor carpi radialis longus muscle', 'supinador': 'Supinator muscle',
    'ecc': 'Extensor carpi ulnaris muscle', 'edc': 'Extensor digitorum muscle', 'alp': 'Abductor pollicis longus muscle',
    'elp': 'Extensor pollicis longus muscle', 'ecp': 'Extensor pollicis brevis muscle', 'eip': 'Extensor indicis muscle',
    'pronred': 'Pronator teres muscle', 'frc': 'Flexor carpi radialis muscle', 'fsd': 'Flexor digitorum superficialis muscle',
    'fdp23': 'Flexor digitorum profundus muscle', 'fdp45': 'Flexor digitorum profundus muscle',
    'flp': 'Flexor pollicis longus muscle', 'pcuad': 'Pronator quadratus muscle', 'acp': 'Abductor pollicis brevis muscle',
    'oponente': 'Opponens pollicis muscle', 'lumb12': 'Lumbricals of the hand', 'lumb34': 'Lumbricals of the hand',
    'fcc': 'Flexor carpi ulnaris muscle', 'adm': 'Abductor digiti minimi muscle of hand', 'pid': 'Dorsal interossei of the hand',
    'intpalm': 'Palmar interossei muscles', 'aductpulg': 'Adductor pollicis muscle',
    'iliopsoas': 'Iliopsoas', 'sartorio': 'Sartorius muscle', 'cuadriceps': 'Quadriceps femoris muscle',
    'aductlargo': 'Adductor longus muscle', 'gracil': 'Gracilis muscle', 'aductmayor': 'Adductor magnus muscle',
    'gluteomedio': 'Gluteus medius', 'tfl': 'Tensor fasciae latae muscle', 'gluteomayor': 'Gluteus maximus',
    'semis': 'Semitendinosus muscle', 'bflarga': 'Biceps femoris muscle', 'bfcorta': 'Biceps femoris muscle',
    'tibant': 'Tibialis anterior muscle', 'eldg': 'Extensor hallucis longus muscle', 'eld': 'Extensor digitorum longus muscle',
    'pedio': 'Extensor digitorum brevis muscle', 'peroneos': 'Fibularis longus', 'tibpost': 'Tibialis posterior muscle',
    'gastro': 'Gastrocnemius muscle', 'soleo': 'Soleus muscle', 'fld': 'Flexor digitorum longus muscle',
    'fldg': 'Flexor hallucis longus muscle', 'abdhallux': 'Abductor hallucis muscle',
    'ecm': 'Sternocleidomastoid muscle', 'diafragma': 'Thoracic diaphragm', 'flexcuello': 'Longus colli muscle',
    'paraesp': 'Erector spinae muscles', 'rectoabd': 'Rectus abdominis muscle', 'orbocular': 'Orbicularis oculi muscle',
    'orbboca': 'Orbicularis oris muscle', 'masetero': 'Masseter muscle', 'lengua': 'Genioglossus',
    'elevpalp': 'Levator palpebrae superioris muscle', 'rectolat': 'Lateral rectus muscle',
    'oblsup': 'Superior oblique muscle', 'velo': 'Levator veli palatini',
}

# Imágenes elegidas a mano (id -> nombre del archivo en Commons, sin "File:").
# Ejemplo: 'deltoides': 'Deltoid muscle top8.png',
OVERRIDES = {
}

API = 'https://en.wikipedia.org/w/api.php'
UA = 'RaizYNervio-study-app/1.3 (personal educational use; one-off downloader, ~75 images, throttled)'
PAUSE = 3  # segundos entre músculos
MAX_W = 720          # ancho final
THUMB_W = 960        # ancho que se pide a Wikimedia
OUT = 'img/musculos'


def fetch(url, timeout=60):
    """Descarga con reintentos: si Wikimedia pide calma (429/503), espera y repite."""
    waits = [10, 20, 40, 60, 90, 120]
    for attempt in range(len(waits) + 1):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503) or attempt == len(waits):
                raise
            ra = e.headers.get('Retry-After')
            w = int(ra) if ra and ra.isdigit() else waits[attempt]
            print(f'      Wikimedia pide esperar; reintento en {w} s...', flush=True)
            time.sleep(w)


def get_json(params):
    params = dict(params, format='json', formatversion='2')
    return json.loads(fetch(API + '?' + urllib.parse.urlencode(params), timeout=30))


def get_bytes(url):
    return fetch(url)


def raster(name):
    return name.lower().rsplit('.', 1)[-1] in ('png', 'jpg', 'jpeg')


def choose_image(title):
    """Devuelve el nombre del archivo más adecuado para el artículo."""
    d = get_json({'action': 'query', 'titles': title, 'redirects': 1,
                  'prop': 'pageimages|images', 'piprop': 'name', 'imlimit': 'max'})
    page = d['query']['pages'][0]
    lead = page.get('pageimage')
    imgs = [i['title'].split(':', 1)[1] for i in page.get('images', [])]
    key = title.split()[0].lower()
    # 1) imagen principal del artículo, si es una imagen fija
    if lead and raster(lead):
        return lead
    # 2) imagen fija cuyo nombre contenga el nombre del músculo
    for n in imgs:
        if raster(n) and key in n.lower():
            return n
    # 3) lámina de Gray
    for n in imgs:
        if raster(n) and 'gray' in n.lower():
            return n
    # 4) último recurso: la principal aunque sea animada (se usa el primer fotograma)
    return lead


def image_info(name):
    d = get_json({'action': 'query', 'titles': 'File:' + name, 'prop': 'imageinfo',
                  'iiprop': 'url|extmetadata|mime', 'iiurlwidth': THUMB_W})
    info = d['query']['pages'][0]['imageinfo'][0]
    meta = info.get('extmetadata', {})
    clean = lambda s: re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s or ''))).strip()
    return {
        'url': info.get('thumburl') or info['url'],
        'orig': info['url'],
        'page': info.get('descriptionurl', ''),
        'artist': clean(meta.get('Artist', {}).get('value'))[:120],
        'license': clean(meta.get('LicenseShortName', {}).get('value')),
    }


def slug(s):
    s = re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
    return s[:60]


def save_image(data, base):
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data))
        im.seek(0)
        im = im.convert('RGB')
        if im.width > MAX_W:
            im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
        path = f'{OUT}/{base}.jpg'
        im.save(path, 'JPEG', quality=80, optimize=True, progressive=True)
        return path
    except ImportError:
        ext = 'png' if data[:4] == b'\x89PNG' else 'jpg' if data[:2] == b'\xff\xd8' else 'gif'
        path = f'{OUT}/{base}.{ext}'
        open(path, 'wb').write(data)
        return path


def enlazar(index):
    """Escribe el campo `imagen` en las preguntas de cada músculo."""
    porMusculo = json.load(open('preguntas-por-musculo.json', encoding='utf-8'))
    cont = json.load(open('contenido.json', encoding='utf-8'))
    deId = {}
    for mid, preguntas in porMusculo.items():
        if mid in index and os.path.exists(index[mid]['file']):
            for pid in preguntas:
                deId[pid] = index[mid]['file']
    n = 0
    for p in cont['preguntas']:
        ruta = deId.get(p['id'])
        if ruta:
            p['imagen'] = ruta
            n += 1
        elif p.get('imagen', '').startswith('img/musculos/'):
            del p['imagen']
    json.dump(cont, open('contenido.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return n


def main():
    force = '--force' in sys.argv
    if not os.path.exists('contenido.json'):
        print('Aviso: no veo contenido.json aquí. Ejecuta el script dentro de la carpeta de la app.')
    os.makedirs(OUT, exist_ok=True)
    idx_path = f'{OUT}/index.json'
    index = {}
    if os.path.exists(idx_path) and not force:
        index = json.load(open(idx_path, encoding='utf-8'))
    elif os.path.exists('img/index.json') and not force:
        # Láminas descargadas con la versión anterior de la app: se reaprovechan
        # tal cual en vez de volver a bajarlas de Wikimedia.
        previas = json.load(open('img/index.json', encoding='utf-8'))
        index = {k: v for k, v in previas.items() if v.get('file') and os.path.exists(v['file'])}
        if index:
            print(f'Reutilizo {len(index)} láminas que ya tenías descargadas.\n')
    try:
        import PIL  # noqa
    except ImportError:
        print('Pillow no está instalado: las imágenes ocuparán más. (pip install pillow)\n')

    done_titles = {}  # título -> entrada (para músculos que comparten imagen)
    report = []
    ids = list(MUSCLES)
    for n, mid in enumerate(ids, 1):
        title = MUSCLES[mid]
        prefix = f'[{n:2}/{len(ids)}] {mid:12}'
        if mid in index and not force and os.path.exists(index[mid]['file']):
            print(f'{prefix} ya estaba', flush=True); report.append((mid, title, index[mid].get('name', ''), 'ya estaba'))
            continue
        try:
            if title in done_titles and mid not in OVERRIDES:
                index[mid] = done_titles[title]
                print(f'{prefix} comparte imagen con {title}')
                report.append((mid, title, index[mid]['name'], 'compartida'))
                continue
            name = OVERRIDES.get(mid) or choose_image(title)
            if not name:
                print(f'{prefix} sin imagen'); report.append((mid, title, '', 'sin imagen')); continue
            info = image_info(name)
            time.sleep(1)
            data = get_bytes(info['url'])
            path = save_image(data, slug(os.path.splitext(name)[0]))
            entry = {'file': path, 'name': name, 'page': info['page'],
                     'credit': ', '.join(x for x in [info['artist'], info['license']] if x)}
            index[mid] = entry
            done_titles[title] = entry
            kb = os.path.getsize(path) // 1024
            print(f'{prefix} {name}  ({kb} KB, {info["license"] or "licencia no indicada"})')
            report.append((mid, title, name, info['license']))
        except Exception as e:
            print(f'{prefix} ERROR: {e}')
            report.append((mid, title, '', f'error: {e}'))
        time.sleep(PAUSE)

    json.dump(index, open(idx_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open(f'{OUT}/informe.csv', 'w', encoding='utf-8') as f:
        f.write('id;articulo;archivo;licencia_o_estado\n')
        for r in report:
            f.write(';'.join(str(x).replace(';', ',') for x in r) + '\n')
    total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT)) // 1024
    ok = sum(1 for m in ids if m in index)
    try:
        n = enlazar(index)
        print(f'\nListo: {ok}/{len(ids)} músculos con imagen, {total / 1024:.1f} MB en {OUT}/')
        print(f'{n} preguntas enlazadas a su lámina en contenido.json.')
    except FileNotFoundError as e:
        print(f'\nImágenes descargadas, pero no he podido enlazarlas: falta {e.filename}.')
        print('Ejecuta el script dentro de la carpeta de la app.')
    print(f'Revisa {OUT}/informe.csv; sube img/ y contenido.json, y sube en uno versionCache y VERSION.')


if __name__ == '__main__':
    main()
