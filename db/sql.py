import sqlite3

db = "game.db"

def init_db():
    # Create the Tribes table
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Tribes (
        d_role_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        d_channel_id INTEGER
    )
    """)

    # Create the Players table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Players (
        d_role_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        real_name TEXT NOT NULL,
        d_channel_id INTEGER,
        tribe_id INTEGER,
        status TEXT,
        placement INTEGER,
        FOREIGN KEY (tribe_id) REFERENCES Tribes(d_role_id)
    )
    """)

    # Commit changes and close the connection
    conn.commit()
    conn.close()


def add_swap():
    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    # Enable foreign key constraint (if Tribes exists and linked)
    cursor.execute("PRAGMA foreign_keys = ON")
    tribes = [
            (1488702476466000093, "NuDiamonds", 1488703576183144551),
            (1488702838166130698, "NuHearts", 1488703656625705070),
            (1488703028243599391, "NuSpades", 1488703750393823262),
    ]

    # Insert the tribe data
    cursor.executemany("""
    INSERT OR IGNORE INTO Tribes (d_role_id, name, d_channel_id)
    VALUES (?, ?, ?)
    """, tribes)
    conn.commit()
    conn.close()


def populate_db():
    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    # Enable foreign key constraint (if Tribes exists and linked)
    cursor.execute("PRAGMA foreign_keys = ON")
    tribes = [
            (0, "None", 0),
            (1481023085061738639, "Clubs", 1481029249996423288),
            (1481023533902467204, "Diamonds", 1481029340996046999),
            (1481023695555268710, "Hearts", 1481029385527234673),
            (1481023869878927441, "Spades", 1481029432226353152),
    ]

    # Insert the tribe data
    cursor.executemany("""
    INSERT OR IGNORE INTO Tribes (d_role_id, name, d_channel_id)
    VALUES (?, ?, ?)
    """, tribes)

    players = [
            (1485771157704544436, "Chimera", "Alma", 1481057037088723117, 1481023085061738639, "CONTESTANT", 0),
            (1485772452557619240, "Dove", "Janessa", 1481057268912095243, 1481023085061738639, "CONTESTANT", 0),
            (1485771162624593920, "Goblin Shark", "Dionne", 1481057522042404938, 1481023085061738639, "CONTESTANT", 0),
            (1485771165141303357, "Kitsune", "Emerald", 1481057617068687430, 1481023085061738639, "CONTESTANT", 0),
            (1485771171327639633, "Stallion", "Indira", 1481058148373762211, 0, "PRE-JURY", 23),
            (1485771160317857885, "Dodo", "Calahan", 1481057236821213244, 1481023533902467204, "CONTESTANT", 0),
            (1485771162012225577, "Gecko", "Yuko", 1481057370468782301, 1481023533902467204, "CONTESTANT", 0),
            (1485771164344127761, "Jackalope", "Zephyra", 1481057567630426273, 1481023533902467204, "CONTESTANT", 0),
            (1485771169209647176, "Porcupine", "Svetlana", 1481057956832350489, 1481023533902467204, "CONTESTANT", 0),
            (1485771170165948437, "Sphinx", "Electra", 1481058081185075231, 0, "PRE-JURY", 22),
            (1485771158274969753, "Cygnus", "Avril", 1481057119171121152, 1481023695555268710, "CONTESTANT", 0),
            (1485771165799813302, "Lynx", "Sharai", 1481057672668119111, 1481023695555268710, "CONTESTANT", 0),
            (1485771168299487264, "Polar Bear", "Sharlene", 1481057898875326534, 1481023695555268710, "CONTESTANT", 0),
            (1485771172149858395, "Swallow", "Kalani", 1481058206733045942, 1481023695555268710, "CONTESTANT", 0),
            (1485771173349298227, "Tarsier", "Cicero", 1481058239226314823, 1481023695555268710, "CONTESTANT", 0),
            (1485771160842141858, "Fennec Fox", "Ivory", 1481057334804480011, 0, "PRE-JURY", 21),
            (1485771167246848240, "Owl", "Constance", 1481057773813760161, 1481023869878927441, "CONTESTANT", 0),
            (1485771169868156928, "Satyr", "Pierre", 1481058007742812223, 1481023869878927441, "CONTESTANT", 0),
            (1485771174096142377, "Whiptail", "Purna", 1481058302065639505, 1481023869878927441, "CONTESTANT", 0),
            (1485771174695665706, "Wolf", "Himari", 1481058344667058257, 1481023869878927441, "CONTESTANT", 0),
            (1485771159042658477, "Dik Dik", "Vaughn", 1481057200502997002, 1481023085061738639, "CONTESTANT", 0),
            (1485771166323970201, "Meerkat", "Odette", 1481057713734549566, 1481023533902467204, "CONTESTANT", 0),
            (1485771168068800572, "Pegasus", "Midori", 1481057855581978777, 1481023869878927441, "CONTESTANT", 0)
        ]

    # Insert all rows
    cursor.executemany("""
    INSERT INTO Players (d_role_id, name, real_name, d_channel_id, tribe_id, status, placement)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, players)



    # Commit and close
    conn.commit()
    conn.close()


def update_player(d_role_id, name, real_name, d_channel_id, tribe_id, status, placement):
    conn = sqlite3.connect("db/" + db)
    cursor = conn.cursor()
    cursor.execute("UPDATE Players SET name = ?, real_name = ?, d_channel_id = ?, tribe_id = ?, status = ?, placement = ? WHERE d_role_id = ?", (name, real_name, d_channel_id, tribe_id, status, placement, d_role_id))
    conn.commit()

def update_tribe(d_role_id, name, d_channel_id):
    conn = sqlite3.connect("db/" + db)
    cursor = conn.cursor()
    cursor.execute("UPDATE Tribes SET name = ?, d_channel_id = ? WHERE d_role_id = ?", (name, d_channel_id, d_role_id))
    conn.commit()



class Tribe:
    def __init__(self, d_role_id, name, d_channel_id):
        self.name = name
        self.d_role_id = d_role_id
        self.d_channel_id = d_channel_id
        self.players = []

class Player:
    def __init__(self, d_role_id, name, real_name, d_channel_id, tribe_id, status, placement):
        self.name = name
        self.real_name = real_name
        self.d_role_id = d_role_id
        self.d_channel_id = d_channel_id
        self.tribe_id = tribe_id
        self.status = status
        self.placement = placement
        self.tribe = None

def get_tribes_empty():
    _tribes = []
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT d_role_id, name, d_channel_id FROM Tribes;")
    tribes = [dict(row) for row in cursor.fetchall()]
    filtered_tribes = [t for t in tribes if t['d_role_id'] != 0]
    for t in filtered_tribes:
        tribe = Tribe(t['d_role_id'], t['name'], t['d_channel_id'])
        _tribes.append(tribe)
        #print(tribe.name)
    conn.close()
    return _tribes


def get_players(tribes):
    #tribes = get_tribes()
    _players = []
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    #cursor.execute("SELECT d_role_id, name, tribe_id FROM Players;")
    cursor.execute("SELECT * FROM Players;")
    players = [dict(row) for row in cursor.fetchall()]
    for p in players:
        player = Player(p['d_role_id'], p['name'], p['real_name'], p['d_channel_id'], p['tribe_id'], p['status'], p['placement'])
        tribe_id = p['tribe_id']
        for t in tribes:
            print(f"checking {t.d_role_id} == {tribe_id}")
            if int(t.d_role_id) == int(tribe_id):
                player.tribe = t
                print(player.name + player.tribe.name)
        _players.append(player)
    conn.close()
    return _players

def get_tribes(tribes=None, players=None):
    if not tribes or not players:
        tribes = get_tribes_empty()
        players = get_players(tribes)
    for p in players:
        for t in tribes:
            if p.tribe == t:
                t.players.append(p)
    return tribes



def main():
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("UPDATE Players SET tribe_id = 0;")
    conn.commit()

if __name__ == '__main__':
    main()
