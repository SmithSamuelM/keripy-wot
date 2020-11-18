# -*- encoding: utf-8 -*-
"""
KERI
keri.base.keeping module

Terminology:
    salt is 128 bit 16 char random bytes used as root entropy to derive seed or secret
    private key same as seed or secret for key pair
    seed or secret or private key is crypto suite length dependent random bytes
    public key

txn.put(
            did.encode(),
            json.dumps(certifiable_data).encode("utf-8")
        )
raw_data = txn.get(did.encode())
    if raw_data is None:
        return None
    return json.loads(raw_data)

ked = json.loads(raw[:size].decode("utf-8"))
raw = json.dumps(ked, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

"""
import os
import stat
import json

from dataclasses import dataclass, asdict, field
from collections import namedtuple

from hio.base import doing

from .. import kering
from ..help import helping
from ..core import coring
from ..db import dbing


Algoage = namedtuple("Algoage", 'randy salty')
Algos = Algoage(randy='randy', salty='salty')  # randy is rerandomize, salty is use salt



@dataclass()
class PubLot:
    """
    Public key list with indexes and datetime created
    """
    pubs: list = field(default_factory=list)  # empty list of fully qualified Base64 public keys.
    ridx: int = 0  # index of rotation (est event) that uses public key set
    kidx: int = 0  # index of key in sequence of public keys
    dt:   str = ""  #  datetime ISO8601 when key set created


    def __iter__(self):
        return iter(asdict(self))



@dataclass()
class PubSit:
    """
    Public key situation and parameters for creating key lists and tracking them
    """
    pidx: int = 0  # prefix index for this keypair sequence
    algo: str = Algos.salty  # default use indices and salt  to create new key pairs
    salt: str = ''  # empty salt  used for index algo.
    level: str = coring.SecLevels.low  # stretch security level for index algo
    old: PubLot = field(default_factory=PubLot)  # previous publot
    new: PubLot = field(default_factory=PubLot)  # newly current publot
    nxt: PubLot = field(default_factory=PubLot)  # next public publot


    def __iter__(self):
        return iter(asdict(self))


def openKeeper(name="test", **kwa):
    """
    Returns contextmanager generated by openLMDB but with Keeper instance
    default name="test"
    default temp=True,

    openLMDB Parameters:
        cls is Class instance of subclass instance
        name is str name of LMDBer dirPath so can have multiple databasers
            at different directory path names thar each use different name
        temp is Boolean, True means open in temporary directory, clear on close
            Otherwise open in persistent directory, do not clear on close
    """
    return dbing.openLMDB(cls=Keeper, name=name, **kwa)


