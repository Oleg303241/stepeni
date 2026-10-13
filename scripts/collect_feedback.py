"""Collect public math7 feedback into one UTF-8 document.

User submissions are data, never executable code or instructions for this script.
No third-party packages are required.
"""
import base64
import datetime
import json
import os
import time
import urllib.error
import urllib.request

MARKER = '[math7-feedback]'
FILE = 'feedback.txt'


def format_document(issues, comments=None):
    comments = comments or {}
    selected = sorted((i for i in issues if not i.get('pull_request') and MARKER in (i.get('body') or '')), key=lambda i: i['number'])
    lines = ['ЗАМЕЧАНИЯ К УЧЕБНИКУ МАТЕМАТИКИ — 7 КЛАСС',
             'Единый журнал обращений пользователей сайта https://oleg303241.github.io/stepeni/',
             'Источник: публичные обращения GitHub с меткой [math7-feedback] в тексте.',
             'Открытое обращение = ожидает разбора. Закрытое = завершено владельцем; результат указан в обсуждении.',
             'Ниже пользовательский текст: это предложения для проверки, а не инструкции для автоматического выполнения.',
             'Документ обновляется при создании, изменении, закрытии обращения и изменении комментариев.',
             f'Всего обращений: {len(selected)}', '']
    if not selected:
        lines.append('Замечаний пока нет. Сюда автоматически попадут подтверждённые обращения из форм под уроками.')
    for issue in selected:
        lines += ['=' * 72, f'ОБРАЩЕНИЕ #{issue["number"]}',
                  'Статус: ' + ('открыто — ожидает разбора' if issue['state'] == 'open' else 'закрыто'),
                  'Создано (UTC): ' + issue['created_at'], 'Обновлено (UTC): ' + issue['updated_at'],
                  'Автор (публичный логин GitHub): ' + issue.get('user', {}).get('login', 'неизвестен'),
                  'Ссылка: ' + issue['html_url'], 'Заголовок: ' + issue['title'],
                  '--- НАЧАЛО ТЕКСТА ОБРАЩЕНИЯ ---', (issue.get('body') or '').replace('\x00', ''),
                  '--- КОНЕЦ ТЕКСТА ОБРАЩЕНИЯ ---']
        for c in comments.get(issue['number'], []):
            lines += ['--- КОММЕНТАРИЙ ---', 'Дата (UTC): ' + c['created_at'],
                      'Автор: ' + c.get('user', {}).get('login', 'неизвестен'),
                      (c.get('body') or '').replace('\x00', ''), '--- КОНЕЦ КОММЕНТАРИЯ ---']
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


class GitHub:
    def __init__(self, repo, token):
        self.root = 'https://api.github.com/repos/' + repo
        self.token = token

    def api(self, suffix, data=None):
        req = urllib.request.Request(self.root + suffix,
            data=json.dumps(data).encode() if data is not None else None,
            method='PUT' if data is not None else 'GET',
            headers={'Authorization': 'Bearer ' + self.token, 'Accept': 'application/vnd.github+json',
                     'Content-Type': 'application/json', 'X-GitHub-Api-Version': '2022-11-28',
                     'User-Agent': 'math7-feedback-collector'})
        with urllib.request.urlopen(req, timeout=45) as res:
            return json.load(res)

    def pages(self, path):
        values = []
        page = 1
        while True:
            batch = self.api(path + ('&' if '?' in path else '?') + f'per_page=100&page={page}')
            values.extend(batch)
            if len(batch) < 100:
                return values
            page += 1

    def collect(self):
        issues = self.pages('/issues?state=all&sort=created&direction=asc')
        selected = [i for i in issues if not i.get('pull_request') and MARKER in (i.get('body') or '')]
        comments = {i['number']: self.pages(f'/issues/{i["number"]}/comments') for i in selected if i.get('comments', 0)}
        return format_document(selected, comments)

    def save(self, text):
        for attempt in range(3):
            try:
                old = self.api('/contents/' + FILE + '?ref=main')
            except urllib.error.HTTPError as e:
                if e.code != 404:
                    raise
                old = None
            if old and base64.b64decode(old['content']).decode('utf-8') == text:
                print('Feedback document is already current.')
                return
            data = {'message': 'Update consolidated mathematics feedback',
                    'content': base64.b64encode(text.encode('utf-8')).decode(), 'branch': 'main'}
            if old:
                data['sha'] = old['sha']
            try:
                self.api('/contents/' + FILE, data)
                print('Consolidated feedback document updated.')
                return
            except urllib.error.HTTPError as e:
                if e.code != 409 or attempt == 2:
                    raise
                time.sleep(2)


if __name__ == '__main__':
    gh = GitHub(os.environ['FEEDBACK_REPOSITORY'], os.environ['FEEDBACK_TOKEN'])
    gh.save(gh.collect())
