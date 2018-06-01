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

import pytest

from micropath import elements


class ElementForTest(elements.Element):
    def set_ident(self, ident):
        super(ElementForTest, self).set_ident(ident)


class OtherElement(elements.Element):
    def set_ident(self, ident):
        pass


class TestElement(object):
    def test_init_base(self):
        result = ElementForTest('ident')

        assert result.ident == 'ident'
        assert result.parent is None
        assert result.paths == {}
        assert result.bindings == {}
        assert result.methods == {}
        assert result.delegation is None

    def test_init_alt(self):
        result = ElementForTest('ident', 'parent')

        assert result.ident == 'ident'
        assert result.parent == 'parent'
        assert result.paths == {}
        assert result.bindings == {}
        assert result.methods == {}
        assert result.delegation is None

    def test_set_ident_base(self):
        obj = ElementForTest(None)

        obj.set_ident('ident')

        assert obj.ident == 'ident'

    def test_set_ident_set(self):
        obj = ElementForTest('ident')

        with pytest.raises(ValueError):
            obj.set_ident('spam')
        assert obj.ident == 'ident'

    @staticmethod
    def sub_sel(subs, *elems):
        return {elem: subs[elem] for elem in elems}

    def test_path_base(self, mocker):
        mock_Path = mocker.patch.object(
            elements, 'Path',
            return_value=mocker.Mock(ident=None),
        )
        obj = ElementForTest('ident')

        result = obj.path()

        assert result == mock_Path.return_value
        mock_Path.assert_called_once_with(None, parent=obj)
        assert obj.paths == {}

    def test_path_with_ident(self, mocker):
        mock_Path = mocker.patch.object(
            elements, 'Path',
            return_value=mocker.Mock(ident='spam'),
        )
        obj = ElementForTest('ident')

        result = obj.path('spam')

        assert result == mock_Path.return_value
        mock_Path.assert_called_once_with('spam', parent=obj)
        assert obj.paths == {'spam': result}

    def test_path_conflict(self, mocker):
        mock_Path = mocker.patch.object(
            elements, 'Path',
            return_value=mocker.Mock(ident='spam'),
        )
        obj = ElementForTest('ident')
        obj.paths['spam'] = 'conflict'

        with pytest.raises(ValueError):
            obj.path('spam')
        mock_Path.assert_called_once_with('spam', parent=obj)
        assert obj.paths == {'spam': 'conflict'}

    def test_binding_base(self, mocker):
        mock_Binding = mocker.patch.object(
            elements, 'Binding',
            return_value=mocker.Mock(ident=None),
        )
        obj = ElementForTest('ident')

        result = obj.bind()

        assert result == mock_Binding.return_value
        mock_Binding.assert_called_once_with(
            None,
            parent=obj,
        )
        assert obj.bindings == {}

    def test_binding_with_ident(self, mocker):
        mock_Binding = mocker.patch.object(
            elements, 'Binding',
            return_value=mocker.Mock(ident='spam'),
        )
        obj = ElementForTest('ident')

        result = obj.bind('spam')

        assert result == mock_Binding.return_value
        mock_Binding.assert_called_once_with(
            'spam',
            parent=obj,
        )
        assert obj.bindings == {'spam': result}

    def test_binding_conflict(self, mocker):
        mock_Binding = mocker.patch.object(
            elements, 'Binding',
            return_value=mocker.Mock(ident='spam'),
        )
        obj = ElementForTest('ident')
        obj.bindings['spam'] = 'conflict'

        with pytest.raises(ValueError):
            obj.bind('spam')
        mock_Binding.assert_called_once_with(
            'spam',
            parent=obj,
        )
        assert obj.bindings == {'spam': 'conflict'}

    def test_route_func(self, mocker):
        mock_Method = mocker.patch.object(
            elements, 'Method',
            return_value=mocker.Mock(ident=None),
        )
        mock_from_func = mocker.patch.object(
            elements.injector.WantSignature, 'from_func',
        )
        obj = ElementForTest('ident')
        func = mocker.Mock(_micropath_handler=False)

        result = obj.route(func)

        assert result == func
        mock_Method.assert_called_once_with(None, func, parent=obj)
        mock_from_func.assert_called_once_with(func)
        assert obj.methods == {None: mock_Method.return_value}
        assert func._micropath_handler is True
        assert func._micropath_elem is obj

    def test_route_no_methods(self, mocker):
        mock_Method = mocker.patch.object(
            elements, 'Method',
            return_value=mocker.Mock(ident=None),
        )
        mock_from_func = mocker.patch.object(
            elements.injector.WantSignature, 'from_func',
        )
        obj = ElementForTest('ident')
        func = mocker.Mock(_micropath_handler=False)

        decorator = obj.route()

        assert callable(decorator)
        assert decorator != func
        mock_Method.assert_not_called()
        mock_from_func.assert_not_called()
        assert obj.methods == {}

        result = decorator(func)

        assert result == func
        mock_Method.assert_called_once_with(None, func, parent=obj)
        mock_from_func.assert_called_once_with(func)
        assert obj.methods == {None: mock_Method.return_value}
        assert func._micropath_handler is True
        assert func._micropath_elem is obj

    def test_route_with_methods(self, mocker):
        methods = {
            'get': mocker.Mock(ident='get'),
            'put': mocker.Mock(ident='put'),
        }
        mock_Method = mocker.patch.object(
            elements, 'Method',
            side_effect=lambda x, f, parent: methods[x],
        )
        mock_from_func = mocker.patch.object(
            elements.injector.WantSignature, 'from_func',
        )
        obj = ElementForTest('ident')
        func = mocker.Mock(_micropath_handler=False)

        decorator = obj.route('get', 'put')

        assert callable(decorator)
        assert decorator != func
        mock_Method.assert_not_called()
        mock_from_func.assert_not_called()
        assert obj.methods == {}

        result = decorator(func)

        assert result == func
        mock_Method.assert_has_calls([
            mocker.call('get', func, parent=obj),
            mocker.call('put', func, parent=obj),
        ])
        assert mock_Method.call_count == 2
        mock_from_func.assert_called_once_with(func)
        assert obj.methods == methods
        assert func._micropath_handler is True
        assert func._micropath_elem is obj

    def test_route_with_methods_internal_duplicate(self, mocker):
        methods = {
            'get': mocker.Mock(ident='get'),
            'put': mocker.Mock(ident='put'),
        }
        mock_Method = mocker.patch.object(
            elements, 'Method',
            side_effect=lambda x, f, parent: methods[x],
        )
        mock_from_func = mocker.patch.object(
            elements.injector.WantSignature, 'from_func',
        )
        obj = ElementForTest('ident')
        func = mocker.Mock(_micropath_handler=False)

        decorator = obj.route('get', 'put', 'get')

        assert callable(decorator)
        assert decorator != func
        mock_Method.assert_not_called()
        mock_from_func.assert_not_called()
        assert obj.methods == {}

        result = decorator(func)

        assert result == func
        mock_Method.assert_has_calls([
            mocker.call('get', func, parent=obj),
            mocker.call('put', func, parent=obj),
        ])
        assert mock_Method.call_count == 2
        mock_from_func.assert_called_once_with(func)
        assert obj.methods == methods
        assert func._micropath_handler is True
        assert func._micropath_elem is obj

    def test_route_with_methods_external_duplicate(self, mocker):
        methods = {
            'get': mocker.Mock(ident='get'),
            'put': mocker.Mock(ident='put'),
        }
        mock_Method = mocker.patch.object(
            elements, 'Method',
            side_effect=lambda x, f, parent: methods[x],
        )
        mock_from_func = mocker.patch.object(
            elements.injector.WantSignature, 'from_func',
        )
        obj = ElementForTest('ident')
        obj.methods['get'] = 'conflict'

        with pytest.raises(ValueError):
            obj.route('get', 'put')
        mock_Method.assert_not_called()
        mock_from_func.assert_not_called()
        assert obj.methods == {'get': 'conflict'}

    def test_mount_base(self, mocker):
        mock_init = mocker.patch.object(
            elements.Delegation, '__init__',
            return_value=None,
        )
        mock_Method = mocker.patch.object(
            elements, 'Method',
            return_value=mocker.Mock(ident=None),
        )
        obj = ElementForTest('ident')

        result = obj.mount('delegation')

        assert isinstance(result, elements.Delegation)
        assert result.element == obj
        assert obj.methods == {}
        assert obj.delegation == result
        mock_init.assert_called_once_with('delegation', {})
        mock_Method.assert_not_called()

    def test_mount_with_methods(self, mocker):
        methods = {
            'get': mocker.Mock(ident='get', delegation=None),
            'put': mocker.Mock(ident='put', delegation=None),
        }
        mock_init = mocker.patch.object(
            elements.Delegation, '__init__',
            return_value=None,
        )
        mock_Method = mocker.patch.object(
            elements, 'Method',
            side_effect=lambda x, f, parent: methods[x],
        )
        obj = ElementForTest('ident')

        result = obj.mount('delegation', 'get', 'put', a=1, b=2)

        assert isinstance(result, elements.Delegation)
        assert result.element == obj
        assert obj.methods == methods
        for meth in methods.values():
            assert meth.delegation == result
        assert obj.delegation is None
        mock_init.assert_called_once_with('delegation', {'a': 1, 'b': 2})
        mock_Method.assert_has_calls([
            mocker.call('get', None, parent=obj),
            mocker.call('put', None, parent=obj),
        ])
        assert mock_Method.call_count == 2

    def test_mount_with_methods_internal_duplication(self, mocker):
        methods = {
            'get': mocker.Mock(ident='get', delegation=None),
            'put': mocker.Mock(ident='put', delegation=None),
        }
        mock_init = mocker.patch.object(
            elements.Delegation, '__init__',
            return_value=None,
        )
        mock_Method = mocker.patch.object(
            elements, 'Method',
            side_effect=lambda x, f, parent: methods[x],
        )
        obj = ElementForTest('ident')

        result = obj.mount('delegation', 'get', 'put', 'get', a=1, b=2)

        assert isinstance(result, elements.Delegation)
        assert result.element == obj
        assert obj.methods == methods
        for meth in methods.values():
            assert meth.delegation == result
        assert obj.delegation is None
        mock_init.assert_called_once_with('delegation', {'a': 1, 'b': 2})
        mock_Method.assert_has_calls([
            mocker.call('get', None, parent=obj),
            mocker.call('put', None, parent=obj),
        ])
        assert mock_Method.call_count == 2

    def test_mount_with_methods_external_duplication(self, mocker):
        methods = {
            'get': mocker.Mock(ident='get', delegation=None),
            'put': mocker.Mock(ident='put', delegation=None),
        }
        mock_init = mocker.patch.object(
            elements.Delegation, '__init__',
            return_value=None,
        )
        mock_Method = mocker.patch.object(
            elements, 'Method',
            side_effect=lambda x, f, parent: methods[x],
        )
        obj = ElementForTest('ident')
        obj.methods['get'] = 'conflict'

        with pytest.raises(ValueError):
            obj.mount('delegation', 'get', 'put', a=1, b=2)
        assert obj.methods == {'get': 'conflict'}
        for meth in methods.values():
            assert meth.delegation is None
        assert obj.delegation is None
        mock_init.assert_called_once_with('delegation', {'a': 1, 'b': 2})
        mock_Method.assert_not_called()

    def test_mount_delegation(self, mocker):
        delegation = elements.Delegation('delegation', {})
        mock_init = mocker.patch.object(
            elements.Delegation, '__init__',
            return_value=None,
        )
        mock_Method = mocker.patch.object(
            elements, 'Method',
            return_value=mocker.Mock(ident=None),
        )
        obj = ElementForTest('ident')

        result = obj.mount(delegation)

        assert result == delegation
        assert result.element == obj
        assert obj.methods == {}
        assert obj.delegation == delegation
        mock_init.assert_not_called()
        mock_Method.assert_not_called()

    def test_mount_delegation_set(self, mocker):
        mock_init = mocker.patch.object(
            elements.Delegation, '__init__',
            return_value=None,
        )
        mock_Method = mocker.patch.object(
            elements, 'Method',
            return_value=mocker.Mock(ident=None),
        )
        obj = ElementForTest('ident')
        obj.delegation = 'spam'

        with pytest.raises(ValueError):
            obj.mount('delegation')
        assert obj.methods == {}
        assert obj.delegation == 'spam'
        mock_init.assert_not_called()
        mock_Method.assert_not_called()


