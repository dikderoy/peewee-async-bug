import asyncio
import logging
import os
from time import time

import peewee
import peewee_async

logger = logging.getLogger(__name__)

MYSQL_USER = 'app'
MYSQL_PASSWORD = 't3stpassw0rd'
MYSQL_DATABASE = 'test_db'
MYSQL_HOST = os.getenv('MYSQL_HOST', '127.0.0.1')
MYSQL_PORT = os.getenv('MYSQL_PORT', 3306)

if not MYSQL_USER or not MYSQL_PASSWORD:
    raise RuntimeError('mysql credentials not configured')

cdb = peewee_async.PooledMySQLDatabase(
    MYSQL_DATABASE,
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    host=MYSQL_HOST,
    port=MYSQL_PORT,
    charset='utf8',
    max_connections=5
)

object_manager = peewee_async.Manager(database=cdb)


class BaseModel(peewee.Model):
    class Meta:
        database = cdb


class _CMetaMixin(peewee.Model):
    created = peewee.TimestampField(
        index=True,
        default=time
    )


class Source(BaseModel, _CMetaMixin):
    """
    CREATE TABLE `source` (
      `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
      `avatar` varchar(255) DEFAULT NULL,
      `name` varchar(255) DEFAULT NULL,
      `type` varchar(255) DEFAULT NULL,
      `origin` varchar(255) NOT NULL DEFAULT '',
    PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
    """
    id = peewee.PrimaryKeyField(
        constraints=[peewee.SQL('AUTO_INCREMENT')]
    )
    title = peewee.CharField(
        max_length=500
    )

    class Meta:
        db_table = 'source'


class Item(BaseModel, _CMetaMixin):
    """
    CREATE TABLE `item` (
        `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
        `sourceId` int(11) unsigned NOT NULL,
        `published` datetime NOT NULL,
        `origin` varchar(255) NOT NULL DEFAULT '',
        `title` text,
        `description` text,
        `mediaCover` varchar(255) DEFAULT NULL,
        `mediaUrl` varchar(255) DEFAULT NULL,
        `type` varchar(255) NOT NULL DEFAULT '',
    PRIMARY KEY (`id`),
    KEY `sourceId` (`sourceId`),
    CONSTRAINT `sourceId` FOREIGN KEY (`sourceId`)
        REFERENCES `source` (`id`) ON DELETE CASCADE ON UPDATE CASCADE)
    ENGINE=InnoDB DEFAULT CHARSET=utf8;
    """
    id = peewee.PrimaryKeyField(
        constraints=[peewee.SQL('AUTO_INCREMENT')]
    )
    title = peewee.CharField(
        max_length=500
    )

    class Meta:
        db_table = 'item'


class Item2Source(BaseModel):
    source = peewee.ForeignKeyField(rel_model=Source, on_delete='RESTRICT', on_update='CASCADE')
    item = peewee.ForeignKeyField(rel_model=Item, on_delete='CASCADE', on_update='CASCADE')

    class Meta:
        primary_key = peewee.CompositeKey('source', 'item')


def _wrap_exceptions(fn):
    async def _wrapper_catch_db_exceptions(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except peewee.InterfaceError as e:
            logger.exception('[mysql] mysql connection trouble, ruin the daemon so it will be restarted')
            asyncio.get_event_loop().stop()
            raise

    return _wrapper_catch_db_exceptions


class ItemMysqlStorageAdapter:
    def __init__(self):
        super().__init__()
        self._manager = object_manager

    async def _get_existing(self, entity: dict, existing: Item = None) -> Item:
        if existing:
            return existing
        logger.debug('find existing db record for %s', entity)
        candidates = await self._manager.prefetch(
            Item.select().where(Item.id == entity['id']),
            Item2Source.select().where(Item2Source.item_id == entity['id'])
        )  # type: list[Item]

        for x in candidates:
            if x.id == entity['id']:
                return x
        raise peewee.DoesNotExist()

    async def update(self, entity: dict, existing: Item = None) -> bool:
        existing = await self._get_existing(entity, existing)

        logger.debug('update entity %s', entity)
        async with self._manager.atomic():
            await self._manager.update(
                existing,
                [field for name, field in Item._meta.fields.items()
                 if name not in [Item.id.name, Item.created.name]])
        logger.debug('update source references for %s', entity)
        # noinspection PyUnresolvedReferences
        if entity.meta.sid is not None and entity.meta.sid \
                not in [ref.source_id for ref in existing.item2source_set_prefetch]:
            source = await self._manager.get(Source, Source.id == entity['sid'])  # type: Source
            logger.debug('create source reference for %s', entity)
            await self._manager.create(Item2Source, item=existing, source=source)

        logger.info('db record for %s saved successfully as %s', entity, existing)
        return True

    async def save(self, entity: dict) -> bool:
        try:
            existing = await self._get_existing(entity)
            return await self.update(entity, existing)
        except peewee.DoesNotExist:
            pass

        logger.debug('no existing db record for %s, creating...', entity)
        async with self._manager.atomic():
            db_model = await self._manager.create(Item, **entity)
        entity['id'] = db_model.id
        logger.debug('created db record id=%s for %s', db_model.id, entity)

        logger.debug('creating source relations for %s with db record %s', entity, db_model.id)
        db_rel = await self._manager.create(Item2Source, source_id=entity['sid'], item=db_model)
        entity['sid'] = db_rel.source_id
        logger.debug('created source relations db record for %s', entity)

        logger.info('db record for %s saved successfully as %s', entity, db_model)
        return True

    async def find(self, properties: dict) -> [dict]:
        main_query = Item.select()
        i2s_query = Item2Source.select()
        if properties != {}:
            if properties.get('sid'):
                i2s_query = i2s_query.where(Item2Source.source_id == properties.pop('sid'))
            main_query = main_query.filter(**properties)

        db_list = await self._manager.prefetch(
            main_query,
            i2s_query,
        )

        return [{'id': item.id,
                 'sid': item.item2source_set_prefetch[0].source_id,
                 'title': item.title,
                 'created': item.created}
                for item in db_list]


class SourceMysqlStorageAdapter:
    def __init__(self):
        super().__init__()
        self._manager = object_manager

    async def load(self, eid) -> dict:
        db_model = await self._manager.get(Source, Source.id == eid)  # type: Source
        return {'id': db_model.id,
                'title': db_model.title,
                'created': db_model.created}

    async def _get_existing(self, entity: dict, existing: Source = None) -> Source:
        if existing:
            return existing
        if entity['id'] is not None:
            return await self._manager.get(
                Source.select().where(Source.id == entity['id']),
            )  # type: Source
        raise peewee.DoesNotExist()

    async def update(self, entity: dict, existing: Source = None) -> bool:
        existing = await self._get_existing(entity, existing)

        async with self._manager.atomic():
            await self._manager.update(
                existing,
                [field for name, field in Source._meta.fields.items()
                 if name not in [Source.id.name, Source.created.name]]
            )

    async def save(self, entity: dict) -> bool:
        try:
            existing = await self._get_existing(entity)
            return await self.update(entity, existing)
        except peewee.DoesNotExist:
            pass

        db_model = await self._manager.create(Source, **entity)
        entity['id'] = db_model.id
        return True

    async def find(self, properties: dict) -> [dict]:
        query = Source.select()
        if properties != {}:
            query = query.filter(**properties)

        db_list = await self._manager.execute(query)  # type: list[Source]
        return [{'id': source_model.id,
                 'title': source_model.title,
                 'created': source_model.created}
                for source_model in db_list]
