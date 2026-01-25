import os

def print_py_tree(path, prefix='', output_file=None):
    full_path = os.path.abspath(path)
    items = [item for item in os.listdir(full_path) 
             if item.endswith('.py') or os.path.isdir(os.path.join(full_path, item))]
    items.sort()
    
    with open(output_file, 'a', encoding='utf-8') as f:
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            line = f"{prefix}{'└── ' if is_last else '├── '}{item}\n"
            print(line.strip())
            f.write(line)
            
            item_path = os.path.join(full_path, item)
            if os.path.isdir(item_path):
                new_prefix = prefix + ('    ' if is_last else '│   ')
                print_py_tree(item_path, new_prefix, output_file)

# Путь к проекту и к выходному файлу
project_path = r"C:\_our_files\oleg\python_projects\first_project\backtest_platform"
output_path = r"C:\_our_files\oleg\python_projects\first_project\py_structure.txt"

# Очищаем файл перед записью
open(output_path, 'w').close()

# Запускаем из корневой папки проекта
print("backtest_platform/")  # Заголовок
with open(output_path, 'a', encoding='utf-8') as f:
    f.write("backtest_platform/\n")
print_py_tree(project_path, '', output_path)

print(f"\n✅ Структура сохранена в: {output_path}")
