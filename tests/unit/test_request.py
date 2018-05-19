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

from micropath import request


class TestRequest(object):
    def test_init(self, mocker):
        result = request.Request.blank(
            '/is/a/test',
            base_url='http://example.com/this',
        )

        assert result.environ['micropath.base_path'] == '/this'

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
