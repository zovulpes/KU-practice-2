#!/usr/bin/env python3
"""
Этап 2 (минимальный, локальный репозиторий)
Сбор прямых зависимостей Maven-проекта.
Только локальный каталог, без git и выбора POM.
"""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET

# -----------------------------
# Загрузка и минимальная валидация конфига
# -----------------------------
def load_config(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Конфиг не найден: {path}")
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    # минимальная валидация
    if "package_name" not in cfg or not cfg["package_name"].strip():
        raise ValueError("package_name обязателен")
    if "repo" not in cfg or not cfg["repo"].strip():
        raise ValueError("repo обязателен")
    if not os.path.isdir(cfg["repo"]):
        raise ValueError(f"Папка репозитория не существует: {cfg['repo']}")
    return cfg

# -----------------------------
# Поиск pom.xml
# -----------------------------
def find_pom(root_path):
    for dirpath, dirnames, filenames in os.walk(root_path):
        if "target" in dirpath.split(os.sep):
            continue
        for fname in filenames:
            if fname.lower() == "pom.xml":
                return os.path.join(dirpath, fname)
    return None

# -----------------------------
# Парсинг прямых зависимостей
# -----------------------------
def parse_dependencies(pom_path):
    tree = ET.parse(pom_path)
    root = tree.getroot()

    def local(tag): return tag.split("}")[-1] if "}" in tag else tag

    deps = []
    for dep_parent in root.findall(".//{*}dependencies"):
        for dep in dep_parent.findall("{*}dependency"):
            gid = dep.find("{*}groupId")
            aid = dep.find("{*}artifactId")
            ver = dep.find("{*}version")
            scope = dep.find("{*}scope")
            deps.append({
                "groupId": (gid.text.strip() if gid is not None and gid.text else ""),
                "artifactId": (aid.text.strip() if aid is not None and aid.text else ""),
                "version": (ver.text.strip() if ver is not None and ver.text else "<no-version>"),
                "scope": (scope.text.strip() if scope is not None and scope.text else "compile"),
            })
    return deps

# -----------------------------
# Основная функция
# -----------------------------
def main():
    parser = argparse.ArgumentParser(description="Этап 2 минимальный")
    parser.add_argument("-c", "--config", required=True, help="Путь к JSON конфигу")
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
    except Exception as e:
        print("Ошибка конфига:", e, file=sys.stderr)
        sys.exit(1)

    pom_path = find_pom(cfg["repo"])
    if not pom_path:
        print("pom.xml не найден в репозитории", file=sys.stderr)
        sys.exit(2)

    print(f"Используется POM: {pom_path}")

    deps = parse_dependencies(pom_path)
    if not deps:
        print("Прямых зависимостей не найдено.")
    else:
        print("Прямые зависимости (groupId : artifactId : version [scope]):")
        for d in deps:
            print(f"- {d['groupId']} : {d['artifactId']} : {d['version']} [{d['scope']}]")

if __name__ == "__main__":
    main()
