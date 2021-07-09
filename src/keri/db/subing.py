# -*- encoding: utf-8 -*-
"""
KERI
keri.db.subdbing module

"""
import json
from dataclasses import dataclass, asdict
from typing import Type, Union, Iterable

import cbor2
import msgpack

from .. import kering
from .. import help
from ..help import helping
from ..core import coring
from ..app  import keeping
from . import dbing



logger = help.ogler.getLogger()


class Suber:
    """
    Sub DB of LMDBer
    """
    Sep = '.'  # separator for combining key iterables

    def __init__(self, db: Type[dbing.LMDBer], *, subkey: str = 'docs.',):
        """
        Parameters:
            db (dbing.LMDBer): base db
            subkey (str):  LMDB sub database key
        """
        self.db = db
        self.sdb = self.db.env.open_db(key=subkey.encode("utf-8"))


    def put(self, keys: Union[str, Iterable], val: Union[bytes, str]):
        """
        Puts val at key made from keys. Does not overwrite

        Parameters:
            keys (tuple): of key strs to be combined in order to form key
            val (bytes): value

        Returns:
            result (Boolean): True If successful, False otherwise, such as key
                              already in database.
        """
        if hasattr(val, "encode"):
            val = val.encode("utf-8")
        return (self.db.putVal(db=self.sdb, key=self._tokey(keys), val=val))


    def pin(self, keys: Union[str, Iterable], val: Union[bytes, str]):
        """
        Pins (sets) val at key made from keys. Overwrites.

        Parameters:
            keys (tuple): of key strs to be combined in order to form key
            val (bytes): value

        Returns:
            result (Boolean): True If successful. False otherwise.
        """
        if hasattr(val, "encode"):
            val = val.encode("utf-8")
        return (self.db.setVal(db=self.sdb, key=self._tokey(keys), val=val))


    def get(self, keys: Union[str, Iterable]):
        """
        Gets val at keys

        Parameters:
            keys (tuple): of key strs to be combined in order to form key

        Returns:
            data (str):  decoded as utf-8
            None if no entry at keys

        Usage:
            Use walrus operator to catch and raise missing entry
            if (data := mydb.get(keys)) is None:
                raise ExceptionHere
            use data here

        """
        data = self.db.getVal(db=self.sdb, key=self._tokey(keys))
        return bytes(data).decode("utf=8") if data is not None else None


    def rem(self, keys: Union[str, Iterable]):
        """
        Removes entry at keys

        Parameters:
            keys (tuple): of key strs to be combined in order to form key

        Returns:
           result (Boolean): True if key exists so delete successful. False otherwise
        """
        return(self.db.delVal(db=self.sdb, key=self._tokey(keys)))


    def getItemIter(self):
        """
        Return iterator over the all the items in subdb

        Returns:
            iterator: of tuples of keys tuple and val bytes for
            each entry in db

        Example:
            if key in database is "a.b" and val is serialization of dataclass
               with attributes x and y then returns
               (("a","b"), dataclass(x=1,y=2))
        """
        for key, val in self.db.getAllItemIter(db=self.sdb, split=False):
            keys = tuple(key.decode("utf-8").split('.'))
            yield (keys, bytes(val).decode("utf-8"))


    def _tokey(self, keys: Union[str, Iterable]):
        """
        Converts key to key str with proper separators and returns key bytes.
        If key is already str then returns. Else If key is iterable (non-str)
        of strs then joins with separator converts to bytes and returns

        Parameters:
           keys (Union[str, Iterable]): str or Iterable of str.

        """
        if hasattr(keys, "encode"):  # str
            return keys.encode("utf-8")
        elif hasattr(keys, "decode"): # bytes
            return keys
        return (self.Sep.join(keys).encode("utf-8"))



class SerderSuber(Suber):
    """
    Sub class of Suber where data is serialized Serder instance
    Automatically serializes and deserializes using Serder methods

    """
    Sep = '.'  # separator for combining key iterables

    def __init__(self, *pa, **kwa):
        """
        Parameters:
            db (dbing.LMDBer): base db
            subkey (str):  LMDB sub database key
        """
        super(SerderSuber, self).__init__(*pa, **kwa)


    def put(self, keys: Union[str, Iterable], val: coring.Serder):
        """
        Puts val at key made from keys. Does not overwrite

        Parameters:
            keys (tuple): of key strs to be combined in order to form key
            val (Serder): instance

        Returns:
            result (Boolean): True If successful, False otherwise, such as key
                              already in database.
        """
        return (self.db.putVal(db=self.sdb,
                               key=self._tokey(keys),
                               val=val.raw))


    def pin(self, keys: Union[str, Iterable], val: coring.Serder):
        """
        Pins (sets) val at key made from keys. Overwrites.

        Parameters:
            keys (tuple): of key strs to be combined in order to form key
            val (Serder): instance

        Returns:
            result (Boolean): True If successful. False otherwise.
        """
        return (self.db.setVal(db=self.sdb,
                               key=self._tokey(keys),
                               val=val.raw))


    def get(self, keys: Union[str, Iterable]):
        """
        Gets Serder at keys

        Parameters:
            keys (tuple): of key strs to be combined in order to form key

        Returns:
            Serder:
            None: if no entry at keys

        Usage:
            Use walrus operator to catch and raise missing entry
            if (srder := mydb.get(keys)) is None:
                raise ExceptionHere
            use srdr here

        """
        raw = self.db.getVal(db=self.sdb, key=self._tokey(keys))
        return coring.Serder(raw=bytes(raw)) if raw is not None else None


    def rem(self, keys: Union[str, Iterable]):
        """
        Removes entry at keys

        Parameters:
            keys (tuple): of key strs to be combined in order to form key

        Returns:
           result (Boolean): True if key exists so delete successful. False otherwise
        """
        return(self.db.delVal(db=self.sdb, key=self._tokey(keys)))


    def getItemIter(self):
        """
        Return iterator over the all the items in subdb

        Returns:
            iterator: of tuples of keys tuple and val Serder for
            each entry in db

        Example:
            if key in database is "a.b" and val is serialization of dataclass
               with attributes x and y then returns
               (("a","b"), dataclass(x=1,y=2))
        """
        for key, raw in self.db.getAllItemIter(db=self.sdb, split=False):
            keys = tuple(key.decode("utf-8").split('.'))
            yield (keys, coring.Serder(raw=bytes(raw)))


