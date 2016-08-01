# TODO(dstanek): this doesn't belong here. it is only here to make
# creating a POC easier.
import functools
import uuid

import dogpile.cache.api
import dogpile.cache.region
import dogpile.util.compat
import six


class CacheRegion(dogpile.cache.CacheRegion):

    @property
    def region_key(self):
        return 'region:' + self.name

    @property
    def region_id(self):
        region_id = self.get(self.region_key)

        if not region_id:
	    region_id = uuid.uuid4().hex
            # TODO(dstanek): this should last forever
            self.set(self.region_key, region_id)

        return region_id

    @property
    def function_key_generator(self):
        return self._function_key_generator

    @function_key_generator.setter
    def function_key_generator(self, func):
        @functools.wraps(func)
        def _function_key_generator(*args, **kwargs):
            generate_key = func(*args, **kwargs)

            @functools.wraps(generate_key)
            def _generate_key(*args):
                key = generate_key(*args)
                return key + self.region_id
            return _generate_key
        self._function_key_generator = _function_key_generator

    def invalidate(self):
        region_key = self.region_key
        self.delete(region_key)
	new_region_id = uuid.uuid4().hex
        # TODO(dstanek): this should last forever
        self.set(region_key, new_region_id)


dogpile.cache.CacheRegion = CacheRegion
dogpile.cache.region.CacheRegion = CacheRegion
