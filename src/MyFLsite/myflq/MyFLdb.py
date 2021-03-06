#!/bin/env python3

## Implementing a database for STRs and SNPs

#Database functions
def login(user="""admin""", passwd="""passall""" ,database='', test=False):
    """
    Returns the formed connection with the db using variablenames: conn, sql
    If test: just tests the connection, and closes it again returning None. 
        An exception should be raised automatically 
        if there's a problem with the connection.
    """
    try: import pymysql as MySQLdb
    except ImportError: import MySQLdb #py2#
    conn = MySQLdb.connect(host = "localhost",
                           user = user,
                           passwd = passwd,
                           db = database)
    #conn.autocommit(True)
    sql = conn.cursor(MySQLdb.cursors.DictCursor)
    #sql.connection().autocommit(True)
    if not test: return (conn,sql)
    else: logout(conn, sql)

def logout(conn,sql):
    """
    Logout from the database connection
    """
    sql.close()
    conn.commit()
    conn.close()

def dbBackup(backupfile='strdb.sql',restore=True,flush=False):
    """
    Backup database
    If flush == 'onlyFlush', no backup is made, but all the tables are emptied.
    """
    import os
    if flush != 'onlyFlush':
        if python2: input = raw_input
        if not backupfile.startswith('/'): backupfile='mysql/'+backupfile
        if restore: os.system('mysql -uroot -p'+input('Password: ')+
                              ' strdb < '+backupfile)
        else: os.system('mysqldump -uroot -p'+input('Password: ')+
        ' strdb > '+backupfile)
    if flush:
        conn,sql=login()
        sql.execute('''TRUNCATE BASElocustrack; TRUNCATE BASEseqs; 
                       TRUNCATE BASEstat; TRUNCATE BASEtech; 
                       TRUNCATE LOCIalleles; TRUNCATE LOCIalleles_CE; 
                       TRUNCATE LOCIconflicts; TRUNCATE LOCIkits; 
                       TRUNCATE LOCInames; ''')
        logout(conn,sql)


#To rebuild all tables, drop them all -- Use with care
def dropTables(sql):
    tables = ('BASEseqs','BASEnames','BASEprimersets','BASEqual','BASEtrack',
              'BASEstat','laboratories','LOCInames','LOCIalleles','LOCIalleles',
              'LOCIalleles_CE','LOCIconflicts')
    for table in tables: sql.execute ("DROP TABLE "+table)


