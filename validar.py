#!/usr/bin/env python3
"""Comprueba una app de estudio antes de desplegarla.

Uso:  python validar.py <carpeta-de-la-app>

Errores  -> hay que arreglarlos, la app fallará o se comportará mal.
Avisos   -> conviene mirarlos, suelen ser preguntas mal construidas.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

errores, avisos = [], []


def err(m): errores.append(m)
def avi(m): avisos.append(m)


def cargar(p: Path):
    if not p.exists():
        err(f"falta {p.name}")
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        err(f"{p.name}: JSON inválido en línea {e.lineno}: {e.msg}")
        return None


def main(carpeta):
    raiz = Path(carpeta)
    if not raiz.is_dir():
        print(f"No existe la carpeta {carpeta}")
        return 2

    cfg = cargar(raiz / "config.json")
    cont = cargar(raiz / "contenido.json")
    teo = cargar(raiz / "teoria.json") if (raiz / "teoria.json").exists() else {"secciones": []}

    for f in ("index.html", "motor.js", "estilos.css", "sw.js", "manifest.json"):
        if not (raiz / f).exists():
            err(f"falta {f}")
    for f in ("icono-192.png", "icono-512.png"):
        if not (raiz / f).exists():
            avi(f"falta {f}: la app no tendrá icono en la pantalla de inicio (hacer-iconos.py)")

    if not cfg or not cont:
        return informe()

    # ---- config ----
    for ruta in ("app.id", "app.nombre", "app.versionCache", "ejeAgrupacion.clave",
                 "estudio.nuevasPorDia", "srs.facilidadInicial", "modulos.teoria"):
        nodo, ok = cfg, True
        for parte in ruta.split("."):
            if isinstance(nodo, dict) and parte in nodo:
                nodo = nodo[parte]
            else:
                ok = False
                break
        if not ok:
            err(f"config.json: falta {ruta}")

    if not re.fullmatch(r"[a-z0-9-]+", str(cfg.get("app", {}).get("id", ""))):
        err("config.json: app.id debe ir en minúsculas, sin espacios (se usa como clave de almacenamiento)")

    sw = (raiz / "sw.js").read_text(encoding="utf-8") if (raiz / "sw.js").exists() else ""
    m = re.search(r"const\s+VERSION\s*=\s*(\d+)", sw)
    if m and int(m.group(1)) != cfg.get("app", {}).get("versionCache"):
        err(f"sw.js VERSION ({m.group(1)}) no coincide con config.json app.versionCache "
            f"({cfg['app'].get('versionCache')}): el móvil seguirá viendo la versión antigua")

    eje = cfg.get("ejeAgrupacion", {}).get("clave", "grupo")
    con_imagenes = cfg.get("modulos", {}).get("imagenes", False)

    # ---- preguntas ----
    preguntas = cont.get("preguntas", [])
    if not preguntas:
        err("contenido.json: no hay preguntas")
        return informe()

    ids = Counter(p.get("id") for p in preguntas)
    for i, n in ids.items():
        if n > 1:
            err(f"id repetido: {i} ({n} veces). Los ids tienen que ser únicos y estables.")

    enunciados = Counter(p.get("enunciado", "").strip().lower() for p in preguntas)
    for e, n in enunciados.items():
        if n > 1 and e:
            avi(f"enunciado repetido {n} veces: «{e[:70]}…»")

    secciones = {s.get("id") for s in teo.get("secciones", [])}
    largo_correcta = 0

    for p in preguntas:
        pid = p.get("id", "(sin id)")
        for campo in ("id", "enunciado", "opciones", "correcta", "explicacion", "tema"):
            if campo not in p:
                err(f"{pid}: falta el campo «{campo}»")
        if eje not in p and eje != "tema":
            err(f"{pid}: falta «{eje}», que es la clave del mapa de aciertos")

        ops = p.get("opciones", [])
        if not isinstance(ops, list) or not (2 <= len(ops) <= 5):
            err(f"{pid}: debe tener entre 2 y 5 opciones (tiene {len(ops) if isinstance(ops, list) else '?'})")
        elif len(set(o.strip().lower() for o in ops)) != len(ops):
            err(f"{pid}: hay opciones repetidas")

        c = p.get("correcta")
        if not isinstance(c, int) or not (0 <= c < len(ops)):
            err(f"{pid}: «correcta» fuera de rango")
        elif ops:
            if len(ops[c]) == max(len(o) for o in ops) and len(ops) > 2:
                largo_correcta += 1

        for mala in ("todas las anteriores", "ninguna de las anteriores", "a y b son"):
            if any(mala in o.lower() for o in ops):
                avi(f"{pid}: evita las opciones del tipo «{mala}…»")

        expl = p.get("explicacion", "")
        if len(expl) < 40:
            avi(f"{pid}: explicación muy corta ({len(expl)} caracteres)")
        if len(expl) > 700:
            avi(f"{pid}: explicación muy larga ({len(expl)} caracteres), se lee mal en el móvil")

        if p.get("teoria") and p["teoria"] not in secciones:
            err(f"{pid}: apunta a la sección de teoría «{p['teoria']}», que no existe")

        if p.get("imagen"):
            if not con_imagenes:
                avi(f"{pid}: tiene imagen pero modulos.imagenes está en false")
            elif not (raiz / p["imagen"]).exists():
                err(f"{pid}: no existe el fichero {p['imagen']}")

    if preguntas and largo_correcta / len(preguntas) > 0.6:
        avi(f"la correcta es la opción más larga en {largo_correcta} de {len(preguntas)} preguntas: "
            "se acaba acertando por la forma, no por saber")

    # ---- reparto por tema ----
    subs = Counter((p.get("tema", "—"), p.get("subtema", "—")) for p in preguntas)
    for (tm, sb), n in subs.items():
        if n < 3:
            avi(f"«{tm} › {sb}» solo tiene {n} pregunta(s): agrúpalo con otro subtema")

    orden = cfg.get("ejeAgrupacion", {}).get("orden") or []
    if orden:
        presentes = {p.get(eje) for p in preguntas}
        for g in presentes - set(orden):
            avi(f"el grupo «{g}» no está en ejeAgrupacion.orden y saldrá al final del mapa")

    # ---- teoría ----
    if cfg.get("modulos", {}).get("teoria"):
        if not teo.get("secciones"):
            err("modulos.teoria es true pero teoria.json no tiene secciones")
        ids_t = Counter(s.get("id") for s in teo.get("secciones", []))
        for i, n in ids_t.items():
            if n > 1:
                err(f"teoria.json: id de sección repetido: {i}")
        for s in teo.get("secciones", []):
            if len(s.get("contenido", "")) < 120:
                avi(f"teoria.json: la sección «{s.get('titulo', s.get('id'))}» es muy breve")
        sin_teoria = [s for s in secciones if not any(p.get("teoria") == s for p in preguntas)]
        if sin_teoria:
            avi(f"{len(sin_teoria)} sección(es) de teoría sin ninguna pregunta enlazada: "
                + ", ".join(sorted(sin_teoria)[:5]))

    print(f"\n{len(preguntas)} preguntas · {len(teo.get('secciones', []))} secciones de teoría · "
          f"{len(subs)} subtemas")
    return informe()


def informe():
    if errores:
        print(f"\nERRORES ({len(errores)})")
        for e in errores:
            print("  ✗ " + e)
    if avisos:
        print(f"\nAVISOS ({len(avisos)})")
        for a in avisos:
            print("  · " + a)
    if not errores and not avisos:
        print("\nTodo correcto.")
    elif not errores:
        print("\nSin errores. Los avisos son opcionales.")
    return 1 if errores else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
