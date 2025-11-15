import argparse
import json
import os
import sys
from collections import deque, defaultdict

class ConfigError(Exception):
    pass


# Конфигурация

def load_config(path):
    if not os.path.exists(path):
        raise ConfigError(f"Файл конфигурации не найден: {path}")
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # Минимальная валидация для этапа 3
    required = ["package_name", "test_repo_mode"]
    for r in required:
        if r not in cfg or not cfg[r].strip():
            raise ConfigError(f"Параметр '{r}' обязателен")
    # max_depth
    cfg["max_depth"] = int(cfg.get("max_depth", 1000))
    cfg["filter_substring"] = cfg.get("filter_substring", "")
    # test_graph_file обязателен, если режим file
    if cfg["test_repo_mode"] == "file":
        if "test_graph_file" not in cfg or not os.path.exists(cfg["test_graph_file"]):
            raise ConfigError(f"Для test_repo_mode=file требуется существующий 'test_graph_file'")
    return cfg


# Чтение графа из тестового файла

def read_test_graph(file_path):
    """
    Формат: Package: Dep1,Dep2,...
    Пакеты — большие латинские буквы
    """
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


# BFS обход графа

def bfs_dependencies(graph, start_pkg, max_depth=1000, filter_substring=""):
    visited = set()
    result = []
    queue = deque()
    queue.append((start_pkg, 0))

    while queue:
        node, depth = queue.popleft()        # Извлекаем узел и его текущую глубину из очереди
        if node in visited:
            continue                         # Если узел уже обработан, пропускаем его (чтобы избежать повторов и циклов)
        if filter_substring and filter_substring in node:
            continue                         # Если имя узла содержит фильтрующую подстроку, пропускаем его и его зависимости
        visited.add(node)                     # Помечаем узел как посещённый
        result.append((node, depth))         # Добавляем узел и его глубину в результирующий список
        if depth >= max_depth:
            continue                         # Если достигли максимальной глубины обхода, не добавляем его зависимости в очередь
        for dep in graph.get(node, []):      # Для каждой зависимости текущего узла
            queue.append((dep, depth + 1))   # Добавляем зависимость в очередь с увеличенной глубиной на 1
    
    return result

# Основная функция

def main():
    parser = argparse.ArgumentParser(description="Этап 3 BFS граф зависимостей")
    parser.add_argument("-c", "--config", required=True, help="Путь к JSON конфигу")
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
    except ConfigError as e:
        print("Ошибка конфигурации:", e, file=sys.stderr)
        sys.exit(1)

    start_pkg = cfg["package_name"].strip()
    max_depth = cfg["max_depth"]
    filter_substring = cfg["filter_substring"]
    test_mode = cfg["test_repo_mode"]

    # Формируем граф
    if test_mode == "file":
        graph = read_test_graph(cfg["test_graph_file"])
    else:
        sys.exit(2)

    # BFS
    deps = bfs_dependencies(graph, start_pkg, max_depth, filter_substring)

    # Вывод
    if not deps:
        print("Ни одного пакета не найдено (возможно, фильтр убрал все пакеты).")
    else:
        print("Пакеты, посещённые при BFS (node : depth):")
        for node, depth in deps:
            print(f"- {node} : {depth}")

if __name__ == "__main__":
    main()
