import dogpile.cache

R = dogpile.cache.make_region()

on_arguments = R.cache_on_arguments
