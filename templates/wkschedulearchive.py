<!DOCTYPE html>
<html>
<head>
    <title>Week Schedule</title>
    <style>
        /* Basic styles for the menu */
        .menu {
            background-color: #333;
            overflow: hidden;
        }

        .menu a {
            float: left;
            display: block;
            color: white;
            text-align: center;
            padding: 14px 16px;
            text-decoration: none;
        }

        .menu a:hover {
            background-color: #ddd;
            color: black;
        }

        /* Styles for individual match/tourney tables */
        .event-table {
            border-collapse: collapse;
            /*width: 50%;  Adjust as needed */
            margin-bottom: 20px; /* Space between tables */
        }

        .event-table th:first-child,
        .event-table td:first-child {
            border: 1px solid black;
            padding: 8px;
            text-align: left;
            width: 300px;
        }

        .event-table th:not(:first-child),
        .event-table td:not(:first-child) {
            border: 1px solid black;
            padding: 8px;
            text-align: left;
            width: 80px;
        }

        .event-table th {
            background-color: #f2f2f2;
        }
        /* Style for the week selection dropdown */
        #week-selector {
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="menu">
        <a href="/">Home</a>
        <a href="/wkschedule">Week Schedule</a>
    </div>

    <h1>All Matches/Tournaments</h1>

    <div id="week-selector">
        <label for="week">Select Week:</label>
        <select id="week" name="week" onchange="window.location.href = '/wkschedule?week=' + this.value;">
            <option value="">All Weeks</option>
            {% for week in [1,1.5,2,2.5,3,4,5,6,7,8,9,10,11,12,13,14,15,16]%}
            <option value="{{ week }}" {% if selected_week == week %}selected{% endif %}>Week {{ week }}</option>
            {% endfor %}
        </select>
    </div>
    
    {% for event in events %}
    <table class="event-table" data-game-index = "0" data-mode="hidden">
        <thead>
            <tr>
                <th>
                    <button class="toggle-scores" onclick="toggleScores(this)">
                        Show Scores
                    </button>
                    <button class="next-game" onclick="nextGame(this)">
                        Next Game
                    </button>
                    <button class="reset-game" onclick="resetGame(this)" style="display: none;">
                        Reset
                    </button>
                </th>
                <th class="score-column final-score" style="display: none;">Sets</th>
                {% for set in event.set_results %}
                <th class="score-column final-score set-header-{{ loop.index0 }}" style="display: none;">S{{ loop.index }}</th>
                {% endfor %}
                <!-- Progressive headers -->
                <th class="score-column progressive set-header-prog" style="display: none;">Sets</th>
                {% for set in event.set_results %}
                <th class="score-column progressive set-header-prog-{{ loop.index0 }}" style="display: none;">D{{ loop.index }}</th>
                {% endfor %}
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>{{ event.team1.team_name }}</td>
                <td class="score-column final-score set-score-final " style="display: none;">{{ event.match_score[0] }}</td>
                {% for set in event.set_results %}
                <td class="score-column final-score set-cell-{{ loop.index0 }}" style="display: none;">{{ set[0] }}</td>
                {% endfor %}
                <!-- Progressive game scores -->
                <td class="score-column progressive set-score-prog" style="display: none;">0</td>
                {% for set in event.set_results %}
                <td class="score-column progressive game-score set-cell-prog-{{ loop.index0 }}" data-set="{{ loop.index0 }}" style="display: none;">0</td>
                {% endfor %}
            </tr>
            <tr>
                <td>{{ event.team2.team_name }}</td>
                <td class="score-column final-score set-score-final" style="display: none;">{{ event.match_score[1] }}</td>
                {% for set in event.set_results %}
                <td class="score-column final-score set-cell-{{ loop.index0 }}" style="display: none;">{{ set[1] }}</td>
                {% endfor %}
                <!-- Progressive game scores -->
                <td class="score-column progressive set-score-prog" style="display: none;">0</td>
                {% for set in event.set_results %}
                <td class="score-column progressive game-score set-cell-prog-{{ loop.index0 }}" data-set="{{ loop.index0 }}" style="display: none;">0</td>
                {% endfor %}
            </tr>
        </tbody>
    </table>

    <!-- Store the game sequence data -->
    <script>
        if (typeof gameData === 'undefined') {
            var gameData = {};
        }
        gameData['event_{{ loop.index }}'] = {
            gameWinners: [
                {% for game in event.games %}
                    {{ game.winner }}{% if not loop.last %},{% endif %}
                {% endfor %}
            ],
            setResults: {{ event.set_results | tojson }}
        };
    </script>
    {% endfor %}

    <script>
    function toggleScores(button) {
        const table = button.closest('table');
        const mode = table.dataset.mode;
        
        if (mode === 'hidden') {
            // Show final scores
            const finalScores = table.querySelectorAll('.final-score');
            finalScores.forEach(col => {
                col.style.display = '';
            });
            table.dataset.mode = 'final';
            button.textContent = 'Hide Scores';
        } else if (mode === 'final') {
            // Hide final scores
            const finalScores = table.querySelectorAll('.final-score');
            finalScores.forEach(col => {
                col.style.display = 'none';
            });
            table.dataset.mode = 'hidden';
            button.textContent = 'Show Scores';
        } else if (mode === 'progressive') {
            // Already in progressive mode, just hide everything and reset
            const progressiveScores = table.querySelectorAll('.progressive');
            progressiveScores.forEach(col => {
                col.style.display = 'none';
            });
            table.dataset.mode = 'hidden';
            button.textContent = 'Show Scores';
            
            // Hide reset button
            table.querySelector('.reset-game').style.display = 'none';
        }
    }


    function nextGame(button) {
        const table = button.closest('table');
        const mode = table.dataset.mode;
        const eventIndex = Array.from(table.parentElement.children).filter(el => el.tagName === 'TABLE').indexOf(table) + 1;
        const data = gameData['event_' + eventIndex];
        
        // If in final mode, switch to progressive mode
        if (mode === 'final') {
            const finalScores = table.querySelectorAll('.final-score');
            finalScores.forEach(col => {
                col.style.display = 'none';
            });
        }
        
        // Switch to progressive mode and show reset button
        if (mode !== 'progressive') {
            table.dataset.mode = 'progressive';
            table.querySelector('.reset-game').style.display = 'inline-block';
            
            // Show the Sets header and column, and first set header and column
            const progressiveHeaders = table.querySelectorAll('.set-header-prog, .set-header-prog-0');
            const progressiveScores = table.querySelectorAll('.set-score-prog, .set-cell-prog-0');
            progressiveHeaders.forEach(col => {
                col.style.display = '';
            });
            progressiveScores.forEach(col => {
                col.style.display = '';
            });
            
            // Update toggle button text
            const toggleBtn = table.querySelector('.toggle-scores');
            toggleBtn.textContent = 'Hide Scores';
        }
        
        let currentGame = parseInt(table.dataset.gameIndex);
        
        if (currentGame >= data.gameWinners.length) {
            return; // No more games
        }
        
        // Get the winner of this game (1 = team1, 2 = team2)
        const winner = data.gameWinners[currentGame];
        
        // Find current set by replaying all games up to current
        let currentSet = 0;
        let team1Games = 0;
        let team2Games = 0;
        let setJustCompleted = false;
        
        for (let i = 0; i <= currentGame; i++) {
            if (data.gameWinners[i] === 1) {
                team1Games++;
            } else {
                team2Games++;
            }
            
            // Check if set is complete (someone reached 4 games)
            if (team1Games === 4 || team2Games === 4) {
                if (i === currentGame) {
                    // We just completed this set on this game
                    setJustCompleted = true;
                }
                if (i < currentGame) {
                    currentSet++;
                    team1Games = 0;
                    team2Games = 0;
                }
            }
        }
        
        // If we just completed a set, show the next set column and header, and reset to 0-0
        if (setJustCompleted && currentSet < data.setResults.length - 1) {
            const nextSet = currentSet + 1;
            const nextSetHeaders = table.querySelectorAll(`.set-header-prog-${nextSet}`);
            const nextSetCells = table.querySelectorAll(`.set-cell-prog-${nextSet}`);
            nextSetHeaders.forEach(cell => {
                cell.style.display = '';
            });
            nextSetCells.forEach(cell => {
                cell.style.display = '';
                cell.textContent = '0';  // Start new set at 0-0
            });
        }
            
        // Update game scores for current set
        const gameScoreCells = table.querySelectorAll('.game-score');
        const numSets = data.setResults.length;
        const team1GameCell = gameScoreCells[currentSet];
        const team2GameCell = gameScoreCells[currentSet + numSets];
        
        if (team1GameCell && team2GameCell) {
            team1GameCell.textContent = team1Games;
            team2GameCell.textContent = team2Games;
        }
        
        // Update set scores
        const setScoreCells = table.querySelectorAll('.set-score-prog');
        let team1Sets = 0;
        let team2Sets = 0;
        
        // Count completed sets
        for (let s = 0; s < currentSet; s++) {
            if (data.setResults[s][0] > data.setResults[s][1]) {
                team1Sets++;
            } else {
                team2Sets++;
            }
        }
        
        // Check if current set is complete
        if (team1Games === 4) {
            team1Sets++;
        } else if (team2Games === 4) {
            team2Sets++;
        }
        
        setScoreCells[0].textContent = team1Sets;
        setScoreCells[1].textContent = team2Sets;
        
        // Increment game index
        table.dataset.gameIndex = currentGame + 1;
        
        // Disable button if match is complete
        if (team1Sets === 3 || team2Sets === 3 || currentGame + 1 >= data.gameWinners.length) {
            button.disabled = true;
            button.textContent = 'Match Complete';
        }
    }



    function resetGame(button) {
        const table = button.closest('table');
        
        // Hide all progressive scores
        const progressiveScores = table.querySelectorAll('.progressive');
        progressiveScores.forEach(col => {
            col.style.display = 'none';
        });
        
        // Reset game index
        table.dataset.gameIndex = 0;
        
        // Reset all game scores to 0
        const gameScoreCells = table.querySelectorAll('.game-score');
        const setScoreCells = table.querySelectorAll('.set-score-prog');
        
        gameScoreCells.forEach(cell => cell.textContent = '0');
        setScoreCells.forEach(cell => cell.textContent = '0');
        
        // Re-enable next game button
        const nextButton = table.querySelector('.next-game');
        nextButton.disabled = false;
        nextButton.textContent = 'Next Game';
        
        // Hide reset button and switch back to hidden mode
        button.style.display = 'none';
        table.dataset.mode = 'hidden';
        
        // Update toggle button
        const toggleBtn = table.querySelector('.toggle-scores');
        toggleBtn.textContent = 'Show Scores';
    }
   
    </script>

    <style>
    .toggle-scores, .next_game, .reset-game {
        padding: 5px 10px;
        margin: 2px;
        cursor: pointer;
        border: 1px solid #ccc;
        border-radius: 3px;
        background-color: #f0f0f0;
        font-size: 12px;
    }

    .toggle-scores:hover, .next-game:hover, .reset-game:hover {
        background-color: #e0e0e0;
    }

    .next-game:disabled {
        background-color: #ddd;
        cursor: not-allowed;
    </style>


</body>
</html>
