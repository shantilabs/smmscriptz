import logging
import sys

import requests
import time

from vkscriptz_core.errors import AccessError, AccessTokenRequired

logger = logging.getLogger('vk')


class VkApi(object):
    VERSION_ID = '5.40'

    def __init__(self, credentials):
        self.credentials = credentials

    def user_groups(self, user_id):
        if not self.credentials.access_token:
            raise AccessTokenRequired()
        for item in self._paginate(
            'https://api.vk.com/method/groups.get',
            1000,
            user_id=user_id,
            extended=1,
            fields='name,screen_name',
            access_token=self.credentials.access_token,
        ):
            yield item

    def group_search(
        self,
        q,
        type=None,
        country_id=None,
        city_id=None,
        future=None,
        sort=0,
    ):
        """
        https://vk.com/dev/groups.search
        """
        if not self.credentials.access_token:
            raise AccessTokenRequired()
        for item in self._paginate(
            'https://api.vk.com/method/groups.search',
            1000,
            q=q,
            type=type,
            country_id=country_id,
            city_id=city_id,
            future=future,
            sort=sort,
            access_token=self.credentials.access_token,
        ):
            yield item

    def group_members(self, group_id):
        """
        https://vk.com/dev/groups.getMembers
        """
        for item in self._paginate(
            'https://api.vk.com/method/groups.getMembers',
            1000,
            group_id=group_id,
            fields='city,connections',
        ):
            yield item

    def likes(self, owner_id, type, item_id):
        """
        https://vk.com/dev/likes.getList
        """
        assert type in (
            'post',
            'comment',
            'photo',
            'audio',
            'video',
            'note',
            'photo_comment',
            'video_comment',
            'topic_comment',
            'sitepage',
        )
        for item in self._paginate(
            'https://api.vk.com/method/likes.getList',
            100,
            owner_id=owner_id,
            item_id=item_id,
            type=type,
        ):
            yield item

    def wall_comments(self, owner_id, post_id, preview_length=0):
        """
        https://vk.com/dev/wall.getComments
        """
        for item in self._paginate(
            'https://api.vk.com/method/wall.getComments',
            100,
            owner_id=owner_id,
            post_id=post_id,
            preview_length=preview_length,
        ):
            yield item

    def wall(self, owner_id):
        """
        https://vk.com/dev/wall.get
        """
        for item in self._paginate(
            'https://api.vk.com/method/wall.get',
            100,
            owner_id=owner_id,
        ):
            yield item

    def group_info(self, group_id):
        """
        https://vk.com/dev/groups.getById
        """
        return next(self._list_request(
            'https://api.vk.com/method/groups.getById',
            group_id=group_id,
        ))

    def user_info(self, user_ids):
        """
        https://vk.com/dev/users.get
        """
        for cur_ids in chunkize(user_ids):
            for item in self._list_request(
                'https://api.vk.com/method/users.get',
                user_ids=','.join(map(str, cur_ids)),
            ):
                yield item

    def group_remove_member(self, group_id, user_id):
        """
        https://vk.com/dev/groups.removeUser
        """
        resp = self._get(
            'https://api.vk.com/method/groups.removeUser',
            group_id=group_id,
            user_id=user_id,
            access_token=self.credentials.access_token,
        )
        self._sleep()
        return 'response' in resp and resp['response'] == 1

    def _sleep(self, sec=0.33):
        logger.debug('sleep %s', sec)
        time.sleep(sec)

    def _paginate(self, url, count, **params):
        for offset in xrange(0, sys.maxint, count):
            if 'access_token' in params:
                self._sleep()
            data = self._get(url, **dict(params, offset=offset, count=count))
            try:
                items = data['response']['items']
            except:
                logger.warn('no items in data: %r', data)
                raise
            if not items:
                break
            for item in items:
                yield item

    def _get(self, url, **params):
        while True:
            logger.debug('get %s %s', url, params)
            resp = requests.get(url, params=dict(params, v=self.VERSION_ID))
            data = resp.json()
            if self._has_tmp_error(data):
                logger.warn('temporary error: %s', data['error'])
                self._sleep()
                continue
            break
        if self._has_access_error(data):
            logger.critical('access error: %s', data['error'])
            raise AccessError()
        return data

    def _list_request(self, url, **params):
        data = self._get(url, **params)
        try:
            items = data['response']
        except:
            logger.warn('no response in data: %s', data)
            raise
        for item in items:
            yield item

    def _has_tmp_error(self, data):
        return 'error' in data and data['error']['error_msg'].startswith((
            'Too many requests',
            'Internal server error',
        ))

    def _has_access_error(self, data):
        return 'error' in data and data['error']['error_msg'].startswith((
            'Access denied',
            'Access to group denied',
            'Permission to perform this action is denied',
        ))


def chunkize(ids, chunk_size=100):
    if not hasattr(ids, '__iter__'):
        ids = [ids]
    for offset in xrange(0, len(ids), chunk_size):
        yield ids[offset:offset + chunk_size]