class TestRoot(object):
    def test_init(self, mocker):
        mock_init = mocker.patch.object(
            elements.Element, '__init__',
            return_value=None,
        )

        result = elements.Root()

        assert isinstance(result, elements.Root)
        mock_init.assert_called_once_with(None)

    def test_set_ident(self):
        obj = elements.Root()

        with pytest.raises(ValueError):
            obj.set_ident('ident')

    def test_add_elem_path(self, mocker):
        elem = mocker.Mock(spec=elements.Path, ident='spam')
        elem.parent = None
        obj = elements.Root()

        obj.add_elem(elem)

        assert obj.paths == {'spam': elem}
        assert obj.bindings == {}
        assert obj.methods == {}
        assert elem.ident == 'spam'
        assert elem.parent is obj
        elem.set_ident.assert_not_called()

    def test_add_elem_path_conflict(self, mocker):
        elem = mocker.Mock(spec=elements.Path, ident='spam')
        elem.parent = None
        obj = elements.Root()
        obj.paths['spam'] = 'conflict'

        with pytest.raises(ValueError):
            obj.add_elem(elem)
        assert obj.paths == {'spam': 'conflict'}
        assert obj.bindings == {}
        assert obj.methods == {}
        assert elem.ident == 'spam'
        assert elem.parent is None
        elem.set_ident.assert_not_called()

    def test_add_elem_binding(self, mocker):
        elem = mocker.Mock(spec=elements.Binding, ident='spam')
        elem.parent = None
        obj = elements.Root()

        obj.add_elem(elem)

        assert obj.paths == {}
        assert obj.bindings == {'spam': elem}
        assert obj.methods == {}
        assert elem.ident == 'spam'
        assert elem.parent is obj
        elem.set_ident.assert_not_called()

    def test_add_elem_binding_conflict(self, mocker):
        elem = mocker.Mock(spec=elements.Binding, ident='spam')
        elem.parent = None
        obj = elements.Root()
        obj.bindings['spam'] = 'conflict'

        with pytest.raises(ValueError):
            obj.add_elem(elem)
        assert obj.paths == {}
        assert obj.bindings == {'spam': 'conflict'}
        assert obj.methods == {}
        assert elem.ident == 'spam'
        assert elem.parent is None
        elem.set_ident.assert_not_called()

    def test_add_elem_method(self, mocker):
        elem = mocker.Mock(spec=elements.Method, ident='spam')
        elem.parent = None
        obj = elements.Root()

        obj.add_elem(elem)

        assert obj.paths == {}
        assert obj.bindings == {}
        assert obj.methods == {'spam': elem}
        assert elem.ident == 'spam'
        assert elem.parent is obj
        elem.set_ident.assert_not_called()

    def test_add_elem_method_conflict(self, mocker):
        elem = mocker.Mock(spec=elements.Method, ident='spam')
        elem.parent = None
        obj = elements.Root()
        obj.methods['spam'] = 'conflict'

        with pytest.raises(ValueError):
            obj.add_elem(elem)
        assert obj.paths == {}
        assert obj.bindings == {}
        assert obj.methods == {'spam': 'conflict'}
        assert elem.ident == 'spam'
        assert elem.parent is None
        elem.set_ident.assert_not_called()

    def test_add_elem_method_all(self, mocker):
        elem = mocker.Mock(spec=elements.Method, ident=None)
        elem.parent = None
        obj = elements.Root()

        obj.add_elem(elem)

        assert obj.paths == {}
        assert obj.bindings == {}
        assert obj.methods == {None: elem}
        assert elem.ident is None
        assert elem.parent is obj
        elem.set_ident.assert_not_called()

    def test_add_elem_method_all_conflict(self, mocker):
        elem = mocker.Mock(spec=elements.Method, ident=None)
        elem.parent = None
        obj = elements.Root()
        obj.methods[None] = 'conflict'

        with pytest.raises(ValueError):
            obj.add_elem(elem)
        assert obj.paths == {}
        assert obj.bindings == {}
        assert obj.methods == {None: 'conflict'}
        assert elem.ident is None
        assert elem.parent is None
        elem.set_ident.assert_not_called()

    def test_add_elem_other(self, mocker):
        elem = mocker.Mock(ident='spam')
        elem.parent = None
        obj = elements.Root()

        with pytest.raises(ValueError):
            obj.add_elem(elem)
        assert obj.paths == {}
        assert obj.bindings == {}
        assert obj.methods == {}
        assert elem.ident == 'spam'
        assert elem.parent is None
        elem.set_ident.assert_not_called()

    def test_add_elem_self(self, mocker):
        obj = elements.Root()

        obj.add_elem(obj)

        assert obj.paths == {}
        assert obj.bindings == {}
        assert obj.methods == {}

    def test_add_elem_root(self, mocker):
        elem = mocker.Mock(spec=elements.Root, ident=None)
        elem.parent = None
        obj = elements.Root()

        with pytest.raises(ValueError):
            obj.add_elem(elem)
        assert obj.paths == {}
        assert obj.bindings == {}
        assert obj.methods == {}
        assert elem.ident is None
        assert elem.parent is None
        elem.set_ident.assert_not_called()

    def test_add_elem_path_no_ident(self, mocker):
        elem = mocker.Mock(spec=elements.Path, ident=None)
        elem.parent = None
        obj = elements.Root()

        obj.add_elem(elem)

        assert obj.paths == {}
        assert obj.bindings == {}
        assert obj.methods == {}
        assert elem.ident is None
        assert elem.parent is obj
        elem.set_ident.assert_not_called()

    def test_add_elem_binding_no_ident(self, mocker):
        elem = mocker.Mock(spec=elements.Binding, ident=None)
        elem.parent = None
        obj = elements.Root()

        obj.add_elem(elem)

        assert obj.paths == {}
        assert obj.bindings == {}
        assert obj.methods == {}
        assert elem.ident is None
        assert elem.parent is obj
        elem.set_ident.assert_not_called()

    def test_add_elem_set_ident(self, mocker):
        elem = mocker.Mock(spec=elements.Path, ident=None)
        elem.parent = None
        obj = elements.Root()

        obj.add_elem(elem, 'spam')

        assert obj.paths == {}
        assert obj.bindings == {}
        assert obj.methods == {}
        assert elem.ident is None
        assert elem.parent is obj
        elem.set_ident.assert_called_once_with('spam')

    def test_add_elem_parents(self, mocker):
        elem = mocker.Mock(spec=elements.Path, ident='spam')
        elem.parent = None
        descendant = mocker.Mock(spec=elements.Path, ident=None)
        descendant.parent = elem
        obj = elements.Root()

        obj.add_elem(descendant, 'descendant')

        assert obj.paths == {'spam': elem}
        assert obj.bindings == {}
        assert obj.methods == {}
        assert elem.ident == 'spam'
        assert elem.parent is obj
        elem.set_ident.assert_not_called()
        descendant.set_ident.assert_called_once_with('descendant')


