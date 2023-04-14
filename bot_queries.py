def build_query(guild_id, game_name, min_date, max_date, user_nm=None):
    
    guild_condition = "guild_id = :guild_id"
    date_condition = "game_date BETWEEN :min_date AND :max_date"
    game_condition = "game_name = :game_name"
    user_condition = "discord_id = :user_nm"

    # all games: winners only
    if game_name == 'winners':
        cols = ['game', 'date', 'winner', 'score']
        query = f"""
            SELECT 
                game_name,
                game_date,
                player_name,
                game_score
            FROM game_view
            WHERE {guild_condition}
            AND {date_condition}
            and game_rank = 1
            ORDER BY game_name, game_date desc;
        """
    
    # all games: single user, single date ## technically this will run with multiple dates FIX IT
    elif game_name == 'my_scores':
        cols = ['game', 'player', 'score', 'rank']
        query = f"""
            SELECT 
                game_name,
                player_name,
                game_score,
                game_rank
            FROM game_view
            WHERE {guild_condition}
            AND {date_condition}
            AND {user_condition}
            ORDER BY game_name, game_date desc;
        """
    
    # specific game: single date
    elif min_date == max_date:  
        cols = ['rank', 'player', 'score', 'points']
        query = f"""
            SELECT 
                game_rank,
                player_name,
                game_score,
                points
            FROM game_view
            WHERE {guild_condition}
            AND {date_condition}
            AND {game_condition}
            ORDER BY game_rank;
        """

    # specific game: date range
    else:  
        cols = ['rank', 'player', 'points']
        query = f"""
        SELECT
            DENSE_RANK() OVER(ORDER BY X.points DESC) as game_rank,
            X.*
        FROM
                (
                SELECT 
                    player_name,
                    sum(points) as points
                FROM game_view
                WHERE {guild_condition}
                AND {date_condition}
                AND {game_condition}
                GROUP BY 1
                ) X
        """

    return cols, query
