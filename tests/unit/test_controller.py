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
import webob.exc

from micropath import controller
from micropath import elements


class ExceptionForTest(Exception):
    pass


class TestControllerMeta(object):
    def test_base(self, mocker):
        mock_Root = mocker.patch.object(controller.elements, 'Root')

        result = controller.ControllerMeta(
            'TestController', (controller.Controller,), {},
        )

        assert result._micropath_root == mock_Root.return_value
        assert result._micropath_delegations == []
        mock_Root.assert_called_once_with()

    def test_alt(self, mocker):
        mock_Root = mocker.patch.object(controller.elements, 'Root')
        namespace = {
            'elem1': mocker.Mock(spec=elements.Path),
            'elem2': mocker.Mock(spec=elements.Binding),
            'deleg1': mocker.Mock(spec=elements.Delegation, element=None),
            'deleg2': mocker.Mock(spec=elements.Delegation, element='elem'),
            'func': mocker.Mock(
                _micropath_methods=[
                    mocker.Mock(spec=elements.Method),
                    mocker.Mock(spec=elements.Method),
                ],
                _micropath_handler=False,
                _micropath_elem=None,
            ),
            'handler1': mocker.Mock(
                _micropath_methods=[],
                _micropath_handler=True,
                _micropath_elem=None,
            ),
            'handler2': mocker.Mock(
                _micropath_methods=[],
                _micropath_handler=True,
                _micropath_elem='elem',
            ),
        }

        result = controller.ControllerMeta(
            'TestController', (controller.Controller,), namespace,
        )

        assert result._micropath_root == mock_Root.return_value
        assert result._micropath_delegations == [
            namespace['deleg1'],
            namespace['deleg2'],
        ]
        assert result.func._micropath_elem is None
        assert result.handler1._micropath_elem == mock_Root.return_value
        assert result.handler2._micropath_elem == 'elem'
        mock_Root.assert_called_once_with()
        mock_Root.return_value.mount.assert_called_once_with(
            namespace['deleg1'],
        )
        mock_Root.return_value.add_elem.assert_has_calls([
            mocker.call(namespace['deleg2'].element, 'deleg2'),
            mocker.call(namespace['elem1'], 'elem1'),
            mocker.call(namespace['elem2'], 'elem2'),
            mocker.call(namespace['func']._micropath_methods[0], 'func'),
            mocker.call(namespace['func']._micropath_methods[1], 'func'),
        ], any_order=True)
        assert mock_Root.return_value.add_elem.call_count == 5


