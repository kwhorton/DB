#!/usr/bin/env python3
"""
Add new players (IDs ending in '33') to player_db.pkl
Generates names for them using Names.xlsx
"""

import pandas as pd
import random
import pickle
import sys
from pathlib import Path


class PlayerDB:
    """
    PlayerDB class definition
    """
    def __init__(self, player_id, name, yeargroup):
        self.player_id = player_id
        self.name = name
        self.yeargroup = yeargroup
        self.seasons = []
        self.stats = []


class NameGenerator:
    """Class to generate unique random names"""
    
    def __init__(self, names_file='Names.xlsx'):
        """Load name data from Excel file"""
        print(f"Loading name data from {names_file}...")
        self.last_names = pd.read_excel(names_file, sheet_name="Sheet1")
        self.first_names_m = pd.read_excel(names_file, sheet_name="Sheet2")
        self.first_names_f = pd.read_excel(names_file, sheet_name="Sheet3")
        print("✓ Name data loaded successfully")
    
    def generate(self):
        """Generate a random name"""
        # Select last name
        ln = random.choices(self.last_names['Name'], weights=self.last_names['Prob'])[0]
        
        # Select first name (75% male, 25% female)
        if random.random() < 0.75:
            fn = random.choices(self.first_names_m['Name'], weights=self.first_names_m['Prob'])[0]
        else:
            fn = random.choices(self.first_names_f['Name'], weights=self.first_names_f['Prob'])[0]
        
        # Return in uppercase format
        return f"{fn} {ln}".upper()
    
    def generate_unique(self, existing_names, max_attempts=100):
        """Generate a unique name not in existing_names set"""
        for attempt in range(max_attempts):
            name = self.generate()
            if name not in existing_names:
                return name
        
        # If we can't find unique name, add a number
        base_name = self.generate()
        counter = 1
        while f"{base_name} {counter}" in existing_names:
            counter += 1
        return f"{base_name} {counter}"


