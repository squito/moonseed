
*tl;dr*

If you want to test `filters.py` in a loop, run:

```
test/test_loop.py --test filters.py
```


*longer way*

I'm nearly always confused about how to run python tests w/ the right sys.path.  I dunno if this is _the_
right way, but this works:

```
python -m pytest test/test_filters.py
```

for running one test.

or to get fancy, you can have your tests running continuously using `entr`:

```
ls quanta_cache.py test/test_filters.py | entr -r python -m pytest test/test_filters.py
```


I do not know if there is a better way, or if its different w/ nosetest instead of pytest.  Just that this seems to work