class TestController(object):
    def test_init(self, mocker):
        delegations = [
            mocker.Mock(),
            mocker.Mock(),
            mocker.Mock(),
        ]
        mocker.patch.object(
            controller.Controller, '_micropath_delegations', delegations,
        )

        result = controller.Controller()

        assert isinstance(result, controller.Controller)
        for deleg in delegations:
            deleg.get.assert_called_once_with(result)

    def check_injector(self, obj, req, mocker, mock_exc_info, **kwargs):
        injector = req.injector.cleanup.return_value.__enter__.return_value
        injector.update.assert_called_once_with(kwargs)
        injector.__setitem__.assert_has_calls([
            mocker.call('request', req),
            mocker.call('root_controller', obj),
        ])
        assert injector.__setitem__.call_count == 2

        mock_micropath_request_error = mocker.patch.object(
            obj, 'micropath_request_error',
            return_value=ExceptionForTest(),
        )
        keys = set()
        for pos, _kw in injector.set_deferred.call_args_list:
            # Get the call arguments
            key = pos[0]
            func = pos[1]
            real_key = (
                controller.Controller.micropath_request_attrs[key] or key
            )

            # Check what happens when the function is called
            assert func(req) == getattr(req, real_key)

            # Check what happens if the attribute doesn't exist
            delattr(req, real_key)
            with pytest.raises(ExceptionForTest):
                func(req)
            mock_micropath_request_error.assert_called_once_with(
                req, real_key, mock_exc_info.return_value,
            )
            mock_micropath_request_error.reset_mock()

            # We've tested for this key
            keys.add(pos[0])

        assert keys == set(controller.Controller.micropath_request_attrs)

    def test_call_base(self, mocker):
        req = mocker.MagicMock(charset='utf-8', urlvars={'a': 1})
        inj = req.injector.cleanup.return_value.__enter__.return_value
        mock_Request = mocker.patch.object(
            controller.Controller, 'micropath_request',
            return_value=req,
        )
        mock_micropath_prepare_injector = mocker.patch.object(
            controller.Controller, 'micropath_prepare_injector',
        )
        mock_micropath_dispatch = mocker.patch.object(
            controller.Controller, '_micropath_dispatch',
        )
        base_resp = mock_micropath_dispatch.return_value
        mock_exc_info = mocker.patch.object(
            controller.sys, 'exc_info',
        )
        mock_micropath_server_error = mocker.patch.object(
            controller.Controller, 'micropath_server_error',
        )
        mocker.patch.object(
            controller.traceback, 'format_exc',
            return_value='exception',
        )
        mock_HTTPInternalServerError = mocker.patch.object(
            controller.webob.exc, 'HTTPInternalServerError',
        )
        obj = controller.Controller()

        result = obj('environ', 'start_response')

        assert req.response == req.ResponseClass.return_value
        resp = req.response.merge_cookies.return_value
        assert result == resp.return_value
        mock_Request.assert_called_once_with('environ')
        req.ResponseClass.assert_called_once_with()
        req.injector.cleanup.assert_called_once_with()
        mock_micropath_prepare_injector.assert_called_once_with(req, inj)
        mock_micropath_dispatch.assert_called_once_with(req, inj)
        mock_exc_info.assert_not_called()
        mock_micropath_server_error.assert_not_called()
        mock_HTTPInternalServerError.assert_not_called()
        req.response.write.assert_not_called()
        req.response.merge_cookies.assert_called_once_with(base_resp)
        resp.assert_called_once_with('environ', 'start_response')
        self.check_injector(obj, req, mocker, mock_exc_info, a=1)

    def test_call_return_none(self, mocker):
        req = mocker.MagicMock(charset='utf-8', urlvars={'a': 1})
        inj = req.injector.cleanup.return_value.__enter__.return_value
        mock_Request = mocker.patch.object(
            controller.Controller, 'micropath_request',
            return_value=req,
        )
        mock_micropath_prepare_injector = mocker.patch.object(
            controller.Controller, 'micropath_prepare_injector',
        )
        mock_micropath_dispatch = mocker.patch.object(
            controller.Controller, '_micropath_dispatch',
            return_value=None,
        )
        mock_exc_info = mocker.patch.object(
            controller.sys, 'exc_info',
        )
        mock_micropath_server_error = mocker.patch.object(
            controller.Controller, 'micropath_server_error',
        )
        mocker.patch.object(
            controller.traceback, 'format_exc',
            return_value='exception',
        )
        mock_HTTPInternalServerError = mocker.patch.object(
            controller.webob.exc, 'HTTPInternalServerError',
        )
        obj = controller.Controller()

        result = obj('environ', 'start_response')

        assert req.response == req.ResponseClass.return_value
        resp = req.response
        assert result == resp.return_value
        mock_Request.assert_called_once_with('environ')
        req.ResponseClass.assert_called_once_with()
        req.injector.cleanup.assert_called_once_with()
        mock_micropath_prepare_injector.assert_called_once_with(req, inj)
        mock_micropath_dispatch.assert_called_once_with(req, inj)
        mock_exc_info.assert_not_called()
        mock_micropath_server_error.assert_not_called()
        mock_HTTPInternalServerError.assert_not_called()
        req.response.write.assert_not_called()
        req.response.merge_cookies.assert_not_called()
        resp.assert_called_once_with('environ', 'start_response')
        self.check_injector(obj, req, mocker, mock_exc_info, a=1)

    def test_call_return_text(self, mocker):
        req = mocker.MagicMock(charset='utf-8', urlvars={'a': 1})
        inj = req.injector.cleanup.return_value.__enter__.return_value
        mock_Request = mocker.patch.object(
            controller.Controller, 'micropath_request',
            return_value=req,
        )
        mock_micropath_prepare_injector = mocker.patch.object(
            controller.Controller, 'micropath_prepare_injector',
        )
        mock_micropath_dispatch = mocker.patch.object(
            controller.Controller, '_micropath_dispatch',
            return_value=u'this\u2026is a test',
        )
        mock_exc_info = mocker.patch.object(
            controller.sys, 'exc_info',
        )
        mock_micropath_server_error = mocker.patch.object(
            controller.Controller, 'micropath_server_error',
        )
        mocker.patch.object(
            controller.traceback, 'format_exc',
            return_value='exception',
        )
        mock_HTTPInternalServerError = mocker.patch.object(
            controller.webob.exc, 'HTTPInternalServerError',
        )
        obj = controller.Controller()

        result = obj('environ', 'start_response')

        assert req.response == req.ResponseClass.return_value
        resp = req.response
        assert result == resp.return_value
        mock_Request.assert_called_once_with('environ')
        req.ResponseClass.assert_called_once_with()
        req.injector.cleanup.assert_called_once_with()
        mock_micropath_prepare_injector.assert_called_once_with(req, inj)
        mock_micropath_dispatch.assert_called_once_with(req, inj)
        mock_exc_info.assert_not_called()
        mock_micropath_server_error.assert_not_called()
        mock_HTTPInternalServerError.assert_not_called()
        req.response.write.assert_called_once_with(
            b'this\xe2\x80\xa6is a test',
        )
        req.response.merge_cookies.assert_not_called()
        resp.assert_called_once_with('environ', 'start_response')
        self.check_injector(obj, req, mocker, mock_exc_info, a=1)

    def test_call_return_bytes(self, mocker):
        req = mocker.MagicMock(charset='utf-8', urlvars={'a': 1})
        inj = req.injector.cleanup.return_value.__enter__.return_value
        mock_Request = mocker.patch.object(
            controller.Controller, 'micropath_request',
            return_value=req,
        )
        mock_micropath_prepare_injector = mocker.patch.object(
            controller.Controller, 'micropath_prepare_injector',
        )
        mock_micropath_dispatch = mocker.patch.object(
            controller.Controller, '_micropath_dispatch',
            return_value=b'this\xe2\x80\xa6is a test',
        )
        mock_exc_info = mocker.patch.object(
            controller.sys, 'exc_info',
        )
        mock_micropath_server_error = mocker.patch.object(
            controller.Controller, 'micropath_server_error',
        )
        mocker.patch.object(
            controller.traceback, 'format_exc',
            return_value='exception',
        )
        mock_HTTPInternalServerError = mocker.patch.object(
            controller.webob.exc, 'HTTPInternalServerError',
        )
        obj = controller.Controller()

        result = obj('environ', 'start_response')

        assert req.response == req.ResponseClass.return_value
        resp = req.response
        assert result == resp.return_value
        mock_Request.assert_called_once_with('environ')
        req.ResponseClass.assert_called_once_with()
        req.injector.cleanup.assert_called_once_with()
        mock_micropath_prepare_injector.assert_called_once_with(req, inj)
        mock_micropath_dispatch.assert_called_once_with(req, inj)
        mock_exc_info.assert_not_called()
        mock_micropath_server_error.assert_not_called()
        mock_HTTPInternalServerError.assert_not_called()
        req.response.write.assert_called_once_with(
            b'this\xe2\x80\xa6is a test',
        )
        req.response.merge_cookies.assert_not_called()
        resp.assert_called_once_with('environ', 'start_response')
        self.check_injector(obj, req, mocker, mock_exc_info, a=1)

    def test_call_http_exception(self, mocker):
        req = mocker.MagicMock(charset='utf-8', urlvars={'a': 1})
        inj = req.injector.cleanup.return_value.__enter__.return_value
        mock_Request = mocker.patch.object(
            controller.Controller, 'micropath_request',
            return_value=req,
        )
        mock_micropath_prepare_injector = mocker.patch.object(
            controller.Controller, 'micropath_prepare_injector',
        )
        exc = webob.exc.HTTPException('test', 'wsgi_response')
        mock_micropath_dispatch = mocker.patch.object(
            controller.Controller, '_micropath_dispatch',
            side_effect=exc,
        )
        mock_exc_info = mocker.patch.object(
            controller.sys, 'exc_info',
        )
        mock_micropath_server_error = mocker.patch.object(
            controller.Controller, 'micropath_server_error',
        )
        mocker.patch.object(
            controller.traceback, 'format_exc',
            return_value='exception',
        )
        mock_HTTPInternalServerError = mocker.patch.object(
            controller.webob.exc, 'HTTPInternalServerError',
        )
        obj = controller.Controller()

        result = obj('environ', 'start_response')

        assert req.response == req.ResponseClass.return_value
        resp = req.response.merge_cookies.return_value
        assert result == resp.return_value
        mock_Request.assert_called_once_with('environ')
        req.ResponseClass.assert_called_once_with()
        req.injector.cleanup.assert_called_once_with()
        mock_micropath_prepare_injector.assert_called_once_with(req, inj)
        mock_micropath_dispatch.assert_called_once_with(req, inj)
        mock_exc_info.assert_not_called()
        mock_micropath_server_error.assert_not_called()
        mock_HTTPInternalServerError.assert_not_called()
        req.response.write.assert_not_called()
        req.response.merge_cookies.assert_called_once_with(exc)
        resp.assert_called_once_with('environ', 'start_response')
        self.check_injector(obj, req, mocker, mock_exc_info, a=1)

    def test_call_exceptionfortest(self, mocker):
        req = mocker.MagicMock(charset='utf-8', urlvars={'a': 1})
        inj = req.injector.cleanup.return_value.__enter__.return_value
        mock_Request = mocker.patch.object(
            controller.Controller, 'micropath_request',
            return_value=req,
        )
        mock_micropath_prepare_injector = mocker.patch.object(
            controller.Controller, 'micropath_prepare_injector',
        )
        mock_micropath_dispatch = mocker.patch.object(
            controller.Controller, '_micropath_dispatch',
            side_effect=ExceptionForTest('test'),
        )
        mock_exc_info = mocker.patch.object(
            controller.sys, 'exc_info',
        )
        mock_micropath_server_error = mocker.patch.object(
            controller.Controller, 'micropath_server_error',
        )
        mocker.patch.object(
            controller.traceback, 'format_exc',
            return_value='exception',
        )
        mock_HTTPInternalServerError = mocker.patch.object(
            controller.webob.exc, 'HTTPInternalServerError',
        )
        obj = controller.Controller()

        result = obj('environ', 'start_response')

        assert req.response == req.ResponseClass.return_value
        resp = req.response.merge_cookies.return_value
        assert result == resp.return_value
        mock_Request.assert_called_once_with('environ')
        req.ResponseClass.assert_called_once_with()
        req.injector.cleanup.assert_called_once_with()
        mock_micropath_prepare_injector.assert_called_once_with(req, inj)
        mock_micropath_dispatch.assert_called_once_with(req, inj)
        mock_exc_info.assert_called_once_with()
        mock_micropath_server_error.assert_called_once_with(
            req, mock_exc_info.return_value,
        )
        base_resp = mock_micropath_server_error.return_value
        mock_HTTPInternalServerError.assert_not_called()
        req.response.write.assert_not_called()
        req.response.merge_cookies.assert_called_once_with(base_resp)
        resp.assert_called_once_with('environ', 'start_response')
        self.check_injector(obj, req, mocker, mock_exc_info, a=1)

    def test_call_last_resort_exception(self, mocker):
        req = mocker.MagicMock(charset='utf-8', urlvars={'a': 1})
        inj = req.injector.cleanup.return_value.__enter__.return_value
        mock_Request = mocker.patch.object(
            controller.Controller, 'micropath_request',
            return_value=req,
        )
        mock_micropath_prepare_injector = mocker.patch.object(
            controller.Controller, 'micropath_prepare_injector',
        )
        mock_micropath_dispatch = mocker.patch.object(
            controller.Controller, '_micropath_dispatch',
            side_effect=ExceptionForTest('test'),
        )
        mock_exc_info = mocker.patch.object(
            controller.sys, 'exc_info',
        )
        mock_micropath_server_error = mocker.patch.object(
            controller.Controller, 'micropath_server_error',
            side_effect=ExceptionForTest('test'),
        )
        mocker.patch.object(
            controller.traceback, 'format_exc',
            return_value='exception',
        )
        mock_HTTPInternalServerError = mocker.patch.object(
            controller.webob.exc, 'HTTPInternalServerError',
        )
        obj = controller.Controller()

        result = obj('environ', 'start_response')

        assert req.response == req.ResponseClass.return_value
        resp = req.response.merge_cookies.return_value
        assert result == resp.return_value
        mock_Request.assert_called_once_with('environ')
        req.ResponseClass.assert_called_once_with()
        req.injector.cleanup.assert_called_once_with()
        mock_micropath_prepare_injector.assert_called_once_with(req, inj)
        mock_micropath_dispatch.assert_called_once_with(req, inj)
        mock_exc_info.assert_called_once_with()
        mock_micropath_server_error.assert_called_once_with(
            req, mock_exc_info.return_value,
        )
        mock_HTTPInternalServerError.assert_called_once_with(None)
        base_resp = mock_HTTPInternalServerError.return_value
        req.response.write.assert_not_called()
        req.response.merge_cookies.assert_called_once_with(base_resp)
        resp.assert_called_once_with('environ', 'start_response')
        self.check_injector(obj, req, mocker, mock_exc_info, a=1)

    def test_call_last_resort_exception_debug(self, mocker):
        req = mocker.MagicMock(charset='utf-8', urlvars={'a': 1})
        inj = req.injector.cleanup.return_value.__enter__.return_value
        mock_Request = mocker.patch.object(
            controller.Controller, 'micropath_request',
            return_value=req,
        )
        mock_micropath_prepare_injector = mocker.patch.object(
            controller.Controller, 'micropath_prepare_injector',
        )
        exc = ExceptionForTest('test')
        mock_micropath_dispatch = mocker.patch.object(
            controller.Controller, '_micropath_dispatch',
            side_effect=exc,
        )
        mock_exc_info = mocker.patch.object(
            controller.sys, 'exc_info',
        )
        mock_micropath_server_error = mocker.patch.object(
            controller.Controller, 'micropath_server_error',
            side_effect=exc,
        )
        mocker.patch.object(
            controller.traceback, 'format_exc',
            return_value='exception',
        )
        mock_HTTPInternalServerError = mocker.patch.object(
            controller.webob.exc, 'HTTPInternalServerError',
        )
        obj = controller.Controller()
        obj.micropath_debug = True

        result = obj('environ', 'start_response')

        assert req.response == req.ResponseClass.return_value
        resp = req.response.merge_cookies.return_value
        assert result == resp.return_value
        mock_Request.assert_called_once_with('environ')
        req.ResponseClass.assert_called_once_with()
        req.injector.cleanup.assert_called_once_with()
        mock_micropath_prepare_injector.assert_called_once_with(req, inj)
        mock_micropath_dispatch.assert_called_once_with(req, inj)
        mock_exc_info.assert_called_once_with()
        mock_micropath_server_error.assert_called_once_with(
            req, mock_exc_info.return_value,
        )
        mock_HTTPInternalServerError.assert_called_once_with('exception')
        base_resp = mock_HTTPInternalServerError.return_value
        req.response.write.assert_not_called()
        req.response.merge_cookies.assert_called_once_with(base_resp)
        resp.assert_called_once_with('environ', 'start_response')
        self.check_injector(obj, req, mocker, mock_exc_info, a=1)

    def test_micropath_dispatch_call_func(self, mocker):
        mock_wants = mocker.patch.object(
            controller.injector, 'wants',
            return_value=False,
        )
        mock_micropath_not_found = mocker.patch.object(
            controller.Controller, 'micropath_not_found',
        )
        mock_micropath_not_implemented = mocker.patch.object(
            controller.Controller, 'micropath_not_implemented',
        )
        mock_micropath_options = mocker.patch.object(
            controller.Controller, 'micropath_options',
        )
        elem = mocker.Mock(methods={})
        mock_micropath_resolve = mocker.patch.object(
            controller.Controller, '_micropath_resolve',
            return_value=(elem, False),
        )
        mock_micropath_delegation = mocker.patch.object(
            controller.Controller, '_micropath_delegation',
            return_value=('func', None),
        )
        mock_micropath_methods = mocker.patch.object(
            controller.Controller, '_micropath_methods',
            return_value=set(['HEAD', 'GET', 'POST']),
        )
        req = mocker.Mock(
            path_info='path_info',
            method='GET',
        )
        inj = mocker.Mock()
        obj = controller.Controller()

        result = obj._micropath_dispatch(req, inj)

        assert result == inj.return_value
        mock_wants.assert_not_called()
        mock_micropath_not_found.assert_not_called()
        mock_micropath_not_implemented.assert_not_called()
        mock_micropath_options.assert_not_called()
        mock_micropath_resolve.assert_called_once_with(req, inj)
        mock_micropath_delegation.assert_called_once_with(req, elem)
        mock_micropath_methods.assert_not_called()
        inj.assert_called_once_with('func', obj)

    def test_micropath_dispatch_call_func_wants_path_info(self, mocker):
        mock_wants = mocker.patch.object(
            controller.injector, 'wants',
            return_value=True,
        )
        mock_micropath_not_found = mocker.patch.object(
            controller.Controller, 'micropath_not_found',
        )
        mock_micropath_not_implemented = mocker.patch.object(
            controller.Controller, 'micropath_not_implemented',
        )
        mock_micropath_options = mocker.patch.object(
            controller.Controller, 'micropath_options',
        )
        elem = mocker.Mock(methods={})
        mock_micropath_resolve = mocker.patch.object(
            controller.Controller, '_micropath_resolve',
            return_value=(elem, True),
        )
        mock_micropath_delegation = mocker.patch.object(
            controller.Controller, '_micropath_delegation',
            return_value=('func', None),
        )
        mock_micropath_methods = mocker.patch.object(
            controller.Controller, '_micropath_methods',
            return_value=set(['HEAD', 'GET', 'POST']),
        )
        req = mocker.Mock(
            path_info='path_info',
            method='GET',
        )
        inj = mocker.Mock()
        obj = controller.Controller()

        result = obj._micropath_dispatch(req, inj)

        assert result == inj.return_value
        mock_wants.assert_called_once_with('func', 'path_info')
        mock_micropath_not_found.assert_not_called()
        mock_micropath_not_implemented.assert_not_called()
        mock_micropath_options.assert_not_called()
        mock_micropath_resolve.assert_called_once_with(req, inj)
        mock_micropath_delegation.assert_called_once_with(req, elem)
        mock_micropath_methods.assert_not_called()
        inj.assert_called_once_with('func', obj)

    def test_micropath_dispatch_call_func_doesnt_want_path_info(self, mocker):
        mock_wants = mocker.patch.object(
            controller.injector, 'wants',
            return_value=False,
        )
        mock_micropath_not_found = mocker.patch.object(
            controller.Controller, 'micropath_not_found',
        )
        mock_micropath_not_implemented = mocker.patch.object(
            controller.Controller, 'micropath_not_implemented',
        )
        mock_micropath_options = mocker.patch.object(
            controller.Controller, 'micropath_options',
        )
        elem = mocker.Mock(methods={})
        mock_micropath_resolve = mocker.patch.object(
            controller.Controller, '_micropath_resolve',
            return_value=(elem, True),
        )
        mock_micropath_delegation = mocker.patch.object(
            controller.Controller, '_micropath_delegation',
            return_value=('func', None),
        )
        mock_micropath_methods = mocker.patch.object(
            controller.Controller, '_micropath_methods',
            return_value=set(['HEAD', 'GET', 'POST']),
        )
        req = mocker.Mock(
            path_info='path_info',
            method='GET',
        )
        inj = mocker.Mock()
        obj = controller.Controller()

        result = obj._micropath_dispatch(req, inj)

        assert result == mock_micropath_not_found.return_value
        mock_wants.assert_called_once_with('func', 'path_info')
        mock_micropath_not_found.assert_called_once_with(req, 'path_info')
        mock_micropath_not_implemented.assert_not_called()
        mock_micropath_options.assert_not_called()
        mock_micropath_resolve.assert_called_once_with(req, inj)
        mock_micropath_delegation.assert_called_once_with(req, elem)
        mock_micropath_methods.assert_not_called()
        inj.assert_not_called()

    def test_micropath_dispatch_call_delegation(self, mocker):
        mock_wants = mocker.patch.object(
            controller.injector, 'wants',
            return_value=False,
        )
        mock_micropath_not_found = mocker.patch.object(
            controller.Controller, 'micropath_not_found',
        )
        mock_micropath_not_implemented = mocker.patch.object(
            controller.Controller, 'micropath_not_implemented',
        )
        mock_micropath_options = mocker.patch.object(
            controller.Controller, 'micropath_options',
        )
        elem = mocker.Mock(methods={})
        mock_micropath_resolve = mocker.patch.object(
            controller.Controller, '_micropath_resolve',
            return_value=(elem, False),
        )
        delegation = mocker.Mock()
        delegation_obj = delegation.get.return_value
        mock_micropath_delegation = mocker.patch.object(
            controller.Controller, '_micropath_delegation',
            return_value=(None, delegation),
        )
        mock_micropath_methods = mocker.patch.object(
            controller.Controller, '_micropath_methods',
            return_value=set(['HEAD', 'GET', 'POST']),
        )
        req = mocker.Mock(
            path_info='path_info',
            method='GET',
        )
        inj = mocker.Mock()
        obj = controller.Controller()

        result = obj._micropath_dispatch(req, inj)

        assert result == delegation_obj._micropath_dispatch.return_value
        mock_wants.assert_not_called()
        mock_micropath_not_found.assert_not_called()
        mock_micropath_not_implemented.assert_not_called()
        mock_micropath_options.assert_not_called()
        mock_micropath_resolve.assert_called_once_with(req, inj)
        mock_micropath_delegation.assert_called_once_with(req, elem)
        mock_micropath_methods.assert_not_called()
        delegation.get.assert_called_once_with(obj)
        delegation_obj._micropath_dispatch.assert_called_once_with(req, inj)
        inj.assert_not_called()

    def test_micropath_dispatch_default_options(self, mocker):
        mock_wants = mocker.patch.object(
            controller.injector, 'wants',
            return_value=False,
        )
        mock_micropath_not_found = mocker.patch.object(
            controller.Controller, 'micropath_not_found',
        )
        mock_micropath_not_implemented = mocker.patch.object(
            controller.Controller, 'micropath_not_implemented',
        )
        mock_micropath_options = mocker.patch.object(
            controller.Controller, 'micropath_options',
        )
        elem = mocker.Mock(methods={'GET': 'getter'})
        mock_micropath_resolve = mocker.patch.object(
            controller.Controller, '_micropath_resolve',
            return_value=(elem, False),
        )
        mock_micropath_delegation = mocker.patch.object(
            controller.Controller, '_micropath_delegation',
            return_value=(None, None),
        )
        mock_micropath_methods = mocker.patch.object(
            controller.Controller, '_micropath_methods',
            return_value=set(['HEAD', 'GET', 'POST']),
        )
        req = mocker.Mock(
            path_info='path_info',
            method='OPTIONS',
        )
        inj = mocker.Mock()
        obj = controller.Controller()

        result = obj._micropath_dispatch(req, inj)

        assert result == mock_micropath_options.return_value
        mock_wants.assert_not_called()
        mock_micropath_not_found.assert_not_called()
        mock_micropath_not_implemented.assert_not_called()
        mock_micropath_options.assert_called_once_with(
            req, ['GET', 'HEAD', 'POST'],
        )
        mock_micropath_resolve.assert_called_once_with(req, inj)
        mock_micropath_delegation.assert_called_once_with(req, elem)
        mock_micropath_methods.assert_called_once_with(elem)
        inj.assert_not_called()

    def test_micropath_dispatch_default_options_no_methods(self, mocker):
        mock_wants = mocker.patch.object(
            controller.injector, 'wants',
            return_value=False,
        )
        mock_micropath_not_found = mocker.patch.object(
            controller.Controller, 'micropath_not_found',
        )
        mock_micropath_not_implemented = mocker.patch.object(
            controller.Controller, 'micropath_not_implemented',
        )
        mock_micropath_options = mocker.patch.object(
            controller.Controller, 'micropath_options',
        )
        elem = mocker.Mock(methods={})
        mock_micropath_resolve = mocker.patch.object(
            controller.Controller, '_micropath_resolve',
            return_value=(elem, False),
        )
        mock_micropath_delegation = mocker.patch.object(
            controller.Controller, '_micropath_delegation',
            return_value=(None, None),
        )
        mock_micropath_methods = mocker.patch.object(
            controller.Controller, '_micropath_methods',
            return_value=set(['HEAD', 'GET', 'POST']),
        )
        req = mocker.Mock(
            path_info='path_info',
            method='OPTIONS',
        )
        inj = mocker.Mock()
        obj = controller.Controller()

        result = obj._micropath_dispatch(req, inj)

        assert result == mock_micropath_not_found.return_value
        mock_wants.assert_not_called()
        mock_micropath_not_found.assert_called_once_with(req, 'path_info')
        mock_micropath_not_implemented.assert_not_called()
        mock_micropath_options.assert_not_called()
        mock_micropath_resolve.assert_called_once_with(req, inj)
        mock_micropath_delegation.assert_called_once_with(req, elem)
        mock_micropath_methods.assert_not_called()
        inj.assert_not_called()

    def test_micropath_dispatch_not_implemented(self, mocker):
        mock_wants = mocker.patch.object(
            controller.injector, 'wants',
            return_value=False,
        )
        mock_micropath_not_found = mocker.patch.object(
            controller.Controller, 'micropath_not_found',
        )
        mock_micropath_not_implemented = mocker.patch.object(
            controller.Controller, 'micropath_not_implemented',
        )
        mock_micropath_options = mocker.patch.object(
            controller.Controller, 'micropath_options',
        )
        elem = mocker.Mock(methods={'GET': 'getter'})
        mock_micropath_resolve = mocker.patch.object(
            controller.Controller, '_micropath_resolve',
            return_value=(elem, False),
        )
        mock_micropath_delegation = mocker.patch.object(
            controller.Controller, '_micropath_delegation',
            return_value=(None, None),
        )
        mock_micropath_methods = mocker.patch.object(
            controller.Controller, '_micropath_methods',
            return_value=set(['HEAD', 'GET', 'POST']),
        )
        req = mocker.Mock(
            path_info='path_info',
            method='GET',
        )
        inj = mocker.Mock()
        obj = controller.Controller()

        result = obj._micropath_dispatch(req, inj)

        assert result == mock_micropath_not_implemented.return_value
        mock_wants.assert_not_called()
        mock_micropath_not_found.assert_not_called()
        mock_micropath_not_implemented.assert_called_once_with(req, 'GET')
        mock_micropath_options.assert_not_called()
        mock_micropath_resolve.assert_called_once_with(req, inj)
        mock_micropath_delegation.assert_called_once_with(req, elem)
        mock_micropath_methods.assert_not_called()
        inj.assert_not_called()

    def test_micropath_dispatch_no_methods(self, mocker):
        mock_wants = mocker.patch.object(
            controller.injector, 'wants',
            return_value=False,
        )
        mock_micropath_not_found = mocker.patch.object(
            controller.Controller, 'micropath_not_found',
        )
        mock_micropath_not_implemented = mocker.patch.object(
            controller.Controller, 'micropath_not_implemented',
        )
        mock_micropath_options = mocker.patch.object(
            controller.Controller, 'micropath_options',
        )
        elem = mocker.Mock(methods={})
        mock_micropath_resolve = mocker.patch.object(
            controller.Controller, '_micropath_resolve',
            return_value=(elem, False),
        )
        mock_micropath_delegation = mocker.patch.object(
            controller.Controller, '_micropath_delegation',
            return_value=(None, None),
        )
        mock_micropath_methods = mocker.patch.object(
            controller.Controller, '_micropath_methods',
            return_value=set(['HEAD', 'GET', 'POST']),
        )
        req = mocker.Mock(
            path_info='path_info',
            method='GET',
        )
        inj = mocker.Mock()
        obj = controller.Controller()

        result = obj._micropath_dispatch(req, inj)

        assert result == mock_micropath_not_found.return_value
        mock_wants.assert_not_called()
        mock_micropath_not_found.assert_called_once_with(req, 'path_info')
        mock_micropath_not_implemented.assert_not_called()
        mock_micropath_options.assert_not_called()
        mock_micropath_resolve.assert_called_once_with(req, inj)
        mock_micropath_delegation.assert_called_once_with(req, elem)
        mock_micropath_methods.assert_not_called()
        inj.assert_not_called()

    def test_micropath_resolve_base(self, mocker):
        elems = {
            None: mocker.Mock(t_paths=['a'], t_bindings=None, skip=False),
            'a': mocker.Mock(t_paths=[], t_bindings='b', skip=False),
            'b': mocker.Mock(t_paths=['c'], t_bindings=None, skip=False),
            'c': mocker.Mock(t_paths=[], t_bindings='d', skip=False),
            'd': mocker.Mock(t_paths=[], t_bindings=None, skip=False),
        }
        for name, elem in elems.items():
            elem.ident = name
            if elem.skip:
                elem.validate.side_effect = elements.SkipBinding()
            elem.paths = {x: elems[x] for x in elem.t_paths}
            elem.bindings = (
                None if elem.t_bindings is None else elems[elem.t_bindings]
            )
        mocker.patch.object(
            controller.Controller, '_micropath_root', elems[None],
        )
        req = mocker.Mock(**{
            'path_info_peek.side_effect': ['a', '1', 'c', '2', ''],
            'urlvars': {},
        })
        inj = {}
        obj = controller.Controller()

        result = obj._micropath_resolve(req, inj)

        assert result == (elems['d'], False)
        url_vars = {
            'b': elems['b'].validate.return_value,
            'd': elems['d'].validate.return_value,
        }
        assert inj == url_vars
        assert req.urlvars == url_vars
        elems['b'].validate.assert_called_once_with(obj, inj, '1')
        elems['d'].validate.assert_called_once_with(obj, inj, '2')

    def test_micropath_resolve_injector_conflict(self, mocker):
        elems = {
            None: mocker.Mock(t_paths=['a'], t_bindings=None, skip=False),
            'a': mocker.Mock(t_paths=[], t_bindings='b', skip=False),
            'b': mocker.Mock(t_paths=['c'], t_bindings=None, skip=False),
            'c': mocker.Mock(t_paths=[], t_bindings='d', skip=False),
            'd': mocker.Mock(t_paths=[], t_bindings=None, skip=False),
        }
        for name, elem in elems.items():
            elem.ident = name
            if elem.skip:
                elem.validate.side_effect = elements.SkipBinding()
            elem.paths = {x: elems[x] for x in elem.t_paths}
            elem.bindings = (
                None if elem.t_bindings is None else elems[elem.t_bindings]
            )
        mocker.patch.object(
            controller.Controller, '_micropath_root', elems[None],
        )
        req = mocker.Mock(**{
            'path_info_peek.side_effect': ['a', '1', 'c', '2', ''],
            'urlvars': {},
        })
        inj = {'d': 'x'}
        obj = controller.Controller()

        result = obj._micropath_resolve(req, inj)

        assert result == (elems['d'], False)
        assert inj == {
            'b': elems['b'].validate.return_value,
            'd': 'x',
        }
        assert req.urlvars == {
            'b': elems['b'].validate.return_value,
            'd': elems['d'].validate.return_value,
        }
        elems['b'].validate.assert_called_once_with(obj, inj, '1')
        elems['d'].validate.assert_called_once_with(obj, inj, '2')

    def test_micropath_resolve_skip_last(self, mocker):
        elems = {
            None: mocker.Mock(t_paths=['a'], t_bindings=None, skip=False),
            'a': mocker.Mock(t_paths=[], t_bindings='b', skip=False),
            'b': mocker.Mock(t_paths=['c'], t_bindings=None, skip=False),
            'c': mocker.Mock(t_paths=[], t_bindings='d', skip=False),
            'd': mocker.Mock(t_paths=[], t_bindings=None, skip=True),
        }
        for name, elem in elems.items():
            elem.ident = name
            if elem.skip:
                elem.validate.side_effect = elements.SkipBinding()
            elem.paths = {x: elems[x] for x in elem.t_paths}
            elem.bindings = (
                None if elem.t_bindings is None else elems[elem.t_bindings]
            )
        mocker.patch.object(
            controller.Controller, '_micropath_root', elems[None],
        )
        req = mocker.Mock(**{
            'path_info_peek.side_effect': ['a', '1', 'c', '2', ''],
            'urlvars': {},
        })
        inj = {}
        obj = controller.Controller()

        result = obj._micropath_resolve(req, inj)

        assert result == (elems['c'], True)
        url_vars = {
            'b': elems['b'].validate.return_value,
        }
        assert inj == url_vars
        assert req.urlvars == url_vars
        elems['b'].validate.assert_called_once_with(obj, inj, '1')
        elems['d'].validate.assert_called_once_with(obj, inj, '2')

    def test_micropath_resolve_unmatched(self, mocker):
        elems = {
            None: mocker.Mock(t_paths=['a'], t_bindings=None, skip=False),
            'a': mocker.Mock(t_paths=[], t_bindings='b', skip=False),
            'b': mocker.Mock(t_paths=['c'], t_bindings=None, skip=False),
            'c': mocker.Mock(t_paths=[], t_bindings=None, skip=False),
        }
        for name, elem in elems.items():
            elem.ident = name
            if elem.skip:
                elem.validate.side_effect = elements.SkipBinding()
            elem.paths = {x: elems[x] for x in elem.t_paths}
            elem.bindings = (
                None if elem.t_bindings is None else elems[elem.t_bindings]
            )
        mocker.patch.object(
            controller.Controller, '_micropath_root', elems[None],
        )
        req = mocker.Mock(**{
            'path_info_peek.side_effect': ['a', '1', 'c', '2', ''],
            'urlvars': {},
        })
        inj = {}
        obj = controller.Controller()

        result = obj._micropath_resolve(req, inj)

        assert result == (elems['c'], True)
        url_vars = {
            'b': elems['b'].validate.return_value,
        }
        assert inj == url_vars
        assert req.urlvars == url_vars
        elems['b'].validate.assert_called_once_with(obj, inj, '1')

    def test_micropath_delegation_base(self, mocker):
        req = mocker.Mock(method='GET')
        meth = mocker.Mock()
        elem = mocker.Mock(methods={'GET': meth})
        obj = controller.Controller()

        result = obj._micropath_delegation(req, elem)

        assert result == (meth.func, meth.delegation)

    def test_micropath_delegation_elem_delegation(self, mocker):
        req = mocker.Mock(method='GET')
        meth = mocker.Mock(delegation=None)
        elem = mocker.Mock(methods={'GET': meth})
        obj = controller.Controller()

        result = obj._micropath_delegation(req, elem)

        assert result == (meth.func, elem.delegation)

    def test_micropath_delegation_head(self, mocker):
        req = mocker.Mock(method='HEAD')
        meth = mocker.Mock()
        elem = mocker.Mock(methods={'GET': meth})
        obj = controller.Controller()

        result = obj._micropath_delegation(req, elem)

        assert result == (meth.func, meth.delegation)

    def test_micropath_delegation_none(self, mocker):
        req = mocker.Mock(method='GET')
        meth = mocker.Mock()
        elem = mocker.Mock(methods={None: meth})
        obj = controller.Controller()

        result = obj._micropath_delegation(req, elem)

        assert result == (meth.func, meth.delegation)

    def test_micropath_delegation_no_method(self, mocker):
        req = mocker.Mock(method='GET')
        elem = mocker.Mock(methods={})
        obj = controller.Controller()

        result = obj._micropath_delegation(req, elem)

        assert result == (None, elem.delegation)

    def test_micropath_methods_base(self, mocker):
        elem = mocker.Mock(methods={'POST': 'poster'})
        obj = controller.Controller()

        result = obj._micropath_methods(elem)

        assert result == set(['POST', 'OPTIONS'])

    def test_micropath_methods_with_get(self, mocker):
        elem = mocker.Mock(methods={'POST': 'poster', 'GET': 'getter'})
        obj = controller.Controller()

        result = obj._micropath_methods(elem)

        assert result == set(['POST', 'OPTIONS', 'GET', 'HEAD'])

    def test_micropath_methods_all(self, mocker):
        elem = mocker.Mock(methods={None: 'method'})
        obj = controller.Controller()

        result = obj._micropath_methods(elem)

        assert result == controller.Controller.micropath_methods

    def test_micropath_methods_all_extra(self, mocker):
        elem = mocker.Mock(methods={None: 'method', 'PATCH': 'patcher'})
        obj = controller.Controller()

        result = obj._micropath_methods(elem)

        assert result == (
            controller.Controller.micropath_methods | set(['PATCH'])
        )

    def test_micropath_construct(self, mocker):
        other = mocker.Mock()
        obj = controller.Controller()

        result = obj.micropath_construct(other, {'a': 1, 'b': 2, 'c': 3})

        assert result == other.return_value
        other.assert_called_once_with(a=1, b=2, c=3)

    def test_micropath_server_error_base(self, mocker):
        mock_format_exception = mocker.patch.object(
            controller.traceback, 'format_exception',
            return_value=['line1\n', 'line2\n', 'line3\n'],
        )
        mock_HTTPInternalServerError = mocker.patch.object(
            controller.webob.exc, 'HTTPInternalServerError',
        )
        obj = controller.Controller()

        result = obj.micropath_server_error('req', ('type', 'value', 'tb'))

        assert result == mock_HTTPInternalServerError.return_value
        mock_format_exception.assert_not_called()
        mock_HTTPInternalServerError.assert_called_once_with(None)

    def test_micropath_server_error_debug(self, mocker):
        mock_format_exception = mocker.patch.object(
            controller.traceback, 'format_exception',
            return_value=['line1\n', 'line2\n', 'line3\n'],
        )
        mock_HTTPInternalServerError = mocker.patch.object(
            controller.webob.exc, 'HTTPInternalServerError',
        )
        obj = controller.Controller()
        obj.micropath_debug = True

        result = obj.micropath_server_error('req', ('type', 'value', 'tb'))

        assert result == mock_HTTPInternalServerError.return_value
        mock_format_exception.assert_called_once_with('type', 'value', 'tb')
        mock_HTTPInternalServerError.assert_called_once_with(
            'line1\nline2\nline3\n',
        )

    def test_micropath_request_error_base(self, mocker):
        mock_format_exception = mocker.patch.object(
            controller.traceback, 'format_exception',
            return_value=['line1\n', 'line2\n', 'line3\n'],
        )
        mock_HTTPBadRequest = mocker.patch.object(
            controller.webob.exc, 'HTTPBadRequest',
        )
        obj = controller.Controller()

        result = obj.micropath_request_error(
            'req', 'key', ('type', 'value', 'tb'),
        )

        assert result == mock_HTTPBadRequest.return_value
        mock_format_exception.assert_not_called()
        mock_HTTPBadRequest.assert_called_once_with(None)

    def test_micropath_request_error_debug(self, mocker):
        mock_format_exception = mocker.patch.object(
            controller.traceback, 'format_exception',
            return_value=['line1\n', 'line2\n', 'line3\n'],
        )
        mock_HTTPBadRequest = mocker.patch.object(
            controller.webob.exc, 'HTTPBadRequest',
        )
        obj = controller.Controller()
        obj.micropath_debug = True

        result = obj.micropath_request_error(
            'req', 'key', ('type', 'value', 'tb'),
        )

        assert result == mock_HTTPBadRequest.return_value
        mock_format_exception.assert_called_once_with('type', 'value', 'tb')
        mock_HTTPBadRequest.assert_called_once_with(
            'Accessing request attribute "key":\nline1\nline2\nline3\n',
        )

    def test_micropath_not_found(self, mocker):
        mock_HTTPNotFound = mocker.patch.object(
            controller.webob.exc, 'HTTPNotFound',
        )
        obj = controller.Controller()

        result = obj.micropath_not_found('req', '/path/info')

        assert result == mock_HTTPNotFound.return_value
        mock_HTTPNotFound.assert_called_once_with()

    def test_micropath_not_implemented(self, mocker):
        mock_HTTPNotImplemented = mocker.patch.object(
            controller.webob.exc, 'HTTPNotImplemented',
        )
        obj = controller.Controller()

        result = obj.micropath_not_implemented('req', 'PUT')

        assert result == mock_HTTPNotImplemented.return_value
        mock_HTTPNotImplemented.assert_called_once_with()

    def test_micropath_options(self, mocker):
        mock_HTTPNoContent = mocker.patch.object(
            controller.webob.exc, 'HTTPNoContent',
        )
        obj = controller.Controller()

        result = obj.micropath_options('request', ['GET', 'HEAD', 'POST'])

        assert result == mock_HTTPNoContent.return_value
        mock_HTTPNoContent.assert_called_once_with(
            headers={'Allow': 'GET,HEAD,POST'},
        )

    def test_micropath_run_base(self, mocker):
        mock_make_server = mocker.patch.object(
            controller.simple_server, 'make_server',
        )
        server = mock_make_server.return_value
        obj = controller.Controller()

        obj.micropath_run()

        mock_make_server.assert_called_once_with('127.0.0.1', 8000, obj)
        server.serve_forever.assert_called_once_with()

    def test_micropath_run_alt(self, mocker):
        mock_make_server = mocker.patch.object(
            controller.simple_server, 'make_server',
        )
        server = mock_make_server.return_value
        obj = controller.Controller()

        obj.micropath_run('10.0.0.1', 5000)

        mock_make_server.assert_called_once_with('10.0.0.1', 5000, obj)
        server.serve_forever.assert_called_once_with()
