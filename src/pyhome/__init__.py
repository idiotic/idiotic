class ItemProxy:
    def __init__(self, item_dict):
        self.__items = item_dict

    def all(self, name, mask=lambda _:True):
        return filter(mask, self.__items.values())

    def __getattr__(self, name):
        if name in self.__items:
            return self.__items[name]
        else:
            raise NameError("Item {} does not exist.".format(name))

_items = {}
items = ItemProxy(_items)

def _mangle_name(name):
    # TODO regex replace things other than spaces
    return name.lower().replace(" ", "_") if name else ""

def _register_item(item):
    global _items
    _items[_mangle_name(item.name)] = item
