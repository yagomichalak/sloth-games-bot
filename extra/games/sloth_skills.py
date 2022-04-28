import discord
from discord.ext import commands
from mysqldb import the_database

from typing import List,Union
from extra import utils

class SlothSkillsTable:
    """ Class for the SlothSkills table in the database. """

    def __init__(self) -> None:
        """ Class init method. """

        pass

    async def update_quest(self, user_id: int, quest_number: int) -> None:
        """ Updates an on-going quest for a member.
        :param user_id: The ID of the user who's updating the quest.
        :param quest_number: The quest number. """

        current_ts = await utils.get_timestamp()

        # Gets Quest
        quest = await self.get_skill_action_by_user_id_and_skill_type(user_id=user_id, skill_type="quest")
        if not quest:
            return

        if quest[7] != quest_number:
            return

        int_content: int = quest[9] + 1
        if int_content <= 5:
            await self.update_sloth_skill_int_content(user_id=user_id, int_content=int_content, current_ts=current_ts)


    async def get_skill_action_by_user_id_and_skill_type(
        self, user_id: int, skill_type: str, multiple: bool = False
    ) -> Union[List[List[Union[int, str]]], List[Union[int, str]], bool]:
        """ Gets a skill action by user ID and skill type.
        :param user_id: The user ID with which to get the skill action.
        :param skill_type: The skill type of the skill action. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM SlothSkills WHERE user_id = %s and skill_type = %s", (user_id, skill_type))
        if multiple:
            skill_actions = await mycursor.fetchall()
        else:
            skill_actions = await mycursor.fetchone()
        await mycursor.close()
        return skill_actions

    async def update_sloth_skill_int_content(self, user_id: int, int_content: int, current_ts: int) -> None:
        """ Updates the integer content of a SlothSkill.
        :param user_id: The user ID.
        :param int_content: The integer content.
        :param current_ts: The current timestamp. """

        mycursor, db = await the_database()
        await mycursor.execute("""
            UPDATE SlothSkills SET edited_timestamp = %s, int_content = %s 
            WHERE user_id = %s""", (current_ts, int_content, user_id))
        await db.commit()
        await mycursor.close()
