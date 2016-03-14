# How to run Idiotic

Idiotic is written in Python3, and packaged as a module. To run idiotic, construct a configuration
directory (`/etc/idiotic` by default) which contains directories `items`, `modules`, and `rules`.

Invoke with
```
python3 -m idiotic -b path/to/config/directory
```
