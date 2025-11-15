import argparse
import json
import os
import sys
import subprocess
from collections import defaultdict

class ConfigError(Exception):
    pass

# --- Загрузка конфигурации ---
def load_config(path):
    if not os.path.exists(path):
        raise ConfigError(f"Файл конфигурации не найден: {path}")
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    required = ["test_repo_mode", "test_graph_file", "output_image"]
    for r in required:
        if r not in cfg or not cfg[r].strip():
            raise ConfigError(f"Параметр '{r}' обязателен")
    return cfg

# --- Чтение графа из тестового файла ---
def read_test_graph(file_path):
    graph = defaultdict(list)
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            pkg, deps = line.split(":", 1)
            pkg = pkg.strip()
            dep_list = [d.strip() for d in deps.split(",") if d.strip()]
            graph[pkg] = dep_list
    return graph

# --- Генерация текста Mermaid для заданного пакета ---
def generate_mermaid(graph, start_pkg):
    visited = set()
    lines = ["graph TD"]

    def visit(node):
        if node in visited:
            return
        visited.add(node)
        for dep in graph.get(node, []):
            lines.append(f"    {node} --> {dep}")
            visit(dep)

    visit(start_pkg)
    return "\n".join(lines)

# --- Сохранение .mmd и конвертация в PNG ---
def save_mermaid_png(mermaid_text, base_name):
    mmd_file = f"{base_name}.mmd"
    png_file = f"{base_name}.png"

    with open(mmd_file, "w", encoding="utf-8") as f:
        f.write(mermaid_text)

    try:
        subprocess.run(["mmdc", "-i", mmd_file, "-o", png_file], check=True)
        print(f"Сгенерирован PNG: {png_file}")
    except FileNotFoundError:
        print("Mermaid CLI (mmdc) не найден. Установите Node.js и mmdc, чтобы генерировать PNG.")
    except subprocess.CalledProcessError as e:
        print("Ошибка при генерации PNG:", e)

# --- Основная функция ---
def main():
    parser = argparse.ArgumentParser(description="Этап 5: визуализация графа зависимостей")
    parser.add_argument("-c", "--config", required=True, help="Путь к JSON конфигу")
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
    except ConfigError as e:
        print("Ошибка конфигурации:", e, file=sys.stderr)
        sys.exit(1)

    if cfg["test_repo_mode"] != "file":
        print("Используйте test_repo_mode=file для тестирования.")
        sys.exit(2)

    graph = read_test_graph(cfg["test_graph_file"])
    print("Граф зависимостей:", graph)

    # Демонстрация для трёх пакетов (можно менять)
    test_packages = ["A", "B", "C"]
    for pkg in test_packages:
        if pkg not in graph:
            print(f"Пакет {pkg} отсутствует в графе.")
            continue
        print(f"\nГенерация Mermaid для пакета {pkg}...")
        mermaid_text = generate_mermaid(graph, pkg)
        save_mermaid_png(mermaid_text, f"{cfg['output_image'].split('.')[0]}_{pkg}")

if __name__ == "__main__":
    main()