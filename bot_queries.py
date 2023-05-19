def build_query(guild_id, game_name, min_date, max_date, user_nm=None):
    
    guild_condition = "guild_id = :guild_id"
    date_condition = "game_date BETWEEN :min_date AND :max_date"
    game_condition = "game_name = :game_name"
    user_condition = "member_nm = :user_nm"

    # check for date range first
    # has_date_range = (min_date != max_date)

    # all games, winners only, single date
    if game_name == 'winners' and min_date == max_date:
        cols = ['Game', 'Winner', 'Score']
        query = f"""
            SELECT 
                game_name,
                player_name,
                game_score
            FROM game_view
            WHERE {guild_condition}
            AND {date_condition}
            and game_rank = 1
            ORDER BY 
                case    when game_name = 'mini'      then 1
                        when game_name = 'boxoffice' then 2
                        when game_name = 'worldle'   then 3
                        when game_name = 'wordle'    then 4
                        when game_name = 'factle'    then 5
                        else 9
                end asc, game_date desc;
        """
    
    # all games, winners only, range of dates
    elif game_name == 'winners' and min_date != max_date:
        cols = ['Game', 'Leader', 'Points', 'Wins', 'Top 3', 'Top 5', 'Played']
        query = f"""
            SELECT 
	            game_name,
                player_name,
                points,
                wins,
                top_3,
                top_5,
                participation
            FROM
                    (
                    SELECT
                        x.game_name,
                        dense_rank() over(partition by game_name order by points desc) as overall_rank,
                        x.player_name,
                        x.points,
                        x.wins,
                        CONCAT(ROUND(x.top_3 * 100), '%') as top_3,
                        CONCAT(ROUND(x.top_5 * 100), '%') as top_5,
                        max(x.games_played) over(partition by x.game_name) as total_games,
                        CONCAT(ROUND((x.games_played / max(x.games_played) over(partition by x.game_name)) * 100), '%') as participation
                    FROM
                            (
                            SELECT 
                                game_name,
                                player_name,
                                sum(points) as points,
                                sum(case when game_rank = 1 then 1 else 0 end) as wins,
                                sum(case when game_rank <= 3 then 1 else 0 end) / sum(1.0) as top_3,
                                sum(case when game_rank <= 5 then 1 else 0 end) / sum(1.0) as top_5,
                                sum(1) as games_played
                            FROM game_view
                            WHERE {guild_condition}
                            AND {date_condition}
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
            WHERE {guild_condition}
            AND {date_condition}
            AND {user_condition}
            ORDER BY 
                case    when game_name = 'mini'      then 1
                        when game_name = 'boxoffice' then 2
                        when game_name = 'worldle'   then 3
                        when game_name = 'wordle'    then 4
                        when game_name = 'factle'    then 5
                        else 9
                end asc, game_date desc;
        """
    
    # specific game: single date
    elif min_date == max_date:  
        cols = ['Rank', 'Player', 'Score', 'Points']
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
        cols = ['Rank', 'Player', 'Points', 'Wins', 'Top 3', 'Top 5', 'Played']
        query = f"""
            SELECT
                dense_rank() over(order by points desc) as overall_rank,
                x.player_name,
                x.points,
                x.wins,
                CONCAT(ROUND(x.top_3 * 100), '%') as top_3,
                CONCAT(ROUND(x.top_5 * 100), '%') as top_5,
                CONCAT(ROUND((x.games_played / max(x.games_played) over()) * 100), '%') as participation
            FROM
                    (
                    SELECT 
                        game_name,
                        player_name,
                        sum(points) as points,
                        sum(case when game_rank = 1 then 1 else 0 end) as wins,
                        sum(case when game_rank <= 3 then 1 else 0 end) / sum(1.0) as top_3,
                        sum(case when game_rank <= 5 then 1 else 0 end) / sum(1.0) as top_5,
                        sum(1) as games_played
                    FROM game_view
                    WHERE {guild_condition}
                    AND {date_condition}
                    AND {game_condition}
                    GROUP BY 1,2
                    ) x
        """

    return cols, query