class TestPath(object):
    def test_set_ident_no_parent(self, mocker):
        mock_set_ident = mocker.patch.object(elements.Element, 'set_ident')
        obj = elements.Path(None)

        obj.set_ident('ident')

        mock_set_ident.assert_called_once_with('ident')

    def test_set_ident_with_parent(self, mocker):
        mock_set_ident = mocker.patch.object(elements.Element, 'set_ident')
        obj = elements.Path(None)
        obj.parent = mocker.Mock(paths={})

        obj.set_ident('ident')

        assert obj.parent.paths == {None: obj}
        mock_set_ident.assert_called_once_with('ident')

    def test_set_ident_conflict(self, mocker):
        mock_set_ident = mocker.patch.object(elements.Element, 'set_ident')
        obj = elements.Path(None)
        obj.parent = mocker.Mock(paths={None: 'conflict'})

        with pytest.raises(ValueError):
            obj.set_ident('ident')
        assert obj.parent.paths == {None: 'conflict'}
        mock_set_ident.assert_called_once_with('ident')


class TestBinding(object):
    def test_init_base(self, mocker):
        mock_init = mocker.patch.object(
            elements.Element, '__init__',
            return_value=None,
        )

        result = elements.Binding('ident')

        assert result._validator is None
        assert result._formatter is None
        mock_init.assert_called_once_with('ident', None)

    def test_init_alt(self, mocker):
        mock_init = mocker.patch.object(
            elements.Element, '__init__',
            return_value=None,
        )

        result = elements.Binding(
            'ident', 'parent',
        )

        assert result._validator is None
        assert result._formatter is None
        mock_init.assert_called_once_with('ident', 'parent')

    def test_hash(self):
        obj = elements.Binding('ident')

        assert hash(obj) == hash('ident')

    def test_eq_equal(self):
        obj1 = elements.Binding('ident')
        obj2 = elements.Binding('ident')

        assert obj1.__eq__(obj2) is True

    def test_eq_unequal(self):
        obj1 = elements.Binding('ident')
        obj2 = elements.Binding('other')

        assert obj1.__eq__(obj2) is False

    def test_eq_wrong_type(self):
        obj1 = elements.Binding('ident')
        obj2 = elements.Path('ident')

        assert obj1.__eq__(obj2) is False

    def test_ne_equal(self):
        obj1 = elements.Binding('ident')
        obj2 = elements.Binding('ident')

        assert obj1.__ne__(obj2) is False

    def test_ne_unequal(self):
        obj1 = elements.Binding('ident')
        obj2 = elements.Binding('other')

        assert obj1.__ne__(obj2) is True

    def test_ne_wrong_type(self):
        obj1 = elements.Binding('ident')
        obj2 = elements.Path('ident')

        assert obj1.__ne__(obj2) is True

    def test_lt_less(self):
        obj1 = elements.Binding('alpha')
        obj2 = elements.Binding('bravo')

        assert obj1.__lt__(obj2) is True

    def test_lt_equal(self):
        obj1 = elements.Binding('alpha')
        obj2 = elements.Binding('alpha')

        assert obj1.__lt__(obj2) is False

    def test_lt_greater(self):
        obj1 = elements.Binding('bravo')
        obj2 = elements.Binding('alpha')

        assert obj1.__lt__(obj2) is False

    def test_lt_wrong_type(self):
        obj1 = elements.Binding('alpha')
        obj2 = elements.Path('bravo')

        assert obj1.__lt__(obj2) is NotImplemented

    def test_set_ident_no_parent(self, mocker):
        mock_set_ident = mocker.patch.object(elements.Element, 'set_ident')
        obj = elements.Binding(None)

        obj.set_ident('ident')

        mock_set_ident.assert_called_once_with('ident')

    def test_set_ident_with_parent(self, mocker):
        mock_set_ident = mocker.patch.object(elements.Element, 'set_ident')
        obj = elements.Binding(None)
        obj.parent = mocker.Mock(bindings={})

        obj.set_ident('ident')

        assert obj.parent.bindings == {None: obj}
        mock_set_ident.assert_called_once_with('ident')

    def test_set_ident_conflict(self, mocker):
        mock_set_ident = mocker.patch.object(elements.Element, 'set_ident')
        obj = elements.Binding(None)
        obj.parent = mocker.Mock(bindings={None: 'conflict'})

        with pytest.raises(ValueError):
            obj.set_ident('ident')
        assert obj.parent.bindings == {None: 'conflict'}
        mock_set_ident.assert_called_once_with('ident')

    def test_validator_base(self, mocker):
        mock_from_func = mocker.patch.object(
            elements.injector.WantSignature, 'from_func',
        )
        obj = elements.Binding('ident')

        result = obj.validator('func')

        assert result == 'func'
        assert obj._validator == 'func'
        mock_from_func.assert_called_once_with('func')

    def test_validator_already_set(self, mocker):
        mock_from_func = mocker.patch.object(
            elements.injector.WantSignature, 'from_func',
        )
        obj = elements.Binding('ident')
        obj._validator = 'spam'

        with pytest.raises(ValueError):
            obj.validator('func')
        assert obj._validator == 'spam'
        mock_from_func.assert_not_called()

    def test_validate_unset(self, mocker):
        inj = mocker.Mock()
        obj = elements.Binding('ident')

        result = obj.validate('controller', inj, 'value')

        assert result == 'value'
        inj.assert_not_called()

    def test_validate_set(self, mocker):
        inj = mocker.Mock()
        obj = elements.Binding('ident')
        obj._validator = 'validator'

        result = obj.validate('controller', inj, 'value')

        assert result == inj.return_value
        inj.assert_called_once_with('validator', 'controller', value='value')

    def test_formatter_base(self):
        obj = elements.Binding('ident')

        result = obj.formatter('func')

        assert result == 'func'
        assert obj._formatter == 'func'

    def test_formatter_already_set(self):
        obj = elements.Binding('ident')
        obj._formatter = 'spam'

        with pytest.raises(ValueError):
            obj.formatter('func')
        assert obj._formatter == 'spam'

    def test_format_unset(self):
        obj = elements.Binding('ident')

        result = obj.format('controller', 1234)

        assert result == '1234'

    def test_format_set(self, mocker):
        obj = elements.Binding('ident')
        obj._formatter = mocker.Mock(return_value='string')

        result = obj.format('controller', 1234)

        assert result == 'string'
        obj._formatter.assert_called_once_with('controller', 1234)


