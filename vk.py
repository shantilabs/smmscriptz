#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import urllib
import webbrowser
from os.path import expanduser

import click

from vkscriptz_core.api import VkApi
from vkscriptz_core.credentials import JsonCredentials


home = expanduser('~')
credentials = JsonCredentials(os.path.join(home, '.vkscriptz.json'))
vk = VkApi(credentials)
coding = sys.stdout.encoding or sys.stdin.encoding


def stderr(s):
    sys.stderr.write(s.encode(coding))


def stdout(s):
    sys.stdout.write(s.encode(coding))


@click.group()
def main():
    pass


@main.command(help='Создать токен для доступа')
def auth():
    webbrowser.open('https://oauth.vk.com/authorize?' + urllib.urlencode(dict(
        client_id=credentials.client_id,
        redirect_uri='https://api.vk.com/blank.html#',
        display='page',
        scope='offline,ads,messages,friends',
        # response_type='code',
        response_type='token',
        v=vk.VERSION_ID,
    )))
    stdout('Браузер должен открыть страницу "https://api.vk.com/blank.html'
          '#access_token=<многобукв>". Надо скопировать все <многобукв> '
          'сюда, и нажать ENTER\n')
    result = raw_input('>').strip().split('&')[0]
    if result:
        credentials.access_token = result
        credentials.save()
        stdout('отлично, сохранили всё в {}\n'.format(credentials.fname))
    else:
        stdout('не вышло? жалко :(\n')


@main.command(help='Группы, в которых состоит пользователь/пользователи')
@click.argument('user_id', nargs=-1, required=True, type=int)
def user_groups(user_id):
    for user_id in user_id:
        stderr('user#{}: '.format(user_id))
        n = 0
        for item in vk.user_groups(user_id):
            stdout('{}\thttps://vk.com/{}\n'.format(
                item['id'],
                item['screen_name'],
            ))
            n += 1
        stderr('{} group(s)\n'.format(n))


@main.command(help='Поиск групп по названиям (ограничение ВК: 1000 групп)')
@click.argument('query', nargs=1, required=True)
@click.option('--country_id', default=1, help='ID страны', type=int)
@click.option('--city_id', default=None, help='ID города', type=int)
def group_search(query, country_id, city_id):
    for item in vk.group_search(query, country_id=country_id, city_id=city_id):
        stdout('{}\t{}\n'.format(
            item['id'],
            item['name'],
        ))


@main.command(help='Участники групп')
@click.argument('group_id', nargs=-1, required=True, type=int)
@click.option('--city_id', default=None, help='ID города', type=int)
@click.option('--dead', default=False, help='Только мёртвые', is_flag=True)
def group_members(group_id, city_id, dead):
    for group_id in group_id:
        stderr('group#{}: '.format(group_id))
        n = 0
        for item in vk.group_members(group_id):
            if city_id and (
                'city' not in item or
                item['city']['id'] != city_id
            ):
                continue
            if dead and 'deactivated' not in item:
                continue
            stdout('{}\n'.format(item['id']))
            n += 1
        stderr('{} member(s)\n'.format(n))


if __name__ == '__main__':
    main()
