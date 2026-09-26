#!/usr/bin/env python3
"""Une los lotes de preguntas de parciales/ en un único contenido.json.

Uso:  python unir.py <carpeta-de-la-app> [version]

Cada fichero de parciales/ es una lista JSON de preguntas, o un objeto
{"preguntas": [...]}. El orden de los ficheros no importa: el orden de
estudio lo decide cada móvil con su propia semilla.

Si contenido.json ya existe, se conservan los ids que ya estaban y solo
se añaden los nuevos: los ids son la memoria del progreso y no se tocan.
"""
import json
import sys
from pathlib import Path


def main(carpeta, version=None):
    raiz = Path(carpeta)
    parciales = raiz / "parciales"
    if not parciales.is_dir():
        print(f"No existe {parciales}")
        return 2

    nuevas, vistos, choques = [], set(), []
    for f in sorted(parciales.glob("*.json")):
        datos = json.loads(f.read_text(encoding="utf-8"))
        lote = datos["preguntas"] if isinstance(datos, dict) else datos
        for p in lote:
            if p["id"] in vistos:
                choques.append((p["id"], f.name))
                continue
            vistos.add(p["id"])
            nuevas.append(p)

    destino = raiz / "contenido.json"
    previas = []
    if destino.exists():
        previas = json.loads(destino.read_text(encoding="utf-8")).get("preguntas", [])

    por_id = {p["id"]: p for p in previas}
    anadidas = 0
    for p in nuevas:
        if p["id"] not in por_id:
            anadidas += 1
        por_id[p["id"]] = p  # el lote manda: así se corrigen preguntas existentes

    salida = {
        "version": version or json.loads(destino.read_text(encoding="utf-8")).get("version", "1")
        if destino.exists() else (version or "1"),
        "preguntas": list(por_id.values()),
    }
    destino.write_text(json.dumps(salida, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"{len(salida['preguntas'])} preguntas en contenido.json ({anadidas} nuevas)")
    if choques:
        print("\nIds repetidos entre lotes (se ha usado el primero):")
        for i, f in choques:
            print(f"  {i} en {f}")
        return 1
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