class TestMethod(object):
    def test_init_base(self, mocker):
        mock_init = mocker.patch.object(
            elements.Element, '__init__',
            return_value=None,
        )

        result = elements.Method('get', 'func')

        assert result.func == 'func'
        mock_init.assert_called_once_with('GET', None)

    def test_init_alt(self, mocker):
        mock_init = mocker.patch.object(
            elements.Element, '__init__',
            return_value=None,
        )

        result = elements.Method(None, 'func', 'parent')

        assert result.func == 'func'
        mock_init.assert_called_once_with(None, 'parent')

    def test_set_ident(self):
        obj = elements.Method(None, 'func')

        with pytest.raises(ValueError):
            obj.set_ident('ident')

    def test_path_base(self):
        obj = elements.Method(None, 'func')

        with pytest.raises(ValueError):
            obj.path()

    def test_path_alt(self):
        obj = elements.Method(None, 'func')

        with pytest.raises(ValueError):
            obj.path('ident')

    def test_bind_base(self):
        obj = elements.Method(None, 'func')

        with pytest.raises(ValueError):
            obj.bind()

    def test_bind_alt(self):
        obj = elements.Method(None, 'func')

        with pytest.raises(ValueError):
            obj.bind('ident')

    def test_route_base(self):
        obj = elements.Method(None, 'func')

        with pytest.raises(ValueError):
            obj.route()

    def test_route_alt(self):
        obj = elements.Method(None, 'func')

        with pytest.raises(ValueError):
            obj.route('get', 'put')

    def test_mount(self, mocker):
        mock_mount = mocker.patch.object(elements.Element, 'mount')
        obj = elements.Method(None, 'func')

        result = obj.mount('delegation')

        assert result == mock_mount.return_value
        mock_mount.assert_called_once_with('delegation')