def add_new_players(roster_file='roster2033.csv', 
                    playerdb_file='player_db.pkl',
                    names_file='Names.xlsx',
                    default_yeargroup=2033,
                    dry_run=False):
    """
    Add new players from roster CSV to player_db.pkl
    
    Args:
        roster_file: CSV file with all players (including new ones)
        playerdb_file: Existing player database pickle file
        names_file: Excel file with name data
        default_yeargroup: Yeargroup to assign to new players
        dry_run: If True, preview changes without saving
    """
    
    print("=" * 70)
    print("Adding New Players to Database")
    print("=" * 70)
    
    if dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be saved\n")
    
    # Load existing player database
    print(f"\n1. Loading existing player database: {playerdb_file}")
    try:
        with open(playerdb_file, 'rb') as f:
            playerdb = pickle.load(f)
        print(f"   ✓ Loaded {len(playerdb)} existing players")
    except FileNotFoundError:
        print(f"   ⚠️  File not found - will create new database")
        playerdb = []
    
    # Create set of existing player IDs
    existing_ids = {player.player_id for player in playerdb}
    print(f"   ✓ Existing player IDs: {len(existing_ids)}")
    
    # Load roster CSV
    print(f"\n2. Loading roster from: {roster_file}")
    try:
        roster_df = pd.read_csv(roster_file)
        print(f"   ✓ Loaded {len(roster_df)} players from roster")
    except FileNotFoundError:
        print(f"   ✗ Error: Roster file not found: {roster_file}")
        return False
    
    # Find new players (IDs ending in '33' that aren't in database)
    print("\n3. Identifying new players...")
    
    # Get all player IDs from roster
    if 'Name' in roster_df.columns:
        # Player IDs are in the 'Name' column
        roster_ids = set(roster_df['Name'].astype(str))
    elif 'PlayerID' in roster_df.columns:
        roster_ids = set(roster_df['PlayerID'].astype(str))
    else:
        print(f"   ✗ Error: Could not find player ID column")
        print(f"   Available columns: {', '.join(roster_df.columns)}")
        return False
    
    # Find IDs ending in '33' that aren't in the database
    new_player_ids = [pid for pid in roster_ids 
                      if pid.endswith('33') and pid not in existing_ids]
    
    if not new_player_ids:
        print("   ✓ No new players to add - all players already in database!")
        return True
    
    print(f"   ✓ Found {len(new_player_ids)} new players to add:")
    for pid in sorted(new_player_ids)[:10]:
        print(f"      - {pid}")
    if len(new_player_ids) > 10:
        print(f"      ... and {len(new_player_ids) - 10} more")
    
    # Collect existing names to avoid duplicates
    print("\n4. Collecting existing names...")
    existing_names = set()
    for player in playerdb:
        if player.name and not player.name.startswith('Unknown'):
            existing_names.add(player.name.upper())
    print(f"   ✓ Found {len(existing_names)} existing names")
    
    # Generate names for new players
    print(f"\n5. Generating names for new players...")
    name_gen = NameGenerator(names_file)
    
    new_players = []
    for player_id in sorted(new_player_ids):
        # Generate unique name
        name = name_gen.generate_unique(existing_names)
        existing_names.add(name)
        
        # Create PlayerDB object
        player = PlayerDB(
            player_id=player_id,
            name=name,
            yeargroup=default_yeargroup
        )
        
        new_players.append(player)
        print(f"   ✓ {player_id} → {name}")
    
    # Show summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Existing players in database: {len(playerdb)}")
    print(f"New players to add:           {len(new_players)}")
    print(f"Total after update:           {len(playerdb) + len(new_players)}")
    
    # Save updated database
    if not dry_run:
        print("\n6. Saving updated database...")
        
        # Create backup
        backup_file = str(playerdb_file) + '.backup'
        if Path(playerdb_file).exists():
            print(f"   Creating backup: {backup_file}")
            with open(backup_file, 'wb') as f_out:
                with open(playerdb_file, 'rb') as f_in:
                    f_out.write(f_in.read())
        
        # Add new players
        playerdb.extend(new_players)
        
        # Save
        print(f"   Saving to: {playerdb_file}")
        with open(playerdb_file, 'wb') as f:
            pickle.dump(playerdb, f)
        
        print(f"   ✓ Successfully saved {len(playerdb)} players")
        
        print("\n" + "=" * 70)
        print("✓ COMPLETE!")
        print("=" * 70)
        print(f"\nAdded {len(new_players)} new players to {playerdb_file}")
        if Path(backup_file).exists():
            print(f"Backup saved to: {backup_file}")
    else:
        print("\n" + "=" * 70)
        print("✓ DRY RUN COMPLETE - No changes saved")
        print("=" * 70)
        print(f"\nWould add {len(new_players)} new players to {playerdb_file}")
        print("Run without --dry-run to apply changes")
    
    return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Add new players (IDs ending in "33") to player_db.pkl',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview changes (dry run)
  python add_new_players_to_db.py --dry-run
  
  # Add new players
  python add_new_players_to_db.py
  
  # Specify custom files
  python add_new_players_to_db.py --roster roster2034.csv --db player_db_2034.pkl
  
  # Specify yeargroup
  python add_new_players_to_db.py --yeargroup 2034
        """
    )
    
    parser.add_argument('--roster', default='roster2033.csv',
                       help='Roster CSV file (default: roster2033.csv)')
    parser.add_argument('--db', default='player_db.pkl',
                       help='Player database pickle file (default: player_db.pkl)')
    parser.add_argument('--names', default='Names.xlsx',
                       help='Names Excel file (default: Names.xlsx)')
    parser.add_argument('--yeargroup', type=int, default=2033,
                       help='Yeargroup for new players (default: 2033)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview changes without saving')
    
    args = parser.parse_args()
    
    # Check if required files exist
    if not Path(args.roster).exists():
        print(f"Error: Roster file not found: {args.roster}")
        sys.exit(1)
    
    if not Path(args.names).exists():
        print(f"Error: Names file not found: {args.names}")
        sys.exit(1)
    
    # Run the update
    try:
        success = add_new_players(
            roster_file=args.roster,
            playerdb_file=args.db,
            names_file=args.names,
            default_yeargroup=args.yeargroup,
            dry_run=args.dry_run
        )
        
        if not success:
            sys.exit(1)
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
