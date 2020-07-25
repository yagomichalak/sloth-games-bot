import mysql.connector
from mysql.connector import Error
import random
from time import sleep

while True:
    n = random.random()
    #Generate 1 random number between 10 and 30
    randomlist = random.sample(range(-50, 50), 1)
    #print(randomlist)

    try:
        connection = mysql.connector.connect(host='localhost',
                                             database='tmp',
                                             user='root',
                                             password='')

        mySql_insert_query = """INSERT INTO temperatuur (graden, datum) 
                               VALUES (%s, CURRENT_DATE) """

        records_to_insert = [(randomlist)]

        cursor = connection.cursor()
        cursor.executemany(mySql_insert_query, records_to_insert)
        connection.commit()
        print(cursor.rowcount, "Record inserted successfully into temperatuur table")

    except mysql.connector.Error as error:
        print("Failed to insert record into MySQL table {}".format(error))

    finally:
        if (connection.is_connected()):
            cursor.close()
            connection.close()
            print("MySQL connection is closed")
        sleep(30)