class TestDelegation(object):
    def test_init(self):
        result = elements.Delegation('controller', 'kwargs')

        assert result.controller == 'controller'
        assert result.kwargs == 'kwargs'
        assert result.element is None
        assert result._cache == {}

    def test_dunder_get_class(self, mocker):
        mock_get = mocker.patch.object(elements.Delegation, 'get')
        obj = elements.Delegation('controller', {})

        result = obj.__get__(None, 'class')

        assert result is obj
        mock_get.assert_not_called()

    def test_dunder_get_object(self, mocker):
        mock_get = mocker.patch.object(elements.Delegation, 'get')
        obj = elements.Delegation('controller', {})

        result = obj.__get__('object', 'class')

        assert result == mock_get.return_value
        mock_get.assert_called_once_with('object')

    def test_set(self):
        target = object()
        obj = elements.Delegation('controller', {})

        obj.__set__(target, 'value')

        assert obj._cache == {id(target): 'value'}

    def test_delete_exists(self):
        target = object()
        obj = elements.Delegation('controller', {})
        obj._cache = {id(target): 'value'}

        obj.__delete__(target)

        assert obj._cache == {}

    def test_delete_missing(self):
        target = object()
        obj = elements.Delegation('controller', {})

        obj.__delete__(target)

        assert obj._cache == {}

    def test_get_cached(self, mocker):
        mock_construct = mocker.patch.object(elements.Delegation, 'construct')
        target = object()
        obj = elements.Delegation('controller', {})
        obj._cache = {id(target): 'value'}

        result = obj.get(target)

        assert result == 'value'
        assert obj._cache == {id(target): 'value'}
        mock_construct.assert_not_called()

    def test_get_uncached(self, mocker):
        mock_construct = mocker.patch.object(elements.Delegation, 'construct')
        target = object()
        obj = elements.Delegation('controller', {})
        obj.element = 'element'

        result = obj.get(target)

        assert result == mock_construct.return_value
        assert obj._cache == {id(target): mock_construct.return_value}
        assert mock_construct.return_value._micropath_parent is target
        assert mock_construct.return_value._micropath_elem == 'element'
        mock_construct.assert_called_once_with(target)

    def test_construct(self, mocker):
        target = mocker.Mock()
        obj = elements.Delegation('controller', 'kwargs')

        result = obj.construct(target)

        assert result == target.micropath_construct.return_value
        target.micropath_construct.assert_called_once_with(
            'controller', 'kwargs',
        )


