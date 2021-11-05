import discord
from discord.ext import commands
from mysqldb import the_database

from extra import utils
import os
from typing import List, Union, Optional


class FastestAnswersTable(commands.Cog):
    """ Category for the FastestAnswers table in the database. """

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client

    
    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def create_fastest_answers_table(self, ctx) -> None:
        """ Creates the FastestAnswers table in the database. """

        await ctx.message.delete()
        member: discord.Member = ctx.author
        if await self.check_fastest_answers_table_exists():
            return await ctx.send(f"**The `FastestAnswers` table already exists, {member.mention}!**")

        mycursor, db = await the_database()
        await mycursor.execute("""
            CREATE TABLE FastestAnswers (
                user_id BIGINT NOT NULL,
                language VARCHAR(50) NOT NULL,
                answer_time DECIMAL(5, 2),
                PRIMARY KEY (user_id, language, answer_time)
            )
        """)
        await db.commit()
        await mycursor.close()
        await ctx.send(f"**Successfully created the `FastestAnswers` table, {member.mention}!**")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def drop_fastest_answers_table(self, ctx) -> None:
        """ Drops the FastestAnswers table from the database. """

        await ctx.message.delete()
        member: discord.Member = ctx.author
        if not await self.check_fastest_answers_table_exists():
            return await ctx.send(f"**The `FastestAnswers` table doesn't exist, {member.mention}!**")

        mycursor, db = await the_database()
        await mycursor.execute("DROP TABLE FastestAnswers")
        await db.commit()
        await mycursor.close()
        await ctx.send(f"**Successfully dropped the `FastestAnswers` table, {member.mention}!**")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def reset_fastest_answers_table(self, ctx) -> None:
        """ Resets the FastestAnswers table in the database. """

        await ctx.message.delete()
        member: discord.Member = ctx.author
        if not await self.check_fastest_answers_table_exists():
            return await ctx.send(f"**The `FastestAnswers` table doesn't exist yet, {member.mention}!**")

        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM FastestAnswers")
        await db.commit()
        await mycursor.close()
        await ctx.send(f"**Successfully reset the `FastestAnswers` table, {member.mention}!**")

    async def check_fastest_answers_table_exists(self) -> bool:
        """ Checks whether the FastestAnswers table exists in the database. """

        mycursor, _ = await the_database()
        await mycursor.execute("SHOW STATUS LIKE 'FastestAnswers'")
        exists = await mycursor.fetchone()
        await mycursor.close()
        if exists:
            return True
        else:
            return False
    
    async def insert_fastest_answer(self, user_id: int, language: str, answer_time: float) -> None:
        """ Inserts an answer with its time into the database.
        :param user_id: The ID of the user who typed the answer.
        :param language: The language answer.
        :param answer_time: The time in which the answer was typed. """

        mycursor, db = await the_database()
        await mycursor.execute("INSERT IGNORE INTO FastestAnswers (user_id, language, answer_time) VALUES (%s, %s, %s)", (user_id, language, answer_time))
        await db.commit()
        await mycursor.close()

    async def get_fastest_answers(self) -> List[List[Union[int, str]]]:
        """ Gets all Fastest Answers. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM FastestAnswers") 
        answers = await mycursor.fetchall()
        await mycursor.close()
        return answers

    async def get_top_ten_fastest_answers(self) -> List[List[Union[int, str]]]:
        """ Gets all Fastest Answers. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM FastestAnswers ORDER BY answer_time DESC LIMIT 10") 
        answers = await mycursor.fetchall()
        await mycursor.close()
        return answers
