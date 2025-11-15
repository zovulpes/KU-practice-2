import argparse
import json
import os
import sys
from collections import defaultdict, deque

class ConfigError(Exception):
    pass

# --- Загрузка конфигурации ---
def load_config(path):
    if not os.path.exists(path):
        raise ConfigError(f"Файл конфигурации не найден: {path}")
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    required = ["package_name", "test_repo_mode"]
    for r in required:
        if r not in cfg or not cfg[r].strip():
            raise ConfigError(f"Параметр '{r}' обязателен")
    cfg["max_depth"] = int(cfg.get("max_depth", 1000))
    cfg["filter_substring"] = cfg.get("filter_substring", "")
    if cfg["test_repo_mode"] == "file":
        if "test_graph_file" not in cfg or not os.path.exists(cfg["test_graph_file"]):
            raise ConfigError(f"Для test_repo_mode=file требуется существующий 'test_graph_file'")
    return cfg

# --- Чтение графа из тестового файла ---
def read_test_graph(file_path):
    graph = defaultdict(list)
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            pkg, deps = line.split(":", 1)
            pkg = pkg.strip()
            dep_list = [d.strip() for d in deps.split(",") if d.strip()]
            graph[pkg] = dep_list
    return graph

# --- BFS обход графа (из этапа 3) ---
def bfs_dependencies(graph, start_pkg, max_depth=1000, filter_substring=""):
    visited = set()
    result = []
    queue = deque()
    queue.append((start_pkg, 0))
    while queue:
        node, depth = queue.popleft()
        if node in visited:
            continue
        if filter_substring and filter_substring in node:
            continue
        visited.add(node)
        result.append((node, depth))
        if depth >= max_depth:
            continue
        for dep in graph.get(node, []):
            queue.append((dep, depth + 1))
    return result

# --- Topological sort (порядок загрузки зависимостей) ---
def topological_sort(graph, start_pkg):
    visited = set()
    temp_mark = set()  # для обнаружения циклов
    result = []

    def visit(node):
        if node in temp_mark:
            raise ValueError(f"Обнаружен цикл в зависимостях: {node}")
        if node not in visited:
            temp_mark.add(node)
            for dep in graph.get(node, []):
                visit(dep)
            temp_mark.remove(node)
            visited.add(node)
            result.append(node)

    try:
        visit(start_pkg)
    except ValueError as e:
        print("Предупреждение:", e)
    result.reverse()  # инвертируем для порядка загрузки
    return result

# --- Основная функция ---
def main():
    parser = argparse.ArgumentParser(description="Этап 4: порядок загрузки зависимостей")
    parser.add_argument("-c", "--config", required=True, help="Путь к JSON конфигу")
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
    except ConfigError as e:
        print("Ошибка конфигурации:", e, file=sys.stderr)
        sys.exit(1)

    start_pkg = cfg["package_name"].strip()
    test_mode = cfg["test_repo_mode"]

    if test_mode == "file":
        graph = read_test_graph(cfg["test_graph_file"])
    else:
        print("Режим Maven пока не реализован. Используйте test_repo_mode=file для теста.")
        sys.exit(2)

    print("Граф зависимостей:", graph)

    # Порядок обхода BFS (как в этапе 3)
    bfs_result = bfs_dependencies(graph, start_pkg, cfg["max_depth"], cfg["filter_substring"])
    print("\nBFS обход (node : depth):")
    for node, depth in bfs_result:
        print(f"- {node} : {depth}")

    # Топологическая сортировка (порядок загрузки)
    print("\nПорядок загрузки зависимостей (topological sort):")
    load_order = topological_sort(graph, start_pkg)
    print(" -> ".join(load_order))

if __name__ == "__main__":
    main()
