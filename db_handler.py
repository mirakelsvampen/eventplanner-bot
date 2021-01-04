from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, create_engine, ForeignKey, Boolean, Sequence
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists
from sqlalchemy.exc import IntegrityError, InvalidRequestError

import logging

logging.basicConfig(
        level=logging.DEBUG,
        filename='backend_logs.log', 
        format='%(asctime)s - %(process)s - %(module)s -  %(levelname)s - %(message)s'
    )

Base = declarative_base()

class Members( Base ):
    __tablename__ = 'members'

    id = Column(String(64), primary_key=True)
    name = Column(String(50))
    mysql_engine = 'InnoDB'

class Lobby( Base ):
    __tablename__ = 'lobby'

    id = Column(String(64), primary_key=True)
    name = Column(String(50))
    date = Column(DateTime)
    size = Column(Integer())
    mysql_engine = 'InnoDB'

class Participants( Base ):
    __tablename__ = 'participants'
    row_id = Column(
        Integer(), Sequence('row_id', start=0, increment=1), primary_key=True
    )
    memid = Column(String(64), ForeignKey('members.id'), nullable=False)
    lobbyid = Column(String(64), ForeignKey('lobby.id'), nullable=False)
    leader = Column(String(50))
    mysql_engine = 'InnoDB'

class MyDatabase():
    """
        Return a database handler object which can be used for working with database entries.
        If the given database name argument is not found then the database shall be created.
    """

    def __init__(self, user, password, ip, port, db_name, debug=False):
        try:
            url = "mysql+mysqldb://%s:%s@%s:%s/%s" % (
                user, password,
                ip, port,
                db_name
            )
        except Exception as err:
            logging.exception("Exception occurred: %s" % (err))

        # configure Session class with desired options
        Session = sessionmaker()
        # create the url (database) if it does not exist
        # and associate it with a sql_alchemy engine.
        if not database_exists(url): 
            logging.debug('database not found, creating a new one named: %s' % (db_name))
            create_database(url)
            engine = (create_engine(url))

            logging.debug('populating %s with tables...' % (db_name))
            Base.metadata.create_all(engine)
            logging.debug('done populating %s with tables!' % (db_name))
        else:
            engine = (create_engine(url))
            
        # associate the created engine with our custom Session class
        Session.configure(bind=engine)
        # work with the session and make it available to all methods
        self.session = Session()

    def transact(self, data):
        """
            Translate passed data into sqlalchemy objects and prepare them for further processing.
            returns a list of objects which can be used by Session().
        """
        transactions = list()
        if data['settings']['member']['id']:
            logging.debug('Preparing member entries...')
            transactions.append(Members(**data['settings']['member']))

        if data['settings']['lobby']['id']:
            logging.debug('Preparing lobby entries...')
            transactions.append(Lobby(**data['settings']['lobby']))

        if data['settings']['participations']['memid'] and data['settings']['participations']['lobbyid']:
            logging.debug('Preparing participation entries...')
            transactions.append(Participants(**data['settings']['participations']))

        call_transaction = getattr(self, data['method'])
        logging.debug('Calling transaction with: %s' % (call_transaction))
        call_transaction(transactions)

    def select_member(self, member_name):
        """
            Get the member id for a given name
        """
        return self.session.query(Members).filter(Members.name == member_name)[0]
    
    def has_no_leader(self, lobby_id):
        """
            Check if a leader is missing in a single given lobby
        """
        has_no_leader = True
        result = self.session.query(Participants).filter(
            Participants.lobbyid == lobby_id 
        )
        if result.all():
            has_no_leader = False
        return has_no_leader

    def select_lobbies(self, member=False, name=False):
        """
            Gather all existing lobbies, if member is false then all
            lobbies are fetched. Else the scope is narrowed down to the member
        """
        existing_lobbies = dict()

        if member and not name: # All lobbies which a member participates in
            scope = self.session.query(Lobby).filter(
                Lobby.id == Participants.lobbyid, Participants.memid == member
            )
        elif name and member: # All lobbies which match "name" and which "member" partakes in. 
            scope = self.session.query(Lobby).filter(
                Lobby.name == name, Lobby.id == Participants.lobbyid, Participants.memid == member
            )
        elif not member and not name:
            scope = self.session.query(Lobby).all()

        if scope:
            for lobby in scope:
                existing_lobbies[lobby.id] = {
                    'name':lobby.name,
                    'date':lobby.date,
                    'participant':list(),
                    'size':lobby.size
                }
                for participant in self.session.query(Participants).filter(Participants.lobbyid == lobby.id):
                    for leader in self.session.query(Members).filter(Members.id == participant.leader):
                        existing_lobbies[lobby.id]['leader'] = leader.name
                    
                    for member in self.session.query(Members).filter(Members.id == participant.memid):
                        existing_lobbies[lobby.id]['participant'].append(member.name)
        return existing_lobbies
                
    def create(self, data):
        
        """
            Append data to a database. The argument "db_name" qeuals equals the database which 
            shall be opened. Tables are appended depending on what fields are True in the passed argument(type dict())
        """

        try:
            for insertion in data:
                logging.debug('Method - CREATE - object: %s' % (insertion))
                self.session.add(insertion)
                self.session.commit()
        except (IntegrityError, InvalidRequestError) as err:
            # this might be a bit risky since it catches all IntegrityError and InvalidRequestErrors
            # this was implemented to avoid crashes when duplicate data is to be transmitted to the database.
            pass

    def modify(self, data):
        
        """
            Append data to a database. The argument "db_name" qeuals equals the database which 
            shall be opened. 
        """
        pass

    def delete_particiant_from_lobby(self, lobby_id, member_id):
        row = self.session.query(Participants).filter(
            Participants.memid == member_id, Participants.lobbyid == lobby_id
        )
        d = row.delete() # return the count of rows matched as returned by the database’s “row count” feature.
        logging.debug("removing %s from %s" % (member_id, lobby_id))
        self.session.commit()
        return d

    def delete_lobby(self, lobby_id):
        """
            Delete a lobby from database
        """
        lobby = self.session.query(Lobby).filter(
            Lobby.id == lobby_id
        )
        logging.debug("Deleting lobby %s because it has no leader" % (lobby_id))
        d_lobby = lobby.delete()
        self.session.commit()


