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
from micropath import request


class TestRequest(object):
    def test_init(self, mocker):
        result = request.Request.blank(
            '/is/a/test',
            base_url='http://example.com/this',
        )

        assert result.environ['micropath.base_path'] == '/this'

    def test_url_for_base(self, mocker):
        elems = {
            'a': mocker.Mock(spec=elements.Path, t_parent=None),
            'b': mocker.Mock(spec=elements.Binding, t_parent='a', **{
                'format.return_value': '1',
            }),
            'c': mocker.Mock(spec=elements.Path, t_parent=None),
            'd': mocker.Mock(spec=elements.Binding, t_parent='c', **{
                'format.return_value': '2',
            }),
        }
        for ident, elem in elems.items():
            elem.ident = ident
            elem.parent = elems[elem.t_parent] if elem.t_parent else None
        controllers = [
            mocker.Mock(root='a', elem=None),
            mocker.Mock(root='c', elem='b'),
        ]
        parent = None
        for cont in controllers:
            cont._micropath_parent = parent
            cont._micropath_elem = (
                elems[cont.elem] if cont.elem else None
            )
            root = mocker.Mock(spec=elements.Root)
            root.parent = None
            elems[cont.root].parent = root
            parent = cont
        meth = mocker.Mock(_micropath_elem=elems['d'])
        mock_get_method_self = mocker.patch.object(
            request.six, 'get_method_self',
            return_value=controllers[-1],
        )
        mock_isclass = mocker.patch.object(
            request.inspect, 'isclass',
            return_value=False,
        )
        obj = request.Request.blank(
            '/is/a/test',
            base_url='http://example.com/this',
        )

        result = obj.url_for(meth, b=1, d=2)

        assert result == 'http://example.com/this/a/1/c/2'
        mock_get_method_self.assert_called_once_with(meth)
        mock_isclass.assert_called_once_with(controllers[-1])

    def test_url_for_too_few_arguments(self, mocker):
        elems = {
            'a': mocker.Mock(spec=elements.Path, t_parent=None),
            'b': mocker.Mock(spec=elements.Binding, t_parent='a', **{
                'format.return_value': '1',
            }),
            'c': mocker.Mock(spec=elements.Path, t_parent=None),
            'd': mocker.Mock(spec=elements.Binding, t_parent='c', **{
                'format.return_value': '2',
            }),
        }
        for ident, elem in elems.items():
            elem.ident = ident
            elem.parent = elems[elem.t_parent] if elem.t_parent else None
        controllers = [
            mocker.Mock(root='a', elem=None),
            mocker.Mock(root='c', elem='b'),
        ]
        parent = None
        for cont in controllers:
            cont._micropath_parent = parent
            cont._micropath_elem = (
                elems[cont.elem] if cont.elem else None
            )
            root = mocker.Mock(spec=elements.Root)
            root.parent = None
            elems[cont.root].parent = root
            parent = cont
        mock_get_method_self = mocker.patch.object(
            request.six, 'get_method_self',
            return_value=controllers[-1],
        )
        mock_isclass = mocker.patch.object(
            request.inspect, 'isclass',
            return_value=False,
        )
        obj = request.Request.blank(
            '/is/a/test',
            base_url='http://example.com/this',
        )

        with pytest.raises(TypeError):
            obj.url_for(b=1, d=2)
        mock_get_method_self.assert_not_called()
        mock_isclass.assert_not_called()

    def test_url_for_too_many_arguments(self, mocker):
        elems = {
            'a': mocker.Mock(spec=elements.Path, t_parent=None),
            'b': mocker.Mock(spec=elements.Binding, t_parent='a', **{
                'format.return_value': '1',
            }),
            'c': mocker.Mock(spec=elements.Path, t_parent=None),
            'd': mocker.Mock(spec=elements.Binding, t_parent='c', **{
                'format.return_value': '2',
            }),
        }
        for ident, elem in elems.items():
            elem.ident = ident
            elem.parent = elems[elem.t_parent] if elem.t_parent else None
        controllers = [
            mocker.Mock(root='a', elem=None),
            mocker.Mock(root='c', elem='b'),
        ]
        parent = None
        for cont in controllers:
            cont._micropath_parent = parent
            cont._micropath_elem = (
                elems[cont.elem] if cont.elem else None
            )
            root = mocker.Mock(spec=elements.Root)
            root.parent = None
            elems[cont.root].parent = root
            parent = cont
        meth = mocker.Mock(_micropath_elem=elems['d'])
        mock_get_method_self = mocker.patch.object(
            request.six, 'get_method_self',
            return_value=controllers[-1],
        )
        mock_isclass = mocker.patch.object(
            request.inspect, 'isclass',
            return_value=False,
        )
        obj = request.Request.blank(
            '/is/a/test',
            base_url='http://example.com/this',
        )

        with pytest.raises(TypeError):
            obj.url_for(meth, 'too', 'many', b=1, d=2)
        mock_get_method_self.assert_not_called()
        mock_isclass.assert_not_called()

    def test_url_for_non_callable(self, mocker):
        elems = {
            'a': mocker.Mock(spec=elements.Path, t_parent=None),
            'b': mocker.Mock(spec=elements.Binding, t_parent='a', **{
                'format.return_value': '1',
            }),
            'c': mocker.Mock(spec=elements.Path, t_parent=None),
            'd': mocker.Mock(spec=elements.Binding, t_parent='c', **{
                'format.return_value': '2',
            }),
        }
        for ident, elem in elems.items():
            elem.ident = ident
            elem.parent = elems[elem.t_parent] if elem.t_parent else None
        controllers = [
            mocker.Mock(root='a', elem=None),
            mocker.Mock(root='c', elem='b'),
        ]
        parent = None
        for cont in controllers:
            cont._micropath_parent = parent
            cont._micropath_elem = (
                elems[cont.elem] if cont.elem else None
            )
            root = mocker.Mock(spec=elements.Root)
            root.parent = None
            elems[cont.root].parent = root
            parent = cont
        meth = mocker.NonCallableMock(_micropath_elem=elems['d'])
        mock_get_method_self = mocker.patch.object(
            request.six, 'get_method_self',
            return_value=controllers[-1],
        )
        mock_isclass = mocker.patch.object(
            request.inspect, 'isclass',
            return_value=False,
        )
        obj = request.Request.blank(
            '/is/a/test',
            base_url='http://example.com/this',
        )

        with pytest.raises(ValueError):
            obj.url_for(meth, b=1, d=2)
        mock_get_method_self.assert_not_called()
        mock_isclass.assert_not_called()

    def test_url_for_no_element(self, mocker):
        elems = {
            'a': mocker.Mock(spec=elements.Path, t_parent=None),
            'b': mocker.Mock(spec=elements.Binding, t_parent='a', **{
                'format.return_value': '1',
            }),
            'c': mocker.Mock(spec=elements.Path, t_parent=None),
            'd': mocker.Mock(spec=elements.Binding, t_parent='c', **{
                'format.return_value': '2',
            }),
        }
        for ident, elem in elems.items():
            elem.ident = ident
            elem.parent = elems[elem.t_parent] if elem.t_parent else None
        controllers = [
            mocker.Mock(root='a', elem=None),
            mocker.Mock(root='c', elem='b'),
        ]
        parent = None
        for cont in controllers:
            cont._micropath_parent = parent
            cont._micropath_elem = (
                elems[cont.elem] if cont.elem else None
            )
            root = mocker.Mock(spec=elements.Root)
            root.parent = None
            elems[cont.root].parent = root
            parent = cont
        meth = mocker.Mock(_micropath_elem=None)
        mock_get_method_self = mocker.patch.object(
            request.six, 'get_method_self',
            return_value=controllers[-1],
        )
        mock_isclass = mocker.patch.object(
            request.inspect, 'isclass',
            return_value=False,
        )
        obj = request.Request.blank(
            '/is/a/test',
            base_url='http://example.com/this',
        )

        with pytest.raises(ValueError):
            obj.url_for(meth, b=1, d=2)
        mock_get_method_self.assert_not_called()
        mock_isclass.assert_not_called()

    def test_url_for_class_method(self, mocker):
        elems = {
            'a': mocker.Mock(spec=elements.Path, t_parent=None),
            'b': mocker.Mock(spec=elements.Binding, t_parent='a', **{
                'format.return_value': '1',
            }),
            'c': mocker.Mock(spec=elements.Path, t_parent=None),
            'd': mocker.Mock(spec=elements.Binding, t_parent='c', **{
                'format.return_value': '2',
            }),
        }
        for ident, elem in elems.items():
            elem.ident = ident
            elem.parent = elems[elem.t_parent] if elem.t_parent else None
        controllers = [
            mocker.Mock(root='a', elem=None),
            mocker.Mock(root='c', elem='b'),
        ]
        parent = None
        for cont in controllers:
            cont._micropath_parent = parent
            cont._micropath_elem = (
                elems[cont.elem] if cont.elem else None
            )
            root = mocker.Mock(spec=elements.Root)
            root.parent = None
            elems[cont.root].parent = root
            parent = cont
        meth = mocker.Mock(_micropath_elem=elems['d'])
        mock_get_method_self = mocker.patch.object(
            request.six, 'get_method_self',
            return_value=controllers[-1],
        )
        mock_isclass = mocker.patch.object(
            request.inspect, 'isclass',
            return_value=True,
        )
        obj = request.Request.blank(
            '/is/a/test',
            base_url='http://example.com/this',
        )

        with pytest.raises(ValueError):
            obj.url_for(meth, b=1, d=2)
        mock_get_method_self.assert_called_once_with(meth)
        mock_isclass.assert_called_once_with(controllers[-1])

    def test_url_for_missing_binding(self, mocker):
        elems = {
            'a': mocker.Mock(spec=elements.Path, t_parent=None),
            'b': mocker.Mock(spec=elements.Binding, t_parent='a', **{
                'format.return_value': '1',
            }),
            'c': mocker.Mock(spec=elements.Path, t_parent=None),
            'd': mocker.Mock(spec=elements.Binding, t_parent='c', **{
                'format.return_value': '2',
            }),
        }
        for ident, elem in elems.items():
            elem.ident = ident
            elem.parent = elems[elem.t_parent] if elem.t_parent else None
        controllers = [
            mocker.Mock(root='a', elem=None),
            mocker.Mock(root='c', elem='b'),
        ]
        parent = None
        for cont in controllers:
            cont._micropath_parent = parent
            cont._micropath_elem = (
                elems[cont.elem] if cont.elem else None
            )
            root = mocker.Mock(spec=elements.Root)
            root.parent = None
            elems[cont.root].parent = root
            parent = cont
        meth = mocker.Mock(_micropath_elem=elems['d'])
        mock_get_method_self = mocker.patch.object(
            request.six, 'get_method_self',
            return_value=controllers[-1],
        )
        mock_isclass = mocker.patch.object(
            request.inspect, 'isclass',
            return_value=False,
        )
        obj = request.Request.blank(
            '/is/a/test',
            base_url='http://example.com/this',
        )

        with pytest.raises(ValueError):
            obj.url_for(meth, b=1)
        mock_get_method_self.assert_called_once_with(meth)
        mock_isclass.assert_called_once_with(controllers[-1])

    def test_injector_cached(self, mocker):
        mock_Injector = mocker.patch.object(request.injector, 'Injector')
        obj = request.Request.blank('/')
        obj.environ['micropath.injector'] = 'cached'

        assert obj.injector == 'cached'
        assert obj.environ['micropath.injector'] == 'cached'
        mock_Injector.assert_not_called()

    def test_injector_uncached(self, mocker):
        mock_Injector = mocker.patch.object(request.injector, 'Injector')
        obj = request.Request.blank('/')

        assert obj.injector == mock_Injector.return_value
        assert obj.environ['micropath.injector'] == mock_Injector.return_value
        mock_Injector.assert_called_once_with()

    def test_base_path_get(self):
        obj = request.Request.blank('/')
        obj.environ['micropath.base_path'] = '/base/path'

        assert obj.base_path == '/base/path'
