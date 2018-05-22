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
        assert isinstance(result.paths, elements.MergingMap)
        assert result.paths == {}
        assert isinstance(result.bindings, elements.BindingMap)
        assert result.bindings == {}
        assert isinstance(result.methods, elements.MergingMap)
        assert result.methods == {}
        assert result._delegation is None
        assert result._master is None

    def test_init_alt(self):
        result = ElementForTest('ident', 'parent')

        assert result.ident == 'ident'
        assert result.parent == 'parent'
        assert isinstance(result.paths, elements.MergingMap)
        assert result.paths == {}
        assert isinstance(result.bindings, elements.BindingMap)
        assert result.bindings == {}
        assert isinstance(result.methods, elements.MergingMap)
        assert result.methods == {}
        assert result._delegation is None
        assert result._master is None

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

    def test_merge_base(self, mocker):
        obj1 = ElementForTest('ident')
        obj2 = ElementForTest('ident')
        subordinates = {
            'o1p1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1p2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o2p1': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2p2': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2b1': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2b2': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2m1': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2m2': mocker.Mock(pre_parent=obj2, expected=obj1),
        }
        for ident, sub in subordinates.items():
            sub.ident = ident
            sub.parent = sub.pre_parent
        obj1.paths = self.sub_sel(subordinates, 'o1p1', 'o1p2')
        obj1.bindings = self.sub_sel(subordinates, 'o1b1', 'o1b2')
        obj1.methods = self.sub_sel(subordinates, 'o1m1', 'o1m2')
        obj2.paths = self.sub_sel(subordinates, 'o2p1', 'o2p2')
        obj2.bindings = self.sub_sel(subordinates, 'o2b1', 'o2b2')
        obj2.methods = self.sub_sel(subordinates, 'o2m1', 'o2m2')

        obj1.merge(obj2)

        assert obj1.parent is None
        assert obj2.parent is None
        assert obj1.paths == self.sub_sel(
            subordinates, 'o1p1', 'o1p2', 'o2p1', 'o2p2',
        )
        assert obj2.paths is obj1.paths
        assert obj1.bindings == self.sub_sel(
            subordinates, 'o1b1', 'o1b2', 'o2b1', 'o2b2',
        )
        assert obj2.bindings is obj1.bindings
        assert obj1.methods == self.sub_sel(
            subordinates, 'o1m1', 'o1m2', 'o2m1', 'o2m2',
        )
        assert obj2.methods is obj1.methods
        assert obj1._delegation is None
        assert obj2._delegation is None
        assert obj1._master is None
        assert obj2._master is obj1
        for sub in subordinates.values():
            assert sub.parent is sub.expected

    def test_merge_obj_not_master(self, mocker):
        obj1 = ElementForTest('ident')
        obj2 = ElementForTest('ident')
        subordinates = {
            'o1p1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1p2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o2p1': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2p2': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2b1': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2b2': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2m1': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2m2': mocker.Mock(pre_parent=obj2, expected=obj2),
        }
        for ident, sub in subordinates.items():
            sub.ident = ident
            sub.parent = sub.pre_parent
        obj1._master = mocker.Mock()
        obj1.paths = self.sub_sel(subordinates, 'o1p1', 'o1p2')
        obj1.bindings = self.sub_sel(subordinates, 'o1b1', 'o1b2')
        obj1.methods = self.sub_sel(subordinates, 'o1m1', 'o1m2')
        obj2.paths = self.sub_sel(subordinates, 'o2p1', 'o2p2')
        obj2.bindings = self.sub_sel(subordinates, 'o2b1', 'o2b2')
        obj2.methods = self.sub_sel(subordinates, 'o2m1', 'o2m2')

        obj1.merge(obj2)

        assert obj1.parent is None
        assert obj2.parent is None
        assert obj1.paths == self.sub_sel(
            subordinates, 'o1p1', 'o1p2',
        )
        assert obj2.paths is not obj1.paths
        assert obj1.bindings == self.sub_sel(
            subordinates, 'o1b1', 'o1b2',
        )
        assert obj2.bindings is not obj1.bindings
        assert obj1.methods == self.sub_sel(
            subordinates, 'o1m1', 'o1m2',
        )
        assert obj2.methods is not obj1.methods
        assert obj1._delegation is None
        assert obj2._delegation is None
        assert obj2._master is None
        obj1._master.merge.assert_called_once_with(obj2)
        for sub in subordinates.values():
            assert sub.parent is sub.expected

    def test_merge_walk_master_chain(self, mocker):
        obj1 = ElementForTest('ident')
        obj2 = ElementForTest('ident')
        obj3 = ElementForTest('ident')
        subordinates = {
            'o1p1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1p2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o2p1': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2p2': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2b1': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2b2': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2m1': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2m2': mocker.Mock(pre_parent=obj2, expected=obj1),
        }
        for ident, sub in subordinates.items():
            sub.ident = ident
            sub.parent = sub.pre_parent
        obj1.paths = self.sub_sel(subordinates, 'o1p1', 'o1p2')
        obj1.bindings = self.sub_sel(subordinates, 'o1b1', 'o1b2')
        obj1.methods = self.sub_sel(subordinates, 'o1m1', 'o1m2')
        obj2.paths = self.sub_sel(subordinates, 'o2p1', 'o2p2')
        obj2.bindings = self.sub_sel(subordinates, 'o2b1', 'o2b2')
        obj2.methods = self.sub_sel(subordinates, 'o2m1', 'o2m2')
        obj3._master = obj2

        obj1.merge(obj3)

        assert obj1.parent is None
        assert obj2.parent is None
        assert obj1.paths == self.sub_sel(
            subordinates, 'o1p1', 'o1p2', 'o2p1', 'o2p2',
        )
        assert obj2.paths is obj1.paths
        assert obj1.bindings == self.sub_sel(
            subordinates, 'o1b1', 'o1b2', 'o2b1', 'o2b2',
        )
        assert obj2.bindings is obj1.bindings
        assert obj1.methods == self.sub_sel(
            subordinates, 'o1m1', 'o1m2', 'o2m1', 'o2m2',
        )
        assert obj2.methods is obj1.methods
        assert obj1._delegation is None
        assert obj2._delegation is None
        assert obj1._master is None
        assert obj2._master is obj1
        assert obj3._master is obj1
        for sub in subordinates.values():
            assert sub.parent is sub.expected

    def test_merge_telescope_delegation(self, mocker):
        obj1 = ElementForTest('ident')
        obj2 = ElementForTest('ident')
        subordinates = {
            'o1p1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1p2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o2p1': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2p2': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2b1': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2b2': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2m1': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2m2': mocker.Mock(pre_parent=obj2, expected=obj1),
        }
        for ident, sub in subordinates.items():
            sub.ident = ident
            sub.parent = sub.pre_parent
        obj1.paths = self.sub_sel(subordinates, 'o1p1', 'o1p2')
        obj1.bindings = self.sub_sel(subordinates, 'o1b1', 'o1b2')
        obj1.methods = self.sub_sel(subordinates, 'o1m1', 'o1m2')
        obj2.paths = self.sub_sel(subordinates, 'o2p1', 'o2p2')
        obj2.bindings = self.sub_sel(subordinates, 'o2b1', 'o2b2')
        obj2.methods = self.sub_sel(subordinates, 'o2m1', 'o2m2')
        obj2._delegation = 'delegation'

        obj1.merge(obj2)

        assert obj1.parent is None
        assert obj2.parent is None
        assert obj1.paths == self.sub_sel(
            subordinates, 'o1p1', 'o1p2', 'o2p1', 'o2p2',
        )
        assert obj2.paths is obj1.paths
        assert obj1.bindings == self.sub_sel(
            subordinates, 'o1b1', 'o1b2', 'o2b1', 'o2b2',
        )
        assert obj2.bindings is obj1.bindings
        assert obj1.methods == self.sub_sel(
            subordinates, 'o1m1', 'o1m2', 'o2m1', 'o2m2',
        )
        assert obj2.methods is obj1.methods
        assert obj1._delegation == 'delegation'
        assert obj2._delegation is None
        assert obj1._master is None
        assert obj2._master is obj1
        for sub in subordinates.values():
            assert sub.parent is sub.expected

    def test_merge_keep_delegation(self, mocker):
        obj1 = ElementForTest('ident')
        obj2 = ElementForTest('ident')
        subordinates = {
            'o1p1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1p2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o2p1': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2p2': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2b1': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2b2': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2m1': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2m2': mocker.Mock(pre_parent=obj2, expected=obj1),
        }
        for ident, sub in subordinates.items():
            sub.ident = ident
            sub.parent = sub.pre_parent
        obj1.paths = self.sub_sel(subordinates, 'o1p1', 'o1p2')
        obj1.bindings = self.sub_sel(subordinates, 'o1b1', 'o1b2')
        obj1.methods = self.sub_sel(subordinates, 'o1m1', 'o1m2')
        obj1._delegation = 'delegation'
        obj2.paths = self.sub_sel(subordinates, 'o2p1', 'o2p2')
        obj2.bindings = self.sub_sel(subordinates, 'o2b1', 'o2b2')
        obj2.methods = self.sub_sel(subordinates, 'o2m1', 'o2m2')

        obj1.merge(obj2)

        assert obj1.parent is None
        assert obj2.parent is None
        assert obj1.paths == self.sub_sel(
            subordinates, 'o1p1', 'o1p2', 'o2p1', 'o2p2',
        )
        assert obj2.paths is obj1.paths
        assert obj1.bindings == self.sub_sel(
            subordinates, 'o1b1', 'o1b2', 'o2b1', 'o2b2',
        )
        assert obj2.bindings is obj1.bindings
        assert obj1.methods == self.sub_sel(
            subordinates, 'o1m1', 'o1m2', 'o2m1', 'o2m2',
        )
        assert obj2.methods is obj1.methods
        assert obj1._delegation == 'delegation'
        assert obj2._delegation is None
        assert obj1._master is None
        assert obj2._master is obj1
        for sub in subordinates.values():
            assert sub.parent is sub.expected

    def test_merge_identical_delegation(self, mocker):
        obj1 = ElementForTest('ident')
        obj2 = ElementForTest('ident')
        delegation = mocker.Mock()
        subordinates = {
            'o1p1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1p2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o2p1': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2p2': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2b1': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2b2': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2m1': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2m2': mocker.Mock(pre_parent=obj2, expected=obj1),
        }
        for ident, sub in subordinates.items():
            sub.ident = ident
            sub.parent = sub.pre_parent
        obj1.paths = self.sub_sel(subordinates, 'o1p1', 'o1p2')
        obj1.bindings = self.sub_sel(subordinates, 'o1b1', 'o1b2')
        obj1.methods = self.sub_sel(subordinates, 'o1m1', 'o1m2')
        obj1._delegation = delegation
        obj2.paths = self.sub_sel(subordinates, 'o2p1', 'o2p2')
        obj2.bindings = self.sub_sel(subordinates, 'o2b1', 'o2b2')
        obj2.methods = self.sub_sel(subordinates, 'o2m1', 'o2m2')
        obj2._delegation = delegation

        obj1.merge(obj2)

        assert obj1.parent is None
        assert obj2.parent is None
        assert obj1.paths == self.sub_sel(
            subordinates, 'o1p1', 'o1p2', 'o2p1', 'o2p2',
        )
        assert obj2.paths is obj1.paths
        assert obj1.bindings == self.sub_sel(
            subordinates, 'o1b1', 'o1b2', 'o2b1', 'o2b2',
        )
        assert obj2.bindings is obj1.bindings
        assert obj1.methods == self.sub_sel(
            subordinates, 'o1m1', 'o1m2', 'o2m1', 'o2m2',
        )
        assert obj2.methods is obj1.methods
        assert obj1._delegation is delegation
        assert obj2._delegation is None
        assert obj1._master is None
        assert obj2._master is obj1
        for sub in subordinates.values():
            assert sub.parent is sub.expected

    def test_merge_bad_types(self, mocker):
        obj1 = ElementForTest('ident')
        obj2 = OtherElement('ident')
        subordinates = {
            'o1p1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1p2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o2p1': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2p2': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2b1': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2b2': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2m1': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2m2': mocker.Mock(pre_parent=obj2, expected=obj2),
        }
        for ident, sub in subordinates.items():
            sub.ident = ident
            sub.parent = sub.pre_parent
        obj1.paths = self.sub_sel(subordinates, 'o1p1', 'o1p2')
        obj1.bindings = self.sub_sel(subordinates, 'o1b1', 'o1b2')
        obj1.methods = self.sub_sel(subordinates, 'o1m1', 'o1m2')
        obj2.paths = self.sub_sel(subordinates, 'o2p1', 'o2p2')
        obj2.bindings = self.sub_sel(subordinates, 'o2b1', 'o2b2')
        obj2.methods = self.sub_sel(subordinates, 'o2m1', 'o2m2')

        with pytest.raises(ValueError):
            obj1.merge(obj2)
        assert obj1.parent is None
        assert obj2.parent is None
        assert obj1.paths == self.sub_sel(
            subordinates, 'o1p1', 'o1p2',
        )
        assert obj2.paths is not obj1.paths
        assert obj1.bindings == self.sub_sel(
            subordinates, 'o1b1', 'o1b2',
        )
        assert obj2.bindings is not obj1.bindings
        assert obj1.methods == self.sub_sel(
            subordinates, 'o1m1', 'o1m2',
        )
        assert obj2.methods is not obj1.methods
        assert obj1._delegation is None
        assert obj2._delegation is None
        assert obj1._master is None
        assert obj2._master is None
        for sub in subordinates.values():
            assert sub.parent is sub.expected

    def test_merge_conflicting_ident(self, mocker):
        obj1 = ElementForTest('ident')
        obj2 = ElementForTest('spam')
        subordinates = {
            'o1p1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1p2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o2p1': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2p2': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2b1': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2b2': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2m1': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2m2': mocker.Mock(pre_parent=obj2, expected=obj2),
        }
        for ident, sub in subordinates.items():
            sub.ident = ident
            sub.parent = sub.pre_parent
        obj1.paths = self.sub_sel(subordinates, 'o1p1', 'o1p2')
        obj1.bindings = self.sub_sel(subordinates, 'o1b1', 'o1b2')
        obj1.methods = self.sub_sel(subordinates, 'o1m1', 'o1m2')
        obj2.paths = self.sub_sel(subordinates, 'o2p1', 'o2p2')
        obj2.bindings = self.sub_sel(subordinates, 'o2b1', 'o2b2')
        obj2.methods = self.sub_sel(subordinates, 'o2m1', 'o2m2')

        with pytest.raises(ValueError):
            obj1.merge(obj2)
        assert obj1.parent is None
        assert obj2.parent is None
        assert obj1.paths == self.sub_sel(
            subordinates, 'o1p1', 'o1p2',
        )
        assert obj2.paths is not obj1.paths
        assert obj1.bindings == self.sub_sel(
            subordinates, 'o1b1', 'o1b2',
        )
        assert obj2.bindings is not obj1.bindings
        assert obj1.methods == self.sub_sel(
            subordinates, 'o1m1', 'o1m2',
        )
        assert obj2.methods is not obj1.methods
        assert obj1._delegation is None
        assert obj2._delegation is None
        assert obj1._master is None
        assert obj2._master is None
        for sub in subordinates.values():
            assert sub.parent is sub.expected

    def test_merge_conflicting_delegation(self, mocker):
        obj1 = ElementForTest('ident')
        obj2 = ElementForTest('ident')
        delegation1 = mocker.Mock()
        delegation2 = mocker.Mock()
        subordinates = {
            'o1p1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1p2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o2p1': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2p2': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2b1': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2b2': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2m1': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2m2': mocker.Mock(pre_parent=obj2, expected=obj2),
        }
        for ident, sub in subordinates.items():
            sub.ident = ident
            sub.parent = sub.pre_parent
        obj1.paths = self.sub_sel(subordinates, 'o1p1', 'o1p2')
        obj1.bindings = self.sub_sel(subordinates, 'o1b1', 'o1b2')
        obj1.methods = self.sub_sel(subordinates, 'o1m1', 'o1m2')
        obj1._delegation = delegation1
        obj2.paths = self.sub_sel(subordinates, 'o2p1', 'o2p2')
        obj2.bindings = self.sub_sel(subordinates, 'o2b1', 'o2b2')
        obj2.methods = self.sub_sel(subordinates, 'o2m1', 'o2m2')
        obj2._delegation = delegation2

        with pytest.raises(ValueError):
            obj1.merge(obj2)
        assert obj1.parent is None
        assert obj2.parent is None
        assert obj1.paths == self.sub_sel(
            subordinates, 'o1p1', 'o1p2',
        )
        assert obj2.paths is not obj1.paths
        assert obj1.bindings == self.sub_sel(
            subordinates, 'o1b1', 'o1b2',
        )
        assert obj2.bindings is not obj1.bindings
        assert obj1.methods == self.sub_sel(
            subordinates, 'o1m1', 'o1m2',
        )
        assert obj2.methods is not obj1.methods
        assert obj1._delegation is delegation1
        assert obj2._delegation is delegation2
        assert obj1._master is None
        assert obj2._master is None
        for sub in subordinates.values():
            assert sub.parent is sub.expected

    def test_merge_parent2_none(self, mocker):
        parent1 = mocker.Mock()
        obj1 = ElementForTest('ident', parent1)
        obj2 = ElementForTest('ident')
        subordinates = {
            'o1p1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1p2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o2p1': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2p2': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2b1': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2b2': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2m1': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2m2': mocker.Mock(pre_parent=obj2, expected=obj2),
        }
        for ident, sub in subordinates.items():
            sub.ident = ident
            sub.parent = sub.pre_parent
        obj1.paths = self.sub_sel(subordinates, 'o1p1', 'o1p2')
        obj1.bindings = self.sub_sel(subordinates, 'o1b1', 'o1b2')
        obj1.methods = self.sub_sel(subordinates, 'o1m1', 'o1m2')
        obj2.paths = self.sub_sel(subordinates, 'o2p1', 'o2p2')
        obj2.bindings = self.sub_sel(subordinates, 'o2b1', 'o2b2')
        obj2.methods = self.sub_sel(subordinates, 'o2m1', 'o2m2')

        with pytest.raises(ValueError):
            obj1.merge(obj2)
        assert obj1.parent is parent1
        assert obj2.parent is None
        assert obj1.paths == self.sub_sel(
            subordinates, 'o1p1', 'o1p2',
        )
        assert obj2.paths is not obj1.paths
        assert obj1.bindings == self.sub_sel(
            subordinates, 'o1b1', 'o1b2',
        )
        assert obj2.bindings is not obj1.bindings
        assert obj1.methods == self.sub_sel(
            subordinates, 'o1m1', 'o1m2',
        )
        assert obj2.methods is not obj1.methods
        assert obj1._delegation is None
        assert obj2._delegation is None
        assert obj1._master is None
        assert obj2._master is None
        for sub in subordinates.values():
            assert sub.parent is sub.expected
        parent1.merge.assert_not_called()

    def test_merge_parent1_none(self, mocker):
        parent2 = mocker.Mock()
        obj1 = ElementForTest('ident')
        obj2 = ElementForTest('ident', parent2)
        subordinates = {
            'o1p1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1p2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o2p1': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2p2': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2b1': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2b2': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2m1': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2m2': mocker.Mock(pre_parent=obj2, expected=obj2),
        }
        for ident, sub in subordinates.items():
            sub.ident = ident
            sub.parent = sub.pre_parent
        obj1.paths = self.sub_sel(subordinates, 'o1p1', 'o1p2')
        obj1.bindings = self.sub_sel(subordinates, 'o1b1', 'o1b2')
        obj1.methods = self.sub_sel(subordinates, 'o1m1', 'o1m2')
        obj2.paths = self.sub_sel(subordinates, 'o2p1', 'o2p2')
        obj2.bindings = self.sub_sel(subordinates, 'o2b1', 'o2b2')
        obj2.methods = self.sub_sel(subordinates, 'o2m1', 'o2m2')

        with pytest.raises(ValueError):
            obj1.merge(obj2)
        assert obj1.parent is None
        assert obj2.parent is parent2
        assert obj1.paths == self.sub_sel(
            subordinates, 'o1p1', 'o1p2',
        )
        assert obj2.paths is not obj1.paths
        assert obj1.bindings == self.sub_sel(
            subordinates, 'o1b1', 'o1b2',
        )
        assert obj2.bindings is not obj1.bindings
        assert obj1.methods == self.sub_sel(
            subordinates, 'o1m1', 'o1m2',
        )
        assert obj2.methods is not obj1.methods
        assert obj1._delegation is None
        assert obj2._delegation is None
        assert obj1._master is None
        assert obj2._master is None
        for sub in subordinates.values():
            assert sub.parent is sub.expected
        parent2.merge.assert_not_called()

    def test_merge_different_parents(self, mocker):
        parent1 = mocker.Mock()
        parent2 = mocker.Mock()
        obj1 = ElementForTest('ident', parent1)
        obj2 = ElementForTest('ident', parent2)
        subordinates = {
            'o1p1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1p2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o2p1': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2p2': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2b1': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2b2': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2m1': mocker.Mock(pre_parent=obj2, expected=obj2),
            'o2m2': mocker.Mock(pre_parent=obj2, expected=obj2),
        }
        for ident, sub in subordinates.items():
            sub.ident = ident
            sub.parent = sub.pre_parent
        obj1.paths = self.sub_sel(subordinates, 'o1p1', 'o1p2')
        obj1.bindings = self.sub_sel(subordinates, 'o1b1', 'o1b2')
        obj1.methods = self.sub_sel(subordinates, 'o1m1', 'o1m2')
        obj2.paths = self.sub_sel(subordinates, 'o2p1', 'o2p2')
        obj2.bindings = self.sub_sel(subordinates, 'o2b1', 'o2b2')
        obj2.methods = self.sub_sel(subordinates, 'o2m1', 'o2m2')

        obj1.merge(obj2)

        assert obj1.parent is parent1
        assert obj2.parent is parent2
        assert obj1.paths == self.sub_sel(
            subordinates, 'o1p1', 'o1p2',
        )
        assert obj2.paths is not obj1.paths
        assert obj1.bindings == self.sub_sel(
            subordinates, 'o1b1', 'o1b2',
        )
        assert obj2.bindings is not obj1.bindings
        assert obj1.methods == self.sub_sel(
            subordinates, 'o1m1', 'o1m2',
        )
        assert obj2.methods is not obj1.methods
        assert obj1._delegation is None
        assert obj2._delegation is None
        assert obj1._master is None
        assert obj2._master is None
        for sub in subordinates.values():
            assert sub.parent is sub.expected
        parent1.merge.assert_called_once_with(parent2)
        parent2.merge.assert_not_called()

    def test_merge_identical_parents(self, mocker):
        parent = mocker.Mock()
        obj1 = ElementForTest('ident', parent)
        obj2 = ElementForTest('ident', parent)
        subordinates = {
            'o1p1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1p2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1b2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m1': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o1m2': mocker.Mock(pre_parent=obj1, expected=obj1),
            'o2p1': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2p2': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2b1': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2b2': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2m1': mocker.Mock(pre_parent=obj2, expected=obj1),
            'o2m2': mocker.Mock(pre_parent=obj2, expected=obj1),
        }
        for ident, sub in subordinates.items():
            sub.ident = ident
            sub.parent = sub.pre_parent
        obj1.paths = self.sub_sel(subordinates, 'o1p1', 'o1p2')
        obj1.bindings = self.sub_sel(subordinates, 'o1b1', 'o1b2')
        obj1.methods = self.sub_sel(subordinates, 'o1m1', 'o1m2')
        obj2.paths = self.sub_sel(subordinates, 'o2p1', 'o2p2')
        obj2.bindings = self.sub_sel(subordinates, 'o2b1', 'o2b2')
        obj2.methods = self.sub_sel(subordinates, 'o2m1', 'o2m2')

        obj1.merge(obj2)

        assert obj1.parent is parent
        assert obj2.parent is parent
        assert obj1.paths == self.sub_sel(
            subordinates, 'o1p1', 'o1p2', 'o2p1', 'o2p2',
        )
        assert obj2.paths is obj1.paths
        assert obj1.bindings == self.sub_sel(
            subordinates, 'o1b1', 'o1b2', 'o2b1', 'o2b2',
        )
        assert obj2.bindings is obj1.bindings
        assert obj1.methods == self.sub_sel(
            subordinates, 'o1m1', 'o1m2', 'o2m1', 'o2m2',
        )
        assert obj2.methods is obj1.methods
        assert obj1._delegation is None
        assert obj2._delegation is None
        assert obj1._master is None
        assert obj2._master is obj1
        for sub in subordinates.values():
            assert sub.parent is sub.expected
        parent.merge.assert_not_called()

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

    def test_binding_base(self, mocker):
        mock_Binding = mocker.patch.object(
            elements, 'Binding',
            return_value=mocker.Mock(ident=None),
        )
        obj = ElementForTest('ident')
        obj.bindings = {}

        result = obj.bind()

        assert result == mock_Binding.return_value
        mock_Binding.assert_called_once_with(
            None,
            parent=obj,
            before=None,
            after=None,
        )
        assert obj.bindings == {}

    def test_binding_alt(self, mocker):
        mock_Binding = mocker.patch.object(
            elements, 'Binding',
            return_value=mocker.Mock(ident='spam'),
        )
        obj = ElementForTest('ident')
        obj.bindings = {}

        result = obj.bind('spam', 'before', 'after')

        assert result == mock_Binding.return_value
        mock_Binding.assert_called_once_with(
            'spam',
            parent=obj,
            before='before',
            after='after',
        )
        assert obj.bindings == {'spam': result}

    def test_route_func(self, mocker):
        mock_Method = mocker.patch.object(
            elements, 'Method',
            return_value=mocker.Mock(ident=None),
        )
        obj = ElementForTest('ident')
        func = mocker.Mock(_micropath_handler=False)

        result = obj.route(func)

        assert result == func
        mock_Method.assert_called_once_with(None, func, parent=obj)
        assert obj.methods == {None: mock_Method.return_value}
        assert func._micropath_handler is True
        assert func._micropath_elem is obj

    def test_route_no_methods(self, mocker):
        mock_Method = mocker.patch.object(
            elements, 'Method',
            return_value=mocker.Mock(ident=None),
        )
        obj = ElementForTest('ident')
        func = mocker.Mock(_micropath_handler=False)

        decorator = obj.route()

        assert callable(decorator)
        assert decorator != func
        mock_Method.assert_not_called()
        assert obj.methods == {}

        result = decorator(func)

        assert result == func
        mock_Method.assert_called_once_with(None, func, parent=obj)
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
        obj = ElementForTest('ident')
        func = mocker.Mock(_micropath_handler=False)

        decorator = obj.route('get', 'put')

        assert callable(decorator)
        assert decorator != func
        mock_Method.assert_not_called()
        assert obj.methods == {}

        result = decorator(func)

        assert result == func
        mock_Method.assert_has_calls([
            mocker.call('get', func, parent=obj),
            mocker.call('put', func, parent=obj),
        ])
        assert mock_Method.call_count == 2
        assert obj.methods == methods
        assert func._micropath_handler is True
        assert func._micropath_elem is obj

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
        assert obj._delegation == result
        mock_init.assert_called_once_with('delegation', {})
        mock_Method.assert_not_called()

    def test_mount_with_methods(self, mocker):
        methods = {
            'get': mocker.Mock(ident='get', _delegation=None),
            'put': mocker.Mock(ident='put', _delegation=None),
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
            assert meth._delegation == result
        assert obj._delegation is None
        mock_init.assert_called_once_with('delegation', {'a': 1, 'b': 2})
        mock_Method.assert_has_calls([
            mocker.call('get', None, parent=obj),
            mocker.call('put', None, parent=obj),
        ])
        assert mock_Method.call_count == 2

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
        assert obj._delegation == delegation
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
        obj._delegation = 'spam'

        with pytest.raises(ValueError):
            obj.mount('delegation')
        assert obj.methods == {}
        assert obj._delegation == 'spam'
        mock_init.assert_not_called()
        mock_Method.assert_not_called()

    def test_mount_master(self, mocker):
        mock_init = mocker.patch.object(
            elements.Delegation, '__init__',
            return_value=None,
        )
        mock_Method = mocker.patch.object(
            elements, 'Method',
            return_value=mocker.Mock(ident=None),
        )
        obj = ElementForTest('ident')
        obj._master = mocker.Mock(**{
            'mount.return_value': mocker.Mock(element=None),
        })

        result = obj.mount('delegation', 'get', 'put', a=1, b=2)

        assert result == obj._master.mount.return_value
        assert result.element is None
        assert obj.methods == {}
        assert obj._delegation is None
        mock_init.assert_not_called()
        mock_Method.assert_not_called()
        obj._master.mount.assert_called_once_with(
            'delegation', 'get', 'put',
            a=1,
            b=2,
        )

    def test_delegation_base(self):
        obj = ElementForTest('ident')
        obj._delegation = 'delegation'

        assert obj.delegation == 'delegation'

    def test_delegation_delegated(self, mocker):
        obj = ElementForTest('ident')
        obj._master = mocker.Mock(delegation='delegation')
        obj._delegation = 'spam'

        assert obj.delegation == 'delegation'


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
        mock_merge = mocker.patch.object(elements.Root, 'merge')
        elem = mocker.Mock(spec=elements.Path, ident='spam')
        elem.parent = None
        obj = elements.Root()
        obj.bindings = {}

        obj.add_elem(elem)

        assert obj.paths == {'spam': elem}
        assert obj.bindings == {}
        assert obj.methods == {}
        assert elem.ident == 'spam'
        assert elem.parent is obj
        mock_merge.assert_not_called()
        elem.set_ident.assert_not_called()

    def test_add_elem_binding(self, mocker):
        mock_merge = mocker.patch.object(elements.Root, 'merge')
        elem = mocker.Mock(spec=elements.Binding, ident='spam')
        elem.parent = None
        obj = elements.Root()
        obj.bindings = {}

        obj.add_elem(elem)

        assert obj.paths == {}
        assert obj.bindings == {'spam': elem}
        assert obj.methods == {}
        assert elem.ident == 'spam'
        assert elem.parent is obj
        mock_merge.assert_not_called()
        elem.set_ident.assert_not_called()

    def test_add_elem_method(self, mocker):
        mock_merge = mocker.patch.object(elements.Root, 'merge')
        elem = mocker.Mock(spec=elements.Method, ident='spam')
        elem.parent = None
        obj = elements.Root()
        obj.bindings = {}

        obj.add_elem(elem)

        assert obj.paths == {}
        assert obj.bindings == {}
        assert obj.methods == {'spam': elem}
        assert elem.ident == 'spam'
        assert elem.parent is obj
        mock_merge.assert_not_called()
        elem.set_ident.assert_not_called()

    def test_add_elem_method_all(self, mocker):
        mock_merge = mocker.patch.object(elements.Root, 'merge')
        elem = mocker.Mock(spec=elements.Method, ident=None)
        elem.parent = None
        obj = elements.Root()
        obj.bindings = {}

        obj.add_elem(elem)

        assert obj.paths == {}
        assert obj.bindings == {}
        assert obj.methods == {None: elem}
        assert elem.ident is None
        assert elem.parent is obj
        mock_merge.assert_not_called()
        elem.set_ident.assert_not_called()

    def test_add_elem_other(self, mocker):
        mock_merge = mocker.patch.object(elements.Root, 'merge')
        elem = mocker.Mock(ident='spam')
        elem.parent = None
        obj = elements.Root()
        obj.bindings = {}

        with pytest.raises(ValueError):
            obj.add_elem(elem)
        assert obj.paths == {}
        assert obj.bindings == {}
        assert obj.methods == {}
        assert elem.ident == 'spam'
        assert elem.parent is None
        mock_merge.assert_not_called()
        elem.set_ident.assert_not_called()

    def test_add_elem_self(self, mocker):
        mock_merge = mocker.patch.object(elements.Root, 'merge')
        obj = elements.Root()
        obj.bindings = {}

        obj.add_elem(obj)

        assert obj.paths == {}
        assert obj.bindings == {}
        assert obj.methods == {}
        mock_merge.assert_not_called()

    def test_add_elem_root(self, mocker):
        mock_merge = mocker.patch.object(elements.Root, 'merge')
        elem = mocker.Mock(spec=elements.Root, ident=None)
        elem.parent = None
        obj = elements.Root()
        obj.bindings = {}

        obj.add_elem(elem)

        assert obj.paths == {}
        assert obj.bindings == {}
        assert obj.methods == {}
        assert elem.ident is None
        assert elem.parent is None
        mock_merge.assert_called_once_with(elem)
        elem.set_ident.assert_not_called()

    def test_add_elem_path_no_ident(self, mocker):
        mock_merge = mocker.patch.object(elements.Root, 'merge')
        elem = mocker.Mock(spec=elements.Path, ident=None)
        elem.parent = None
        obj = elements.Root()
        obj.bindings = {}

        obj.add_elem(elem)

        assert obj.paths == {}
        assert obj.bindings == {}
        assert obj.methods == {}
        assert elem.ident is None
        assert elem.parent is obj
        mock_merge.assert_not_called()
        elem.set_ident.assert_not_called()

    def test_add_elem_binding_no_ident(self, mocker):
        mock_merge = mocker.patch.object(elements.Root, 'merge')
        elem = mocker.Mock(spec=elements.Binding, ident=None)
        elem.parent = None
        obj = elements.Root()
        obj.bindings = {}

        obj.add_elem(elem)

        assert obj.paths == {}
        assert obj.bindings == {}
        assert obj.methods == {}
        assert elem.ident is None
        assert elem.parent is obj
        mock_merge.assert_not_called()
        elem.set_ident.assert_not_called()

    def test_add_elem_set_ident(self, mocker):
        mock_merge = mocker.patch.object(elements.Root, 'merge')
        elem = mocker.Mock(spec=elements.Path, ident=None)
        elem.parent = None
        obj = elements.Root()
        obj.bindings = {}

        obj.add_elem(elem, 'spam')

        assert obj.paths == {}
        assert obj.bindings == {}
        assert obj.methods == {}
        assert elem.ident is None
        assert elem.parent is obj
        mock_merge.assert_not_called()
        elem.set_ident.assert_called_once_with('spam')

    def test_add_elem_parents(self, mocker):
        mock_merge = mocker.patch.object(elements.Root, 'merge')
        elem = mocker.Mock(spec=elements.Path, ident='spam')
        elem.parent = None
        descendant = mocker.Mock(spec=elements.Path, ident=None)
        descendant.parent = elem
        obj = elements.Root()
        obj.bindings = {}

        obj.add_elem(descendant, 'descendant')

        assert obj.paths == {'spam': elem}
        assert obj.bindings == {}
        assert obj.methods == {}
        assert elem.ident == 'spam'
        assert elem.parent is obj
        mock_merge.assert_not_called()
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


class TestBinding(object):
    def test_init_base(self, mocker):
        mock_init = mocker.patch.object(
            elements.Element, '__init__',
            return_value=None,
        )

        result = elements.Binding('ident')

        assert result.before == set()
        assert result.after == set()
        assert result._validator is None
        assert result._formatter is None
        mock_init.assert_called_once_with('ident', None)

    def test_init_alt(self, mocker):
        mock_init = mocker.patch.object(
            elements.Element, '__init__',
            return_value=None,
        )

        result = elements.Binding(
            'ident', 'parent', ['b1', 'b2'], ['a1', 'a2'],
        )

        assert result.before == set(['b1', 'b2'])
        assert result.after == set(['a1', 'a2'])
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

    def test_validator_base(self):
        obj = elements.Binding('ident')

        result = obj.validator('func')

        assert result == 'func'
        assert obj._validator == 'func'

    def test_validator_already_set(self):
        obj = elements.Binding('ident')
        obj._validator = 'spam'

        with pytest.raises(ValueError):
            obj.validator('func')
        assert obj._validator == 'spam'

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
            obj.bind('ident', 'before', 'after')

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


class TestMergingMap(object):
    def test_init(self):
        result = elements.MergingMap()

        assert result._map == {}

    def test_len(self):
        obj = elements.MergingMap()
        obj._map = {'a': 1, 'b': 2, 'c': 3}

        assert len(obj) == 3

    def test_iter(self):
        obj = elements.MergingMap()
        obj._map = {'a': 1, 'b': 2, 'c': 3}

        assert set(iter(obj)) == set(['a', 'b', 'c'])

    def test_getitem(self):
        obj = elements.MergingMap()
        obj._map = {'a': 1, 'b': 2, 'c': 3}

        assert obj['a'] == 1

    def test_setitem_new(self, mocker):
        obj = elements.MergingMap()
        item = mocker.Mock(ident='spam')

        obj['spam'] = item

        assert obj._map == {'spam': item}

    def test_setitem_merge(self, mocker):
        obj = elements.MergingMap()
        existing = mocker.Mock()
        obj._map = {'spam': existing}
        item = mocker.Mock(ident='spam')

        obj['spam'] = item

        assert obj._map == {'spam': existing}
        existing.merge.assert_called_once_with(item)

    def test_delitem_exists(self):
        obj = elements.MergingMap()
        obj._map = {'spam': 'item'}

        with pytest.raises(ValueError):
            del obj['spam']

    def test_delitem_missing(self):
        obj = elements.MergingMap()

        with pytest.raises(KeyError):
            del obj['spam']


class TestFromAdj(object):
    def test_base(self):
        adjacency = {'spam': set(['a', 'b', 'c', 'd']), 'other': set()}

        result = elements._from_adj(adjacency, 'spam')

        assert isinstance(result, elements._VisitElem)
        assert result[0] == 'spam'
        assert list(result[1]) == ['d', 'c', 'b', 'a']
        assert adjacency == {'other': set()}


class TestBindingMap(object):
    def test_init(self, mocker):
        mock_init = mocker.patch.object(
            elements.MergingMap, '__init__',
            return_value=None,
        )

        result = elements.BindingMap()

        assert result._order is None
        mock_init.assert_called_once_with()

    def test_iter_uncached(self, mocker):
        def fake_visit(adj, elem):
            obj._order[:] = [obj._map[x] for x in ('a', 'b', 'c')]
            adj.pop(obj._map['c'], None)
        mock_visit = mocker.patch.object(
            elements.BindingMap, '_visit',
            side_effect=fake_visit,
        )
        obj = elements.BindingMap()
        obj._map['c'] = elements.Binding('c')
        obj._map['e'] = elements.Binding('e')
        obj._map['a'] = elements.Binding('a', before=[obj._map['c']])
        obj._map['d'] = elements.Binding('d', after=[obj._map['a']])
        obj._map['b'] = elements.Binding('b', before=[obj._map['d']])
        adjacency = {x: obj._map[x] for x in ('a', 'b', 'd', 'e')}

        result = list(iter(obj))

        assert result == ['c', 'b', 'a']
        assert obj._order == [obj._map[x] for x in ('c', 'b', 'a')]
        assert mock_visit.call_count == 4
        for i, key in enumerate(['e', 'd', 'b', 'a']):
            mock_visit.call_args_list[i][0][0] == adjacency

    def test_iter_cached(self, mocker):
        def fake_visit(adj, elem):
            obj._order[:] = [obj._map[x] for x in ('a', 'b', 'c')]
            adj.pop(obj._map['c'], None)
        mock_visit = mocker.patch.object(
            elements.BindingMap, '_visit',
            side_effect=fake_visit,
        )
        obj = elements.BindingMap()
        obj._map['c'] = elements.Binding('c')
        obj._map['e'] = elements.Binding('e')
        obj._map['a'] = elements.Binding('a', before=[obj._map['c']])
        obj._map['d'] = elements.Binding('d', after=[obj._map['a']])
        obj._map['b'] = elements.Binding('b', before=[obj._map['d']])
        obj._order = [obj._map[x] for x in ('a', 'b', 'c')]

        result = list(iter(obj))

        assert result == ['a', 'b', 'c']
        assert obj._order == [obj._map[x] for x in ('a', 'b', 'c')]
        mock_visit.assert_not_called()

    def test_setitem(self, mocker):
        mock_setitem = mocker.patch.object(elements.MergingMap, '__setitem__')
        obj = elements.BindingMap()
        obj._order = 'cached'

        obj['spam'] = 'value'

        assert obj._order is None
        mock_setitem.assert_called_once_with('spam', 'value')

    def test_visit(self, mocker):
        bindings = {x: elements.Binding(x) for x in ('a', 'b', 'c', 'd', 'e')}
        adjacency = {
            bindings['b']: {bindings['d']},
            bindings['c']: set(),
            bindings['d']: {bindings['b']},
            bindings['e']: set(),
        }
        elem = elements._VisitElem(
            bindings['a'], iter(bindings[x] for x in ('d', 'c')),
        )
        obj = elements.BindingMap()
        obj._order = []

        obj._visit(adjacency, elem)

        assert adjacency == {bindings['e']: set()}
        assert obj._order == [bindings[x] for x in ['b', 'd', 'c', 'a']]


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
        mock_Binding.assert_called_once_with(None, before=None, after=None)

    def test_alt(self, mocker):
        mock_Binding = mocker.patch.object(elements, 'Binding')

        result = elements.bind('ident', 'before', 'after')

        assert result == mock_Binding.return_value
        mock_Binding.assert_called_once_with(
            'ident',
            before='before',
            after='after',
        )


class TestRoute(object):
    def test_func(self, mocker):
        mock_Method = mocker.patch.object(
            elements, 'Method',
            return_value=mocker.Mock(ident=None),
        )
        func = mocker.Mock(_micropath_methods=None, _micropath_handler=False)

        result = elements.route(func)

        assert result == func
        mock_Method.assert_called_once_with(None, func)
        assert func._micropath_methods == [mock_Method.return_value]
        assert func._micropath_handler is True

    def test_no_methods(self, mocker):
        mock_Method = mocker.patch.object(
            elements, 'Method',
            return_value=mocker.Mock(ident=None),
        )
        func = mocker.Mock(_micropath_methods=None, _micropath_handler=False)

        decorator = elements.route()

        assert callable(decorator)
        assert decorator != func
        mock_Method.assert_not_called()
        assert func._micropath_methods is None
        assert func._micropath_handler is False

        result = decorator(func)

        assert result == func
        mock_Method.assert_called_once_with(None, func)
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
        func = mocker.Mock(_micropath_methods=None, _micropath_handler=False)

        decorator = elements.route('get', 'put')

        assert callable(decorator)
        assert decorator != func
        mock_Method.assert_not_called()
        assert func._micropath_methods is None
        assert func._micropath_handler is False

        result = decorator(func)

        assert result == func
        mock_Method.assert_has_calls([
            mocker.call('get', func),
            mocker.call('put', func),
        ])
        assert mock_Method.call_count == 2
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
            'get': mocker.Mock(ident='get', _delegation=None),
            'put': mocker.Mock(ident='put', _delegation=None),
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
