import peewee

from app.sql import Item, Item2Source, Source

peewee.drop_model_tables([Item, Source, Item2Source], fail_silently=True)
peewee.create_model_tables([Item, Source, Item2Source])