#Create tables
def makeTables(sql):
    #Tables for basic sequence input
        #When a sequence gets added at the very least BASEstat and
        #BASEtrack will have to be updated
    sql.execute ("""
    CREATE TABLE IF NOT EXISTS BASEseqs (
    `seqID` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `sequence` TEXT(1000) NOT NULL 
             COMMENT 'sequence of allele, error sequence or primer'
    )
    COMMENT 'All sequences are maintained here, ref to seqID in other tables';
         """)    
    sql.execute ("""
    CREATE TABLE IF NOT EXISTS BASEnames (
    `locusName` CHAR(40) NOT NULL PRIMARY KEY 
              COMMENT  'the name of the locus: mandatory',
    `locusType` INT NULL 
        COMMENT 'repeatsize if STR, 0 for SNP, NULL unknown locusType',
    `ref_alleleNumber` CHAR(10) 
      COMMENT  'If STR, repeat nr of the ref seq: e.g. 4.1 = 4 r, 1 extra bp',
    `ref_seqID` INT COMMENT  'optional ref sequence ID in BASEseqs',
     FOREIGN KEY (`ref_seqID`) REFERENCES BASEseqs (`seqID`) ON DELETE CASCADE,
    `mask_seqID` INT COMMENT  'optional ref mask seq ID in BASEseqs',
     FOREIGN KEY (`mask_seqID`) REFERENCES BASEseqs (`seqID`) ON DELETE CASCADE
    )
    COMMENT 'table with loci names config info that are used in the database';
         """)
    sql.execute ("""
    CREATE TABLE IF NOT EXISTS BASEprimersets (
    `primersetID` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `locusName` CHAR(40) NOT NULL 
           COMMENT  'this is the reference to table BASEnames',
    `forwardP` INT NOT NULL COMMENT  'forward primer id from BASEseqs',
    `reverseP` INT NOT NULL COMMENT  'reverse primer id from BASEseqs',
    
    FOREIGN KEY (`locusName`) REFERENCES BASEnames (`locusName`) 
                                                   ON DELETE CASCADE,
    FOREIGN KEY (`forwardP`) REFERENCES BASEseqs (`seqID`),
    FOREIGN KEY (`reverseP`) REFERENCES BASEseqs (`seqID`)    
    )
    COMMENT 'table with all the primersets in use per locus';
         """)
    sql.execute ("""
    CREATE TABLE IF NOT EXISTS BASEqual (
    `qualID` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `technology` CHAR(40) COMMENT 'technology used, e.g. Illumina',
    `filterLevel` DOUBLE (5,4) 
        COMMENT  'filterlevel for (error) seqs, format: 0.x, e.g. 0.01 (=1%)'
    )
    COMMENT 'table with information how sequences were retrieved';
         """)
    sql.execute ("""
    CREATE TABLE IF NOT EXISTS laboratories (
    `labID` CHAR(40) NOT NULL UNIQUE KEY COMMENT  'id of submitting laboratory',
    `passphrase` CHAR(200) NOT NULL
    )
    COMMENT 'Laboratories submitting to current database - for quality control';
         """)
    sql.execute("""INSERT INTO laboratories (labID,passphrase) VALUES ("NA","NA");""")
    sql.execute ("""
    CREATE TABLE IF NOT EXISTS BASEtrack (
    `entryID` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `locusName` CHAR(40) NOT NULL, FOREIGN KEY (`locusName`) 
        REFERENCES BASEnames (`locusName`),
    `qualID` INT NOT NULL COMMENT  'this is the reference to table BASEqual',
        FOREIGN KEY (`qualID`) REFERENCES BASEqual (`qualID`) ON DELETE CASCADE,
    `labID` CHAR(40) NOT NULL COMMENT  'id submitting laboratory',
        FOREIGN KEY (`labID`) REFERENCES laboratories (`labID`) 
                      ON DELETE CASCADE,
    `validated` BOOLEAN NOT NULL DEFAULT '0' COMMENT  'at least 1 valid allele',
    `manualRevision` BOOLEAN NOT NULL DEFAULT '0' COMMENT  'manual validation',
    `nrSeqs` INT NOT NULL COMMENT  'number of sequences submitted',
    `nrReads` INT NOT NULL COMMENT  'total number reads of the submitted seq',
    `population` CHAR(100) DEFAULT 'NA' COMMENT  'generic origin of sample',
    `entryTime` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    COMMENT 'tracks each submission of sequences to the database';
         """)
    sql.execute ("""
    CREATE TABLE IF NOT EXISTS BASEstat (
    `entryID` INT NOT NULL 
     COMMENT  'this is the reference to the BASEtrack table',
     FOREIGN KEY (`entryID`) REFERENCES BASEtrack (`entryID`) ON DELETE CASCADE,
    `seqID` INT NOT NULL 
     COMMENT  'this is the reference to the sequence in table BASEseqs',
     FOREIGN KEY (`seqID`) REFERENCES BASEseqs (`seqID`) ON DELETE CASCADE,
    `primersetID` INT NULL COMMENT 'primers with which seq was sequenced',
        FOREIGN KEY (`primersetID`) REFERENCES BASEprimersets (`primersetID`),
    `validated` INT DEFAULT '-1'
        COMMENT '-1 not validated, 0 valid., > 0 if valid. error seq. In last case int is reference seqID',
    `alleleValidation` CHAR(10)
        COMMENT 'e.g. for STR: "10.1" or "10.1:4" => allele nr 10.1, :4 => repeat size 4; e.g. SNP "SNP:allele info"',
    `seqCount` BIGINT NOT NULL COMMENT 'number of reads with this sequence'
    )
    COMMENT 'stats on each submitted sequence';
         """)
    
    #Tables for processing loci and profiles
    sql.execute ("""
    CREATE TABLE IF NOT EXISTS LOCInames (
    `locusName` CHAR(40) NOT NULL UNIQUE KEY COMMENT 'id of the locus',
    `locusType` INT NOT NULL DEFAULT '0' COMMENT  'repeatsize if STR, else 0',
    `refseq` TEXT(1000) NOT NULL COMMENT 'reference sequence for the locus',
    `ref_forwardP` CHAR(40) COMMENT  'reference forward primer',
    `ref_reverseP` CHAR(40) COMMENT  'reference reverse primer',
    `flank_forwardP` TEXT(1000) COMMENT 'forward flanking (without primer seq)',
    `flank_reverseP` TEXT(1000) COMMENT 'reverse flanking (without primer seq)',
    `ref_length` INT 
     COMMENT 'length based on the flanking sequences, not including them',
    `ref_alleleNumber` CHAR(10) 
        COMMENT  'If STR, STR number of the ref seq: e.g. 4.1 = 4 r, 1 extra bp'
    )
    COMMENT 'this table is used directly for the analysis of unknown samples';
         """)
    sql.execute ("""
    CREATE TABLE IF NOT EXISTS LOCIkits (
    `kitName` CHAR(40) NOT NULL COMMENT 'name of the sequencing kit',
    `locusName` CHAR(40) NOT NULL COMMENT 'id for a locus from LOCInames',
    UNIQUE (kitName,locusName)
    )
    COMMENT 'kits that can be used for analysis of unknown samples';
         """)
    sql.execute ("""
    CREATE TABLE IF NOT EXISTS LOCIalleles (
    `locusName` CHAR(40) NOT NULL 
     COMMENT 'identification of the locus in table LOCInames',
    `alleleNumber` DOUBLE (4,1) 
     COMMENT 'a number is not required for non STRs like amelogenine',
    `alleleNomen` CHAR(100) COMMENT 'allele nomenclature entry',
    `alleleSeq` TEXT(1000) NOT NULL 
     COMMENT 'allele sequence for the locus, between the flanking seqs',
    `freqOK` BOOLEAN NOT NULL DEFAULT '0' 
        COMMENT  'sign allele population for calculating profile probability',
    `popFrequency` FLOAT COMMENT  'population frequency of the allele'
    )
    COMMENT 'all the alleles that were used for determining flanks';
         """)
    sql.execute ("""
    CREATE TABLE IF NOT EXISTS LOCIalleles_CE (
    `locusName` CHAR(40) NOT NULL 
     COMMENT 'identification of the locus in table LOCInames',
    `alleleNumber` DOUBLE (4,1) 
     COMMENT 'a number is not required for non STRs like amelogenine',
    `alleleNomen` CHAR(100) COMMENT 'allele nomenclature entry',
    `popFrequency` FLOAT NOT NULL 
     COMMENT  'capillary electrophoresis population frequency of the allele',
    UNIQUE (locusName,alleleNumber)
    );
         """)
    sql.execute ("""
    CREATE TABLE IF NOT EXISTS LOCIconflicts (
    `locusName` CHAR(40) NOT NULL 
        COMMENT 'id of a locus with conflicting validation info in LOCInames',
    `validConflict` CHAR(40) NOT NULL COMMENT 'nature of validation conflict'
    );
         """)