class Keeper(dbing.LMDBer):
    """
    Keeper sets up named sub databases for key pair storage.  Methods provide
    key pair creation and data signing.

    Inherited Attributes:
        .name is LMDB database name did2offer
        .temp is Boolean, True means open db in /tmp directory
        .headDirPath is head directory path for db
        .mode is numeric os dir permissions for db directory
        .path is LMDB main (super) database directory path
        .env is LMDB main (super) database environment
        .opened is Boolean, True means LMDB .env at .path is opened.
                            Otherwise LMDB .env is closed

    Attributes:
        .prms is named sub DB whose values are parameters
            Keyed by parameter labels
            Value is parameter
               parameters:
                   pidx is hex index of next prefix key-pair sequence to be incepted
                   salt is root salt for  generating key pairs
        .pris is named sub DB whose values are private keys
            Keyed by public key (fully qualified qb64)
            Value is private key (fully qualified qb64)
        .sits is named sub DB whose values are serialized dicts of PubSit instance
            Keyed by identifer prefix (fully qualified qb64)
            Value is  serialized parameter dict (JSON) of public key situation
                {
                  algo: ,
                  salt: ,
                  level: ,
                  old: { pubs: ridx:, kidx,  dt:},
                  new: { pubs: ridx:, kidx:, dt:},
                  new: { pubs: ridx:, kidx:, dt:}
                }

    Properties:

    Directory Mode for Restricted Access Permissions
    stat.S_ISVTX  is Sticky bit. When this bit is set on a directory it means
        that a file in that directory can be renamed or deleted only by the
        owner of the file, by the owner of the directory, or by a privileged process.

    stat.S_IRUSR Owner has read permission.
    stat.S_IWUSR Owner has write permission.
    stat.S_IXUSR Owner has execute permission.
    """
    HeadDirPath = "/usr/local/var"  # default in /usr/local/var
    TailDirPath = "keri/keep"
    AltHeadDirPath = "~"  #  put in ~ as fallback when desired not permitted
    AltTailDirPath = ".keri/keep"
    TempHeadDir = "/tmp"
    TempPrefix = "keri_keep_"
    TempSuffix = "_test"
    MaxNamedDBs = 8
    DirMode = stat.S_ISVTX | stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR  # 0o1700


    def __init__(self, headDirPath=None, dirMode=None, reopen=True, **kwa):
        """
        Setup named sub databases.

        Inherited Parameters:
            name is str directory path name differentiator for main database
                When system employs more than one keri database, name allows
                differentiating each instance by name
                default name='main'
            temp is boolean, assign to .temp
                True then open in temporary directory, clear on close
                Othewise then open persistent directory, do not clear on close
                default temp=False
            headDirPath is optional str head directory pathname for main database
                If not provided use default .HeadDirpath
                default headDirPath=None so uses self.HeadDirPath
            dirMode is numeric optional os dir permissions mode
                default dirMode=None so do not set mode
            reopen is boolean, IF True then database will be reopened by this init
                default reopen=True

        Notes:

        dupsort=True for sub DB means allow unique (key,pair) duplicates at a key.
        Duplicate means that is more than one value at a key but not a redundant
        copies a (key,value) pair per key. In other words the pair (key,value)
        must be unique both key and value in combination.
        Attempting to put the same (key,value) pair a second time does
        not add another copy.

        Duplicates are inserted in lexocographic order by value, insertion order.

        """
        if dirMode is None:
            dirMode = self.DirMode  # defaults to restricted permissions for non temp

        super(Keeper, self).__init__(headDirPath=headDirPath, dirMode=dirMode,
                                     reopen=reopen, **kwa)


    def reopen(self, **kwa):
        """
        Open sub databases
        """
        super(Keeper, self).reopen(**kwa)

        # Create by opening first time named sub DBs within main DB instance
        # Names end with "." as sub DB name must include a non Base64 character
        # to avoid namespace collisions with Base64 identifier prefixes.

        self.prms = self.env.open_db(key=b'prms.')
        self.pris = self.env.open_db(key=b'pris.')
        self.sits = self.env.open_db(key=b'sits.')

    # .prms methods
    def putPrm(self, key, val):
        """
        Write parameter as val to key
        key is parameter label
        Does not overwrite existing val if any
        Returns True If val successfully written Else False
        Return False if key already exists
        """
        return self.putVal(self.prms, key, val)


    def setPrm(self, key, val):
        """
        Write parameter as val to key
        key is parameter label
        Overwrites existing val if any
        Returns True If val successfully written Else False
        """
        return self.setVal(self.prms, key, val)


    def getPrm(self, key):
        """
        Return parameter val at key label
        key is fully qualified public key
        Returns None if no entry at key
        """
        return self.getVal(self.prms, key)


    def delPrm(self, key):
        """
        Deletes value at key.
        val is fully qualified private key
        key is fully qualified public key
        Returns True If key exists in database Else False
        """
        return self.delVal(self.prms, key)


    # .pris methods
    def putPri(self, key, val):
        """
        Write fully qualified private key as val to key
        key is fully qualified public key
        Does not overwrite existing val if any
        Returns True If val successfully written Else False
        Return False if key already exists
        """
        return self.putVal(self.pris, key, val)


    def setPri(self, key, val):
        """
        Write fully qualified private key as val to key
        key is fully qualified public key
        Overwrites existing val if any
        Returns True If val successfully written Else False
        """
        return self.setVal(self.pris, key, val)


    def getPri(self, key):
        """
        Return private key val at key
        key is fully qualified public key
        Returns None if no entry at key
        """
        return self.getVal(self.pris, key)


    def delPri(self, key):
        """
        Deletes value at key.
        val is fully qualified private key
        key is fully qualified public key
        Returns True If key exists in database Else False
        """
        return self.delVal(self.pris, key)

    # .sits methods
    def putSit(self, key, val):
        """
        Write serialized dict of PubSit as val to key
        key is fully qualified prefix
        Does not overwrite existing val if any
        Returns True If val successfully written Else False
        Return False if key already exists
        """
        return self.putVal(self.sits, key, val)


    def setSit(self, key, val):
        """
        Write serialized parameter dict as val to key
        key is fully qualified prefix
        Overwrites existing val if any
        Returns True If val successfully written Else False
        """
        return self.setVal(self.sits, key, val)


    def getSit(self, key):
        """
        Return serialized parameter dict at key
        key is fully qualified prefix
        Returns None if no entry at key
        """
        return self.getVal(self.sits, key)


    def delSit(self, key):
        """
        Deletes value at key.
        key is fully qualified prefix
        val is serialized parameter dict at key
        Returns True If key exists in database Else False
        """
        return self.delVal(self.sits, key)


