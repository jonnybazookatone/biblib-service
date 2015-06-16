"""
Models use to define the database

The database is not initiated here, but a pointer is created named db. This is
to be passed to the app creator within the Flask blueprint.
"""

import uuid
import base64
from datetime import datetime
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.types import TypeDecorator, CHAR, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID

db = SQLAlchemy()

class GUID(TypeDecorator):
    """
    Platform-independent GUID type.

    Uses Postgresql's UUID type, otherwise uses
    CHAR(32), storing as stringified hex values.

    Taken from http://docs.sqlalchemy.org/en/latest/core/custom_types.html
    ?highlight=guid#backend-agnostic-guid-type

    Does not work if you simply do the following:
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    as Flask cannot serialise UUIDs correctly.

    """
    # Refers to the class of type being decorated
    impl = CHAR

    @staticmethod
    def uuid_to_slug(_uuid):
        """
        Convert a UUID to a slug

        See a discussion about the details here:
        http://stackoverflow.com/questions/12270852/
        convert-uuid-32-character-hex-string-into-a-
        youtube-style-short-id-and-back
        :param _uuid: unique identifier for the library

        :return: base64 URL safe slug
        """
        return base64.urlsafe_b64encode(
            _uuid.bytes
        ).rstrip('=\n').replace('/', '_')

    @staticmethod
    def slug_to_uuid(_slug):
        """
        Convert a slug to a UUID

        See a discussion about the details here:
        http://stackoverflow.com/questions/12270852/
        convert-uuid-32-character-hex-string-into-a-
        youtube-style-short-id-and-back

        Keep in mind that base64 only works on bytes, and so they have to be
        encoded in ASCII. Flask uses unicode, and so you must modify the
         encoding before passing it to base64. This is fine, given we output
         all our encoded URLs for libraries as strings encoded in ASCII and do
         not accept any unicode characters.

        :param _slug: base64 URL safe slug

        :return: unique identifier for the library
        """
        print 'Converting slug', _slug

        return uuid.UUID(
            bytes=base64.urlsafe_b64decode(
                (_slug.replace('_', '/') + '==').encode('ascii')
            )
        ).__str__()

    @staticmethod
    def load_dialect_impl(dialect):
        """
        Load the native type for the database type being used
        :param dialect: database type being used

        :return: native type of the database
        """
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    @staticmethod
    def process_bind_param(value, dialect):
        """
        Format the value for insertion in to the database
        :param value: value of interest
        :param dialect: database type

        :return: value cast to type expected
        """
        if value is None:
            return value

        if isinstance(value, str):
            value = GUID.slug_to_uuid(value)

        if dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return '{0:.32x}'.format(uuid.UUID(value))
            else:
                # hexstring
                return '{0:.32x}'.format(value)

    @staticmethod
    def process_result_value(value, dialect):
        """
        Format the value when it is removed from the database
        :param value: value of interest
        :param dialect: database type

        :return: value cast to the type expected
        """
        if value is None:
            return value
        else:
            return GUID.uuid_to_slug(uuid.UUID(value))

    @staticmethod
    def compare_against_backend(dialect, conn_type):
        """
        Return True if the types are different,
        False if not, or None to allow the default implementation
        to compare these types
        :param dialect: database type
        :param conn_type: type of the field

        :return: boolean
        """
        if dialect.name == 'postgresql':
            return isinstance(conn_type, UUID)
        else:
            return isinstance(conn_type, String)

class MutableList(Mutable, list):
    """
    The PostgreSQL type ARRAY cannot be mutated once it is set. This hack is
    written by the author of SQLAlchemy as a solution. For further reading,
    see:

    https://groups.google.com/forum/#!topic/sqlalchemy/ZiDlGJkVTM0

    and

    http://kirang.in/2014/08/09/
    creating-a-mutable-array-data-type-in-sqlalchemy
    """
    def append(self, value):
        """
        Define an append action
        :param value: value to be appended

        :return: no return
        """

        list.append(self, value)
        self.changed()

    def remove(self, value):
        """
        Define a remove action
        :param value: value to be removed

        :return: no return
        """

        list.remove(self, value)
        self.changed()

    def extend(self, value):
        """
        Define an extend action
        :param value: list to extend with

        :return: no return
        """
        list.extend(self, value)
        self.changed()

    def shorten(self, value):
        """
        Define a shorten action. Opposite to extend

        :param value: values to remove

        :return: no return
        """
        for item in value:
            self.remove(item)

    def upsert(self, value):
        """
        Add values that do not exist in the current list
        :param value:
        :return:
        """
        value = list(set(value))
        value = [item for item in value if item not in list(self)]

        self.extend(value)

    @classmethod
    def coerce(cls, key, value):
        """
        Re-define the coerce. Ensures that a class deriving from Mutable is
        always returned

        :param key:
        :param value:

        :return:
        """
        if not isinstance(value, MutableList):
            if isinstance(value, list):
                return MutableList(value)
            return Mutable.coerce(key, value)
        else:
            return value


class User(db.Model):
    """
    User table
    Foreign-key absolute_uid is the primary key of the user in the user
    database microservice.
    """
    __bind_key__ = 'libraries'
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    absolute_uid = db.Column(db.Integer, unique=True)
    permissions = db.relationship('Permissions',
                                  backref='user')

    def __repr__(self):
        return '<User {0}, {1}>'\
            .format(self.id, self.absolute_uid)


class Library(db.Model):
    """
    Library table
    This represents a collection of bibcodes, a biblist, and can be thought of
    much like a bibtex file.
    """
    __bind_key__ = 'libraries'
    __tablename__ = 'library'
    id = db.Column(GUID, primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(50))
    description = db.Column(db.String(50))
    public = db.Column(db.Boolean)
    bibcode = db.Column(MutableList.as_mutable(ARRAY(db.String(50))),
                        default=[])
    date_created = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    date_last_modified = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    permissions = db.relationship('Permissions',
                                  backref='library',
                                  cascade='delete')

    # @hybrid_property
    # def id(self):
    #     """
    #     Convert the ID to a URL safe slug
    #     """
    #     return Library.uuid_to_slug(self._id)
    #
    # @id.setter
    # def id(self, id):
    #     self._id = Library.slug_to_uuid(id)

    def __repr__(self):
        return '<Library, library_id: {0} name: {1}, ' \
               'description: {2}, public: {3},' \
               'bibcode: {4}>'\
            .format(self.id,
                    self.name,
                    self.description,
                    self.public,
                    self.bibcode)


class Permissions(db.Model):
    """
    Permissions table

    Logically connects the library and user table. Whereby, a Library belongs
    to a user, and the user can give permissions to other users to view their
    libraries.
    User (1) to Permissions (Many)
    Library (1) to Permissions (Many)
    """
    __bind_key__ = 'libraries'
    __tablename__ = 'permissions'
    id = db.Column(db.Integer, primary_key=True)
    read = db.Column(db.Boolean, default=False)
    write = db.Column(db.Boolean, default=False)
    admin = db.Column(db.Boolean, default=False)
    owner = db.Column(db.Boolean, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    library_id = db.Column(GUID, db.ForeignKey('library.id'))

    def __repr__(self):
        return '<Permissions, user_id: {0}, library_id: {1}, read: {2}, '\
               'write: {3}, admin: {4}, owner: {5}'\
            .format(self.user_id, self.library_id, self.read, self.write,
                    self.admin, self.owner)