#Create views and functions
#sql.execute('DROP VIEW BASEcombined;')
def makeViews(sql):
    sql.execute ("""
    CREATE VIEW BASEcombined AS 
           SELECT BASEnames.locusName,forwardP,reverseP,seqID,alleleValidation 
           FROM BASEnames
           JOIN BASEtrack USING (locusName) 
           JOIN BASEstat USING (entryID)
           JOIN BASEprimersets USING (primersetID);
         """)

def makeFunctions(sql):
    sql.execute("""
                CREATE FUNCTION getSeq (primer INT)
                RETURNS TEXT(1000) DETERMINISTIC
                RETURN (SELECT sequence FROM BASEseqs WHERE seqID = primer);
                """)
    #READS SQL DATA


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=
                            'Add a user, or database for the MyFLq application')
    parser.add_argument('user',
                        help='User for which a database will be created')
    parser.add_argument('db',nargs='*',help='Database[s] to create')
    parser.add_argument('-p','--password',
                help='MySQL user password (if not provided, will be asked for)')
    parser.add_argument('--delete', action="store_true",
                        help='Delete database[s] instead')
    parser.add_argument('--delete-user', action="store_true",
                        help='Delete user instead')
    parser.add_argument('--install', action="store_true", 
                        help='No longer implemented => use sed -i ...')
    args = parser.parse_args()
    if not args.password:
        import getpass
        try: args.password = getpass.getpass(
                'MySQL password for '+args.user+': ')
        except EOFError: args.password = input(
                'MySQL password for '+args.user+': ')
    else:
        #Check if user and password match
        #=> if user is authorised to make or change MyFLq databases
        conn,sql = login()
        sql.execute("""
        SELECT User FROM mysql.user WHERE User = %s;
        """,(args.user,))
        if not sql.rowcount:
            sql.execute("CREATE USER %s@'localhost' IDENTIFIED BY %s;",
                        (args.user,args.password))
        if not (args.delete or args.delete_user):
            for db in args.db:
                sql.execute("CREATE DATABASE "+db+";")
                sql.execute("GRANT ALL ON "+db+
                            ".* TO %s@'localhost';",(args.user,))
            
            #Make tables
            for db in args.db:
                sql.execute("USE "+db+";")
                makeTables(sql)
                makeViews(sql)
                makeFunctions(sql)
        elif args.delete_user:
            sql.execute("SELECT Db FROM mysql.db WHERE User = %s;", (args.user,))
            for db in sql.fetchall():
                db = db['Db']
                sql.execute("DROP DATABASE "+db.decode()+";")
                        #The mysql.'tables' return b'' strings
            sql.execute("DROP USER '"+args.user+"'@'localhost'")

        elif args.delete:
            for db in args.db:
                login(user=args.user,passwd=args.password,database=db,test=True)
                sql.execute("DROP DATABASE "+db+";")
        logout(conn,sql)
            
    #print(args) #debug    