class KeeperDoer(doing.Doer):
    """
    Basic Keeper Doer ( LMDB Database )

    Inherited Attributes:
        .done is Boolean completion state:
            True means completed
            Otherwise incomplete. Incompletion maybe due to close or abort.

    Attributes:
        .keeper is Keeper or LMDBer subclass

    Inherited Properties:
        .tyme is float ._tymist.tyme, relative cycle or artificial time
        .tock is float, desired time in seconds between runs or until next run,
                 non negative, zero means run asap

    Properties:

    Methods:
        .wind  injects ._tymist dependency
        .__call__ makes instance callable
            Appears as generator function that returns generator
        .do is generator method that returns generator
        .enter is enter context action method
        .recur is recur context action method or generator method
        .exit is exit context method
        .close is close context method
        .abort is abort context method

    Hidden:
       ._tymist is Tymist instance reference
       ._tock is hidden attribute for .tock property
    """

    def __init__(self, keeper, **kwa):
        """
        Inherited Parameters:
           tymist is Tymist instance
           tock is float seconds initial value of .tock

        Parameters:
           keeper is Keeper instance
        """
        super(KeeperDoer, self).__init__(**kwa)
        self.keeper = keeper


    def enter(self):
        """"""
        self.keeper.reopen()


    def exit(self):
        """"""
        self.keeper.close()


class Creator:
    """
    Class for creating a key pair based on algorithm.

    Attributes:

    Properties:

    Methods:
        .create is method to create key pair

    Hidden:

    """

    def __init__(self, **kwa):
        """
        Setup Creator.

        Parameters:

        """


    def create(self, **kwa):
        """
        Returns tuple of signers one per key pair
        """
        return []


class RandyCreator(Creator):
    """
    Class for creating a key pair based on re-randomizing each seed algorithm.

    Attributes:

    Properties:

    Methods:
        .create is method to create key pair

    Hidden:

    """


    def __init__(self, **kwa):
        """
        Setup Creator.

        Parameters:

        """
        super(RandyCreator, self).__init__(**kwa)


    def create(self, codes=None, count=1, code=coring.CryOneDex.Ed25519_Seed,
               transferable=True, **kwa):
        """
        Returns list of signers one per kidx in kidxs

        Parameters:
            ridx is int rotation index for key pair set
            kidx is int starting key index for key pair set
            count is into number of key pairs in set
        """
        signers = []
        if not codes:  # if not codes make list len count of same code
            codes = [code for i in range(count)]

        for code in codes:
            signers.append(coring.Signer(code=code, transferable=transferable))
        return signers



class SaltyCreator(Creator):
    """
    Class for creating a key pair based on random salt plus path stretch algorithm.

    Attributes:
        .salter is salter instance

    Properties:


    Methods:
        .create is method to create key pair

    Hidden:
        ._salter holds instance for .salter property
    """

    def __init__(self, salt=None, level=None, **kwa):
        """
        Setup Creator.

        Parameters:

        """
        super(SaltyCreator, self).__init__(**kwa)
        self.salter = coring.Salter(qb64=salt, level=level)


    @property
    def salt(self):
        """
        salt property getter
        """
        return self.salter.qb64


    @property
    def level(self):
        """
        level property getter
        """
        return self.salter.level


    def create(self, codes=None, count=1, code=coring.CryOneDex.Ed25519_Seed,
               ridx=0, kidx=0, level=None, transferable=True, temp=False, **kwa):
        """
        Returns list of signers one per kidx in kidxs

        Parameters:
            ridx is int rotation index for key pair set
            kidx is int starting key index for key pair set
            count is into number of key pairs in set
        """
        signers = []
        if not codes:  # if not codes make list len count of same code
            codes = [code for i in range(count)]
        for i, code in enumerate(codes):
            path = "{:x}{:x}".format(ridx,kidx + i)
            signers.append(self.salter.signer(path=path,
                                              code=code,
                                              transferable=transferable,
                                              level=level,
                                              temp=temp))
        return signers


