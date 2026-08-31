from app.modules.database import Database

if __name__ == '__main__':
    print('Creating or updating database tables...')
    Database.create_tables()
    print('Database setup completed successfully.')
