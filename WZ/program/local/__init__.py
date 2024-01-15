from importlib import import_module

from core.basic_data import get_database, CONFIG
get_database()  # to ensure that <CONFIG> is initialized
region = CONFIG.REGION

def __getattr__(mod):
    print("GET", mod)
    m = import_module(f"local.{region}.{mod}")
    print("  -->", m)
    globals()[mod] = m
    return m

## To use:
# import local
# ...
# module = local.module
# attribute = local.module.attribute
#
# ... OR ...
#
# from local import module1, module2
# attr1 = module1.attr
# attr2 = module2.attr
