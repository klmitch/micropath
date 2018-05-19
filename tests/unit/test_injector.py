# Copyright (C) 2018 by Kevin L. Mitchell <klmitch@mit.edu>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License. You may
# obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing
# permissions and limitations under the License.

import functools
import inspect

import pytest
import six

from micropath import injector


class TestWantSignature(object):
    if six.PY2:
        def test_py2_getsig_noargs(self, mocker):
            argspec = inspect.ArgSpec([], None, None, None)
            mock_getargspec = mocker.patch.object(
                injector.inspect, 'getargspec',
                return_value=argspec,
            )

            result = injector.WantSignature._getsig('func')

            assert result == (
                [],
                set(),
                set(),
                False,
                False,
            )
            mock_getargspec.assert_called_once_with('func')

        def test_py2_getsig_withargs_nodefaults(self, mocker):
            argspec = inspect.ArgSpec(['a', 'b', 'c'], None, None, None)
            mock_getargspec = mocker.patch.object(
                injector.inspect, 'getargspec',
                return_value=argspec,
            )

            result = injector.WantSignature._getsig('func')

            assert result == (
                ['a', 'b', 'c'],
                set(['a', 'b', 'c']),
                set(),
                False,
                False,
            )
            mock_getargspec.assert_called_once_with('func')

        def test_py2_getsig_withargs_withdefaults(self, mocker):
            argspec = inspect.ArgSpec(['a', 'b', 'c'], None, None, (2, 3))
            mock_getargspec = mocker.patch.object(
                injector.inspect, 'getargspec',
                return_value=argspec,
            )

            result = injector.WantSignature._getsig('func')

            assert result == (
                ['a', 'b', 'c'],
                set(['a']),
                set(['b', 'c']),
                False,
                False,
            )
            mock_getargspec.assert_called_once_with('func')

        def test_py2_getsig_allposargs(self, mocker):
            argspec = inspect.ArgSpec(['a', 'b', 'c'], 'd', None, (2, 3))
            mock_getargspec = mocker.patch.object(
                injector.inspect, 'getargspec',
                return_value=argspec,
            )

            result = injector.WantSignature._getsig('func')

            assert result == (
                ['a', 'b', 'c'],
                set(['a']),
                set(['b', 'c']),
                True,
                False,
            )
            mock_getargspec.assert_called_once_with('func')

        def test_py2_getsig_allkwargs(self, mocker):
            argspec = inspect.ArgSpec(['a', 'b', 'c'], None, 'e', (2, 3))
            mock_getargspec = mocker.patch.object(
                injector.inspect, 'getargspec',
                return_value=argspec,
            )

            result = injector.WantSignature._getsig('func')

            assert result == (
                ['a', 'b', 'c'],
                set(['a']),
                set(['b', 'c']),
                False,
                True,
            )
            mock_getargspec.assert_called_once_with('func')
    else:  # Python 3
        def test_py3_getsig_noargs(self, mocker):
            signature = inspect.Signature(parameters=[])
            mock_signature = mocker.patch.object(
                injector.inspect, 'signature',
                return_value=signature,
            )

            result = injector.WantSignature._getsig('func')

            assert result == (
                [],
                set(),
                set(),
                False,
                False,
            )
            mock_signature.assert_called_once_with(
                'func',
                follow_wrapped=False,
            )

        def test_py3_getsig_withargs_nodefaults(self, mocker):
            signature = inspect.Signature(parameters=[
                inspect.Parameter('a', inspect.Parameter.POSITIONAL_ONLY),
                inspect.Parameter(
                    'b', inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                inspect.Parameter('c', inspect.Parameter.KEYWORD_ONLY),
            ])
            mock_signature = mocker.patch.object(
                injector.inspect, 'signature',
                return_value=signature,
            )

            result = injector.WantSignature._getsig('func')

            assert result == (
                ['a', 'b'],
                set(['b', 'c']),
                set(),
                False,
                False,
            )
            mock_signature.assert_called_once_with(
                'func',
                follow_wrapped=False,
            )

        def test_py3_getsig_withargs_withdefaults(self, mocker):
            signature = inspect.Signature(parameters=[
                inspect.Parameter('a', inspect.Parameter.POSITIONAL_ONLY),
                inspect.Parameter(
                    'b', inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                inspect.Parameter(
                    'c', inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=3,
                ),
                inspect.Parameter(
                    'd', inspect.Parameter.KEYWORD_ONLY,
                    default=4,
                ),
            ])
            mock_signature = mocker.patch.object(
                injector.inspect, 'signature',
                return_value=signature,
            )

            result = injector.WantSignature._getsig('func')

            assert result == (
                ['a', 'b', 'c'],
                set(['b']),
                set(['c', 'd']),
                False,
                False,
            )
            mock_signature.assert_called_once_with(
                'func',
                follow_wrapped=False,
            )

        def test_py3_getsig_allposargs(self, mocker):
            signature = inspect.Signature(parameters=[
                inspect.Parameter('a', inspect.Parameter.POSITIONAL_ONLY),
                inspect.Parameter(
                    'b', inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                inspect.Parameter(
                    'c', inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=3,
                ),
                inspect.Parameter('d', inspect.Parameter.VAR_POSITIONAL),
                inspect.Parameter(
                    'e', inspect.Parameter.KEYWORD_ONLY,
                    default=4,
                ),
            ])
            mock_signature = mocker.patch.object(
                injector.inspect, 'signature',
                return_value=signature,
            )

            result = injector.WantSignature._getsig('func')

            assert result == (
                ['a', 'b', 'c'],
                set(['b']),
                set(['c', 'e']),
                True,
                False,
            )
            mock_signature.assert_called_once_with(
                'func',
                follow_wrapped=False,
            )

        def test_py3_getsig_allkwargs(self, mocker):
            signature = inspect.Signature(parameters=[
                inspect.Parameter('a', inspect.Parameter.POSITIONAL_ONLY),
                inspect.Parameter(
                    'b', inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                inspect.Parameter(
                    'c', inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=3,
                ),
                inspect.Parameter(
                    'd', inspect.Parameter.KEYWORD_ONLY,
                    default=4,
                ),
                inspect.Parameter('e', inspect.Parameter.VAR_KEYWORD),
            ])
            mock_signature = mocker.patch.object(
                injector.inspect, 'signature',
                return_value=signature,
            )

            result = injector.WantSignature._getsig('func')

            assert result == (
                ['a', 'b', 'c'],
                set(['b']),
                set(['c', 'd']),
                False,
                True,
            )
            mock_signature.assert_called_once_with(
                'func',
                follow_wrapped=False,
            )

    def test_from_func_cached(self, mocker):
        mock_getsig = mocker.patch.object(
            injector.WantSignature, '_getsig',
            return_value=(
                ['a', 'b', 'c'], set(['a']), set(['b', 'c']),
                False, False,
            ),
        )
        mock_init = mocker.patch.object(
            injector.WantSignature, '__init__',
            return_value=None,
        )
        func = mocker.Mock(_micropath_signature='signature')

        result = injector.WantSignature.from_func(func)

        assert result == 'signature'
        assert func._micropath_signature == 'signature'
        mock_getsig.assert_not_called()
        mock_init.assert_not_called()

    def test_from_func_uncached_base(self, mocker):
        mock_getsig = mocker.patch.object(
            injector.WantSignature, '_getsig',
            return_value=(
                ['a', 'b', 'c'], set(['a']), set(['b', 'c']),
                False, False,
            ),
        )
        mock_init = mocker.patch.object(
            injector.WantSignature, '__init__',
            return_value=None,
        )
        func = mocker.Mock(spec=[])

        result = injector.WantSignature.from_func(func)

        assert isinstance(result, injector.WantSignature)
        assert func._micropath_signature is result
        mock_getsig.assert_called_once_with(func)
        mock_init.assert_called_once_with(
            func, ['a', 'b', 'c'], set(['a']), set(['b', 'c']),
            False, False,
        )

    def test_from_func_uncached_not_allkw(self, mocker):
        mock_getsig = mocker.patch.object(
            injector.WantSignature, '_getsig',
            return_value=(
                ['a', 'b', 'c'], set(['a']), set(['b', 'c']),
                False, False,
            ),
        )
        mock_init = mocker.patch.object(
            injector.WantSignature, '__init__',
            return_value=None,
        )
        func = mocker.Mock(spec=[])

        result = injector.WantSignature.from_func(
            func,
            provides=['d'],
            required=['e'],
            optional=['f'],
        )

        assert isinstance(result, injector.WantSignature)
        assert func._micropath_signature is result
        mock_getsig.assert_called_once_with(func)
        mock_init.assert_called_once_with(
            func, ['a', 'b', 'c'], set(['a']), set(['b', 'c']),
            False, False,
        )

    def test_from_func_uncached_with_allkw_and_req_opt(self, mocker):
        mock_getsig = mocker.patch.object(
            injector.WantSignature, '_getsig',
            return_value=(
                ['a', 'b', 'c'], set(['a']), set(['b', 'c']),
                False, True,
            ),
        )
        mock_init = mocker.patch.object(
            injector.WantSignature, '__init__',
            return_value=None,
        )
        func = mocker.Mock(spec=[])

        result = injector.WantSignature.from_func(
            func,
            provides=['d'],
            required=['e'],
            optional=['f'],
        )

        assert isinstance(result, injector.WantSignature)
        assert func._micropath_signature is result
        mock_getsig.assert_called_once_with(func)
        mock_init.assert_called_once_with(
            func, ['a', 'b', 'c'], set(['a', 'e']), set(['b', 'c', 'f']),
            False, False,
        )

    def test_from_func_uncached_with_allkw_without_req_opt(self, mocker):
        mock_getsig = mocker.patch.object(
            injector.WantSignature, '_getsig',
            return_value=(
                ['a', 'b', 'c'], set(['a']), set(['b', 'c']),
                False, True,
            ),
        )
        mock_init = mocker.patch.object(
            injector.WantSignature, '__init__',
            return_value=None,
        )
        func = mocker.Mock(spec=[])

        result = injector.WantSignature.from_func(
            func,
            provides=['d'],
        )

        assert isinstance(result, injector.WantSignature)
        assert func._micropath_signature is result
        mock_getsig.assert_called_once_with(func)
        mock_init.assert_called_once_with(
            func, ['a', 'b', 'c'], set(['a']), set(['b', 'c']),
            False, True,
        )

    def test_from_func_uncached_wrapper(self, mocker):
        mock_getsig = mocker.patch.object(
            injector.WantSignature, '_getsig',
            return_value=(
                ['a', 'b', 'c'], set(['a']), set(['b', 'c']),
                False, False,
            ),
        )
        mock_init = mocker.patch.object(
            injector.WantSignature, '__init__',
            return_value=None,
        )
        func = mocker.Mock(spec=[])
        wrapped = mocker.Mock(_micropath_signature=mocker.Mock(
            required=set(['b', 'd', 'e']),
            optional=set(['f']),
        ))

        result = injector.WantSignature.from_func(
            func,
            wrapped=wrapped,
            provides=['d'],
        )

        assert isinstance(result, injector.WantSignature)
        assert func._micropath_signature is result
        mock_getsig.assert_called_once_with(func)
        mock_init.assert_called_once_with(
            func, ['a', 'b', 'c'], set(['a', 'b', 'e']), set(['c', 'f']),
            False, False,
        )

    def test_init_base(self):
        result = injector.WantSignature(
            'func', ['a', 'b', 'c'], set(['a']), set(['b', 'c']),
            'pos', 'kw',
        )

        assert result.func == 'func'
        assert result.arg_order == ['a', 'b', 'c']
        assert result.required == set(['a'])
        assert result.optional == set(['b', 'c'])
        assert result.all_pos == 'pos'
        assert result.all_kw == 'kw'
        assert result.all_args == set(['a', 'b', 'c'])

    def test_init_overlap(self):
        with pytest.raises(ValueError):
            injector.WantSignature(
                'func', ['a', 'b', 'c'], set(['a', 'b']), set(['b', 'c']),
                'pos', 'kw',
            )

    def test_contains_true(self):
        obj = injector.WantSignature(
            'func', ['a', 'b', 'c'], set(['a']), set(['b', 'c']),
            False, False,
        )

        assert 'b' in obj

    def test_contains_false(self):
        obj = injector.WantSignature(
            'func', ['a', 'b', 'c'], set(['a']), set(['b', 'c']),
            False, False,
        )

        assert 'd' not in obj

    def test_contains_all_kw(self):
        obj = injector.WantSignature(
            'func', ['a', 'b', 'c'], set(['a']), set(['b', 'c']),
            False, True,
        )

        assert 'd' in obj

    def test_call_base(self, mocker):
        func = mocker.Mock()
        obj = injector.WantSignature(
            func, ['a', 'b', 'c'], set(['a']), set(['b', 'c']),
            False, False,
        )

        result = obj((), {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5})

        assert result == func.return_value
        func.assert_called_once_with(a=1, b=2, c=3)

    def test_call_positional(self, mocker):
        func = mocker.Mock()
        obj = injector.WantSignature(
            func, ['self', 'a', 'b', 'c'], set(['self', 'a']), set(['b', 'c']),
            False, False,
        )

        result = obj(('self',), {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5})

        assert result == func.return_value
        func.assert_called_once_with('self', a=1, b=2, c=3)

    def test_call_too_many_positional(self, mocker):
        func = mocker.Mock()
        obj = injector.WantSignature(
            func, ['a', 'b', 'c'], set(['a']), set(['b', 'c']),
            False, False,
        )

        with pytest.raises(TypeError):
            obj(
                ('a', 'b', 'c', 'd'), {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5},
            )
        func.assert_not_called()

    def test_call_all_positional(self, mocker):
        func = mocker.Mock()
        obj = injector.WantSignature(
            func, ['a', 'b', 'c'], set(['a']), set(['b', 'c']),
            True, False,
        )

        result = obj(
            ('a', 'b', 'c', 'd'), {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5},
        )

        assert result == func.return_value
        func.assert_called_once_with('a', 'b', 'c', 'd')

    def test_call_additional(self, mocker):
        func = mocker.Mock()
        obj = injector.WantSignature(
            func, ['a', 'b', 'c'], set(['a']), set(['b', 'c']),
            False, False,
        )

        result = obj(
            (), {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5},
            {'b': 'b'},
        )

        assert result == func.return_value
        func.assert_called_once_with(a=1, b='b', c=3)

    def test_call_all_kw(self, mocker):
        func = mocker.Mock()
        obj = injector.WantSignature(
            func, ['a', 'b', 'c'], set(['a']), set(['b', 'c']),
            False, True,
        )

        result = obj(
            (), {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5},
            {'b': 'b', 'f': 'f'},
        )

        assert result == func.return_value
        func.assert_called_once_with(a=1, b='b', c=3, d=4, e=5, f='f')

    def test_call_missing(self, mocker):
        func = mocker.Mock()
        obj = injector.WantSignature(
            func, ['a', 'b', 'c'], set(['a']), set(['b', 'c']),
            False, False,
        )

        with pytest.raises(TypeError):
            obj((), {'b': 2, 'c': 3, 'd': 4, 'e': 5})
        func.assert_not_called()


class TestInjectorCleanup(object):
    def test_init(self):
        result = injector.InjectorCleanup('injector')

        assert result.injector == 'injector'
        assert result.keep is None

    def test_enter(self, mocker):
        inject = mocker.Mock(_keys=set(['a', 'b', 'c']))
        obj = injector.InjectorCleanup(inject)

        result = obj.__enter__()

        assert result is inject
        assert obj.keep is not inject._keys
        assert obj.keep == inject._keys

    def test_exit(self, mocker):
        inject = mocker.MagicMock(_keys=set(['a', 'b', 'c', 'd', 'e', 'f']))
        obj = injector.InjectorCleanup(inject)
        obj.keep = set(['a', 'b', 'c'])

        result = obj.__exit__(None, None, None)

        assert result is None
        assert obj.keep is None
        inject.__delitem__.assert_has_calls([
            mocker.call('d'),
            mocker.call('e'),
            mocker.call('f'),
        ], any_order=True)
        assert inject.__delitem__.call_count == 3


class TestInjector(object):
    def test_init(self):
        result = injector.Injector()

        assert result._available == {}
        assert result._deferred == {}
        assert result._keys == set()

    def test_len(self):
        obj = injector.Injector()
        obj._keys |= set(['a', 'b', 'c'])

        assert len(obj) == 3

    def test_iter(self):
        obj = injector.Injector()
        obj._keys |= set(['a', 'b', 'c'])

        assert set(iter(obj)) == obj._keys

    def test_getitem_available(self, mocker):
        mock_call = mocker.patch.object(
            injector.Injector, '__call__',
            return_value='deferred',
        )
        obj = injector.Injector()
        obj._available['a'] = 1
        obj._keys = set(['a'])

        assert obj['a'] == 1
        assert obj._available == {'a': 1}
        mock_call.assert_not_called()

    def test_getitem_deferred(self, mocker):
        mock_call = mocker.patch.object(
            injector.Injector, '__call__',
            return_value='deferred',
        )
        obj = injector.Injector()
        obj._deferred['a'] = 'func'
        obj._keys = set(['a'])

        assert obj['a'] == 'deferred'
        assert obj._available == {'a': 'deferred'}
        mock_call.assert_called_once_with('func')

    def test_getitem_missing(self, mocker):
        mock_call = mocker.patch.object(
            injector.Injector, '__call__',
            return_value='deferred',
        )
        obj = injector.Injector()

        with pytest.raises(KeyError):
            obj['a']
        assert obj._available == {}
        mock_call.assert_not_called()

    def test_setitem(self):
        obj = injector.Injector()

        obj['a'] = 1

        assert obj._available == {'a': 1}
        assert obj._keys == set(['a'])

    def test_delitem_available_only(self):
        obj = injector.Injector()
        obj._available['a'] = 1
        obj._keys = set(['a'])

        del obj['a']

        assert obj._available == {}
        assert obj._deferred == {}
        assert obj._keys == set()

    def test_delitem_deferred_only(self):
        obj = injector.Injector()
        obj._deferred['a'] = 'deferred'
        obj._keys = set(['a'])

        del obj['a']

        assert obj._available == {}
        assert obj._deferred == {}
        assert obj._keys == set()

    def test_delitem_available_and_deferred(self):
        obj = injector.Injector()
        obj._available['a'] = 1
        obj._deferred['a'] = 'deferred'
        obj._keys = set(['a'])

        del obj['a']

        assert obj._available == {}
        assert obj._deferred == {}
        assert obj._keys == set()

    def test_delitem_missing(self):
        obj = injector.Injector()

        with pytest.raises(KeyError):
            del obj['a']
        assert obj._available == {}
        assert obj._deferred == {}
        assert obj._keys == set()

    def test_call_base(self, mocker):
        mock_ismethod = mocker.patch.object(
            injector.inspect, 'ismethod',
            return_value=False,
        )
        mock_get_method_self = mocker.patch.object(
            injector.six, 'get_method_self',
            return_value='obj',
        )
        mock_get_method_function = mocker.patch.object(
            injector.six, 'get_method_function',
            return_value='method',
        )
        mock_from_func = mocker.patch.object(
            injector.WantSignature, 'from_func',
        )
        obj = injector.Injector()

        result = obj('func', 1, 2, 3, a=4, b=5, c=6)

        assert result == mock_from_func.return_value.return_value
        mock_ismethod.assert_called_once_with('func')
        mock_get_method_self.assert_not_called()
        mock_get_method_function.assert_not_called()
        mock_from_func.assert_called_once_with('func')
        mock_from_func.return_value.assert_called_once_with(
            (1, 2, 3), obj, {'a': 4, 'b': 5, 'c': 6},
        )

    def test_call_method(self, mocker):
        mock_ismethod = mocker.patch.object(
            injector.inspect, 'ismethod',
            return_value=True,
        )
        mock_get_method_self = mocker.patch.object(
            injector.six, 'get_method_self',
            return_value='obj',
        )
        mock_get_method_function = mocker.patch.object(
            injector.six, 'get_method_function',
            return_value='method',
        )
        mock_from_func = mocker.patch.object(
            injector.WantSignature, 'from_func',
        )
        obj = injector.Injector()

        result = obj('func', 1, 2, 3, a=4, b=5, c=6)

        assert result == mock_from_func.return_value.return_value
        mock_ismethod.assert_called_once_with('func')
        mock_get_method_self.assert_called_once_with('func')
        mock_get_method_function.assert_called_once_with('func')
        mock_from_func.assert_called_once_with('method')
        mock_from_func.return_value.assert_called_once_with(
            ('obj', 1, 2, 3), obj, {'a': 4, 'b': 5, 'c': 6},
        )

    def test_call_no_func(self, mocker):
        mock_ismethod = mocker.patch.object(
            injector.inspect, 'ismethod',
            return_value=False,
        )
        mock_get_method_self = mocker.patch.object(
            injector.six, 'get_method_self',
            return_value='obj',
        )
        mock_get_method_function = mocker.patch.object(
            injector.six, 'get_method_function',
            return_value='method',
        )
        mock_from_func = mocker.patch.object(
            injector.WantSignature, 'from_func',
        )
        obj = injector.Injector()

        with pytest.raises(TypeError):
            obj(a=4, b=5, c=6)
        mock_ismethod.assert_not_called()
        mock_get_method_self.assert_not_called()
        mock_get_method_function.assert_not_called()
        mock_from_func.assert_not_called()
        mock_from_func.return_value.assert_not_called()

    def test_set_deferred(self):
        obj = injector.Injector()

        obj.set_deferred('a', 'deferred')

        assert obj._deferred == {'a': 'deferred'}

    def test_cleanup(self, mocker):
        mock_InjectorCleanup = mocker.patch.object(
            injector, 'InjectorCleanup',
        )
        obj = injector.Injector()

        result = obj.cleanup()

        assert result == mock_InjectorCleanup.return_value
        mock_InjectorCleanup.assert_called_once_with(obj)


class TestInject(object):
    def test_base(self, mocker):
        mock_from_func = mocker.patch.object(
            injector.WantSignature, 'from_func',
        )
        func = mocker.Mock()

        decorator = injector.inject()

        assert callable(decorator)
        mock_from_func.assert_not_called()

        result = decorator(func)

        assert result == func
        mock_from_func.assert_called_once_with(
            func,
            required=None,
            optional=None,
        )
        func.assert_not_called()

    def test_alt(self, mocker):
        mock_from_func = mocker.patch.object(
            injector.WantSignature, 'from_func',
        )
        func = mocker.Mock()

        decorator = injector.inject(required='required', optional='optional')

        assert callable(decorator)
        mock_from_func.assert_not_called()

        result = decorator(func)

        assert result == func
        mock_from_func.assert_called_once_with(
            func,
            required='required',
            optional='optional',
        )
        func.assert_not_called()


class TestWraps(object):
    def test_base(self, mocker):
        mock_from_func = mocker.patch.object(
            injector.WantSignature, 'from_func',
        )
        mock_wraps = mocker.patch.object(injector.six, 'wraps')
        func = mocker.Mock()

        decorator = injector.wraps('wrapped')

        assert callable(decorator)
        mock_from_func.assert_not_called()
        mock_wraps.assert_not_called()

        result = decorator(func)

        assert result == mock_wraps.return_value.return_value
        assert result._micropath_signature == mock_from_func.return_value
        mock_from_func.assert_called_once_with(
            func, 'wrapped', None, [], [],
        )
        mock_wraps.assert_called_once_with(
            'wrapped', functools.WRAPPER_ASSIGNMENTS,
            functools.WRAPPER_UPDATES,
        )
        mock_wraps.return_value.assert_called_once_with(func)

    def test_alt(self, mocker):
        mock_from_func = mocker.patch.object(
            injector.WantSignature, 'from_func',
        )
        mock_wraps = mocker.patch.object(injector.six, 'wraps')
        func = mocker.Mock()

        decorator = injector.wraps(
            'wrapped', 'assigned', 'updated', 'provides', 'required',
            'optional',
        )

        assert callable(decorator)
        mock_from_func.assert_not_called()
        mock_wraps.assert_not_called()

        result = decorator(func)

        assert result == mock_wraps.return_value.return_value
        assert result._micropath_signature == mock_from_func.return_value
        mock_from_func.assert_called_once_with(
            func, 'wrapped', 'provides', 'required', 'optional',
        )
        mock_wraps.assert_called_once_with(
            'wrapped', 'assigned', 'updated',
        )
        mock_wraps.return_value.assert_called_once_with(func)


class TestCallWrapped(object):
    def test_base(self, mocker):
        mock_from_func = mocker.patch.object(
            injector.WantSignature, 'from_func',
        )

        result = injector.call_wrapped('func', 'args', 'kwargs')

        assert result == mock_from_func.return_value.return_value
        mock_from_func.assert_called_once_with('func')
        mock_from_func.return_value.assert_called_once_with('args', 'kwargs')


class TestWants(object):
    def test_true(self, mocker):
        mock_from_func = mocker.patch.object(
            injector.WantSignature, 'from_func',
            return_value=set(['a']),
        )

        result = injector.wants('func', 'a')

        assert result is True
        mock_from_func.assert_called_once_with('func')

    def test_false(self, mocker):
        mock_from_func = mocker.patch.object(
            injector.WantSignature, 'from_func',
            return_value=set(['a']),
        )

        result = injector.wants('func', 'b')

        assert result is False
        mock_from_func.assert_called_once_with('func')
