import asyncio
import unittest
from unittest import TestCase

import peewee

from app.sql import Item, Item2Source, ItemMysqlStorageAdapter, Source, SourceMysqlStorageAdapter, object_manager

srepo = SourceMysqlStorageAdapter()
irepo = ItemMysqlStorageAdapter()


class TestItem(TestCase):
    @staticmethod
    async def clear_tables():
        await object_manager.execute(
            Item2Source.delete()
        )
        await object_manager.execute(
            Item.delete()
        )
        await object_manager.execute(
            Source.delete()
        )
        await object_manager.close()

    @classmethod
    def setUpClass(cls):
        peewee.drop_model_tables([Item, Source, Item2Source], fail_silently=True)
        peewee.create_model_tables([Item, Source, Item2Source])

    @classmethod
    def tearDownClass(cls):
        asyncio.get_event_loop().run_until_complete(
            cls.clear_tables()
        )

    def test_1_succeed(self):
        async def test():
            print('add 1st record')
            await self.add_record(1)
            # note: no sleep! and it works
            t = asyncio.Task(self.add_record(2))
            print('add 2nd record')
            await t
            print('success')

        asyncio.get_event_loop().run_until_complete(test())

    def test_2_fails(self):
        async def test():
            print('add 3rd record')
            await self.add_record(3)
            await asyncio.sleep(60 * 20)
            t = asyncio.Task(self.add_record(4))
            print('add 4th record')
            await t
            print('success')

        asyncio.get_event_loop().run_until_complete(test())

    @staticmethod
    async def add_record(identifier: int):
        async with object_manager.atomic():
            source = await srepo.save({'id': identifier, 'title': 's_%s' % identifier})
        async with object_manager.atomic():
            item = await irepo.save({'id': identifier, 'sid': 1, 'title': 'i_%s' % identifier})
        return source, item


if __name__ == '__main__':
    unittest.main()
