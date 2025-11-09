import uuid
from typing import Any, Dict, List, Iterable

class _DocSnap:
    def __init__(self, id: str, data: Dict[str, Any] | None, ref):
        self.id = id
        self._data = data
        self.reference = ref
    def to_dict(self) -> Dict[str, Any] | None:
        return dict(self._data) if self._data is not None else None
    @property
    def exists(self) -> bool:
        return self._data is not None

class _DocRef:
    def __init__(self, col, doc_id: str | None = None):
        self._col = col
        self.id = doc_id or str(uuid.uuid4()).replace("-", "")[:20]
    def set(self, data: Dict[str, Any]):
        self._col._docs[self.id] = dict(data)
    def get(self, transaction=None) -> _DocSnap:
        # Return a snapshot with None data if document doesn't exist
        # transaction parameter ignored for fake DB
        data = self._col._docs.get(self.id)
        return _DocSnap(self.id, data, self)
    def update(self, fields: Dict[str, Any]):
        if self.id in self._col._docs:
            self._col._docs[self.id].update(fields)
        else:
            # For update on non-existent doc, create it
            self._col._docs[self.id] = dict(fields)
    def delete(self):
        self._col._docs.pop(self.id, None)

class _Query:
    def __init__(self, col, filters: List, order: str | None):
        self._col = col
        self._filters = filters
        self._order = order
    def where(self, *, filter):
        # filter has .field_path, .op_string, .value (same names as google FieldFilter)
        self._filters.append((filter.field_path, filter.op_string, filter.value))
        return self
    def order_by(self, field: str):
        self._order = field
        return self
    def stream(self) -> Iterable[_DocSnap]:
        items = []
        for doc_id, data in self._col._docs.items():
            ok = True
            for field, op, val in self._filters:
                v = _get_nested(data, field)
                if op == "==":
                    ok = ok and (v == val)
                elif op == "<=":
                    ok = ok and (v is not None and v <= val)
                elif op == ">=":
                    ok = ok and (v is not None and v >= val)
                else:
                    ok = False
                if not ok:
                    break
            if ok:
                items.append(_DocSnap(doc_id, data, _DocRef(self._col, doc_id)))
        if self._order:
            items.sort(key=lambda s: str(_get_nested(s._data, self._order) or ""))
        return items

def _get_nested(d: Dict[str, Any], path: str | None):
    if path is None: return None
    cur = d
    for p in path.split("."):
        if not isinstance(cur, dict): return None
        cur = cur.get(p)
    return cur

class FakeCollection:
    def __init__(self, name: str):
        self._name = name
        self._docs: Dict[str, Dict[str, Any]] = {}
    def document(self, doc_id: str | None = None):
        return _DocRef(self, doc_id)
    # Support both .where(filter=FieldFilter(...)) and .where(...).where(...)
    def where(self, *, filter):
        return _Query(self, [(filter.field_path, filter.op_string, filter.value)], order=None)
    def stream(self):
        # not used directly in our app, but handy
        for doc_id, data in self._docs.items():
            yield _DocSnap(doc_id, data, _DocRef(self, doc_id))

class FakeTransaction:
    """
    Fake transaction for testing - mimics basic Firestore transaction interface.
    In tests, transactions don't need real ACID properties.
    """
    def __init__(self):
        self._read_only = False
        self._id = None
        self._write_pbs = []
        self._max_attempts = 3

    def _begin(self, retry_id=None):
        """Mock begin - no-op for testing"""
        pass

    def _rollback(self):
        """Mock rollback - no-op for testing"""
        pass

    def _commit(self):
        """Mock commit - no-op for testing"""
        pass

    def _clean_up(self):
        """Mock cleanup - no-op for testing"""
        pass

    def update(self, reference, data):
        """Mock update - directly updates the document"""
        reference.update(data)

class FakeDB:
    def __init__(self):
        self._cols: Dict[str, FakeCollection] = {}
    def collection(self, name: str) -> FakeCollection:
        if name not in self._cols:
            self._cols[name] = FakeCollection(name)
        return self._cols[name]
    def transaction(self):
        """Return a fake transaction object for testing"""
        return FakeTransaction()
