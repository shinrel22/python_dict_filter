class DictFilter(object):
    def __init__(self,
                 data,
                 include_fields=None,
                 exclude_fields=None):
        if not include_fields:
            include_fields = []

        if not exclude_fields:
            exclude_fields = []

        self.include_fields = include_fields

        self.exclude_fields = exclude_fields

        self.data = data

    def _convert_fields_to_list(self, fields):
        result = []
        for field in fields:
            if not isinstance(field, str):
                continue
            result.append(field.split('.'))
        return result

    def _dive_to_get_value(self, data, path, default=None):
        key = path[0]
        value = data.get(key)

        if not value:
            return default

        if len(path) == 1:
            return value

        if not isinstance(value, dict):
            raise TypeError('Can only dive to dict')

        return self._dive_to_get_value(value, path[1:], default)

    def _dive_to_set_value(self, data, path, value=None):

        key = path[0]

        if len(path) == 1:
            data[key] = value
            return

        if key not in data:
            data[key] = {}

        return self._dive_to_set_value(data[key], path[1:], value)

    def _copy(self, origin, path, result, current_level=None):

        if not path:
            return result

        if not current_level:
            current_level = []

        key = path[0]
        if key not in origin:
            return result

        value = origin.get(key)
        current_level.append(key)

        if not value or len(path) == 1:
            self._dive_to_set_value(result, current_level, value)
            return result

        if isinstance(value, list):
            current_data = self._dive_to_get_value(result, current_level, [])
            path = path[1:]

            for index, i in enumerate(value):
                if isinstance(i, list):
                    raise ValueError(
                        'Unsupported list nested inside list at key: %s' % key)

                try:
                    v = current_data[index]
                except IndexError:
                    v = None

                if not isinstance(i, dict):
                    try:
                        current_data[index] = i
                    except IndexError:
                        current_data.append(i)
                    continue

                if not v:
                    v = {}
                    current_data.append(self._copy(i, path, v))
                else:
                    current_data[index] = self._copy(i, path, v)

            self._dive_to_set_value(result, current_level, current_data)

        return self._copy(value, path[1:], result, current_level)

    def _flatten_fields(self, data, pre=None):
        pre = pre[:] if pre else []
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict):
                    for d in self._flatten_fields(value, pre + [key]):
                        yield d
                elif isinstance(value, (list, tuple, set)):
                    if not len(value):
                        continue
                    v = value[0]
                    for d in self._flatten_fields(v, pre + [key]):
                        yield d
                else:
                    yield pre + [key]
        else:
            yield pre

    def _get_diff_fields(self, from_fields, to_fields):
        result = []

        check_fields = list(map(
            lambda f: '.'.join(f),
            to_fields
        ))

        for array_type_field in from_fields:
            is_ok = True

            str_type_field = '.'.join(array_type_field)
            for cf in check_fields:
                if cf in str_type_field:
                    is_ok = False
                    break

            if not is_ok:
                continue

            result.append(array_type_field)

        return result

    def run(self):
        if not self.include_fields and not self.exclude_fields:
            return self.data

        result = dict()

        included_fields = self._convert_fields_to_list(
            self.include_fields
        )

        excluded_fields = self._convert_fields_to_list(
            self.exclude_fields
        )

        if included_fields:
            result_fields = included_fields
        else:
            result_fields = list(self._flatten_fields(self.data))
            result_fields = self._get_diff_fields(
                result_fields,
                excluded_fields
            )

        for field in result_fields:
            result = self._copy(self.data, field, result)
        return result


VERSION = (0, 0, 1)