class DataForm( object ):
    """
        "Renders" a template with provided data which then can be passed to database
    """
    def __init__(self, method):
        ALLOWED_METHODS = list(
            [
                'create',
                'delete',
                'modify',
            ]
        )
        if method in ALLOWED_METHODS:
            self.method = method
            self.member = False
            self.memid = False
            self.lobby = False
            self.date = False
            self.lobbyid = False
            self.lobby_size = False
            self.participation_member = False
            self.participation_lobby = False
            
        else:
            raise Exception('No valid argument given to parameter "method". Allowed values: create, delete or modify.')
            
    def render(self):
        """
            render all attributes into json/dictionary.
        """
        return {
            'method':self.method,
            'settings': {
                'member':{
                    'id': self.memid,
                    'name': self.member
                },
                'lobby':{
                    'id': self.lobbyid,
                    'name': self.lobby,
                    'date': self.date,
                    'size': self.lobby_size
                },
                'participations':{
                    'memid': self.participation_member,
                    'lobbyid':self.participation_lobby,
                    'leader': self.participation_member
                }
            }
        }


if __name__ == '__main__':
    # Debuging section
    # TODO: Testing mode, check out assertions
    from datetime import datetime
    from pprint import pprint

    #db_name = ''.join(names.get_full_name().split(' '))
    #print('using db name: %s' % (db_name))

    db_settings = {
            'ip':'127.0.0.1',
            'port':'3306',
            'user':'root',
            'password':'Syp9393',
            'db_name':'BotTest',
            'debug':False
        }

    db = MyDatabase(**db_settings)
    db.select()


    # create_settings = DataForm('create')
    # modify_settings = DataForm('modify')
    # remove_settings = DataForm('delete')

    # # TEST: Adding a new lobby
    # data = data_form(lobbyid=random.getrandbits(64), lobby='testlobby', date=datetime.now(), method='create')
    # pprint('TEST - Creating a new lobby: %s' % (data))
    # db.transact(data)

    # # TEST: Adding member to database
    # data = data_form(memid='146673512923267274', member='Mirakelsvampen', method='create')
    # pprint('TEST - Creating a new member: %s' % (data))
    # db.transact(data)

    # TEST: Create participation entry
    # create_settings.participation_member = '146673512923267074'
    # create_settings.participation_lobby = '266541615822941422'
    # data01 = create_settings.render()
    # pprint('TEST - Create participation entry: %s' % (data01))
    # db.transact(data01)

    # TEST: Adding a new member to existing lobby

    # TEST: Deleting a lobby

    # TEST: Promoting a another participant to leader of a lobby