class MatterSuber(Suber):
    """
    Sub class of Suber where data is Matter subclass instance .qb64b property
    which is a fully qualified serialization
    Automatically serializes and deserializes from qb64b to/from Matter instances

    """
    Sep = '.'  # separator for combining key iterables

    def __init__(self, *pa, klas: Type[coring.Matter] = coring.Matter, **kwa):
        """
        Parameters:
            db (dbing.LMDBer): base db
            subkey (str):  LMDB sub database key
            klas (Type[coring.Matter]): Class reference to subclass of Matter
        """
        super(MatterSuber, self).__init__(*pa, **kwa)
        self.klas = klas


    def put(self, keys: Union[str, Iterable], val: coring.Matter):
        """
        Puts val at key made from keys. Does not overwrite

        Parameters:
            keys (tuple): of key strs to be combined in order to form key
            val (Matter): instance

        Returns:
            result (Boolean): True If successful, False otherwise, such as key
                              already in database.
        """
        return (self.db.putVal(db=self.sdb,
                               key=self._tokey(keys),
                               val=val.qb64b))


    def pin(self, keys: Union[str, Iterable], val: coring.Matter):
        """
        Pins (sets) val at key made from keys. Overwrites.

        Parameters:
            keys (tuple): of key strs to be combined in order to form key
            val (Matter): instance

        Returns:
            result (Boolean): True If successful. False otherwise.
        """
        return (self.db.setVal(db=self.sdb,
                               key=self._tokey(keys),
                               val=val.qb64b))


    def get(self, keys: Union[str, Iterable]):
        """
        Gets Serder at keys

        Parameters:
            keys (tuple): of key strs to be combined in order to form key

        Returns:
            val (Matter):
            None if no entry at keys

        Usage:
            Use walrus operator to catch and raise missing entry
            if (srder := mydb.get(keys)) is None:
                raise ExceptionHere
            use srdr here

        """
        val = self.db.getVal(db=self.sdb, key=self._tokey(keys))
        return self.klas(qb64b=bytes(val)) if val is not None else None


    def rem(self, keys: Union[str, Iterable]):
        """
        Removes entry at keys

        Parameters:
            keys (tuple): of key strs to be combined in order to form key

        Returns:
           result (Boolean): True if key exists so delete successful. False otherwise
        """
        return(self.db.delVal(db=self.sdb, key=self._tokey(keys)))


    def getItemIter(self):
        """
        Return iterator over the all the items in subdb

        Returns:
            iterator: of tuples of keys tuple and val Serder for
            each entry in db

        Example:
            if key in database is "a.b" and val is serialization of dataclass
               with attributes x and y then returns
               (("a","b"), dataclass(x=1,y=2))
        """
        for key, val in self.db.getAllItemIter(db=self.sdb, split=False):
            keys = tuple(key.decode("utf-8").split('.'))
            yield (keys, self.klas(qb64b=bytes(val)))




class SignerSuber(MatterSuber):
    """
    Sub class of MatterSuber where data is Signer subclass instance .qb64b propery
    which is a fully qualified serialization and uses the key which is the qb64b
    of the signer.verfer to get the transferable property of the verfer
    Automatically serializes and deserializes from qb64b to/from Signer instances

    """
    Sep = '.'  # separator for combining key iterables

    def __init__(self, *pa, klas: Type[coring.Signer] = coring.Signer, **kwa):
        """
        Parameters:
            db (dbing.LMDBer): base db
            subkey (str):  LMDB sub database key
            klas (Type[coring.Matter]): Class reference to subclass of Matter
        """
        if not (issubclass(klas, coring.Signer)):
            raise ValueError("Invalid klas type={}, expected {}."
                             "".format(klas, coring.Signer))
        super(SignerSuber, self).__init__(*pa, **kwa)
        self.klas = klas


    def get(self, keys: Union[str, Iterable]):
        """
        Gets Serder at keys

        Parameters:
            keys (tuple): of key strs to be combined in order to form key

        Returns:
            val (Matter):
            None if no entry at keys

        Usage:
            Use walrus operator to catch and raise missing entry
            if (srder := mydb.get(keys)) is None:
                raise ExceptionHere
            use srdr here

        """
        key = self._tokey(keys)
        val = self.db.getVal(db=self.sdb, key=key)
        verfer = coring.Verfer(qb64b=key)
        return (self.klas(qb64b=bytes(val), transferable=verfer.transferable)
                if val is not None else None)


    def getItemIter(self):
        """
        Return iterator over the all the items in subdb

        Returns:
            iterator: of tuples of keys tuple and val Serder for
            each entry in db

        Example:
            if key in database is "a.b" and val is serialization of dataclass
               with attributes x and y then returns
               (("a","b"), dataclass(x=1,y=2))
        """
        for key, val in self.db.getAllItemIter(db=self.sdb, split=False):
            keys = tuple(key.decode("utf-8").split('.'))
            verfer = coring.Verfer(qb64b=key)
            yield (keys, self.klas(qb64b=bytes(val),
                                   transferable=verfer.transferable))
