from global_functions import *

def build_query(guild_id, game_name, min_date, max_date, user_nm=None):
    
    # Initialize the parameters list
    query_params = []

    # Add common parameters
    query_params.append(guild_id)
    query_params.extend([min_date, max_date])  # These are needed in every query

    is_date_range = False if min_date == max_date else True

    # all games, winners only, single date
    if game_name == 'winners' and min_date == max_date:
        cols = ['Game', 'Winner', 'Score']
        query = f"""
            SELECT 
                game_name,
                player_name,
                game_score
            FROM game_view
            WHERE guild_id = %s
            AND game_date BETWEEN %s AND %s
            and game_rank = 1
            ORDER BY game_name, game_date desc;
        """
    
    # all games, winners only, range of dates
    elif game_name == 'winners' and is_date_range:
        cols = ['Game', 'Leader', 'Points', 'Avg', 'Played']
        query = f"""
            SELECT 
	            game_name,
                player_name,
                points,
                avg_score,
                games_played
            FROM
                    (
                    SELECT
                        x.game_name,
                        dense_rank() over(partition by game_name order by points desc) as overall_rank,
                        x.player_name,
                        x.points,
                        x.avg_score,
                        x.games_played
                    FROM
                            (
                            SELECT 
                                game_name,
                                player_name,
                                sum(points) as points,
                                sum(1) as games_played,
                                round(avg(seconds), 1) as avg_score
                            FROM game_view
                            WHERE guild_id = %s
                            AND game_date BETWEEN %s AND %s
                            GROUP BY 1,2
                            ) x
                    ) z
            where z.overall_rank = 1
        """

    # all games: single user, single date ## technically this will run with multiple dates FIX IT
    elif game_name == 'my_scores':
        cols = ['Game', 'Player', 'Score', 'Rank']
        query = f"""
            SELECT 
                game_name,
                player_name,
                game_score,
                game_rank
            FROM game_view
            WHERE guild_id = %s
            AND game_date BETWEEN %s AND %s
            AND member_nm = %s
            ORDER BY game_name, game_date desc;
        """
        query_params.append(user_nm)

    # specific game, single date, today
    elif min_date == max_date and max_date == get_today().strftime("%Y-%m-%d"):
        cols = ['Rank', 'Player', 'Score', 'Points']
        query = f"""
            SELECT 
                game_rank,
                player_name,
                game_score,
                points
            FROM leaderboard_today
            WHERE guild_id = %s
            AND game_date BETWEEN %s AND %s
            AND game_name = %s
        """
        query_params.append(game_name)

    # specific game, single date, not today
    elif min_date == max_date:  
        cols = ['Rank', 'Player', 'Score', 'Points']
        query = f"""
            SELECT 
                game_rank,
                player_name,
                game_score,
                points
            FROM game_view
            WHERE guild_id = %s
            AND game_date BETWEEN %s AND %s
            AND game_name = %s
            ORDER BY case when game_rank is null then 1 else 0 end, game_rank;
        """
        query_params.append(game_name)

    # specific game: date range
    else:  
        cols = ['Rank', 'Player', 'Points', '1st', '2nd', '3rd', '4th', '5th', 'Played', 'Avg']
        query = f"""
            SELECT
                dense_rank() over(order by points desc) as overall_rank,
                x.player_name,
                x.points,
                x.wins,
                x.rank2,
                x.rank3,
                x.rank4,
                x.rank5,
                x.games_played,
                x.avg_time
            FROM
                    (
                    SELECT 
                        game_name,
                        player_name,
                        sum(points) as points,
                        sum(case when game_rank = 1 then 1 else 0 end) as wins,
                        sum(case when game_rank = 2 then 1 else 0 end) as rank2,
                        sum(case when game_rank = 3 then 1 else 0 end) as rank3,
                        sum(case when game_rank = 4 then 1 else 0 end) as rank4,
                        sum(case when game_rank = 5 then 1 else 0 end) as rank5,
                        sum(case when game_rank <= 3 then 1 else 0 end) as top_3,
                        sum(case when game_rank <= 5 then 1 else 0 end) as top_5,
                        sum(1) as games_played,
                        round(avg(seconds), 1) as avg_time
                    FROM game_view
                    WHERE guild_id = %s
                    AND game_date BETWEEN %s AND %s
                    AND game_name = %s
                    GROUP BY 1,2
                    ) x
        """
        query_params.append(game_name)

    # Convert the list to a tuple
    params_tuple = tuple(query_params)

    return cols, query, params_tuple