class TestPathFunc(object):
    def test_base(self, mocker):
        mock_Path = mocker.patch.object(elements, 'Path')

        result = elements.path()

        assert result == mock_Path.return_value
        mock_Path.assert_called_once_with(None)

    def test_alt(self, mocker):
        mock_Path = mocker.patch.object(elements, 'Path')

        result = elements.path('ident')

        assert result == mock_Path.return_value
        mock_Path.assert_called_once_with('ident')


class TestBind(object):
    def test_base(self, mocker):
        mock_Binding = mocker.patch.object(elements, 'Binding')

        result = elements.bind()

        assert result == mock_Binding.return_value
        mock_Binding.assert_called_once_with(None)

    def test_alt(self, mocker):
        mock_Binding = mocker.patch.object(elements, 'Binding')

        result = elements.bind('ident')

        assert result == mock_Binding.return_value
        mock_Binding.assert_called_once_with(
            'ident',
        )


class TestRoute(object):
    def test_func(self, mocker):
        mock_Method = mocker.patch.object(
            elements, 'Method',
            return_value=mocker.Mock(ident=None),
        )
        mock_from_func = mocker.patch.object(
            elements.injector.WantSignature, 'from_func',
        )
        func = mocker.Mock(_micropath_methods=None, _micropath_handler=False)

        result = elements.route(func)

        assert result == func
        mock_Method.assert_called_once_with(None, func)
        mock_from_func.assert_called_once_with(func)
        assert func._micropath_methods == [mock_Method.return_value]
        assert func._micropath_handler is True

    def test_no_methods(self, mocker):
        mock_Method = mocker.patch.object(
            elements, 'Method',
            return_value=mocker.Mock(ident=None),
        )
        mock_from_func = mocker.patch.object(
            elements.injector.WantSignature, 'from_func',
        )
        func = mocker.Mock(_micropath_methods=None, _micropath_handler=False)

        decorator = elements.route()

        assert callable(decorator)
        assert decorator != func
        mock_Method.assert_not_called()
        mock_from_func.assert_not_called()
        assert func._micropath_methods is None
        assert func._micropath_handler is False

        result = decorator(func)

        assert result == func
        mock_Method.assert_called_once_with(None, func)
        mock_from_func.assert_called_once_with(func)
        assert func._micropath_methods == [mock_Method.return_value]
        assert func._micropath_handler is True

    def test_with_methods(self, mocker):
        methods = {
            'get': mocker.Mock(ident='get'),
            'put': mocker.Mock(ident='put'),
        }
        mock_Method = mocker.patch.object(
            elements, 'Method',
            side_effect=lambda x, f: methods[x],
        )
        mock_from_func = mocker.patch.object(
            elements.injector.WantSignature, 'from_func',
        )
        func = mocker.Mock(_micropath_methods=None, _micropath_handler=False)

        decorator = elements.route('get', 'put')

        assert callable(decorator)
        assert decorator != func
        mock_Method.assert_not_called()
        mock_from_func.assert_not_called()
        assert func._micropath_methods is None
        assert func._micropath_handler is False

        result = decorator(func)

        assert result == func
        mock_Method.assert_has_calls([
            mocker.call('get', func),
            mocker.call('put', func),
        ])
        assert mock_Method.call_count == 2
        mock_from_func.assert_called_once_with(func)
        assert func._micropath_methods == [methods[x] for x in ('get', 'put')]
        assert func._micropath_handler is True

    def test_with_methods_internal_duplicate(self, mocker):
        methods = {
            'get': mocker.Mock(ident='get'),
            'put': mocker.Mock(ident='put'),
        }
        mock_Method = mocker.patch.object(
            elements, 'Method',
            side_effect=lambda x, f: methods[x],
        )
        mock_from_func = mocker.patch.object(
            elements.injector.WantSignature, 'from_func',
        )
        func = mocker.Mock(_micropath_methods=None, _micropath_handler=False)

        decorator = elements.route('get', 'put', 'get')

        assert callable(decorator)
        assert decorator != func
        mock_Method.assert_not_called()
        mock_from_func.assert_not_called()
        assert func._micropath_methods is None
        assert func._micropath_handler is False

        result = decorator(func)

        assert result == func
        mock_Method.assert_has_calls([
            mocker.call('get', func),
            mocker.call('put', func),
        ])
        assert mock_Method.call_count == 2
        mock_from_func.assert_called_once_with(func)
        assert func._micropath_methods == [methods[x] for x in ('get', 'put')]
        assert func._micropath_handler is True


