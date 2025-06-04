import os
import json
import main


def test_add_and_list(tmp_path, capsys):
    data_file = tmp_path / 'tasks.json'
    main.DATA_FILE = data_file
    main.add_task('테스트')
    main.list_tasks()
    captured = capsys.readouterr()
    assert '테스트' in captured.out


def test_complete(tmp_path):
    data_file = tmp_path / 'tasks.json'
    main.DATA_FILE = data_file
    main.add_task('끝내기')
    main.complete_task(0)
    with open(data_file, 'r', encoding='utf-8') as f:
        tasks = json.load(f)
    assert tasks[0]['done'] is True
