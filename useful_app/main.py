import json
import sys
from pathlib import Path

DATA_FILE = Path('tasks.json')


def load_tasks():
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_tasks(tasks):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)


def add_task(text):
    tasks = load_tasks()
    tasks.append({'text': text, 'done': False})
    save_tasks(tasks)


def list_tasks():
    tasks = load_tasks()
    for idx, task in enumerate(tasks, 1):
        status = '✔' if task.get('done') else '✗'
        print(f"{idx}. [{status}] {task.get('text')}")


def complete_task(index):
    tasks = load_tasks()
    if 0 <= index < len(tasks):
        tasks[index]['done'] = True
        save_tasks(tasks)


def usage():
    print("Usage:")
    print("  python main.py add <task>")
    print("  python main.py list")
    print("  python main.py done <task_number>")


def main(argv):
    if len(argv) < 2:
        usage()
        return
    cmd = argv[1]
    if cmd == 'add' and len(argv) > 2:
        add_task(' '.join(argv[2:]))
    elif cmd == 'list':
        list_tasks()
    elif cmd == 'done' and len(argv) > 2 and argv[2].isdigit():
        complete_task(int(argv[2]) - 1)
    else:
        usage()


if __name__ == '__main__':
    main(sys.argv)
