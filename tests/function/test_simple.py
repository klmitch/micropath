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

import micropath

from tests.function import utils


class BookController(micropath.Controller):
    @micropath.route('get')
    def index(self, request, sub_id=None):
        return 'book::index(sub_id=%s)' % utils.safestr(sub_id)

    @micropath.route('post')
    def create(self, request, sub_id=None):
        return 'book::create(sub_id=%s)' % utils.safestr(sub_id)

    book_id = micropath.bind()

    @book_id.route('get')
    def get(self, request, book_id, sub_id=None):
        return 'book::get(book_id=%s, sub_id=%s)' % (
            utils.safestr(book_id), utils.safestr(sub_id),
        )

    @book_id.route('put')
    def update(self, request, book_id, sub_id=None):
        return 'book::update(book_id=%s, sub_id=%s)' % (
            utils.safestr(book_id), utils.safestr(sub_id),
        )

    @book_id.route('delete')
    def delete(self, request, book_id, sub_id=None):
        return 'book::delete(book_id=%s, sub_id=%s)' % (
            utils.safestr(book_id), utils.safestr(sub_id),
        )


class SubscriberController(micropath.Controller):
    @micropath.route('get')
    def index(self, request):
        return 'sub::index()'

    @micropath.route('post')
    def create(self, request):
        return 'sub::create()'

    sub_id = micropath.bind()

    @sub_id.route('get')
    def get(self, request, sub_id):
        return 'sub::get(sub_id=%s)' % utils.safestr(sub_id)

    @sub_id.route('put')
    def update(self, request, sub_id):
        return 'sub::update(sub_id=%s)' % utils.safestr(sub_id)

    @sub_id.route('delete')
    def delete(self, request, sub_id):
        return 'sub::delete(sub_id=%s)' % utils.safestr(sub_id)

    books = sub_id.path().mount(BookController)


