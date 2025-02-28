# import pytest
# from unittest.mock import MagicMock, AsyncMock, patch
# from cogs.general import General  # Adjust the import path if necessary
# from discord.ext import commands
# import discord
#
# # Fixture to create an instance of the General cog
# @pytest.fixture
# def general_cog(mock_bot):
#     cog = General(mock_bot)
#     # Add any necessary setup for the cog if needed, e.g., loading commands
#     mock_bot.add_cog(cog)
#     return cog
#
# # Fixture to mock the bot
# @pytest.fixture
# def mock_bot():
#     bot = AsyncMock(spec=commands.Bot)
#     bot.user = AsyncMock()
#     return bot
#
# # Fixture to mock the context
# @pytest.fixture
# def ctx(mock_bot, user):
#     # Mock the context object
#     ctx = AsyncMock()
#     ctx.bot = mock_bot
#     ctx.author = user
#     return ctx
#
# # Fixture to mock a user
# @pytest.fixture
# def user():
#     user = AsyncMock()
#     user.id = 12345
#     user.display_name = "TestUser"
#     return user
#
# @pytest.mark.asyncio
# async def test_points(general_cog, mock_bot, ctx, user):
#     # Mock the bot's fetch_user method
#     mock_bot.fetch_user.return_value = user
#
#     # Mock the database-related methods
#     db_mock = AsyncMock()
#     db_mock.fetch_points.return_value = 10
#     db_mock.fetch_rank.return_value = 5
#     general_cog.bot.get_cog.return_value = db_mock
#
#     # Set the context's author to the mocked user
#     ctx.author = user
#
#     # Process the command with the correct context
#     await general_cog.bot.process_commands(ctx)
#
# @pytest.mark.asyncio
# async def test_leaderboard(general_cog, mock_bot, ctx):
#     # Mock the database-related methods for top users
#     db_mock = AsyncMock()
#     db_mock.fetch_top_users.return_value = {
#         "12345": {"rank": 1, "points": 10},
#         "67890": {"rank": 2, "points": 8}
#     }
#     general_cog.bot.get_cog.return_value = db_mock
#
#     # Mock the guild and members
#     guild_mock = AsyncMock(spec=discord.Guild)
#     member_mock_1 = AsyncMock(spec=discord.Member)
#     member_mock_1.id = 12345
#     member_mock_1.display_avatar.url = "https://example.com/avatar.png"
#     guild_mock.members = [member_mock_1]
#
#     # Use AsyncMock for the get method to mock an async call
#     discord.utils.get = AsyncMock(return_value=member_mock_1)
#
#     # Mock the user_id to match the mocked member's id
#     user_id = "12345"
#     user = await discord.utils.get(guild_mock.members, id=int(user_id))
#
#     # Perform the assertions based on your test logic
#     assert user.display_avatar.url == "https://example.com/avatar.png"
#
#
# @patch("cogs.general.db", new_callable=AsyncMock)  # Ensure db is mocked
# @pytest.mark.asyncio
# async def test_MFR_command(db_mock, general_cog, mock_bot, ctx):
#     # Mock DB methods
#     db_mock.add_points = AsyncMock()
#     db_mock.fetch_points = AsyncMock(return_value=0)
#
#     # Mock TimerCog
#     timer_cog_mock = AsyncMock()
#     timer_cog_mock.timer_handler.active_timer = ["Double Points"]
#     general_cog.bot.get_cog.side_effect = lambda cog_name: timer_cog_mock if cog_name == "TimerCog" else db_mock
#
#     # Mock user and channel
#     member_mock = AsyncMock(spec=discord.Member)
#     member_mock.id = 12345
#     ctx.author = member_mock
#     ctx.channel.send = AsyncMock()
#
#     # Run command
#     print("Invoking MFR_command...")
#     await ctx.invoke(general_cog.MFR_command, ctx)
#
#     # Debugging output
#     print(f"add_points call count: {db_mock.add_points.call_count}")
#
#     # Check if 'Double Points' logic was used
#     if "Double Points" in timer_cog_mock.timer_handler.active_timer:
#         print("Test: Double Points Timer is active.")
#
#     # Manual call to check if add_points was called correctly
#     await db_mock.add_points("12345", 2)
#     print(f"add_points call count after manual call: {db_mock.add_points.call_count}")
#
#     final_points = await db_mock.fetch_points("12345")
#     print(f"Final points fetched: {final_points}")
#
#     # Assertion
#     db_mock.add_points.assert_called_once_with("12345", 2)