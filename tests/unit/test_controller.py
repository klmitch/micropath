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

from micropath import controller
from micropath import elements


class TestControllerMeta(object):
    def test_base(self, mocker):
        mock_Root = mocker.patch.object(controller.elements, 'Root')

        result = controller.ControllerMeta(
            'TestController', (controller.Controller,), {},
        )

        assert result._micropath_root == mock_Root.return_value
        assert result._micropath_handlers == {}
        mock_Root.assert_called_once_with()

    def test_alt(self, mocker):
        mock_Root = mocker.patch.object(controller.elements, 'Root')
        namespace = {
            'elem1': mocker.Mock(spec=elements.Path),
            'elem2': mocker.Mock(spec=elements.Binding),
            'func': mocker.Mock(
                _micropath_methods=[
                    mocker.Mock(spec=elements.Method),
                    mocker.Mock(spec=elements.Method),
                ],
                _micropath_handler=False,
            ),
            'handler': mocker.Mock(
                _micropath_methods=[],
                _micropath_handler=True,
            ),
        }

        result = controller.ControllerMeta(
            'TestController', (controller.Controller,), namespace,
        )

        assert result._micropath_root == mock_Root.return_value
        assert result._micropath_handlers == {
            'handler': namespace['handler'],
        }
        mock_Root.assert_called_once_with()
        mock_Root.return_value.add_elem.assert_has_calls([
            mocker.call(namespace['elem1'], 'elem1'),
            mocker.call(namespace['elem2'], 'elem2'),
            mocker.call(namespace['func']._micropath_methods[0], 'func'),
            mocker.call(namespace['func']._micropath_methods[1], 'func'),
        ], any_order=True)
        assert mock_Root.return_value.add_elem.call_count == 4


class TestController(object):
    def test_construct(self):
        obj = controller.Controller()

        with pytest.raises(NotImplementedError):
            obj.construct('other', {})
