# py_code/test.py
import py_code.config as CFG
import sys
print("config file:", getattr(CFG, "__file__", "N/A"))
print("dir(config):", [k for k in dir(CFG) if not k.startswith("_")])
print("sys.path[0]:", sys.path[0])
print("ROOT_DIR exists?", hasattr(CFG, "ROOT_DIR"))
print(CFG.ROOT_DIR)