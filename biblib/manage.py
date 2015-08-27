"""
Alembic migration management file
"""

from flask import current_app
from flask.ext.script import Manager, Command, Option
from flask.ext.migrate import Migrate, MigrateCommand
from models import db, User, Permissions, Library
from app import create_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

# Load the app with the factory
app = create_app()

class CreateDatabase(Command):
    """
    Creates the database based on models.py
    """
    @staticmethod
    def run(app=app):
        """
        Creates the database in the application context
        :return: no return
        """
        with app.app_context():
            db.create_all()
            db.session.commit()

class DestroyDatabase(Command):
    """
    Creates the database based on models.py
    """
    @staticmethod
    def run(app=app):
        """
        Creates the database in the application context
        :return: no return
        """
        with app.app_context():
            db.drop_all()
            # db.session.remove()

class DeleteStaleUsers(Command):
    """
    Compares the users that exist within the API to those within the
    microservice and deletes any stale users that no longer exist. The logic
    also takes care of the associated permissions and libraries depending on
    the cascade that has been implemented.
    """
    @staticmethod
    def run(app=app):
        """
        Carries out the deletion of the stale content
        """
        with app.app_context():

            # Obtain the list of API users
            api_engine = create_engine(
                current_app.config['BIBLIB_ADSWS_API_DB_URI']
            )
            api_session_maker = scoped_session(sessionmaker(bind=api_engine))
            api_session = api_session_maker()

            postgres_search_text = 'SELECT id FROM users;'
            result = api_session.execute(postgres_search_text).fetchall()
            list_of_api_users = [int(r[0]) for r in result]

            api_session.close()

            # Loop through every use in the service database
            removal_list = []
            for service_user in User.query.all():
                if service_user.absolute_uid not in list_of_api_users:
                    try:
                        # Obtain the libraries that should be deleted
                        libraries, permissions = db.session.query(
                            Permissions, Library
                        ).join(Permissions.library)\
                            .filter(Permissions.user_id == service_user.id)\
                            .all()

                        # Delete all the libraries found
                        # By cascade this should delete all the permissions
                        [db.session.delete(library) for library in libraries]
                        db.session.delete(service_user)
                    except Exception as error:
                        current_app.logger.info('Problem with database: {0}'
                                                .format(error))
                        db.session.rollback()
            db.session.commit()


# Set up the alembic migration
migrate = Migrate(app, db, compare_type=True)

# Setup the command line arguments using Flask-Script
manager = Manager(app)
manager.add_command('db', MigrateCommand)
manager.add_command('createdb', CreateDatabase())
manager.add_command('destroydb', DestroyDatabase())
manager.add_command('syncdb', DeleteStaleUsers())

if __name__ == '__main__':
    manager.run()