class TestMount(object):
    def test_base(self, mocker):
        mock_init = mocker.patch.object(
            elements.Delegation, '__init__',
            return_value=None,
        )
        mock_Method = mocker.patch.object(
            elements, 'Method',
            return_value=mocker.Mock(ident=None),
        )

        result = elements.mount('delegation')

        assert isinstance(result, elements.Delegation)
        assert not hasattr(result, '_micropath_methods')
        mock_init.assert_called_once_with('delegation', {})
        mock_Method.assert_not_called()

    def test_with_methods(self, mocker):
        methods = {
            'get': mocker.Mock(ident='get', delegation=None),
            'put': mocker.Mock(ident='put', delegation=None),
        }
        mock_init = mocker.patch.object(
            elements.Delegation, '__init__',
            return_value=None,
        )
        mock_Method = mocker.patch.object(
            elements, 'Method',
            side_effect=lambda x, f: methods[x],
        )

        result = elements.mount('delegation', 'get', 'put', a=1, b=2)

        assert isinstance(result, elements.Delegation)
        assert result._micropath_methods == [methods['get'], methods['put']]
        mock_init.assert_called_once_with('delegation', {'a': 1, 'b': 2})
        mock_Method.assert_has_calls([
            mocker.call('get', None),
            mocker.call('put', None),
        ])

    def test_with_methods_internal_duplication(self, mocker):
        methods = {
            'get': mocker.Mock(ident='get', delegation=None),
            'put': mocker.Mock(ident='put', delegation=None),
        }
        mock_init = mocker.patch.object(
            elements.Delegation, '__init__',
            return_value=None,
        )
        mock_Method = mocker.patch.object(
            elements, 'Method',
            side_effect=lambda x, f: methods[x],
        )

        result = elements.mount('delegation', 'get', 'put', 'get', a=1, b=2)

        assert isinstance(result, elements.Delegation)
        assert result._micropath_methods == [methods['get'], methods['put']]
        mock_init.assert_called_once_with('delegation', {'a': 1, 'b': 2})
        mock_Method.assert_has_calls([
            mocker.call('get', None),
            mocker.call('put', None),
        ])

    def test_delegation(self, mocker):
        delegation = elements.Delegation('delegation', {})
        mock_init = mocker.patch.object(
            elements.Delegation, '__init__',
            return_value=None,
        )
        mock_Method = mocker.patch.object(
            elements, 'Method',
            return_value=mocker.Mock(ident=None),
        )

        result = elements.mount(delegation)

        assert result == delegation
        assert not hasattr(result, '_micropath_methods')
        mock_init.assert_not_called()
        mock_Method.assert_not_called()