class TestSimple(object):
    def test_subscriber_index(self):
        controller = SubscriberController()

        status, _headers, body = utils.invoke(
            controller, '/',
            method='GET',
        )

        assert status == '200 OK'
        assert body == b'sub::index()'

    def test_subscriber_index_url_for(self):
        controller = SubscriberController()
        req = micropath.Request.blank('/', base_url='http://example.com')

        result = req.url_for(controller.index)

        assert result == 'http://example.com/'

    def test_subscriber_index_url_for_scriptname(self):
        controller = SubscriberController()
        req = micropath.Request.blank('/', base_url='http://example.com/api')

        result = req.url_for(controller.index)

        assert result == 'http://example.com/api/'

    def test_subscriber_create(self):
        controller = SubscriberController()

        status, _headers, body = utils.invoke(
            controller, '/',
            method='POST',
        )

        assert status == '200 OK'
        assert body == b'sub::create()'

    def test_subscriber_create_url_for(self):
        controller = SubscriberController()
        req = micropath.Request.blank('/', base_url='http://example.com')

        result = req.url_for(controller.create)

        assert result == 'http://example.com/'

    def test_subscriber_create_url_for_scriptname(self):
        controller = SubscriberController()
        req = micropath.Request.blank('/', base_url='http://example.com/api')

        result = req.url_for(controller.create)

        assert result == 'http://example.com/api/'

    def test_subscriber_options(self):
        controller = SubscriberController()

        status, headers, body = utils.invoke(
            controller, '/',
            method='OPTIONS',
        )

        assert status == '204 No Content'
        assert 'allow' in headers
        assert headers['allow'] == 'GET,HEAD,OPTIONS,POST'
        assert body == b''

    def test_subscriber_other(self):
        controller = SubscriberController()

        status, _headers, _body = utils.invoke(
            controller, '/',
            method='OTHER',
        )

        assert status == '501 Not Implemented'

    def test_subscriber_subid_get(self):
        controller = SubscriberController()

        status, _headers, body = utils.invoke(
            controller, '/1234',
            method='GET',
        )

        assert status == '200 OK'
        assert body == b'sub::get(sub_id=1234)'

    def test_subscriber_get_url_for(self):
        controller = SubscriberController()
        req = micropath.Request.blank('/', base_url='http://example.com')

        result = req.url_for(controller.get, sub_id='1234')

        assert result == 'http://example.com/1234'

    def test_subscriber_get_url_for_scriptname(self):
        controller = SubscriberController()
        req = micropath.Request.blank('/', base_url='http://example.com/api')

        result = req.url_for(controller.get, sub_id='1234')

        assert result == 'http://example.com/api/1234'

    def test_subscriber_subid_update(self):
        controller = SubscriberController()

        status, _headers, body = utils.invoke(
            controller, '/1234',
            method='PUT',
        )

        assert status == '200 OK'
        assert body == b'sub::update(sub_id=1234)'

    def test_subscriber_update_url_for(self):
        controller = SubscriberController()
        req = micropath.Request.blank('/', base_url='http://example.com')

        result = req.url_for(controller.update, sub_id='1234')

        assert result == 'http://example.com/1234'

    def test_subscriber_update_url_for_scriptname(self):
        controller = SubscriberController()
        req = micropath.Request.blank('/', base_url='http://example.com/api')

        result = req.url_for(controller.update, sub_id='1234')

        assert result == 'http://example.com/api/1234'

    def test_subscriber_subid_delete(self):
        controller = SubscriberController()

        status, _headers, body = utils.invoke(
            controller, '/1234',
            method='DELETE',
        )

        assert status == '200 OK'
        assert body == b'sub::delete(sub_id=1234)'

    def test_subscriber_delete_url_for(self):
        controller = SubscriberController()
        req = micropath.Request.blank('/', base_url='http://example.com')

        result = req.url_for(controller.delete, sub_id='1234')

        assert result == 'http://example.com/1234'

    def test_subscriber_delete_url_for_scriptname(self):
        controller = SubscriberController()
        req = micropath.Request.blank('/', base_url='http://example.com/api')

        result = req.url_for(controller.delete, sub_id='1234')

        assert result == 'http://example.com/api/1234'

    def test_subscriber_subid_options(self):
        controller = SubscriberController()

        status, headers, body = utils.invoke(
            controller, '/1234',
            method='OPTIONS',
        )

        assert status == '204 No Content'
        assert 'allow' in headers
        assert headers['allow'] == 'DELETE,GET,HEAD,OPTIONS,PUT'
        assert body == b''

    def test_subscriber_subid_other(self):
        controller = SubscriberController()

        status, _headers, _body = utils.invoke(
            controller, '/1234',
            method='OTHER',
        )

        assert status == '501 Not Implemented'

    def test_book_index(self):
        controller = SubscriberController()

        status, _headers, body = utils.invoke(
            controller, '/1234/books',
            method='GET',
        )

        assert status == '200 OK'
        assert body == b'book::index(sub_id=1234)'

    def test_book_index_url_for(self):
        controller = SubscriberController()
        req = micropath.Request.blank('/', base_url='http://example.com')

        result = req.url_for(controller.books.index, sub_id='1234')

        assert result == 'http://example.com/1234/books'

    def test_book_index_url_for_scriptname(self):
        controller = SubscriberController()
        req = micropath.Request.blank('/', base_url='http://example.com/api')

        result = req.url_for(controller.books.index, sub_id='1234')

        assert result == 'http://example.com/api/1234/books'

    def test_book_create(self):
        controller = SubscriberController()

        status, _headers, body = utils.invoke(
            controller, '/1234/books',
            method='POST',
        )

        assert status == '200 OK'
        assert body == b'book::create(sub_id=1234)'

    def test_book_create_url_for(self):
        controller = SubscriberController()
        req = micropath.Request.blank('/', base_url='http://example.com')

        result = req.url_for(controller.books.create, sub_id='1234')

        assert result == 'http://example.com/1234/books'

    def test_book_create_url_for_scriptname(self):
        controller = SubscriberController()
        req = micropath.Request.blank('/', base_url='http://example.com/api')

        result = req.url_for(controller.books.create, sub_id='1234')

        assert result == 'http://example.com/api/1234/books'

    def test_book_options(self):
        controller = SubscriberController()

        status, headers, body = utils.invoke(
            controller, '/1234/books',
            method='OPTIONS',
        )

        assert status == '204 No Content'
        assert 'allow' in headers
        assert headers['allow'] == 'GET,HEAD,OPTIONS,POST'
        assert body == b''

    def test_book_other(self):
        controller = SubscriberController()

        status, _headers, _body = utils.invoke(
            controller, '/1234/books',
            method='OTHER',
        )

        assert status == '501 Not Implemented'

    def test_book_bookid_get(self):
        controller = SubscriberController()

        status, _headers, body = utils.invoke(
            controller, '/1234/books/5678',
            method='GET',
        )

        assert status == '200 OK'
        assert body == b'book::get(book_id=5678, sub_id=1234)'

    def test_book_bookid_get_url_for(self):
        controller = SubscriberController()
        req = micropath.Request.blank('/', base_url='http://example.com')

        result = req.url_for(
            controller.books.get,
            sub_id='1234',
            book_id='5678',
        )

        assert result == 'http://example.com/1234/books/5678'

    def test_book_bookid_get_url_for_scriptname(self):
        controller = SubscriberController()
        req = micropath.Request.blank('/', base_url='http://example.com/api')

        result = req.url_for(
            controller.books.get,
            sub_id='1234',
            book_id='5678',
        )

        assert result == 'http://example.com/api/1234/books/5678'

    def test_book_bookid_update(self):
        controller = SubscriberController()

        status, _headers, body = utils.invoke(
            controller, '/1234/books/5678',
            method='PUT',
        )

        assert status == '200 OK'
        assert body == b'book::update(book_id=5678, sub_id=1234)'

    def test_book_bookid_update_url_for(self):
        controller = SubscriberController()
        req = micropath.Request.blank('/', base_url='http://example.com')

        result = req.url_for(
            controller.books.update,
            sub_id='1234',
            book_id='5678',
        )

        assert result == 'http://example.com/1234/books/5678'

    def test_book_bookid_update_url_for_scriptname(self):
        controller = SubscriberController()
        req = micropath.Request.blank('/', base_url='http://example.com/api')

        result = req.url_for(
            controller.books.update,
            sub_id='1234',
            book_id='5678',
        )

        assert result == 'http://example.com/api/1234/books/5678'

    def test_book_bookid_delete(self):
        controller = SubscriberController()

        status, _headers, body = utils.invoke(
            controller, '/1234/books/5678',
            method='DELETE',
        )

        assert status == '200 OK'
        assert body == b'book::delete(book_id=5678, sub_id=1234)'

    def test_book_bookid_delete_url_for(self):
        controller = SubscriberController()
        req = micropath.Request.blank('/', base_url='http://example.com')

        result = req.url_for(
            controller.books.delete,
            sub_id='1234',
            book_id='5678',
        )

        assert result == 'http://example.com/1234/books/5678'

    def test_book_bookid_delete_url_for_scriptname(self):
        controller = SubscriberController()
        req = micropath.Request.blank('/', base_url='http://example.com/api')

        result = req.url_for(
            controller.books.delete,
            sub_id='1234',
            book_id='5678',
        )

        assert result == 'http://example.com/api/1234/books/5678'

    def test_book_bookid_options(self):
        controller = SubscriberController()

        status, headers, body = utils.invoke(
            controller, '/1234/books/5678',
            method='OPTIONS',
        )

        assert status == '204 No Content'
        assert 'allow' in headers
        assert headers['allow'] == 'DELETE,GET,HEAD,OPTIONS,PUT'
        assert body == b''

    def test_book_bookid_other(self):
        controller = SubscriberController()

        status, _headers, _body = utils.invoke(
            controller, '/1234/books/5678',
            method='OTHER',
        )

        assert status == '501 Not Implemented'
