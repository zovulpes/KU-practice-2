import argparse
import json
import os
import sys
from urllib.parse import urlparse

# Допустимые значения режима работы с тестовым репозиторием
ALLOWED_TEST_MODES = {"off", "local-file", "mock"}

# Допустимые расширения для файла с изображением графа
ALLOWED_IMAGE_EXTS = {".png", ".svg", ".pdf"}


# Специальное исключение для ошибок конфигурации,
# чтобы отличать их от других типов ошибок.
class ConfigError(Exception):
    pass


def is_probably_url(s: str) -> bool:
    """
    Простая проверка того, похоже ли значение на URL.
    Используется для различения URL и локальных путей к файлам.
    """
    try:
        p = urlparse(s)
        # Мы считаем строку URL-like, если есть схема (http/https/git/ssh),
        # и есть либо сетевой адрес (netloc), либо путь.
        return p.scheme in ('http', 'https', 'git', 'ssh') and bool(p.netloc or p.path)
    except Exception:
        return False


def validate_config(cfg: dict) -> dict:
    """
    Проверяет корректность всех параметров конфигурации.
    Возвращает очищенный словарь, либо выбрасывает ConfigError.
    """

    errors = []  # накапливаем ошибки, чтобы вывести их все разом

    
    # Проверка параметра package_name
    
    package_name = cfg.get("package_name")
    if package_name is None:
        errors.append("Отсутствует параметр 'package_name'.")
    elif not isinstance(package_name, str) or not package_name.strip():
        errors.append("Параметр 'package_name' должен быть непустой строкой.")

    
    # Проверка параметра repo
    
    repo = cfg.get("repo")
    if repo is None:
        errors.append("Отсутствует параметр 'repo'.")
    elif not isinstance(repo, str) or not repo.strip():
        errors.append("Параметр 'repo' должен быть непустой строкой (URL или локальный путь).")
    else:
        repo_str = repo.strip()

        # Если значение похоже на URL — проверяем базовую валидность
        if is_probably_url(repo_str):
            p = urlparse(repo_str)
            if not p.scheme or not (p.netloc or p.path):
                errors.append(f"'repo' похоже на URL, но невалидно: {repo_str}")
        # Если не похоже на URL — считаем локальным путем (будем проверять позже)

    
    # Проверка test_repo_mode
    
    mode = cfg.get("test_repo_mode")
    if mode is None:
        errors.append("Отсутствует параметр 'test_repo_mode'.")
    elif not isinstance(mode, str):
        errors.append("Параметр 'test_repo_mode' должен быть строкой.")
    elif mode not in ALLOWED_TEST_MODES:
        errors.append(
            f"Неверное значение 'test_repo_mode': {mode}. "
            f"Допустимые значения: {sorted(ALLOWED_TEST_MODES)}"
        )

    
    # Проверка output_image
    
    out = cfg.get("output_image")
    if out is None:
        errors.append("Отсутствует параметр 'output_image'.")
    elif not isinstance(out, str) or not out.strip():
        errors.append("Параметр 'output_image' должен быть непустой строкой.")
    else:
        _, ext = os.path.splitext(out.strip())
        if not ext:
            errors.append("Параметр 'output_image' должен содержать расширение (.png/.svg/.pdf).")
        elif ext.lower() not in ALLOWED_IMAGE_EXTS:
            errors.append(
                f"Расширение '{ext}' не поддерживается. "
                f"Допустимые: {sorted(ALLOWED_IMAGE_EXTS)}"
            )

    
    # Проверка max_depth
    
    max_depth = cfg.get("max_depth")
    if max_depth is None:
        errors.append("Отсутствует параметр 'max_depth'.")
    elif isinstance(max_depth, bool):
        # bool — это наследник int, поэтому нужно проверять отдельно
        errors.append("Параметр 'max_depth' должен быть целым числом >= 0, не boolean.")
    elif not isinstance(max_depth, int):
        errors.append("Параметр 'max_depth' должен быть целым числом.")
    elif max_depth < 0:
        errors.append("Параметр 'max_depth' должен быть >= 0.")

    
    # Проверка filter_substring
    
    fsub = cfg.get("filter_substring")
    if fsub is None:
        errors.append("Отсутствует параметр 'filter_substring'.")
    elif not isinstance(fsub, str):
        errors.append("Параметр 'filter_substring' должен быть строкой (может быть пустой).")

    
    # Дополнительные проверки связки параметров
    
    if isinstance(mode, str) and mode == "local-file" and isinstance(repo, str):
        repo_path = repo.strip()
        # В режиме "local-file" путь обязан существовать
        if not os.path.exists(repo_path):
            errors.append(
                f"Режим 'local-file' указан, но путь, указанный в 'repo', не существует: {repo_path}"
            )

    # Если есть ошибки — выводим их все сразу
    if errors:
        raise ConfigError("\n".join(errors))

    # Возвращаем нормализованную конфигурацию
    return {
        "package_name": package_name.strip(),
        "repo": repo.strip(),
        "test_repo_mode": mode,
        "output_image": out.strip(),
        "max_depth": max_depth,
        "filter_substring": fsub,
    }


def load_config_from_file(path: str) -> dict:
    """
    Загружает JSON-файл конфигурации.
    Выбрасывает ConfigError при любой проблеме.
    """

    # Проверка существования файла
    if not os.path.exists(path):
        raise ConfigError(f"Файл конфигурации не найден: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Ошибка разбора JSON в файле {path}: {e}")
    except Exception as e:
        raise ConfigError(f"Ошибка чтения файла {path}: {e}")

    # Корневой элемент конфигурации должен быть объектом
    if not isinstance(data, dict):
        raise ConfigError("JSON-конфигурация должна быть объектом (ключ-значение).")

    return data


def print_kv(cfg: dict):
    """
    Выводит параметры конфигурации в формате «ключ: значение».
    Требование задания.
    """
    print("Параметры конфигурации (ключ: значение):")
    for k in ["package_name", "repo", "test_repo_mode", "output_image", "max_depth", "filter_substring"]:
        v = cfg.get(k)

        # Для красоты выводим пустую строку как "<empty string>"
        if isinstance(v, str) and v == "":
            v_display = "<empty string>"
        else:
            v_display = str(v)

        print(f"- {k}: {v_display}")


def main(argv=None):
    """
    Основная точка входа.
    Обрабатывает аргументы CLI, загружает конфиг, валидирует и выводит параметры.
    """

    # Создаём парсер аргументов
    parser = argparse.ArgumentParser(
        description="Минимальный прототип визуализатора графа зависимостей (этап 1)."
    )
    parser.add_argument(
        "--config", "-c",
        help="Путь к JSON конфигурационному файлу.",
        required=True
    )

    args = parser.parse_args(argv)

    try:
        # Загружаем и валидируем конфигурацию
        raw = load_config_from_file(args.config)
        cfg = validate_config(raw)
    except ConfigError as e:
        # Ошибки конфигурации выводим пользователю
        print("Ошибка конфигурации:", file=sys.stderr)
        print(str(e), file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        # Любая другая неожиданная ошибка
        print("Неожиданная ошибка при загрузке конфигурации:", file=sys.stderr)
        print(str(e), file=sys.stderr)
        sys.exit(3)

    # Этап 1: просто выводим параметры
    print_kv(cfg)

    return 0


if __name__ == "__main__":
    sys.exit(main())