class Creatory:
    """
    Factory class for creating Creator subclasses to create key pairs based on
    the provided algorithm.

    Usage: creator = Creatory(algo='salty').make(salt=b'0123456789abcdef')

    Attributes:

    Properties:

    Methods:
        .create is method to create key pair

    Hidden:
        ._create is method reference set to one of algorithm methods
        ._novelCreate
        ._indexCreate
    """

    def __init__(self, algo=Algos.salty):
        """
        Setup Creator.

        Parameters:
            algo is str code for algorithm

        """
        if algo == Algos.randy:
            self._make = self._makeNovel
        elif algo == Algos.salty:
            self._make = self._makeSalty
        else:
            raise ValueError("Unsupported creation algorithm ={}.".format(algo))

    def make(self, **kwa):
        """
        Returns Creator subclass based on inited algo
        """
        return (self._make(**kwa))


    def _makeNovel(self, **kwa):
        """

        """
        return RandyCreator(**kwa)

    def _makeSalty(self, **kwa):
        """

        """
        return SaltyCreator(**kwa)



class Manager:
    """
    Class for managing key pair creation, storage, retrieval, and message signing.

    Attributes:
        .keeper is Keeper instance (LMDB)
        .signers is dict of Signer instances keyed by public key cached signers

    Properties:


    Methods:


    Hidden:
    """
    def __init__(self, keeper=None):
        """
        Setup Creator.

        Parameters:
            keeper is Keeper instance (LMDB)

        """
        if keeper is None:
            keeper = Keeper()

        self.keeper = keeper
        self.signers = dict()


    def incept(self, icodes=None, icount=1, icode=coring.CryOneDex.Ed25519_Seed,
                     ncodes=None, ncount=1, ncode=coring.CryOneDex.Ed25519_Seed,
                     dcode=coring.CryOneDex.Blake3_256,
                     algo=Algos.salty, salt=None, level=None,
                     transferable=True, temp=False):
        """
        Returns duple (verfers, digers) for inception event where
            verfers is list of current public key verfers
                public key is verfer.qb64
            digers is list of next public key digers
                digest to xor is diger.raw

        Incept a prefix. Use first public key as temporary prefix.
        Must .repre later to move pubsit dict to correct permanent prefix.
        Store the dictified PubSit in the keeper under the first public key


        Parameters:
            icodes is list of private key derivation codes qb64 str
                one per incepting key pair
            icount is int count of incepting public keys when icodes not provided
            icode is str derivation code qb64  of all icount incepting public keys
                when icodes list not provided
            ncodes is list of private key derivation codes qb64 str
                one per next key pair
            ncount is int count of next public keys when icodes not provided
            ncode is str derivation code qb64  of all ncount next public keys
                when ncodes not provided
            dcode is str derivation code of next key digests
            algo is str key creation algorithm code
            salt is str qb64 random salt when salty algorithm used
            level is str security level code with salty algorithm used
            transferable is if each public key uses transferable code or not
                default is transferable special case is non-transferable
                not the same as if the derived identifier prefix is transferable
                the derived prefix is set elsewhere
            temp is temporary for testing it modifies level if salty algorithm

        When both ncodes is empty and ncount is 0 then the nxt is null and will
            not be rotatable (non-transferable prefix)

        """
        ridx = 0
        kidx = 0

        creator = Creatory(algo=algo).make(salt=salt, level=level)

        if not icodes:  # all same code, make list of len icount of same code
            icodes = [icode for i in range(icount)]

        isigners = creator.create(codes=icodes,
                                  ridx=ridx, kidx=kidx,
                                  transferable=transferable, temp=temp)
        verfers = [signer.verfer for signer in isigners]

        if not ncodes:  # all same code, make list of len ncount of same code
            ncodes = [ncode for i in range(ncount)]

        # count set to 0 to ensure does not create signers if ncodes is empty
        nsigners = creator.create(codes=ncodes, count=0,
                                  ridx=ridx+1, kidx=kidx+len(icodes),
                                  transferable=transferable, temp=temp)
        digers = [coring.Diger(ser=signer.verfer.qb64b) for signer in nsigners]

        if salt is None:  # assign proper default
            salt = creator.salt if hasattr(creator, 'salt') else ''

        if level is None:  # assign proper default
            level = creator.level if hasattr(creator, 'level') else coring.SecLevels.low

        dt = helping.nowIso8601()
        ps = PubSit(algo=algo, salt=salt, level=level,
                        new=PubLot(pubs=[verfer.qb64 for verfer in verfers],
                                   ridx=ridx, kidx=kidx, dt=dt),
                        nxt=PubLot(pubs=[signer.verfer.qb64 for signer in nsigners],
                                   ridx=ridx+1, kidx=kidx+len(icodes), dt=dt)
                    )

        pre = verfers[0].qb64b
        result = self.keeper.putSit(key=pre, val=json.dumps(asdict(ps)).encode("utf-8"))
        if not result:
            raise ValueError("Already incepted pre={}.".format(pre.decode("utf-8")))

        for signer in isigners:  # store secrets (private key val keyed by public key)
            self.keeper.putPri(key=signer.verfer.qb64b, val=signer.qb64b)
            self.signers[signer.verfer.qb64] = signer

        for signer in nsigners:  # store secrets (private key val keyed by public key)
            self.keeper.putPri(key=signer.verfer.qb64b, val=signer.qb64b)
            self.signers[signer.verfer.qb64] = signer

        return (verfers, digers)


    def repre(self, old, new):
        """
        Moves PubSit dict in keeper db from old pre to new pre db key
        Paraameters:
           old is str for old prefix of pubsit dict in keeper db
           new is str for new prefix to move pubsit dict to in keeper db
        """


    def rotate(self, pre, codes=None, count=1, code=coring.CryOneDex.Ed25519_Seed,
                     dcode=coring.CryOneDex.Blake3_256,
                     transferable=True, temp=False):
        """
        Returns duple (verfers, digers) for rotation event of keys for pre where
            verfers is list of current public key verfers
                public key is verfer.qb64
            digers is list of next public key digers
                digest to xor is diger.raw

        Rotate a prefix.
        Store the updated dictified PubSit in the keeper under pre

        Parameters:
            pre is str qb64 of prefix
            codes is list of private key derivation codes qb64 str
                one per next key pair
            count is int count of next public keys when icodes not provided
            code is str derivation code qb64  of all ncount next public keys
                when ncodes not provided
            dcode is str derivation code of next key digests
            transferable is if public key is transferable or not
                default is transferable special case is non-transferable
            temp is temporary for testing it modifies level if salty algorithm

        """
        rawsit = self.keeper.getSit(key=pre.encode("utf-8"))
        if rawsit is None:
            raise ValueError("Attempt to rotate nonexistent pre={}.".format(pre))

        ps = helping.datify(PubSit, json.loads(bytes(rawsit).decode("utf-8")))

        if not ps.nxt.pubs:  # empty nxt public keys so non-transferable prefix
            raise ValueError("Attempt to rotate nontransferable pre={}.".format(pre))

        old = ps.old  # save old so can clean out if rotate successful
        ps.old = ps.new  # move new to old
        ps.new = ps.nxt  # move nxt to new

        verfers = []  #  assign verfers from old nxt now new.
        for pub in ps.new.pubs:
            if pub in self.signers:
                verfers.append(self.signers[pub].verfer)
            else:
                verfer = coring.Verfer(qb64=pub)  # need for nontrans code
                raw = self.keeper.getPri(key=pub.encode("utf-8"))
                if raw is None:
                    raise ValueError("Missing prikey in db for pubkey={}".format(pub))
                pri = bytes(raw)
                signer = coring.Signer(qb64b=pri,
                                       transferable= not verfer.nontrans)
                verfers.append(signer.verfer)
                self.signers[pub] = signer


        creator = Creatory(algo=ps.algo).make(salt=ps.salt, level=ps.level)

        if not codes:  # all same code, make list of len count of same code
            codes = [code for i in range(count)]

        ridx = ps.new.ridx + 1
        kidx = ps.nxt.kidx + len(ps.new.pubs)

        # count set to 0 to ensure does not create signers if codes is empty
        signers = creator.create(codes=codes, count=0,
                                 ridx=ridx, kidx=kidx,
                                 transferable=transferable, temp=temp)
        digers = [coring.Diger(ser=signer.verfer.qb64b) for signer in signers]

        dt = helping.nowIso8601()
        ps.nxt = PubLot(pubs=[signer.verfer.qb64 for signer in signers],
                              ridx=ridx, kidx=kidx, dt=dt)

        result = self.keeper.setSit(key=pre.encode("utf-8"),
                                    val=json.dumps(asdict(ps)).encode("utf-8"))
        if not result:
            raise ValueError("Problem updating pubsit db for pre={}.".format(pre))

        for pub in old.pubs:  # remove old signers and old prikeys
            if pub in self.signers:
                del self.signers[pub]
                self.keeper.delPri(key=pub.encode("utf-8"))

        for signer in signers:  # store secrets (private key val keyed by public key)
            self.keeper.putPri(key=signer.verfer.qb64b, val=signer.qb64b)
            self.signers[signer.verfer.qb64] = signer

        return (verfers, digers)
