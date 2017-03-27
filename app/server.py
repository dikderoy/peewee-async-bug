from aiohttp import web

from app.sql import ItemMysqlStorageAdapter, SourceMysqlStorageAdapter

app = web.Application(debug=True)

item_repo = ItemMysqlStorageAdapter()
source_repo = SourceMysqlStorageAdapter()


async def item_save_handler(item: dict):
    # resolve source by its origin
    candidates = await source_repo.find({'id': item['sid']})  # type: list[dict]
    cnd_amount = len(candidates)
    if cnd_amount > 0:
        existing = candidates[0]  # type: dict
        item['sid'] = existing['id']
    elif cnd_amount == 0:
        item['sid'] = None
        raise web.HTTPPartialContent()

    await item_repo.save(item)


async def source_save_handler(source: dict):
    await source_repo.save(source)
