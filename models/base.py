from collections import OrderedDict

from jester import JesterClient


class Column:

    __slots__ = "type", "optional", "default", "unique"

    def __init__(self, typ: str, optional: bool = False, default: str = None, unique = False):
        self.type = typ
        self.optional = optional
        self.default = default
        self.unique = unique

    def compile(self):
        text = self.type
        if not self.optional:
            text += " NOT NULL"
        if self.default is not None:
            text += " DEFAULT " + self.default
        if self.unique and self.optional:
            raise ValueError("Unique keys can not be optional")
        elif self.unique:
            text += " PRIMARY KEY"
        return text

    def __eq__(self, other: str):
        return self, other


class BaseMeta(type):

    def __new__(mcs, name, bases, clsattrs):

        if name != 'Base':
            table_name = clsattrs.get("TABLE_NAME", name.lower())
            _fields = OrderedDict({name: arg for name, arg in clsattrs.items() if isinstance(arg, Column)})

            with JesterClient() as client:
                client.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
                all_db = [l[0] for l in client.fetch_all()]
                if table_name not in all_db:
                    columns = " ".join("{} {},".format(name, val.compile()) for name, val in _fields.items())[:-1]
                    client.execute("CREATE TABLE {} ({})".format(table_name, columns))

            clsattrs["_fields"] = _fields
            clsattrs['table_name'] = table_name

        return super().__new__(mcs, name, bases, clsattrs)


class Base(metaclass=BaseMeta):

    table_name: str
    _fields: dict

    def __init__(self, args: tuple):
        for name, value in zip(self._fields, args):
            setattr(self, name, value)

    def __iter__(self):
        for field in self._fields:
            yield getattr(self, field)
    
    @classmethod
    def create(cls, **fields):
        fields = OrderedDict(fields)

        if not all(name in fields for name, col in cls._fields.items() if not col.optional):
            raise ValueError("Not all required columns were provided")
        if not all(name in cls._fields for name in fields):
            raise ValueError("Provided unknown columns")

        with JesterClient() as client:
            values = ", ".join("?" for _ in fields)
            client.execute("INSERT INTO {} ({}) VALUES ({})".format(cls.table_name, ", ".join(fields), values),
                           *fields.values())

    @classmethod
    def _create_query(cls, querys):
        if isinstance(querys[0], tuple):
            matched = {}
            for query in querys:
                for name, col in cls._fields.items():
                    if query[0] is col:
                        matched[name] = query[1]
        else:
            primary = next(name for name, col in cls._fields.items() if col.unique)
            matched = {primary: querys[0]}

        return " AND ".join("{} = ?".format(name) for name in matched), matched.values()

    @classmethod
    def find_all(cls):
        with JesterClient() as client:
            client.execute("SELECT * FROM " + cls.table_name)
            return [*map(cls, client.fetch_all())]
    
    @classmethod
    def find(cls, *querys):
        query, values = cls._create_query(querys)
        sql = "SELECT * FROM {} WHERE ".format(cls.table_name) + query
        with JesterClient() as client:
            client.execute(sql, *values)
            return [*map(cls, client.fetch_all())]

    @classmethod
    def find_one(cls, *query):
        return cls.find(*query)[0]

    @classmethod
    def delete(cls, *querys):
        query, values = cls._create_query(querys)
        sql = "DELETE FROM {} WHERE ".format(cls.table_name) + query
        with JesterClient() as client:
            client.execute(sql, *values)

    def delete_self(self):
        query = tuple(zip(self._fields.values(), self))
        self.delete(*query)
